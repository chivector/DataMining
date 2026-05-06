import pandas as pd

from spatial_llm_mining.findings import build_findings


def test_findings_capture_l1_l3_gap() -> None:
    accuracy = pd.DataFrame(
        [
            {"model": "M1", "level": "L1", "accuracy": 0.90},
            {"model": "M1", "level": "L2", "accuracy": 0.80},
            {"model": "M1", "level": "L3", "accuracy": 0.60},
        ]
    )
    bullets = build_findings(
        features=pd.DataFrame(),
        analysis={
            "accuracy": accuracy,
            "noise": pd.DataFrame(),
            "consistency": pd.DataFrame(),
            "failures": pd.DataFrame(),
        },
    )
    assert any("M1" in b and "L3" in b for b in bullets)


def test_findings_handle_empty_inputs() -> None:
    bullets = build_findings(
        features=pd.DataFrame(),
        analysis={
            "accuracy": pd.DataFrame(),
            "noise": pd.DataFrame(),
            "consistency": pd.DataFrame(),
            "failures": pd.DataFrame(),
        },
    )
    assert bullets == []
