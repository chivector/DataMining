from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path
from typing import Iterable, Sequence

import pandas as pd

from .io_utils import project_path
from .providers import ModelProvider


EXPERIMENT_ID = "wheelchair_turning_multistrategy_v1"

DEFAULT_PROMPT_SOURCES: tuple[tuple[str, Path], ...] = (
    ("baseline", project_path("data", "prompts.csv")),
    (
        "real_world_archetype_matrix",
        project_path("data", "prompts_real_world_archetype_matrix.csv"),
    ),
    ("halton_space_filling", project_path("data", "prompts_halton_space_filling.csv")),
    (
        "dimensionless_ratio_design",
        project_path("data", "prompts_dimensionless_ratio_design.csv"),
    ),
    (
        "constraint_boundary_solver",
        project_path("data", "prompts_constraint_boundary_solver.csv"),
    ),
)

REQUIRED_PROMPT_COLUMNS: tuple[str, ...] = (
    "prompt_id",
    "case_id",
    "level",
    "noise_label",
    "noise_text",
    "stair_width_cm",
    "landing_depth_cm",
    "wheelchair_width_cm",
    "wheelchair_length_cm",
    "turn_radius_cm",
    "clearance_margin_cm",
    "criticality",
    "reference_judgment",
    "prompt",
)

RESPONSE_KEY_COLUMNS: tuple[str, ...] = ("provider", "model", "repeat", "prompt_uid")


def parse_prompt_sources(source_args: Sequence[str] | None = None) -> list[tuple[str, Path]]:
    """Parse CLI source specs in ``strategy=path`` form.

    With no explicit sources, return the curated experiment subset chosen for
    the first real run.
    """
    if not source_args:
        return list(DEFAULT_PROMPT_SOURCES)

    sources: list[tuple[str, Path]] = []
    for item in source_args:
        if "=" not in item:
            raise ValueError(f"Invalid source spec {item!r}; expected strategy=path")
        strategy, path = item.split("=", 1)
        strategy = strategy.strip()
        if not strategy:
            raise ValueError(f"Invalid source spec {item!r}; strategy is empty")
        sources.append((strategy, Path(path.strip())))
    return sources


def build_experiment_prompts(
    sources: Iterable[tuple[str, Path]] | None = None,
    experiment_id: str = EXPERIMENT_ID,
) -> pd.DataFrame:
    """Combine selected prompt CSVs into one long experiment prompt table."""
    frames: list[pd.DataFrame] = []
    for strategy, path in sources or DEFAULT_PROMPT_SOURCES:
        if not path.exists():
            raise FileNotFoundError(f"Prompt source not found for {strategy}: {path}")
        prompts = pd.read_csv(path)
        missing = [col for col in REQUIRED_PROMPT_COLUMNS if col not in prompts.columns]
        if missing:
            raise ValueError(f"{path} is missing required columns: {missing}")

        prompts = prompts.copy()
        prompts = prompts.drop(
            columns=[c for c in ("strategy", "experiment_id", "prompt_uid") if c in prompts.columns]
        )
        if prompts["prompt_id"].astype(str).duplicated().any():
            dupes = prompts.loc[prompts["prompt_id"].astype(str).duplicated(), "prompt_id"].head(5).tolist()
            raise ValueError(f"{path} has duplicate prompt_id values within strategy {strategy}: {dupes}")

        prompts.insert(0, "strategy", strategy)
        prompts.insert(1, "experiment_id", experiment_id)
        prompts.insert(2, "prompt_uid", strategy + "__" + prompts["prompt_id"].astype(str))
        frames.append(prompts)

    if not frames:
        return pd.DataFrame(columns=["strategy", "experiment_id", "prompt_uid", *REQUIRED_PROMPT_COLUMNS])

    combined = pd.concat(frames, ignore_index=True)
    if combined["prompt_uid"].duplicated().any():
        dupes = combined.loc[combined["prompt_uid"].duplicated(), "prompt_uid"].head(5).tolist()
        raise ValueError(f"Combined experiment prompts contain duplicate prompt_uid values: {dupes}")
    return combined


def response_key_set(existing: pd.DataFrame) -> set[tuple[str, str, int, str]]:
    if existing.empty or not set(RESPONSE_KEY_COLUMNS).issubset(existing.columns):
        return set()
    keys: set[tuple[str, str, int, str]] = set()
    for _, row in existing.iterrows():
        keys.add(
            (
                str(row["provider"]),
                str(row["model"]),
                int(row["repeat"]),
                str(row["prompt_uid"]),
            )
        )
    return keys


