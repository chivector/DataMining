from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import matplotlib.pyplot as plt
import seaborn as sns

from spatial_llm_mining.analysis import configure_plot_style
from spatial_llm_mining.io_utils import ensure_dir, project_path


def _per_group_stats(df: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        df.dropna(subset=["ai_judgment"])
        .groupby(["model", "prompt_uid"], as_index=False)
        .agg(
            repeats=("repeat", "count"),
            distinct_judgments=("ai_judgment", "nunique"),
            judgments=("ai_judgment", lambda s: tuple(sorted(s.astype(str).tolist()))),
            level=("level", "first"),
            noise_label=("noise_label", "first"),
            strategy=("strategy", "first"),
            case_id=("case_id", "first"),
            reference_judgment=("reference_judgment", "first"),
            is_correct_mean=("is_correct", "mean"),
        )
    )
    grouped = grouped[grouped["repeats"] >= 2].copy()
    grouped["fully_consistent"] = grouped["distinct_judgments"] == 1
    grouped["fully_divergent"] = grouped["distinct_judgments"] >= 3
    return grouped


def _majority_judgment(judgments: tuple[str, ...]) -> str:
    if not judgments:
        return ""
    counts: dict[str, int] = {}
    for j in judgments:
        counts[j] = counts.get(j, 0) + 1
    best = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[0]
    return best[0]


def consistency_by_model(groups: pd.DataFrame) -> pd.DataFrame:
    out = (
        groups.groupby("model", as_index=False)
        .agg(
            groups_n=("prompt_uid", "count"),
            self_consistency=("fully_consistent", "mean"),
            fully_divergent_rate=("fully_divergent", "mean"),
            mean_accuracy=("is_correct_mean", "mean"),
        )
        .sort_values("self_consistency", ascending=False)
    )
    return out


def consistency_by_model_level(groups: pd.DataFrame) -> pd.DataFrame:
    return (
        groups.groupby(["model", "level"], as_index=False)
        .agg(
            groups_n=("prompt_uid", "count"),
            self_consistency=("fully_consistent", "mean"),
            fully_divergent_rate=("fully_divergent", "mean"),
        )
        .sort_values(["model", "level"])
    )


def consistency_by_model_noise(groups: pd.DataFrame) -> pd.DataFrame:
    return (
        groups.groupby(["model", "noise_label"], as_index=False)
        .agg(
            groups_n=("prompt_uid", "count"),
            self_consistency=("fully_consistent", "mean"),
        )
        .sort_values(["model", "noise_label"])
    )


def consistency_by_model_strategy(groups: pd.DataFrame) -> pd.DataFrame:
    return (
        groups.groupby(["model", "strategy"], as_index=False)
        .agg(
            groups_n=("prompt_uid", "count"),
            self_consistency=("fully_consistent", "mean"),
        )
        .sort_values(["model", "strategy"])
    )


def unstable_cases(groups: pd.DataFrame, top_n: int = 50) -> pd.DataFrame:
    unstable = groups[~groups["fully_consistent"]].copy()
    unstable["judgment_signature"] = unstable["judgments"].astype(str)
    unstable = unstable.sort_values(
        ["distinct_judgments", "model", "case_id"], ascending=[False, True, True]
    )
    cols = [
        "model",
        "case_id",
        "strategy",
        "level",
        "noise_label",
        "reference_judgment",
        "repeats",
        "distinct_judgments",
        "judgment_signature",
        "prompt_uid",
    ]
    return unstable[cols].head(top_n)


def confident_wrong_cases(groups: pd.DataFrame, top_n: int = 50) -> pd.DataFrame:
    confident_wrong = groups[
        (groups["fully_consistent"]) & (groups["is_correct_mean"] == 0)
    ].copy()
    confident_wrong["majority_judgment"] = confident_wrong["judgments"].apply(_majority_judgment)
    cols = [
        "model",
        "case_id",
        "strategy",
        "level",
        "noise_label",
        "reference_judgment",
        "majority_judgment",
        "repeats",
        "prompt_uid",
    ]
    return (
        confident_wrong[cols]
        .sort_values(["model", "case_id"])
        .head(top_n)
    )


