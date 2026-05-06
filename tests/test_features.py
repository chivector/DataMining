from spatial_llm_mining.features import count_reasoning_steps, extract_judgment


def test_extract_judgment_final_answer() -> None:
    assert extract_judgment("分析略。\n最终判断：能通过") == "can_pass"
    assert extract_judgment("分析略。\n最终判断：不能通过") == "cannot_pass"
    assert extract_judgment("分析略。\n最终判断：不确定") == "uncertain"


def test_extract_judgment_markdown_heading_styles() -> None:
    # 真实 gpt-4o 回复里出现的 markdown 标题格式
    assert extract_judgment("步骤略\n### 最终判断\n不能通过") == "cannot_pass"
    assert extract_judgment("步骤略\n### 最终判断\n能通过") == "can_pass"
    assert extract_judgment("步骤略\n### 最终判断\n不确定") == "uncertain"
    assert extract_judgment("步骤略\n**最终判断**：能通过") == "can_pass"
    assert extract_judgment("步骤略\n**最终判断** 不能通过") == "cannot_pass"


def test_count_reasoning_steps_numbered_lines() -> None:
    text = "1. 识别场景\n2. 估算余量\n3. 给出结论\n最终判断：能通过"
    assert count_reasoning_steps(text) == 3
