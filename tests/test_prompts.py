from spatial_llm_mining.prompts import build_prompt_matrix


def test_prompt_matrix_size() -> None:
    prompts = build_prompt_matrix(
        levels=["L1", "L2", "L3"],
        noise_conditions={"none": "", "lighting": "灯光偏暗。"},
        num_cases=2,
    )
    assert len(prompts) == 12
    assert prompts["prompt_id"].is_unique
