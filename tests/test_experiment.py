import pandas as pd

from spatial_llm_mining.experiment import (
    build_experiment_prompts,
    collect_response_rows,
    collection_coverage,
    collection_plan,
    mark_api_failures,
    response_key_set,
)
from spatial_llm_mining.features import extract_features
from spatial_llm_mining.providers import MockProvider


def _prompt_rows() -> list[dict]:
    return [
        {
            "prompt_id": "P001_L2_none",
            "case_id": "P001",
            "level": "L2",
            "noise_label": "none",
            "noise_text": "",
            "stair_width_cm": 96,
            "landing_depth_cm": 100,
            "wheelchair_width_cm": 64,
            "wheelchair_length_cm": 105,
            "turn_radius_cm": 82,
            "clearance_margin_cm": 18,
            "criticality": "wide",
            "reference_judgment": "can_pass",
            "prompt": "请判断电动轮椅能否完成 90 度转弯。最终判断：能通过/不能通过/不确定",
        }
    ]


def _write_prompt_source(path, prompt_id: str = "P001_L2_none") -> None:
    rows = _prompt_rows()
    rows[0]["prompt_id"] = prompt_id
    pd.DataFrame(rows).to_csv(path, index=False, encoding="utf-8-sig")


def test_build_experiment_prompts_makes_strategy_uid_unique(tmp_path) -> None:
    source_a = tmp_path / "a.csv"
    source_b = tmp_path / "b.csv"
    _write_prompt_source(source_a)
    _write_prompt_source(source_b)

    prompts = build_experiment_prompts([("baseline", source_a), ("other_strategy", source_b)])

    assert len(prompts) == 2
    assert prompts["prompt_uid"].is_unique
    assert set(prompts["prompt_uid"]) == {
        "baseline__P001_L2_none",
        "other_strategy__P001_L2_none",
    }


def test_resume_key_uses_prompt_uid_not_prompt_id(tmp_path) -> None:
    source_a = tmp_path / "a.csv"
    source_b = tmp_path / "b.csv"
    _write_prompt_source(source_a)
    _write_prompt_source(source_b)
    prompts = build_experiment_prompts([("baseline", source_a), ("other_strategy", source_b)])
    existing = pd.DataFrame(
        [
            {
                "provider": "mock",
                "model": "GPT-4o-sim",
                "repeat": 0,
                "prompt_uid": "baseline__P001_L2_none",
            }
        ]
    )

    plan = collection_plan(
        prompts,
        provider_name="mock",
        models=["GPT-4o-sim"],
        repeats=1,
        seen=response_key_set(existing),
    )

    assert len(plan) == 1
    assert plan[0][2]["prompt_uid"] == "other_strategy__P001_L2_none"


def test_mock_collection_preserves_strategy_and_builds_features(tmp_path) -> None:
    source_a = tmp_path / "a.csv"
    source_b = tmp_path / "b.csv"
    _write_prompt_source(source_a)
    _write_prompt_source(source_b)
    prompts = build_experiment_prompts([("baseline", source_a), ("other_strategy", source_b)])

    responses, failures = collect_response_rows(
        prompts=prompts,
        provider=MockProvider(),
        provider_name="mock",
        models=["GPT-4o-sim"],
        repeats=1,
    )
    features = mark_api_failures(extract_features(responses))

    assert failures == 0
    assert len(responses) == 2
    assert set(responses["strategy"]) == {"baseline", "other_strategy"}
    assert responses["response"].str.len().min() > 0
    assert len(features) == len(responses)
    assert {"strategy", "prompt_uid", "ai_judgment", "error_category"}.issubset(features.columns)


def test_collection_coverage_counts_expected_prompt_uids(tmp_path) -> None:
    source_a = tmp_path / "a.csv"
    source_b = tmp_path / "b.csv"
    _write_prompt_source(source_a)
    _write_prompt_source(source_b)
    prompts = build_experiment_prompts([("baseline", source_a), ("other_strategy", source_b)])
    responses, _ = collect_response_rows(
        prompts=prompts,
        provider=MockProvider(),
        provider_name="mock",
        models=["GPT-4o-sim"],
        repeats=1,
    )

    coverage = collection_coverage(
        responses=responses,
        prompts=prompts,
        models=["GPT-4o-sim"],
        repeats=1,
        provider_name="mock",
    )

    assert len(coverage) == 2
    assert set(coverage["coverage_rate"]) == {1.0}
    assert set(coverage["success_rows"]) == {1}
