from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("LOKY_MAX_CPU_COUNT", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.font_manager import FontProperties
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier, export_text

from .association import mine_rules
from .findings import build_findings, write_findings_md
from .io_utils import ensure_dir, load_yaml, project_path, write_json
from .perturbation import perturbation_flip_table, perturbation_summary, plot_perturbation
from .text_cluster import cluster_error_responses, write_clusters


FONT_PATH = Path("C:/Windows/Fonts/NotoSansSC-VF.ttf")


def configure_plot_style() -> FontProperties | None:
    sns.set_theme(style="whitegrid", font_scale=0.95)
    if FONT_PATH.exists():
        font_prop = FontProperties(fname=str(FONT_PATH))
        plt.rcParams["font.sans-serif"] = [font_prop.get_name(), "SimHei", "Microsoft YaHei"]
        plt.rcParams["axes.unicode_minus"] = False
        return font_prop
    plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "Arial Unicode MS"]
    plt.rcParams["axes.unicode_minus"] = False
    return None


def _accuracy_by_level(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby(["model", "level"], as_index=False)
        .agg(
            accuracy=("is_correct", "mean"),
            formula_rate=("has_formula", "mean"),
            coordinate_rate=("uses_coordinate", "mean"),
            avg_steps=("reasoning_steps", "mean"),
            samples=("prompt_id", "count"),
        )
        .sort_values(["model", "level"])
    )


def _noise_flip_rate(df: pd.DataFrame) -> pd.DataFrame:
    key = ["model", "case_id", "level", "repeat"]
    baseline = (
        df[df["noise_label"] == "none"][key + ["ai_judgment"]]
        .rename(columns={"ai_judgment": "baseline_judgment"})
        .copy()
    )
    noisy = df[df["noise_label"] != "none"].merge(baseline, on=key, how="left")
    noisy["flipped"] = noisy["ai_judgment"] != noisy["baseline_judgment"]
    return (
        noisy.groupby(["model", "noise_label"], as_index=False)
        .agg(
            flip_rate=("flipped", "mean"),
            noisy_accuracy=("is_correct", "mean"),
            samples=("prompt_id", "count"),
        )
        .sort_values(["model", "flip_rate"], ascending=[True, False])
    )


def _level_consistency(df: pd.DataFrame) -> pd.DataFrame:
    grouped = df.groupby(["model", "case_id", "noise_label", "repeat"])
    rows = []
    for keys, part in grouped:
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
                "model": keys[0],
                "case_id": keys[1],
                "noise_label": keys[2],
                "repeat": keys[3],
                "level_consistency": pair_agree,
                "all_levels_same": len(set(values)) == 1,
                "l1_judgment": values[0],
                "l2_judgment": values[1],
                "l3_judgment": values[2],
            }
        )
    return pd.DataFrame(rows)


def _failure_modes(df: pd.DataFrame) -> pd.DataFrame:
    errors = df[df["error_category"] != "none"].copy()
    if errors.empty:
        return pd.DataFrame(columns=["model", "error_category", "count", "share"])
    counts = errors.groupby(["model", "error_category"], as_index=False).size()
    totals = counts.groupby("model")["size"].transform("sum")
    counts["share"] = counts["size"] / totals
    return counts.rename(columns={"size": "count"}).sort_values(["model", "count"], ascending=[True, False])


def _model_boundaries(df: pd.DataFrame, consistency: pd.DataFrame, noise: pd.DataFrame) -> pd.DataFrame:
    acc = _accuracy_by_level(df).pivot(index="model", columns="level", values="accuracy").reset_index()
    cons = consistency.groupby("model", as_index=False)["level_consistency"].mean()
    flip = noise.groupby("model", as_index=False)["flip_rate"].mean()
    formula = df.groupby("model", as_index=False).agg(
        formula_rate=("has_formula", "mean"),
        coordinate_rate=("uses_coordinate", "mean"),
    )
    merged = acc.merge(cons, on="model").merge(flip, on="model").merge(formula, on="model")
    for col in ["L1", "L2", "L3"]:
        if col not in merged:
            merged[col] = np.nan

    feature_cols = ["L1", "L2", "L3", "level_consistency", "flip_rate", "formula_rate", "coordinate_rate"]
    x = merged[feature_cols].fillna(0).to_numpy()
    n_clusters = min(4, len(merged))
    if n_clusters > 1:
        labels = KMeans(n_clusters=n_clusters, n_init=20, random_state=20260505).fit_predict(StandardScaler().fit_transform(x))
    else:
        labels = np.zeros(len(merged), dtype=int)
    merged["cluster"] = labels
    merged["cognitive_style"] = merged.apply(_style_label, axis=1)
    merged["boundary_definition"] = merged.apply(_boundary_text, axis=1)
    return merged


def _style_label(row: pd.Series) -> str:
    if row["flip_rate"] >= 0.28:
        return "噪声敏感型"
    if row["L3"] >= row["L1"] and row["coordinate_rate"] >= 0.35:
        return "符号逻辑型"
    if row["L1"] - row["L3"] >= 0.10:
        return "视觉直觉型"
    return "混合稳健型"