def collection_plan(
    prompts: pd.DataFrame,
    provider_name: str,
    models: Sequence[str],
    repeats: int,
    seen: set[tuple[str, str, int, str]] | None = None,
) -> list[tuple[str, int, pd.Series]]:
    if "prompt_uid" not in prompts.columns:
        raise ValueError("Experiment prompts must include prompt_uid")
    seen = seen or set()
    plan: list[tuple[str, int, pd.Series]] = []
    for model in models:
        for repeat in range(repeats):
            for _, prompt_row in prompts.iterrows():
                key = (provider_name, model, repeat, str(prompt_row["prompt_uid"]))
                if key in seen:
                    continue
                plan.append((model, repeat, prompt_row))
    return plan


def provider_runtime_metadata(provider: ModelProvider, repeat: int) -> dict[str, object]:
    seed = getattr(provider, "seed", pd.NA)
    run_seed: object = pd.NA
    if seed is not pd.NA:
        try:
            run_seed = int(seed) + int(repeat)
        except (TypeError, ValueError):
            run_seed = seed
    return {
        "temperature": getattr(provider, "temperature", pd.NA),
        "max_tokens": getattr(provider, "max_tokens", pd.NA),
        "seed": run_seed,
    }


def collect_response_rows(
    prompts: pd.DataFrame,
    provider: ModelProvider,
    provider_name: str,
    models: Sequence[str],
    repeats: int,
    seen: set[tuple[str, str, int, str]] | None = None,
    limit: int | None = None,
    on_error: str = "skip",
    collected_at: str | None = None,
) -> tuple[pd.DataFrame, int]:
    """Collect response rows without writing files.

    Scripts use this for smoke-scale collection; the streaming CLI keeps its own
    periodic write loop for larger real API runs.
    """
    if on_error not in {"skip", "abort"}:
        raise ValueError("on_error must be 'skip' or 'abort'")
    plan = collection_plan(prompts, provider_name, models, repeats, seen)
    if limit is not None:
        plan = plan[:limit]
    collected_at = collected_at or datetime.now().isoformat(timespec="seconds")

    rows: list[dict] = []
    failures = 0
    for model, repeat, prompt_row in plan:
        start = time.perf_counter()
        status = "success"
        error_message = ""
        try:
            response = provider.complete(prompt_row, model=model, repeat=repeat)
        except Exception as exc:  # noqa: BLE001 - provider failures are external
            failures += 1
            status = "failed"
            error_message = str(exc)
            response = ""
            if on_error == "abort":
                elapsed = time.perf_counter() - start
                rows.append(
                    response_record(
                        prompt_row,
                        provider,
                        provider_name,
                        model,
                        repeat,
                        collected_at,
                        response,
                        status,
                        error_message,
                        elapsed,
                    )
                )
                raise
        elapsed = time.perf_counter() - start
        rows.append(
            response_record(
                prompt_row,
                provider,
                provider_name,
                model,
                repeat,
                collected_at,
                response,
                status,
                error_message,
                elapsed,
            )
        )
    return pd.DataFrame(rows), failures


def response_record(
    prompt_row: pd.Series,
    provider: ModelProvider,
    provider_name: str,
    model: str,
    repeat: int,
    collected_at: str,
    response: str,
    status: str,
    error_message: str,
    latency_seconds: float,
) -> dict[str, object]:
    return {
        **prompt_row.to_dict(),
        "provider": provider_name,
        "model": model,
        "repeat": repeat,
        "collected_at": collected_at,
        **provider_runtime_metadata(provider, repeat),
        "status": status,
        "error_message": error_message,
        "latency_seconds": round(float(latency_seconds), 4),
        "response": response,
    }


def mark_api_failures(features: pd.DataFrame) -> pd.DataFrame:
    if "status" not in features.columns:
        return features
    out = features.copy()
    failed = out["status"].astype(str) != "success"
    if failed.any():
        out.loc[failed, "ai_judgment"] = "uncertain"
        out.loc[failed, "is_correct"] = False
        out.loc[failed, "is_uncertain"] = True
        out.loc[failed, "error_category"] = "api_failure"
    return out


def accuracy_by_strategy_level(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby(["strategy", "model", "level"], as_index=False)
        .agg(
            accuracy=("is_correct", "mean"),
            formula_rate=("has_formula", "mean"),
            coordinate_rate=("uses_coordinate", "mean"),
            avg_steps=("reasoning_steps", "mean"),
            samples=("prompt_uid", "count"),
        )
        .sort_values(["strategy", "model", "level"])
    )


