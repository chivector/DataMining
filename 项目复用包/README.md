# 基于已有 Prompt 的多模型 API 实验采集：项目复用包

本复用包适用于“Prompt 已经由其他同学或上游脚本生成，当前小组负责调用不同模型 API 跑实验、保存模型原始回答，并为后续数据挖掘分析准备结构化数据”的项目。

它不是 Prompt 生成模板，也不是报告写作模板。核心任务是把已有 Prompt 矩阵变成可复现、可断点续跑、可追踪模型版本和运行参数的模型行为数据集。

## 适用项目

适合：

- 已经存在一个或多个 Prompt CSV 文件，且包含 `prompt_id`、`prompt`、实验标签或元数据字段。
- 需要调用多个 LLM/API 网关，对同一批 Prompt 做横向比较。
- 需要支持长时间运行、断点续跑、失败记录、并发控制和覆盖率检查。
- 后续有人会基于原始回复做特征抽取、数据挖掘、统计图表或报告。

不适合：

- 还没有 Prompt 数据，需要从零设计题目和采样策略的项目。
- 只需要人工少量复制粘贴模型回答的项目。
- 只写最终分析结论、不需要保留原始模型行为数据的项目。
- 必须把真实密钥写进代码或复用材料的项目。

## 本项目分工定位

本项目中，Prompt 生成部分已经完成，包括 baseline 和多种策略型 Prompt 文件。我们复用这些 Prompt，重点实现：

- 合并代表性 Prompt 子集，生成 `data/experiment_prompts.csv`。
- 通过 DF/OpenAI-compatible API 调用 12 个模型。
- 每条 Prompt 每个模型重复采样 3 次。
- 采集原始回复到 `data/raw/model_responses_experiment.csv`。
- 保留 `strategy`、`prompt_uid`、`model`、`repeat`、`status`、`latency_seconds`、`response` 等字段。
- 构建行为特征表 `data/processed/behavior_features_experiment.csv`，供后续分析使用。

当前正式实验规模：

```text
5 prompt sources × 300 prompts × 12 models × 3 repeats = 54,000 API calls
```

## 推荐目录结构

```text
project/
├─ config/                           # API 参数、模型列表、采样参数
├─ data/
│  ├─ prompts.csv                    # baseline Prompt
│  ├─ prompts_<strategy>.csv          # 上游生成的策略 Prompt
│  ├─ experiment_prompts.csv          # 本阶段合并后的实验 Prompt
│  ├─ raw/model_responses_experiment.csv
│  └─ processed/behavior_features_experiment.csv
├─ docs/                             # 运行说明和实验记录
├─ scripts/
│  ├─ build_experiment_prompts.py
│  ├─ collect_experiment_responses.py
│  ├─ build_experiment_features.py
│  ├─ analyze_experiment.py
│  └─ list_api_models.py
├─ src/                              # provider、特征抽取和分析代码
├─ tests/                            # 断点续跑、prompt_uid、provider 测试
└─ 项目复用包/                       # 本复用包
```

## 使用步骤

1. 填写 `PROJECT_INTAKE.md`，确认 Prompt 文件、模型来源、API 网关、运行规模和安全要求。
2. 按 `PLAN.md` 检查 Prompt 字段、构造全局唯一 `prompt_uid`，并确认断点续跑键。
3. 使用 `COMMANDS.md` 中的命令测试 API、列出模型、做小样本 smoke test。
4. 正式运行 `collect_experiment_responses.py` 或一键脚本，长时间采集模型回复。
5. 运行特征构建和覆盖率检查，确认是否存在失败、重复、空回复或模型不可用。
6. 将原始回复表和行为特征表交给后续数据挖掘/分析阶段。

## 核心原则

- 复用已有 Prompt，不重新发明 Prompt 生成策略。
- 原始回复必须完整保留，不只保存最终判断。
- 断点续跑键必须包含 `prompt_uid`，不能只用 `prompt_id`。
- 失败调用也要记录 `status=failed` 和 `error_message`。
- 并发数量要可控，遇到 429/500/503 或 timeout 时应降并发或分模型重跑。
- 不把真实 API key 写入复用包、README、配置文件或报告。

## 本复用包文件

- `AGENTS.md`：给未来 Codex 的 API 实验采集规则。
- `PLAN.md`：从 Prompt 接收到行为数据交付的阶段式计划。
- `ONE_SHOT_PROMPT.md`：下次直接复制给 Codex 的完整执行 prompt。
- `PROJECT_INTAKE.md`：用户填写的项目信息表。
- `COMMANDS.md`：本项目常用采集、续跑、检查命令。
- `REVIEW_CHECKLIST.md`：原始回复表和行为特征表的最终自查清单。
- `FINAL_QA_PROTOCOL.md`：采集交付前质量验证流程。
- `SUMMARY_THIS_PROJECT.md`：本项目 API 采集阶段经验总结。
- `CODEBASE_MAP.md`：当前代码结构和关键模块。
- `TROUBLESHOOTING.md`：API、断点续跑、并发和数据文件常见问题。
- `project-skill/SKILL.md`：Codex Skill 草稿。
