from __future__ import annotations

from pathlib import Path
from textwrap import wrap

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.backends.backend_pdf import PdfPages

from .analysis import configure_plot_style
from .io_utils import ensure_parent


def _add_wrapped_text(ax: plt.Axes, text: str, x: float, y: float, width: int = 60, size: int = 11) -> float:
    lines: list[str] = []
    for paragraph in text.split("\n"):
        if not paragraph.strip():
            lines.append("")
        else:
            lines.extend(wrap(paragraph, width=width, break_long_words=False, replace_whitespace=False))
    for line in lines:
        ax.text(x, y, line, fontsize=size, va="top")
        y -= 0.045 if line else 0.025
    return y


def _draw_table(ax: plt.Axes, df: pd.DataFrame, bbox: list[float], font_size: int = 8) -> None:
    table = ax.table(
        cellText=df.values,
        colLabels=df.columns,
        cellLoc="center",
        colLoc="center",
        bbox=bbox,
    )
    table.auto_set_font_size(False)
    table.set_fontsize(font_size)
    for (row, _), cell in table.get_celld().items():
        if row == 0:
            cell.set_facecolor("#DCEBFA")
            cell.set_text_props(weight="bold")
        else:
            cell.set_facecolor("#FFFFFF" if row % 2 else "#F6F8FA")


