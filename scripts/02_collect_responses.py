from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from spatial_llm_mining.io_utils import ensure_parent, load_yaml, project_path
from spatial_llm_mining.providers import build_provider


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect LLM responses for prompt matrix.")
    parser.add_argument(
        "--provider",
        default="mock",
        choices=["mock", "df", "openai", "anthropic", "deepseek"],
    )
    parser.add_argument(
        "--models",
        default=None,
        help="Comma-separated model names. Defaults to config mock_models / df_models.",
    )
    parser.add_argument("--repeats", type=int, default=None)
    parser.add_argument("--input", default=str(project_path("data", "prompts.csv")))
    parser.add_argument("--output", default=str(project_path("data", "raw", "model_responses.csv")))
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Skip (model, repeat, prompt_id) tuples already present in --output.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional cap on number of new (model, repeat, prompt) calls; useful for smoke tests.",
    )
    parser.add_argument(
        "--on-error",
        default="skip",
        choices=["skip", "abort"],
        help="What to do when a single API call fails after all retries.",
    )
    return parser.parse_args()


def _load_existing(output_path: Path) -> tuple[pd.DataFrame, set[tuple[str, int, str]]]:
    if not output_path.exists():
        return pd.DataFrame(), set()
    existing = pd.read_csv(output_path)
    if existing.empty or not {"model", "repeat", "prompt_id"}.issubset(existing.columns):
        return existing, set()
    seen = {
        (str(r["model"]), int(r["repeat"]), str(r["prompt_id"]))
        for _, r in existing.iterrows()
    }
    return existing, seen


def main() -> None:
    args = parse_args()
    config = load_yaml(project_path("config", "experiment.yml"))
    prompts = pd.read_csv(args.input)
    if args.models:
        models = [m.strip() for m in args.models.split(",") if m.strip()]
    elif args.provider == "mock":
        models = list(config["mock_models"])
    elif args.provider == "df" and config.get("df_models"):
        models = list(config["df_models"])
    else:
        raise SystemExit("--models is required for non-mock providers")
    repeats = args.repeats if args.repeats is not None else int(config["default_repeats"])
    provider = build_provider(args.provider)

    output_path = Path(args.output)
    ensure_parent(output_path)

    existing_df, seen = _load_existing(output_path) if args.resume else (pd.DataFrame(), set())
    new_rows: list[dict] = []
    collected_at = datetime.now().isoformat(timespec="seconds")
    plan: list[tuple[str, int, pd.Series]] = []
    for model in models:
        for repeat in range(repeats):
            for _, prompt_row in prompts.iterrows():
                key = (model, repeat, str(prompt_row["prompt_id"]))
                if key in seen:
                    continue
                plan.append((model, repeat, prompt_row))

    if args.limit is not None:
        plan = plan[: args.limit]

    total = len(plan)
    if total == 0:
        print(f"nothing to do (existing rows: {len(existing_df)}). output -> {output_path}")
        return

    try:
        from tqdm import tqdm

        iterator = tqdm(plan, total=total, desc=f"{args.provider}", unit="call")
    except ImportError:
        iterator = plan

    failures = 0
    for idx, (model, repeat, prompt_row) in enumerate(iterator, start=1):
        try:
            response = provider.complete(prompt_row, model=model, repeat=repeat)
        except Exception as exc:  # noqa: BLE001 - record-and-continue strategy
            failures += 1
            msg = f"[{idx}/{total}] {model} r{repeat} {prompt_row['prompt_id']} FAILED: {exc}"
            if args.on_error == "abort":
                print(msg, file=sys.stderr)
                raise
            print(msg, file=sys.stderr)
            response = ""
        new_rows.append(
            {
                **prompt_row.to_dict(),
                "provider": args.provider,
                "model": model,
                "repeat": repeat,
                "collected_at": collected_at,
                "response": response,
            }
        )

        if args.provider != "mock" and idx % 25 == 0:
            partial = (
                pd.concat([existing_df, pd.DataFrame(new_rows)], ignore_index=True)
                if not existing_df.empty
                else pd.DataFrame(new_rows)
            )
            partial.to_csv(output_path, index=False, encoding="utf-8-sig")

    combined = (
        pd.concat([existing_df, pd.DataFrame(new_rows)], ignore_index=True)
        if not existing_df.empty
        else pd.DataFrame(new_rows)
    )
    combined.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(
        f"wrote {len(new_rows)} new responses (total {len(combined)}, failures {failures}) -> {output_path}"
    )


if __name__ == "__main__":
    main()