def _boundary_text(row: pd.Series) -> str:
    weakest_level = min(["L1", "L2", "L3"], key=lambda col: row[col])
    level_name = {"L1": "自然语言描述", "L2": "具体参数", "L3": "数学建模"}[weakest_level]
    if row["flip_rate"] >= 0.28:
        return f"主要边界出现在无关描述扰动下，{level_name}场景更易发生判断翻转。"
    if row["level_consistency"] < 0.70:
        return f"主要边界是描述层级迁移不稳定，进入{level_name}后结论一致性下降。"
    return f"整体较稳定，但在{level_name}和临界余量场景下仍存在逻辑坍塌风险。"


def _decision_tree_text(df: pd.DataFrame) -> str:
    work = df.copy()
    work["level_code"] = work["level"].map({"L1": 1, "L2": 2, "L3": 3})
    work["has_noise"] = (work["noise_label"] != "none").astype(int)
    work["is_borderline"] = (work["criticality"] == "borderline").astype(int)
    features = [
        "level_code",
        "has_noise",
        "is_borderline",
        "clearance_margin_cm",
        "reasoning_steps",
        "has_formula",
        "uses_coordinate",
    ]
    if work["is_correct"].nunique() < 2:
        return "样本中正确性类别不足，未训练决策树。"
    clf = DecisionTreeClassifier(max_depth=4, min_samples_leaf=12, random_state=20260505)
    clf.fit(work[features], work["is_correct"].astype(int))
    return export_text(clf, feature_names=features)


def create_figures(
    df: pd.DataFrame,
    accuracy: pd.DataFrame,
    noise: pd.DataFrame,
    consistency: pd.DataFrame,
    failures: pd.DataFrame,
    boundaries: pd.DataFrame,
    fig_dir: Path,
) -> None:
    ensure_dir(fig_dir)
    configure_plot_style()

    pivot = accuracy.pivot(index="model", columns="level", values="accuracy")
    plt.figure(figsize=(7.2, 4.2))
    sns.heatmap(pivot, annot=True, fmt=".2f", cmap="YlGnBu", vmin=0, vmax=1)
    plt.title("不同描述层级下的判断准确率")
    plt.xlabel("Prompt 层级")
    plt.ylabel("模型")
    plt.tight_layout()
    plt.savefig(fig_dir / "accuracy_heatmap.png", dpi=180)
    plt.close()

    plt.figure(figsize=(8.4, 4.2))
    sns.barplot(data=noise, x="noise_label", y="flip_rate", hue="model")
    plt.title("无关信息导致的判断翻转率")
    plt.xlabel("干扰项")
    plt.ylabel("翻转率")
    plt.xticks(rotation=18, ha="right")
    plt.ylim(0, max(0.45, float(noise["flip_rate"].max()) + 0.05))
    plt.tight_layout()
    plt.savefig(fig_dir / "noise_flip_rate.png", dpi=180)
    plt.close()

    cons_summary = consistency.groupby(["model", "noise_label"], as_index=False)["level_consistency"].mean()
    plt.figure(figsize=(8.4, 4.2))
    sns.lineplot(data=cons_summary, x="noise_label", y="level_consistency", hue="model", marker="o")
    plt.title("L1-L3 描述迁移的一致性得分")
    plt.xlabel("干扰项")
    plt.ylabel("一致性得分")
    plt.xticks(rotation=18, ha="right")
    plt.ylim(0, 1.02)
    plt.tight_layout()
    plt.savefig(fig_dir / "level_consistency.png", dpi=180)
    plt.close()

    if not failures.empty:
        plt.figure(figsize=(8.4, 4.6))
        sns.barplot(data=failures, x="error_category", y="share", hue="model")
        plt.title("错误样本中的失效模式占比")
        plt.xlabel("失效模式")
        plt.ylabel("占比")
        plt.xticks(rotation=20, ha="right")
        plt.tight_layout()
        plt.savefig(fig_dir / "failure_modes.png", dpi=180)
        plt.close()

    radar_cols = ["L1", "L2", "L3", "level_consistency", "formula_rate", "coordinate_rate"]
    labels = ["L1准确", "L2准确", "L3准确", "一致性", "公式率", "坐标率"]
    angles = np.linspace(0, 2 * np.pi, len(radar_cols), endpoint=False).tolist()
    angles += angles[:1]
    fig = plt.figure(figsize=(6.4, 6.4))
    ax = plt.subplot(111, polar=True)
    for _, row in boundaries.iterrows():
        values = [float(row[c]) for c in radar_cols]
        values += values[:1]
        ax.plot(angles, values, label=row["model"], linewidth=1.8)
        ax.fill(angles, values, alpha=0.08)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels)
    ax.set_ylim(0, 1)
    ax.set_title("模型认知特征雷达图", pad=18)
    ax.legend(loc="upper right", bbox_to_anchor=(1.28, 1.10))
    plt.tight_layout()
    plt.savefig(fig_dir / "model_radar.png", dpi=180)
    plt.close()

    plt.figure(figsize=(6.4, 4.6))
    sns.scatterplot(
        data=boundaries,
        x="level_consistency",
        y="flip_rate",
        hue="cognitive_style",
        style="model",
        s=120,
    )
    for _, row in boundaries.iterrows():
        plt.text(row["level_consistency"] + 0.005, row["flip_rate"] + 0.005, row["model"], fontsize=8)
    plt.title("模型认知边界聚类视图")
    plt.xlabel("层级一致性")
    plt.ylabel("平均噪声翻转率")
    plt.tight_layout()
    plt.savefig(fig_dir / "cluster_map.png", dpi=180)
    plt.close()


