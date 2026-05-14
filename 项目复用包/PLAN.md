# 可复用执行计划：已有 Prompt 的 API 实验采集

## 阶段 0：确认输入与边界

- [ ] 确认 Prompt 已由上游生成，本阶段不重写 Prompt 生成逻辑。
- [ ] 确认要纳入 API 采集的 Prompt 文件列表。
- [ ] 确认模型来源、API 网关、可用模型列表和调用预算。
- [ ] 确认是否允许运行长时间采集、并发采集和后续分析脚本。
- [ ] 确认 API key 只通过环境变量或本地 `.env` 提供，不写入复用包。

## 阶段 1：Prompt 表检查与合并

- [ ] 检查每个 Prompt CSV 是否包含 `prompt_id`、`prompt` 和必要元数据字段。
- [ ] 检查各策略文件字段是否一致。
- [ ] 为每条 Prompt 添加 `strategy`、`experiment_id`、`prompt_uid`。
- [ ] 确认 `prompt_uid` 全局唯一。
- [ ] 输出统一实验输入表，例如 `data/experiment_prompts.csv`。

## 阶段 2：模型与运行参数确认

- [ ] 通过 `/models` 或服务商文档确认模型 ID 可用。
- [ ] 更新 `config/experiment.yml` 中的 `df_models`。
- [ ] 确认 `temperature`、`max_tokens`、`timeout_seconds`、`max_retries`、`seed`。
- [ ] 确认完整调用规模：`prompt_count × model_count × repeats`。
- [ ] 根据网关稳定性选择 `--workers`、`--log-every`、`--flush-every`。

## 阶段 3：小样本冒烟

- [ ] 先运行 `list_api_models.py` 或 API 连通性测试。
- [ ] 用 `--limit` 采集少量样本。
- [ ] 检查输出 CSV 是否包含 `status=success`、非空 `response` 和合理 `latency_seconds`。
- [ ] 运行特征抽取，确认 `ai_judgment` 能被解析。
- [ ] 检查是否有重复 `(provider, model, repeat, prompt_uid)`。

## 阶段 4：正式采集

- [ ] 使用 `collect_experiment_responses.py` 正式采集。
- [ ] 开启 `--resume`，保留断点续跑。
- [ ] 使用 `--schedule interleaved`，让中途结果尽快覆盖不同模型和策略。
- [ ] 定期观察终端日志中的成功数、失败数、ETA 和当前模型。
- [ ] 遇到 429、500、503 或 timeout，先降低 `--workers` 或分模型采集。
- [ ] 中断时确认已写盘，再重新运行同一命令续跑。

## 阶段 5：特征与覆盖率检查

- [ ] 运行 `build_experiment_features.py`。
- [ ] 运行 `analyze_experiment.py` 生成 `collection_coverage.csv`。
- [ ] 检查每个 `strategy × model × repeat` 的覆盖率。
- [ ] 检查失败记录是否集中在某些模型或错误类型。
- [ ] 对持续失败的模型决定是否剔除、替换或单独补跑。

## 阶段 6：交付给数据挖掘阶段

- [ ] 保留原始回复表，不覆盖或截断。
- [ ] 保留行为特征表。
- [ ] 输出覆盖率和失败情况说明。
- [ ] 明确哪些模型/策略已完成，哪些只部分完成。
- [ ] 不提前写数据挖掘结论，只交付可分析数据和运行记录。
