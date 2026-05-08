from spatial_llm_mining.prompts import ADDITIONAL_PROMPT_STRATEGIES, build_prompt_matrix


def test_prompt_matrix_size() -> None:
    prompts = build_prompt_matrix(
        levels=["L1", "L2", "L3"],
        noise_conditions={"none": "", "lighting": "灯光偏暗。"},
        num_cases=2,
    )
    assert len(prompts) == 12
    assert prompts["prompt_id"].is_unique


def test_additional_prompt_strategies_keep_matrix_shape() -> None:
    assert len(ADDITIONAL_PROMPT_STRATEGIES) == 11
    expected_columns = list(
        build_prompt_matrix(
            levels=["L1"],
            noise_conditions={"none": ""},
            num_cases=1,
        ).columns
    )

    for strategy in ADDITIONAL_PROMPT_STRATEGIES:
        prompts = build_prompt_matrix(
            levels=["L1", "L2", "L3"],
            noise_conditions={"none": "", "lighting": "灯光偏暗。"},
            num_cases=2,
            strategy=strategy.name,
        )
        assert len(prompts) == 12
        assert prompts["prompt_id"].is_unique
        assert list(prompts.columns) == expected_columns


def test_additional_prompt_strategies_cover_both_judgments() -> None:
    for strategy in ADDITIONAL_PROMPT_STRATEGIES:
        prompts = build_prompt_matrix(
            levels=["L1", "L2", "L3"],
            noise_conditions={"none": ""},
            num_cases=20,
            strategy=strategy.name,
        )
        assert {"can_pass", "cannot_pass"}.issubset(set(prompts["reference_judgment"]))
