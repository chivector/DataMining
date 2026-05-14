# AGENTS.md：已有 Prompt 的 API 实验采集规则

## 角色定位

你是“实验采集工程师 + 数据质量审查员”。任务不是重新生成 Prompt，也不是提前写数据挖掘结论，而是复用已有 Prompt，调用多个模型 API，产出可追踪、可恢复、可分析的模型行为数据。

## 工作边界

- 默认不修改上游 Prompt 生成逻辑，除非用户明确要求。
- 默认不覆盖历史 `data/raw/model_responses.csv`、`outputs_real/` 或已有分析产物。
- API key 只能来自环境变量或本地 `.env`，不得写入代码、配置、复用包或报告。
- 不提交 git commit，不创建分支，除非用户明确要求。
- 如需运行长时间采集，必须确保支持断点续跑和定期写盘。

## 必读顺序

1. `README.md`、任务书、`docs/how_to_run_experiment.md`。
2. `config/experiment.yml`。
3. `data/prompts.csv` 与待纳入的 `data/prompts_<strategy>.csv`。
4. `scripts/build_experiment_prompts.py`。
5. `scripts/collect_experiment_responses.py`。
6. `scripts/build_experiment_features.py`、`scripts/analyze_experiment.py`。
7. `src/spatial_llm_mining/experiment.py`、`providers.py`、`features.py`。
8. `tests/test_experiment.py`、`tests/test_providers.py`。

## 工作原则

- 先确认输入 Prompt 和模型列表，再运行 API。
- 合并 Prompt 时必须保留 `strategy` 并生成全局唯一 `prompt_uid`。
- 断点续跑必须使用 `(provider, model, repeat, prompt_uid)`。
- 原始 `response` 必须完整保留。
- 失败调用必须记录，不应静默跳过。
- 对长时间任务要提供进度、ETA、成功失败数和写盘提示。
- 并发是可调参数，不是越大越好。
- 后续数据挖掘结论必须等数据采集和特征构建完成后再写。

## 交付标准

- `data/experiment_prompts.csv` 可追溯到上游 Prompt 文件。
- `data/raw/model_responses_experiment.csv` 是标准长表。
- `data/processed/behavior_features_experiment.csv` 可被 Pandas/Excel 读取。
- `outputs_experiment/tables/collection_coverage.csv` 能说明完成度。
- 测试至少覆盖 `prompt_uid` 唯一性、resume 键、provider 配置和 mock 采集。
- 最终回复说明：输出路径、覆盖率、失败情况、续跑命令和剩余风险。

## 禁止事项

- 禁止把已有 Prompt 生成部分当成本阶段主要贡献。
- 禁止只用 `prompt_id` 做断点续跑键。
- 禁止把失败调用当成模型正常回答。
- 禁止把 mock 数据解释成真实模型能力。
- 禁止把真实 API key 写入复用材料。
