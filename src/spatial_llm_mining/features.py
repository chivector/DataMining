from __future__ import annotations

import re
from functools import lru_cache

import pandas as pd

from .io_utils import load_yaml, project_path


JUDGMENT_PATTERNS = [
    # 模板答案：'最终判断' 后允许冒号、空白、换行、markdown 标记 (** ## ### `)
    # 顺序：先匹配 cannot_pass / uncertain，再 can_pass，避免 "不能通过" 中的 "能通过" 被误抓。
    (re.compile(r"最终判断[\s:：*#`]*不能通过"), "cannot_pass"),
    (re.compile(r"最终判断[\s:：*#`]*不确定"), "uncertain"),
    (re.compile(r"最终判断[\s:：*#`]*能通过"), "can_pass"),
    # 兜底自由文本（无显式 '最终判断' 标识时使用）
    (re.compile(r"不能\s*(顺利)?通过|过不去|无法通过"), "cannot_pass"),
    (re.compile(r"可以\s*(顺利)?通过|能够通过|能通过"), "can_pass"),
]

ERROR_KEYWORDS = {
    "noise_distraction": ["扶手", "噪声", "催促", "灯光", "环境", "颜色"],
    "unit_confusion": ["单位", "厘米", "米制", "换算"],
    "concept_confusion": ["概念混淆", "通道净宽直接等同", "半径", "直径"],
    "calculation_collapse": ["算式链条不稳定", "形式化参数较多", "方程", "边界相交"],
    "intuition_overfit": ["直觉", "缺少精确尺寸", "日常空间"],
}


def extract_judgment(text: str) -> str:
    for pattern, label in JUDGMENT_PATTERNS:
        if pattern.search(text):
            return label
    return "uncertain"


def count_reasoning_steps(text: str) -> int:
    numbered = re.findall(r"(?m)^\s*\d+[.、)]", text)
    if numbered:
        return len(numbered)
    sentences = re.split(r"[。！？\n]+", text)
    return sum(1 for s in sentences if s.strip())


def classify_error(text: str, is_correct: bool, is_uncertain: bool) -> str:
    if is_correct and not is_uncertain:
        return "none"
    if is_uncertain:
        return "under_specification"
    for label, keywords in ERROR_KEYWORDS.items():
        if any(word in text for word in keywords):
            return label
    return "unknown_error"


@lru_cache(maxsize=1)
def load_noise_keywords() -> dict[str, list[str]]:
    path = project_path("config", "noise_keywords.yml")
    if not path.exists():
        return {}
    raw = load_yaml(path) or {}
    return {label: [str(p) for p in phrases or []] for label, phrases in raw.items()}


def find_noise_keyword_hit(text: str, noise_label: str) -> str:
    """Return the first phrase from ``noise_keywords[noise_label]`` that the model
    quoted back in its response, or ``"none"`` if it ignored all of them.
    Used by FP-Growth to mine fine-grained ``trigger_phrase -> failure_mode`` rules.
    """
    if not noise_label or noise_label == "none":
        return "none"
    phrases = load_noise_keywords().get(noise_label, [])
    for phrase in phrases:
        if phrase and phrase in text:
            return phrase
    return "none"


def extract_features(responses: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in responses.iterrows():
        text = str(row["response"])
        judgment = extract_judgment(text)
        is_correct = judgment == row["reference_judgment"]
        is_uncertain = judgment == "uncertain"
        has_formula = bool(re.search(r"[=<>≤≥≈+\-*/()]|min\(|max\(|theta|R=|W=|D=", text))
        uses_coordinate = bool(re.search(r"坐标|x-y|x 轴|y 轴|theta|原点|方程|包络", text, re.I))
        noise_label = str(row.get("noise_label", "none"))
        keyword_hit = find_noise_keyword_hit(text, noise_label)
        rows.append(
            {
                **row.to_dict(),
                "ai_judgment": judgment,
                "is_correct": bool(is_correct),
                "is_uncertain": bool(is_uncertain),
                "reasoning_steps": count_reasoning_steps(text),
                "response_chars": len(text),
                "has_formula": has_formula,
                "uses_coordinate": uses_coordinate,
                "noise_keyword_hit": keyword_hit,
                "noise_keyword_present": keyword_hit != "none",
                "error_category": classify_error(text, bool(is_correct), bool(is_uncertain)),
            }
        )
    return pd.DataFrame(rows)
