import pandas as pd

from spatial_llm_mining.text_cluster import cluster_error_responses


def _toy_errors() -> pd.DataFrame:
    rows = []
    for i in range(40):
        rows.append(
            {
                "model": "M1" if i % 2 == 0 else "M2",
                "error_category": "concept_confusion" if i % 3 else "calculation_collapse",
                "response": "通道净宽和转弯半径混淆，最终判断：不能通过。" + (" 噪声 干扰" if i % 5 else ""),
            }
        )
    rows.append({"model": "M1", "error_category": "concept_confusion", "response": float("nan")})
    rows.append({"model": "M1", "error_category": "concept_confusion", "response": ""})
    return pd.DataFrame(rows)


def test_cluster_handles_nan_and_empty() -> None:
    res = cluster_error_responses(_toy_errors(), n_clusters=2)
    assert not res.empty
    assert {"cluster_id", "size", "top_terms", "dominant_model", "dominant_failure"} <= set(res.columns)


def test_cluster_returns_empty_when_no_errors() -> None:
    df = pd.DataFrame([{"model": "M1", "error_category": "none", "response": "OK"}])
    res = cluster_error_responses(df, n_clusters=2)
    assert res.empty