def noise_flip_rate_by_strategy(df: pd.DataFrame) -> pd.DataFrame:
    key = ["strategy", "model", "case_id", "level", "repeat"]
    baseline = (
        df[df["noise_label"] == "none"][key + ["ai_judgment"]]
        .rename(columns={"ai_judgment": "baseline_judgment"})
        .copy()
    )
    noisy = df[df["noise_label"] != "none"].merge(baseline, on=key, how="left")
    noisy["flipped"] = noisy["ai_judgment"] != noisy["baseline_judgment"]
    return (
        noisy.groupby(["strategy", "model", "noise_label"], as_index=False)
        .agg(
            flip_rate=("flipped", "mean"),
            noisy_accuracy=("is_correct", "mean"),
            samples=("prompt_uid", "count"),
        )
        .sort_values(["strategy", "model", "flip_rate"], ascending=[True, True, False])
    )


def level_consistency_by_strategy(df: pd.DataFrame) -> pd.DataFrame:
    grouped = df.groupby(["strategy", "model", "case_id", "noise_label", "repeat"])
    rows: list[dict] = []
    for keys, part in grouped:
        strategy, model, case_id, noise_label, repeat = keys
        judgments = part.set_index("level")["ai_judgment"].to_dict()
        if not {"L1", "L2", "L3"}.issubset(judgments):
            continue
        values = [judgments["L1"], judgments["L2"], judgments["L3"]]
        pair_agree = (
            int(values[0] == values[1])
            + int(values[0] == values[2])
            + int(values[1] == values[2])
        ) / 3
        rows.append(
            {
                "strategy": strategy,
                "model": model,
                "case_id": case_id,
                "noise_label": noise_label,
                "repeat": repeat,
                "level_consistency": pair_agree,
                "all_levels_same": len(set(values)) == 1,
            }
        )
    detail = pd.DataFrame(rows)
    if detail.empty:
        return pd.DataFrame(
            columns=["strategy", "model", "noise_label", "level_consistency", "all_levels_same_rate", "groups"]
        )
    return (
        detail.groupby(["strategy", "model", "noise_label"], as_index=False)
        .agg(
            level_consistency=("level_consistency", "mean"),
            all_levels_same_rate=("all_levels_same", "mean"),
            groups=("case_id", "count"),
        )
        .sort_values(["strategy", "model", "noise_label"])
    )


def failure_modes_by_strategy(df: pd.DataFrame) -> pd.DataFrame:
    errors = df[df["error_category"] != "none"].copy()
    if errors.empty:
        return pd.DataFrame(columns=["strategy", "model", "error_category", "count", "share"])
    counts = errors.groupby(["strategy", "model", "error_category"], as_index=False).size()
    totals = counts.groupby(["strategy", "model"])["size"].transform("sum")
    counts["share"] = counts["size"] / totals
    return counts.rename(columns={"size": "count"}).sort_values(
        ["strategy", "model", "count"], ascending=[True, True, False]
    )


def collection_coverage(
    responses: pd.DataFrame,
    prompts: pd.DataFrame,
    models: Sequence[str],
    repeats: int,
    provider_name: str = "df",
) -> pd.DataFrame:
    expected = prompts.groupby("strategy", as_index=False).agg(
        expected_prompts=("prompt_uid", "nunique")
    )
    observed = (
        responses.groupby(["provider", "strategy", "model", "repeat"], as_index=False)
        .agg(
            observed_rows=("prompt_uid", "count"),
            unique_prompts=("prompt_uid", "nunique"),
            success_rows=("status", lambda s: int((s.astype(str) == "success").sum()))
            if "status" in responses.columns
            else ("prompt_uid", "count"),
            failed_rows=("status", lambda s: int((s.astype(str) != "success").sum()))
            if "status" in responses.columns
            else ("prompt_uid", lambda s: 0),
        )
    )

    rows: list[dict] = []
    for _, exp in expected.iterrows():
        for model in models:
            for repeat in range(repeats):
                rows.append(
                    {
                        "provider": provider_name,
                        "strategy": exp["strategy"],
                        "model": model,
                        "repeat": repeat,
                        "expected_prompts": int(exp["expected_prompts"]),
                    }
                )
    skeleton = pd.DataFrame(rows)
    merged = skeleton.merge(observed, on=["provider", "strategy", "model", "repeat"], how="left")
    for col in ("observed_rows", "unique_prompts", "success_rows", "failed_rows"):
        merged[col] = merged[col].fillna(0).astype(int)
    merged["coverage_rate"] = merged["unique_prompts"] / merged["expected_prompts"].where(
        merged["expected_prompts"] != 0, 1
    )
    merged["success_rate"] = merged["success_rows"] / merged["expected_prompts"].where(
        merged["expected_prompts"] != 0, 1
    )
    return merged.sort_values(["strategy", "model", "repeat"]).reset_index(drop=True)
