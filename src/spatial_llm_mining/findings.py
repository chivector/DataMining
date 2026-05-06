"""自动生成 "基于统计的发现" 段落。

任务验收要求形如:

    "通过对 300 次采样分析，我们发现当增加 5% 的无关环境描述时，
     模型 A 的逻辑一致性下降了 40%。"

本模块从 ``run_analysis`` 输出的描述性表里抽取若干 top-k 反差并写成 markdown
bullet。结果同时写入 ``outputs/findings.md`` 与 PDF 报告首页。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


def _fmt_pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def _level_gap_findings(accuracy: pd.DataFrame) -> list[str]:
    if accuracy.empty:
        return []
    pivot = accuracy.pivot(index="model", columns="level", values="accuracy")
    bullets: list[str] = []
    for model, row in pivot.iterrows():
        if "L1" not in row or "L3" not in row:
            continue
        l1, l3 = float(row.get("L1", 0)), float(row.get("L3", 0))
        gap = l1 - l3
        if abs(gap) >= 0.05:
            direction = "下降" if gap > 0 else "上升"
            bullets.append(
                f"模型 **{model}** 从 L1 自然语言描述切换到 L3 数学建模时，准确率{direction} "
                f"{_fmt_pct(abs(gap))}（{_fmt_pct(l1)} → {_fmt_pct(l3)}），"
                f"提示该模型{'倾向视觉直觉' if gap > 0 else '受益于形式化表达'}。"
            )
    return bullets


def _noise_findings(noise: pd.DataFrame) -> list[str]:
    if noise.empty:
        return []
    bullets: list[str] = []
    grouped = noise.groupby("model")
    for model, sub in grouped:
        worst = sub.sort_values("flip_rate", ascending=False).iloc[0]
        if float(worst["flip_rate"]) >= 0.05:
            bullets.append(
                f"在干扰 **{worst['noise_label']}** 下，模型 **{model}** 的判断翻转率达到 "
                f"{_fmt_pct(float(worst['flip_rate']))}（共 {int(worst['samples'])} 个样本），"
                "说明无关信息显著改变了它的几何推理结论。"
            )
    return bullets


def _consistency_findings(consistency: pd.DataFrame) -> list[str]:
    if consistency.empty:
        return []
    summary = consistency.groupby("model")["level_consistency"].agg(["mean", "min", "count"]).reset_index()
    bullets: list[str] = []
    for _, row in summary.iterrows():
        mean = float(row["mean"])
        if mean < 0.85:
            bullets.append(
                f"模型 **{row['model']}** 在 L1-L3 描述迁移上的平均一致性仅 {_fmt_pct(mean)}，"
                f"最低 {_fmt_pct(float(row['min']))}（基于 {int(row['count'])} 个 case×repeat 组合），"
                "存在 **描述越数学越糊涂** 的反常现象。"
            )
    return bullets


def _failure_findings(failures: pd.DataFrame) -> list[str]:
    if failures.empty:
        return []
    top = failures.sort_values("share", ascending=False).groupby("model").head(1)
    bullets: list[str] = []
    for _, row in top.iterrows():
        bullets.append(
            f"模型 **{row['model']}** 错误样本中占比最高的失效模式是 "
            f"`{row['error_category']}`（{_fmt_pct(float(row['share']))}，{int(row['count'])} 例），"
            "建议在报告中重点展开该模式的典型回复。"
        )
    return bullets


def _keyword_findings(features: pd.DataFrame) -> list[str]:
    if "noise_keyword_hit" not in features.columns:
        return []
    sub = features[features["noise_keyword_hit"] != "none"]
    if sub.empty:
        return []
    grouped = sub.groupby(["noise_keyword_hit"]).agg(
        hits=("is_correct", "count"),
        accuracy=("is_correct", "mean"),
    )
    overall_acc = float(features["is_correct"].mean())
    bullets: list[str] = []
    for keyword, row in grouped.iterrows():
        if int(row["hits"]) < 10:
            continue
        delta = overall_acc - float(row["accuracy"])
        if delta >= 0.05:
            bullets.append(
                f"当模型在回复中复述触发词 **{keyword}** 时，整体准确率 {_fmt_pct(float(row['accuracy']))} "
                f"低于全局均值 {_fmt_pct(overall_acc)}（差 {_fmt_pct(delta)}，命中样本 {int(row['hits'])} 例），"
                "提示该词容易把模型从几何推理拉向感性判断。"
            )
    return bullets


def _perturbation_findings(perturb_summary: pd.DataFrame) -> list[str]:
    if perturb_summary is None or perturb_summary.empty:
        return []
    bullets: list[str] = []
    for _, row in perturb_summary.iterrows():
        rate = float(row["flip_rate"])
        if rate >= 0.10 and int(row["pairs"]) >= 3:
            bullets.append(
                f"对 borderline 场景的 **{row['param']} ±1cm** 扰动，"
                f"模型 **{row['model']}** 在 {int(row['pairs'])} 对对照中翻转率 "
                f"{_fmt_pct(rate)}，符合任务里定义的 *逻辑坍塌* 特征。"
            )
    return bullets


def build_findings(
    features: pd.DataFrame,
    analysis: dict[str, Any],
    perturb_summary: pd.DataFrame | None = None,
) -> list[str]:
    bullets: list[str] = []
    bullets += _level_gap_findings(analysis.get("accuracy", pd.DataFrame()))
    bullets += _consistency_findings(analysis.get("consistency", pd.DataFrame()))
    bullets += _noise_findings(analysis.get("noise", pd.DataFrame()))
    bullets += _failure_findings(analysis.get("failures", pd.DataFrame()))
    bullets += _keyword_findings(features)
    if perturb_summary is not None:
        bullets += _perturbation_findings(perturb_summary)
    return bullets


def write_findings_md(
    bullets: list[str],
    output_path: Path,
    sample_count: int,
    model_count: int,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    header = (
        "# 自动生成的核心规律发现\n\n"
        f"基于 {sample_count} 条模型回复、{model_count} 个模型的统计结果，"
        "本文件列出了具有显著差异的发现，可直接写入挖掘分析报告。\n\n"
    )
    if not bullets:
        body = "_本轮数据未触发任何阈值条件，请增加重复数或扩展噪声词表。_\n"
    else:
        body = "\n".join(f"- {item}" for item in bullets) + "\n"
    output_path.write_text(header + body, encoding="utf-8")
