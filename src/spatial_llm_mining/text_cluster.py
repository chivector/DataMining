"""对错误回复做文本聚类，归纳 AI 在'轮椅转弯'空间逻辑上的典型盲区。

任务要求 "对错误判例进行文本挖掘，归纳 AI 在'轮椅转弯'空间逻辑上的典型盲区"。
本模块用 TF-IDF + KMeans 把 ``error_category != 'none'`` 的回复聚成 K 类，每类
导出 top-N 关键词与 1-2 条样本。
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer


_CHINESE_TOKEN = re.compile(r"[一-鿿]+|[A-Za-z]+|[0-9]+(?:cm|mm|m)?")


def _tokenize(text: str) -> list[str]:
    text = str(text or "")
    tokens: list[str] = []
    for match in _CHINESE_TOKEN.findall(text):
        if len(match) <= 1:
            continue
        # 把长汉字串切成 2-gram，避免把整段文字当成单一 token
        if re.fullmatch(r"[一-鿿]+", match) and len(match) >= 3:
            tokens.extend(match[i : i + 2] for i in range(len(match) - 1))
        else:
            tokens.append(match)
    return tokens


def cluster_error_responses(
    features: pd.DataFrame,
    n_clusters: int = 4,
    max_features: int = 4000,
    random_state: int = 20260505,
) -> pd.DataFrame:
    """Return a long-form table: one row per (cluster_id, info)."""
    errors = features[features.get("error_category", "") != "none"].copy()
    if errors.empty or "response" not in errors.columns:
        return pd.DataFrame(columns=["cluster_id", "size", "top_terms", "sample_text", "dominant_model", "dominant_failure"])

    vectorizer = TfidfVectorizer(
        tokenizer=_tokenize,
        token_pattern=None,
        max_features=max_features,
        min_df=2,
    )
    try:
        matrix = vectorizer.fit_transform(errors["response"].astype(str))
    except ValueError:
        return pd.DataFrame(columns=["cluster_id", "size", "top_terms", "sample_text", "dominant_model", "dominant_failure"])
    n_clusters = max(2, min(n_clusters, matrix.shape[0]))
    kmeans = KMeans(n_clusters=n_clusters, n_init=10, random_state=random_state)
    labels = kmeans.fit_predict(matrix)
    errors = errors.assign(cluster_id=labels)

    feature_names = np.array(vectorizer.get_feature_names_out())
    centers = kmeans.cluster_centers_
    rows: list[dict] = []
    for cid in sorted(set(labels)):
        sub = errors[errors["cluster_id"] == cid]
        top_idx = np.argsort(centers[cid])[::-1][:8]
        top_terms = ", ".join(feature_names[top_idx].tolist())
        sample_text = str(sub.iloc[0]["response"])[:240].replace("\n", " ")
        dominant_model = sub["model"].value_counts().idxmax() if "model" in sub.columns else ""
        dominant_failure = sub["error_category"].value_counts().idxmax()
        rows.append(
            {
                "cluster_id": int(cid),
                "size": int(len(sub)),
                "top_terms": top_terms,
                "sample_text": sample_text,
                "dominant_model": dominant_model,
                "dominant_failure": dominant_failure,
            }
        )
    return pd.DataFrame(rows).sort_values("size", ascending=False).reset_index(drop=True)


def write_clusters(table: pd.DataFrame, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(output_path, index=False, encoding="utf-8-sig")