def _load_fpgrowth_config() -> dict[str, float]:
    cfg_path = project_path("config", "experiment.yml")
    if not cfg_path.exists():
        return {}
    cfg = load_yaml(cfg_path) or {}
    return dict(cfg.get("fpgrowth") or {})


def _format_itemset(items: tuple[str, ...] | frozenset[str]) -> str:
    return " & ".join(sorted(items))


def _serialize_rules(rules: pd.DataFrame) -> pd.DataFrame:
    if rules.empty:
        return rules
    out = rules.copy()
    if "antecedents" in out:
        out["antecedents"] = out["antecedents"].apply(_format_itemset)
    if "consequents" in out:
        out["consequents"] = out["consequents"].apply(_format_itemset)
    if "itemsets" in out:
        out["itemsets"] = out["itemsets"].apply(_format_itemset)
    return out


def run_analysis(df: pd.DataFrame, output_dir: Path) -> dict[str, pd.DataFrame | str]:
    table_dir = output_dir / "tables"
    fig_dir = output_dir / "figures"
    ensure_dir(table_dir)
    ensure_dir(fig_dir)

    accuracy = _accuracy_by_level(df)
    noise = _noise_flip_rate(df)
    consistency = _level_consistency(df)
    failures = _failure_modes(df)
    boundaries = _model_boundaries(df, consistency, noise)
    tree_text = _decision_tree_text(df)

    fp_cfg = _load_fpgrowth_config()
    rules_result = mine_rules(
        df,
        min_support=float(fp_cfg.get("min_support", 0.10)),
        min_confidence=float(fp_cfg.get("min_confidence", 0.60)),
        max_len=int(fp_cfg.get("max_len", 4)),
    )

    accuracy.to_csv(table_dir / "accuracy_by_level.csv", index=False, encoding="utf-8-sig")
    noise.to_csv(table_dir / "noise_flip_rate.csv", index=False, encoding="utf-8-sig")
    consistency.to_csv(table_dir / "level_consistency.csv", index=False, encoding="utf-8-sig")
    failures.to_csv(table_dir / "failure_modes.csv", index=False, encoding="utf-8-sig")
    boundaries.to_csv(table_dir / "model_boundaries.csv", index=False, encoding="utf-8-sig")
    write_json(table_dir / "decision_tree_rules.json", {"rules": tree_text})

    _serialize_rules(rules_result["frequent_itemsets"]).to_csv(
        table_dir / "frequent_itemsets.csv", index=False, encoding="utf-8-sig"
    )
    _serialize_rules(rules_result["rules"]).to_csv(
        table_dir / "association_rules.csv", index=False, encoding="utf-8-sig"
    )
    _serialize_rules(rules_result["outcome_rules"]).to_csv(
        table_dir / "outcome_rules.csv", index=False, encoding="utf-8-sig"
    )

    perturb_flips = perturbation_flip_table(df)
    perturb_summary = perturbation_summary(perturb_flips)
    perturb_flips.to_csv(table_dir / "perturbation_flip.csv", index=False, encoding="utf-8-sig")
    perturb_summary.to_csv(table_dir / "perturbation_summary.csv", index=False, encoding="utf-8-sig")
    plot_perturbation(perturb_summary, fig_dir / "perturbation_threshold.png")

    error_clusters = cluster_error_responses(df)
    write_clusters(error_clusters, table_dir / "error_text_clusters.csv")

    create_figures(df, accuracy, noise, consistency, failures, boundaries, fig_dir)

    bullets = build_findings(
        df,
        {
            "accuracy": accuracy,
            "noise": noise,
            "consistency": consistency,
            "failures": failures,
        },
        perturb_summary=perturb_summary,
    )
    write_findings_md(
        bullets,
        output_dir / "findings.md",
        sample_count=len(df),
        model_count=int(df["model"].nunique()) if "model" in df.columns else 0,
    )

    return {
        "accuracy": accuracy,
        "noise": noise,
        "consistency": consistency,
        "failures": failures,
        "boundaries": boundaries,
        "decision_tree": tree_text,
        "frequent_itemsets": rules_result["frequent_itemsets"],
        "association_rules": rules_result["rules"],
        "outcome_rules": rules_result["outcome_rules"],
        "perturbation_flips": perturb_flips,
        "perturbation_summary": perturb_summary,
        "error_clusters": error_clusters,
        "findings": bullets,
    }