def _insert_image_page(pdf: PdfPages, image_path: Path, title: str) -> None:
    fig, ax = plt.subplots(figsize=(11.69, 8.27))
    ax.axis("off")
    ax.text(0.04, 0.96, title, fontsize=20, weight="bold", va="top")
    img = mpimg.imread(image_path)
    ax.imshow(img, extent=[0.06, 0.94, 0.08, 0.86], aspect="auto")
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def build_pdf_report(
    features: pd.DataFrame,
    analysis: dict[str, pd.DataFrame | str],
    output_pdf: Path,
    figures_dir: Path,
) -> None:
    ensure_parent(output_pdf)
    configure_plot_style()

    accuracy = analysis["accuracy"].copy()
    noise = analysis["noise"].copy()
    boundaries = analysis["boundaries"].copy()
    failures = analysis["failures"].copy()
    decision_tree = str(analysis["decision_tree"])

    total_samples = len(features)
    prompt_count = features["prompt_id"].nunique()
    model_count = features["model"].nunique()
    overall_accuracy = features["is_correct"].mean()
    avg_flip = noise["flip_rate"].mean()
    avg_consistency = analysis["consistency"]["level_consistency"].mean()

    best_level = (
        accuracy.groupby("level")["accuracy"].mean().sort_values(ascending=False).index[0]
    )
    worst_level = (
        accuracy.groupby("level")["accuracy"].mean().sort_values().index[0]
    )
    most_sensitive_noise = (
        noise.groupby("noise_label")["flip_rate"].mean().sort_values(ascending=False).index[0]
    )

    with PdfPages(output_pdf) as pdf:
        fig, ax = plt.subplots(figsize=(11.69, 8.27))
        ax.axis("off")
        ax.text(0.05, 0.92, "大语言模型空间建模能力的认知边界与逻辑一致性挖掘分析", fontsize=22, weight="bold")
        ax.text(0.05, 0.86, "案例：电动轮椅在狭窄楼梯转角处的 90 度转弯判断", fontsize=14)
        summary = (
            f"本报告基于 {prompt_count} 个阶梯式 Prompt 和 {total_samples} 条模型回复进行分析，"
            f"覆盖 {model_count} 个模型、L1 自然语言描述、L2 具体参数、L3 数学建模三类表达方式，"
            "并加入材质颜色、环境噪声、灯光、情绪压力等无关扰动。"
        )
        y = _add_wrapped_text(ax, summary, 0.05, 0.76, width=75, size=12)
        highlights = [
            f"总体判断准确率：{overall_accuracy:.1%}",
            f"平均 L1-L3 层级一致性：{avg_consistency:.1%}",
            f"平均噪声翻转率：{avg_flip:.1%}",
            f"平均表现最好层级：{best_level}；最弱层级：{worst_level}",
            f"最易诱发判断翻转的干扰项：{most_sensitive_noise}",
        ]
        ax.text(0.05, y - 0.02, "核心统计发现", fontsize=16, weight="bold")
        y -= 0.08
        for item in highlights:
            ax.text(0.08, y, f"- {item}", fontsize=12, va="top")
            y -= 0.052

        narrative = analysis.get("findings") if isinstance(analysis, dict) else None
        if narrative:
            y -= 0.02
            ax.text(0.05, y, "自动归纳的差异点（top 5）", fontsize=14, weight="bold")
            y -= 0.05
            for bullet in list(narrative)[:5]:
                clean = bullet.replace("**", "")
                y = _add_wrapped_text(ax, f"- {clean}", 0.06, y, width=88, size=10)
                y -= 0.005
        matrix = (
            features[["level", "noise_label", "criticality", "prompt"]]
            .drop_duplicates()
            .head(5)
            .copy()
        )
        matrix["prompt"] = matrix["prompt"].str.slice(0, 58) + "..."
        ax.text(0.05, 0.36, "实验矩阵示例", fontsize=16, weight="bold")
        _draw_table(ax, matrix, [0.05, 0.08, 0.90, 0.24], font_size=7)
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)

        fig, ax = plt.subplots(figsize=(11.69, 8.27))
        ax.axis("off")
        ax.text(0.05, 0.94, "模型认知边界定义", fontsize=20, weight="bold", va="top")
        display = boundaries[
            ["model", "L1", "L2", "L3", "level_consistency", "flip_rate", "cognitive_style", "boundary_definition"]
        ].copy()
        for col in ["L1", "L2", "L3", "level_consistency", "flip_rate"]:
            display[col] = display[col].map(lambda v: f"{v:.1%}")
        display.columns = ["模型", "L1", "L2", "L3", "一致性", "翻转率", "类型", "认知边界"]
        _draw_table(ax, display, [0.04, 0.38, 0.92, 0.46], font_size=7)
        tree_intro = "决策树用于解释哪些因素最影响模型是否判断正确。下方规则来自行为特征数据："
        ax.text(0.05, 0.31, "可解释规则摘要", fontsize=16, weight="bold")
        y = _add_wrapped_text(ax, tree_intro, 0.05, 0.26, width=85, size=11)
        _add_wrapped_text(ax, decision_tree[:900], 0.05, y - 0.02, width=95, size=8)
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)

        for image_name, title in [
            ("accuracy_heatmap.png", "不同描述层级下的判断准确率"),
            ("noise_flip_rate.png", "无关信息导致的判断翻转率"),
            ("level_consistency.png", "L1-L3 描述迁移的一致性得分"),
            ("model_radar.png", "模型认知特征雷达图"),
            ("cluster_map.png", "模型认知边界聚类视图"),
            ("perturbation_threshold.png", "borderline 场景 ±1cm 微扰下的判断翻转"),
        ]:
            path = figures_dir / image_name
            if path.exists():
                _insert_image_page(pdf, path, title)

        if not failures.empty:
            _insert_image_page(pdf, figures_dir / "failure_modes.png", "错误样本中的失效模式占比")

        outcome_rules = analysis.get("outcome_rules") if isinstance(analysis, dict) else None
        if isinstance(outcome_rules, pd.DataFrame) and not outcome_rules.empty:
            fig, ax = plt.subplots(figsize=(11.69, 8.27))
            ax.axis("off")
            ax.text(0.05, 0.94, "FP-Growth 关联规则（结果维度）", fontsize=20, weight="bold", va="top")
            intro = (
                "下方表格为 FP-Growth 在行为特征上的输出，仅保留结果项位于 RHS 的规则，"
                "可直接用于解释“在何种 Prompt/扰动条件下，模型最容易给出某种判断或失效模式”。"
            )
            _add_wrapped_text(ax, intro, 0.05, 0.88, width=85, size=11)
            preview_cols = [c for c in [
                "antecedents", "consequents", "support", "confidence", "lift",
            ] if c in outcome_rules.columns]
            preview = outcome_rules[preview_cols].head(12).copy()
            for col in ("support", "confidence", "lift"):
                if col in preview.columns:
                    preview[col] = preview[col].map(lambda v: f"{float(v):.2f}")
            if "antecedents" in preview.columns:
                preview["antecedents"] = preview["antecedents"].apply(
                    lambda v: " & ".join(sorted(v)) if isinstance(v, (tuple, list, set, frozenset)) else str(v)
                )
            if "consequents" in preview.columns:
                preview["consequents"] = preview["consequents"].apply(
                    lambda v: " & ".join(sorted(v)) if isinstance(v, (tuple, list, set, frozenset)) else str(v)
                )
            _draw_table(ax, preview, [0.04, 0.18, 0.92, 0.66], font_size=7)
            pdf.savefig(fig, bbox_inches="tight")
            plt.close(fig)

        clusters = analysis.get("error_clusters") if isinstance(analysis, dict) else None
        if isinstance(clusters, pd.DataFrame) and not clusters.empty:
            fig, ax = plt.subplots(figsize=(11.69, 8.27))
            ax.axis("off")
            ax.text(0.05, 0.94, "错误回复文本聚类", fontsize=20, weight="bold", va="top")
            intro = (
                "对 error_category != none 的样本做 TF-IDF + KMeans 聚类，"
                "每个簇展示出现频率最高的 2-gram、主导模型与典型样例，"
                "用于快速定位 AI 在轮椅转弯任务中的盲区类型。"
            )
            _add_wrapped_text(ax, intro, 0.05, 0.88, width=85, size=11)
            preview = clusters[["cluster_id", "size", "dominant_model", "dominant_failure", "top_terms", "sample_text"]].copy()
            preview["sample_text"] = preview["sample_text"].str.slice(0, 90) + "..."
            preview["top_terms"] = preview["top_terms"].str.slice(0, 70)
            _draw_table(ax, preview, [0.03, 0.20, 0.94, 0.62], font_size=7)
            pdf.savefig(fig, bbox_inches="tight")
            plt.close(fig)

        fig, ax = plt.subplots(figsize=(11.69, 8.27))
        ax.axis("off")
        ax.text(0.05, 0.94, "结论与使用建议", fontsize=20, weight="bold", va="top")
        conclusion = (
            "1. 空间问题的模型表现并不随描述形式单调提升。部分模型在 L1 的自然语言描述中依赖空间常识可以得到较好结论，"
            "但进入 L3 形式化几何描述后，公式和坐标表达会暴露其内部逻辑链条的不稳定性。\n"
            "2. 无关信息会改变回答风格，并在临界余量场景中显著增加判断翻转。材质、噪声、光照和情绪压力并不改变几何事实，"
            "但会诱导模型从几何推理转向安全保守或感性判断。\n"
            "3. 建议真实实验至少对每个 Prompt 重复采样 3 次，并记录模型版本、温度、日期与系统提示词。"
            "如果用于课程提交，应将本项目默认的 mock 数据替换为真实 API 采集结果。"
        )
        _add_wrapped_text(ax, conclusion, 0.06, 0.84, width=86, size=12)
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)