def plot_self_consistency_bar(model_table: pd.DataFrame, figures_dir: Path) -> Path:
    df = model_table.copy().sort_values("self_consistency", ascending=True)
    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    bars = ax.barh(df["model"], df["self_consistency"], color=sns.color_palette("crest", n_colors=len(df)))
    ax.set_xlabel("Repeat self-consistency (3 次全一致比例)")
    ax.set_ylabel("Model")
    ax.set_xlim(0, 1.0)
    for bar, val in zip(bars, df["self_consistency"].tolist()):
        ax.text(val + 0.01, bar.get_y() + bar.get_height() / 2, f"{val:.0%}", va="center", fontsize=9)
    ax.set_title("同一 prompt 三次重复采样的自一致性")
    fig.tight_layout()
    path = figures_dir / "self_consistency_by_model.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def plot_consistency_vs_accuracy(model_table: pd.DataFrame, figures_dir: Path) -> Path:
    fig, ax = plt.subplots(figsize=(6.5, 5))
    ax.scatter(
        model_table["self_consistency"],
        model_table["mean_accuracy"],
        s=80,
        c="#1f77b4",
        edgecolor="white",
    )
    for _, row in model_table.iterrows():
        ax.annotate(
            row["model"],
            xy=(row["self_consistency"], row["mean_accuracy"]),
            xytext=(5, 4),
            textcoords="offset points",
            fontsize=8,
        )
    ax.set_xlabel("Repeat self-consistency")
    ax.set_ylabel("Mean accuracy (group-level)")
    ax.set_xlim(0, 1.05)
    ax.set_ylim(0, 1.0)
    ax.axhline(0.5, color="grey", linestyle="--", linewidth=0.8, alpha=0.6)
    ax.axvline(0.5, color="grey", linestyle="--", linewidth=0.8, alpha=0.6)
    ax.set_title("自一致性 vs 准确率（右下象限 = 自信但错）")
    fig.tight_layout()
    path = figures_dir / "self_consistency_vs_accuracy.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def plot_consistency_heatmap_level(level_table: pd.DataFrame, figures_dir: Path) -> Path:
    pivot = level_table.pivot(index="model", columns="level", values="self_consistency")
    pivot = pivot.reindex(columns=["L1", "L2", "L3"])
    fig, ax = plt.subplots(figsize=(5.5, 4.5))
    sns.heatmap(
        pivot,
        annot=True,
        fmt=".0%",
        cmap="YlGnBu",
        vmin=0,
        vmax=1,
        ax=ax,
        cbar_kws={"label": "self-consistency"},
    )
    ax.set_title("模型 × 描述层级的自一致性")
    fig.tight_layout()
    path = figures_dir / "self_consistency_heatmap_level.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def render_findings(model_table: pd.DataFrame, level_table: pd.DataFrame, noise_table: pd.DataFrame) -> list[str]:
    findings: list[str] = []
    findings.append("## Repeat 自一致性发现（新增）")
    findings.append("")
    findings.append(
        "在同一 (model, prompt_uid) 上重复 3 次采样，"
        "如果三次 ai_judgment 完全相同计为自一致，"
        "以下为每个模型的自一致比例及微观表现。"
    )
    findings.append("")
    findings.append("| 模型 | 样本组 | 自一致性 | 三词全不同比例 | 均准确率 |")
    findings.append("| --- | --- | --- | --- | --- |")
    for _, row in model_table.sort_values("self_consistency", ascending=False).iterrows():
        findings.append(
            f"| {row['model']} | {int(row['groups_n'])} | "
            f"{row['self_consistency']:.1%} | {row['fully_divergent_rate']:.1%} | "
            f"{row['mean_accuracy']:.1%} |"
        )
    findings.append("")

    pivot = level_table.pivot(index="model", columns="level", values="self_consistency")
    if {"L1", "L3"}.issubset(pivot.columns):
        diff = (pivot["L3"] - pivot["L1"]).dropna()
        if len(diff):
            largest_drop = diff.idxmin()
            drop_value = diff.min()
            largest_rise = diff.idxmax()
            rise_value = diff.max()
            findings.append(
                f"- L1→L3 自一致性下降最多的是 **{largest_drop}**，"
                f"降幅 {drop_value:.1%}；上升最多的是 **{largest_rise}**，"
                f"幅度 {rise_value:.1%}。"
            )

    # Identify "confident but wrong" risk: high self-consistency, low accuracy
    risk = model_table[(model_table["self_consistency"] > 0.7) & (model_table["mean_accuracy"] < 0.5)]
    if not risk.empty:
        names = ", ".join(risk.sort_values("self_consistency", ascending=False)["model"].tolist())
        findings.append(
            f"- 高自信但高错率的模型（自一致性>70%且准确率<50%）: {names}。"
            "这类模型在 prompt 微扰动下不会动摇，但会稳定输出错误结论。"
        )

    # Noise sensitivity: per-model max consistency drop across noise vs none
    noise_pivot = noise_table.pivot(index="model", columns="noise_label", values="self_consistency")
    if "none" in noise_pivot.columns:
        worst_records: list[tuple[str, str, float]] = []
        for model in noise_pivot.index:
            baseline = noise_pivot.loc[model, "none"]
            others = noise_pivot.loc[model].drop(labels=["none"])
            if pd.isna(baseline) or others.dropna().empty:
                continue
            drop = (baseline - others).max()
            label = (baseline - others).idxmax()
            if drop > 0.1:
                worst_records.append((model, label, drop))
        if worst_records:
            findings.append("")
            findings.append(
                "- 噪声对自一致性的冲击（与 none 相比跨类别最大降幅）:"
            )
            for model, label, drop in sorted(worst_records, key=lambda x: -x[2])[:6]:
                findings.append(
                    f"  - {model} 在 **{label}** 下自一致性下降 {drop:.1%}。"
                )
    return findings


