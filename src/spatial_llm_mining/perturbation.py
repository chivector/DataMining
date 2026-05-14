"""1cm 微扰逻辑坍塌实验。

针对 borderline（临界余量）场景，在保持其它参数不变的前提下对楼梯净宽 W
与转弯半径 R 各做 ±1cm 共 4 个变体；任务文本里的关键描述也跟着变。把
变体也跑一遍模型，统计：

- 单一 1cm 扰动是否导致同模型同 Prompt 的判断翻转。
- 不同模型在阈值附近的稳定性差异。

输出 ``outputs/tables/perturbation_flip.csv`` 与
``outputs/figures/perturbation_threshold.png``。
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from .io_utils import ensure_dir
from .prompts import Scenario, build_scenarios, render_prompt


_PERTURBATIONS: tuple[tuple[str, str, int], ...] = (
    ("W", "stair_width_cm", -1),
    ("W", "stair_width_cm", +1),
    ("R", "turn_radius_cm", -1),
    ("R", "turn_radius_cm", +1),
)


def _scenario_with_offset(base: Scenario, field: str, delta: int) -> Scenario:
    new_value = max(1, getattr(base, field) + delta)
    bumped = replace(base, **{field: new_value})
    side_clearance = bumped.stair_width_cm - bumped.wheelchair_width_cm
    turn_clearance = bumped.landing_depth_cm - bumped.turn_radius_cm
    margin = min(side_clearance, turn_clearance)
    if margin >= 10:
        judgment, criticality = "can_pass", "wide"
    elif margin >= 3:
        judgment, criticality = "can_pass", "borderline"
    elif margin >= -4:
        judgment, criticality = "cannot_pass", "borderline"
    else:
        judgment, criticality = "cannot_pass", "narrow"
    return replace(bumped, clearance_margin_cm=margin, reference_judgment=judgment, criticality=criticality)


def build_perturbation_matrix(num_cases: int = 20) -> pd.DataFrame:
    """One row per (case, perturbation, level=L2)."""
    rows: list[dict] = []
    for s in build_scenarios(num_cases):
        if s.criticality != "borderline":
            continue
        rows.append(
            {
                "case_id": s.case_id,
                "perturb_id": f"{s.case_id}_base",
                "param": "base",
                "delta": 0,
                "stair_width_cm": s.stair_width_cm,
                "turn_radius_cm": s.turn_radius_cm,
                "clearance_margin_cm": s.clearance_margin_cm,
                "reference_judgment": s.reference_judgment,
                "level": "L2",
                "noise_label": "none",
                "noise_text": "",
                "criticality": s.criticality,
                "wheelchair_width_cm": s.wheelchair_width_cm,
                "wheelchair_length_cm": s.wheelchair_length_cm,
                "landing_depth_cm": s.landing_depth_cm,
                "prompt": render_prompt(s, "L2", ""),
                "prompt_id": f"{s.case_id}_pert_base",
            }
        )
        for label, field, delta in _PERTURBATIONS:
            mutated = _scenario_with_offset(s, field, delta)
            rows.append(
                {
                    "case_id": s.case_id,
                    "perturb_id": f"{s.case_id}_{label}{delta:+d}",
                    "param": label,
                    "delta": delta,
                    "stair_width_cm": mutated.stair_width_cm,
                    "turn_radius_cm": mutated.turn_radius_cm,
                    "clearance_margin_cm": mutated.clearance_margin_cm,
                    "reference_judgment": mutated.reference_judgment,
                    "level": "L2",
                    "noise_label": "none",
                    "noise_text": "",
                    "criticality": mutated.criticality,
                    "wheelchair_width_cm": mutated.wheelchair_width_cm,
                    "wheelchair_length_cm": mutated.wheelchair_length_cm,
                    "landing_depth_cm": mutated.landing_depth_cm,
                    "prompt": render_prompt(mutated, "L2", ""),
                    "prompt_id": f"{s.case_id}_pert_{label}{delta:+d}",
                }
            )
    return pd.DataFrame(rows)


def collect_perturbation_responses(matrix: pd.DataFrame, provider, model: str, repeat: int = 0) -> pd.DataFrame:
    """Run any provider over the perturbation matrix; useful for mock smoke tests
    or to add perturbation samples on top of a real-API run."""
    rows = []
    for _, prow in matrix.iterrows():
        text = provider.complete(prow, model=model, repeat=repeat)
        rows.append({**prow.to_dict(), "model": model, "repeat": repeat, "response": text})
    return pd.DataFrame(rows)


def perturbation_flip_table(features: pd.DataFrame) -> pd.DataFrame:
    """Compute, for each (model, case_id), how often a ±1cm shift flips the model's
    judgment relative to the un-perturbed L2/no-noise reading.

    Operates directly on ``behavior_features.csv``: the original 300-prompt L2/none
    rows act as ``base``; perturbation rows are detected by ``perturb_id`` if a
    perturbation matrix has been merged in, otherwise we fall back to comparing
    the same ``case_id`` across a ``stair_width_cm``/``turn_radius_cm`` shift of 1.
    """
    base_mask = (features["level"] == "L2") & (features["noise_label"] == "none")
    id_cols = ["strategy"] if "strategy" in features.columns else []
    base_cols = id_cols + ["model", "case_id", "repeat", "ai_judgment", "stair_width_cm", "turn_radius_cm"]
    base = features[base_mask][base_cols].copy()
    if base.empty:
        return pd.DataFrame(columns=[*id_cols, "model", "case_id", "param", "delta", "flipped", "samples"])
    base = base.rename(columns={"ai_judgment": "base_judgment"})

    group_cols = id_cols + ["model", "case_id", "stair_width_cm", "turn_radius_cm"]
    base = base.groupby(group_cols, as_index=False).agg(
        base_judgment=("base_judgment", lambda s: s.value_counts().idxmax()),
        repeats=("repeat", "count"),
    )

    rows: list[dict] = []
    for _, b in base.iterrows():
        for param, field, delta in _PERTURBATIONS:
            target_value = b[field] + delta
            other_field = "turn_radius_cm" if field == "stair_width_cm" else "stair_width_cm"
            mask = (
                (features["model"] == b["model"])
                & (features["case_id"] == b["case_id"])
                & (features["level"] == "L2")
                & (features["noise_label"] == "none")
                & (features[field] == target_value)
                & (features[other_field] == b[other_field])
            )
            for col in id_cols:
                mask &= features[col] == b[col]
            sub = features[mask]
            if sub.empty:
                continue
            mode_judgment = sub["ai_judgment"].value_counts().idxmax()
            rows.append(
                {
                    **({col: b[col] for col in id_cols}),
                    "model": b["model"],
                    "case_id": b["case_id"],
                    "param": param,
                    "delta": delta,
                    "base_judgment": b["base_judgment"],
                    "perturbed_judgment": mode_judgment,
                    "flipped": mode_judgment != b["base_judgment"],
                    "samples": int(len(sub)),
                }
            )
    return pd.DataFrame(rows)


def perturbation_summary(flips: pd.DataFrame) -> pd.DataFrame:
    if flips.empty:
        return pd.DataFrame(columns=["model", "param", "flip_rate", "pairs"])
    return (
        flips.groupby(["model", "param"], as_index=False)
        .agg(flip_rate=("flipped", "mean"), pairs=("flipped", "count"))
        .sort_values(["model", "flip_rate"], ascending=[True, False])
    )


def plot_perturbation(summary: pd.DataFrame, fig_path: Path) -> None:
    if summary.empty:
        return
    ensure_dir(fig_path.parent)
    plt.figure(figsize=(7.6, 4.2))
    sns.barplot(data=summary, x="param", y="flip_rate", hue="model")
    plt.title("borderline 场景 ±1cm 微扰下的判断翻转率")
    plt.xlabel("被扰动的参数")
    plt.ylabel("翻转率")
    plt.ylim(0, max(0.45, float(summary["flip_rate"].max()) + 0.05))
    plt.tight_layout()
    plt.savefig(fig_path, dpi=180)
    plt.close()
