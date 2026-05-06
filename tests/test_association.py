import pandas as pd

from spatial_llm_mining.association import build_transactions, mine_rules


def _toy_features() -> pd.DataFrame:
    rows = []
    for level in ("L1", "L2", "L3"):
        for noise in ("none", "ambient_noise"):
            for correct in (True, False):
                rows.append(
                    {
                        "model": "demo",
                        "level": level,
                        "noise_label": noise,
                        "criticality": "borderline",
                        "has_formula": True,
                        "uses_coordinate": False,
                        "ai_judgment": "can_pass" if correct else "cannot_pass",
                        "is_correct": correct,
                        "is_uncertain": False,
                        "error_category": "none" if correct else "calculation_collapse",
                    }
                )
    return pd.DataFrame(rows * 8)


def test_build_transactions_one_per_row() -> None:
    df = _toy_features()
    txns = build_transactions(df)
    assert len(txns) == len(df)
    sample = txns[0]
    assert any(item.startswith("level=") for item in sample)
    assert any(item.startswith("error_category=") for item in sample)


def test_mine_rules_emits_outcome_subset() -> None:
    df = _toy_features()
    result = mine_rules(df, min_support=0.05, min_confidence=0.5)
    assert "outcome_rules" in result
    if not result["outcome_rules"].empty:
        head = result["outcome_rules"].iloc[0]
        rhs = head["consequents"]
        assert isinstance(rhs, tuple)
        assert rhs[0].split("=")[0] in {"is_correct", "is_uncertain", "ai_judgment", "error_category"}