def append_findings(findings_md: Path, lines: list[str]) -> None:
    text = "\n".join(lines).strip() + "\n"
    if findings_md.exists():
        existing = findings_md.read_text(encoding="utf-8")
        if "## Repeat 自一致性发现" in existing:
            before, _, _ = existing.partition("## Repeat 自一致性发现")
            existing = before.rstrip() + "\n\n"
        else:
            existing = existing.rstrip() + "\n\n"
        findings_md.write_text(existing + text, encoding="utf-8")
    else:
        findings_md.write_text(text, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compute repeat self-consistency metrics for the experiment dataset.")
    parser.add_argument(
        "--input",
        default=str(project_path("data", "processed", "behavior_features_experiment.csv")),
    )
    parser.add_argument("--output-dir", default=str(project_path("outputs_experiment")))
    parser.add_argument("--require-full-three-repeats", action="store_true", help="Only keep groups with exactly 3 repeats.")
    parser.add_argument("--top-unstable", type=int, default=50)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    configure_plot_style()

    df = pd.read_csv(args.input)
    if "status" in df.columns:
        df = df[df["status"].astype(str) == "success"].copy()
    if df.empty:
        raise SystemExit("no successful rows in input")

    groups = _per_group_stats(df)
    if args.require_full_three_repeats:
        groups = groups[groups["repeats"] == 3].copy()
    if groups.empty:
        raise SystemExit("no (model, prompt_uid) groups with >=2 repeats")

    output_dir = Path(args.output_dir)
    tables_dir = output_dir / "tables"
    figures_dir = output_dir / "figures"
    ensure_dir(tables_dir)
    ensure_dir(figures_dir)

    model_table = consistency_by_model(groups)
    level_table = consistency_by_model_level(groups)
    noise_table = consistency_by_model_noise(groups)
    strategy_table = consistency_by_model_strategy(groups)
    unstable = unstable_cases(groups, top_n=args.top_unstable)
    confident_wrong = confident_wrong_cases(groups, top_n=args.top_unstable)

    model_table.to_csv(tables_dir / "self_consistency_by_model.csv", index=False)
    level_table.to_csv(tables_dir / "self_consistency_by_model_level.csv", index=False)
    noise_table.to_csv(tables_dir / "self_consistency_by_model_noise.csv", index=False)
    strategy_table.to_csv(tables_dir / "self_consistency_by_model_strategy.csv", index=False)
    unstable.to_csv(tables_dir / "self_consistency_unstable_cases.csv", index=False)
    confident_wrong.to_csv(tables_dir / "self_consistency_confident_wrong.csv", index=False)

    plot_self_consistency_bar(model_table, figures_dir)
    plot_consistency_vs_accuracy(model_table, figures_dir)
    plot_consistency_heatmap_level(level_table, figures_dir)

    findings_md = output_dir / "findings.md"
    append_findings(findings_md, render_findings(model_table, level_table, noise_table))

    print("[ok] self-consistency analysis written under", output_dir)
    print(model_table.to_string(index=False))


if __name__ == "__main__":
    main()
