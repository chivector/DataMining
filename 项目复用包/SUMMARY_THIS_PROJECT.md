# 本项目 API 实验采集阶段经验总结

## 项目目标

本阶段的目标不是重新设计 Prompt，而是复用已经生成好的轮椅转弯 Prompt，调用多个大语言模型 API，采集模型面对同一批空间推理问题时的原始回答。最终产物要服务后续数据挖掘分析：判断抽取、推理过程特征、噪声翻转率、层级一致性、模型边界聚类和失效模式归纳。

## 本阶段实际完成的工作流

1. 接收并复用上游 Prompt 文件：`data/prompts.csv` 与若干 `data/prompts_<strategy>.csv`。
2. 选取 5 组代表性 Prompt 源：baseline、现实原型、Halton 空间填充、无量纲比例、约束边界求解。
3. 合并为 `data/experiment_prompts.csv`，新增 `strategy`、`experiment_id`、`prompt_uid`。
4. 将断点续跑键改为 `(provider, model, repeat, prompt_uid)`，避免不同策略中相同 `prompt_id` 被误判为已完成。
5. 使用 DF/OpenAI-compatible 网关调用 12 个模型，每条 Prompt 重复 3 次。
6. 支持多线程采集、进度日志、ETA、定期写盘、Ctrl+C 中断写盘。
7. 原始回复写入 `data/raw/model_responses_experiment.csv`。
8. 行为特征写入 `data/processed/behavior_features_experiment.csv`。
9. 输出覆盖率、按策略准确率、噪声翻转率、层级一致性和失效模式表，供后续分析继续使用。

## 关键实验规模

- Prompt 源数量：5 组。
- 每组 Prompt：`20 cases × 3 levels × 5 noises = 300`。
- API 阶段 Prompt 总数：1500。
- 模型数量：12。
- 重复次数：3。
- 理论调用总数：`1500 × 12 × 3 = 54,000`。

## 当前模型集合

保留已开始采集的 4 个模型：

- `gpt-4o`
- `gpt-4o-mini`
- `claude-3-5-sonnet-latest`
- `deepseek-chat`

新增 8 个强模型：

- `gpt-5.5`
- `claude-opus-4-6`
- `claude-sonnet-4-6-thinking`
- `gemini-3-flash-preview`
- `grok-4`
- `deepseek-v4-pro`
- `qwen3-max`
- `Kimi-K2-Thinking`

## 本项目关键文件

- `data/experiment_prompts.csv`：API 采集阶段统一 Prompt 表。
- `data/raw/model_responses_experiment.csv`：模型原始回答长表。
- `data/processed/behavior_features_experiment.csv`：行为特征表。
- `outputs_experiment/`：实验阶段分析输出目录。
- `config/experiment.yml`：模型列表、API 参数、重试参数。
- `scripts/build_experiment_prompts.py`：合并 Prompt 源并生成 `prompt_uid`。
- `scripts/collect_experiment_responses.py`：多模型 API 采集、断点续跑、并发、写盘。
- `scripts/build_experiment_features.py`：从原始回复抽取行为特征。
- `scripts/analyze_experiment.py`：生成实验级统计表和图。
- `scripts/list_api_models.py`：列出 API 网关支持的模型。
- `scripts/run_df_experiment.ps1` / `scripts/run_df_experiment.sh`：一键运行脚本。
- `src/spatial_llm_mining/experiment.py`：实验 prompt 合并、采集计划、覆盖率和策略级统计。
- `src/spatial_llm_mining/providers.py`：DF/OpenAI-compatible provider 与本地 `.env` 读取。
- `tests/test_experiment.py`：验证 `prompt_uid`、resume 和 mock 采集。

## 返工原因

- 初始采集脚本只用 `(model, repeat, prompt_id)` 判断断点续跑，无法区分不同策略中的同名 Prompt。
- 一开始采集顺序按模型优先，早期结果只覆盖单个模型和 baseline，不利于中途查看部分数据。
- 长时间 API 调用需要更密集的进度日志、ETA、写盘提示和 Ctrl+C 保护。
- 模型数量从早期 4 个扩展到 12 个，配置和文档需要同步。
- 用户环境中 API key 设置容易出现 PowerShell 变量名错误，因此 provider 兼容了 `DF_API_UEY` 这个常见误拼写。

## 最终策略

- 将上游 Prompt 视为固定输入，本阶段只负责“实验采集层”。
- 用 `prompt_uid = strategy + "__" + prompt_id` 作为跨策略唯一标识。
- 默认使用 `--schedule interleaved`，让部分结果尽快覆盖多个模型、策略和重复轮次。
- 默认使用可调 `--workers` 并发，建议根据网关稳定性从 4、8、12 逐步调整。
- 失败记录不丢弃，保留 `status` 和 `error_message`，后续可以单独补跑或过滤。

## 以后要避免

- 不要把 Prompt 生成阶段和 API 采集阶段混成一个任务。
- 不要只保存最终判断，必须保留完整 `response`。
- 不要直接覆盖历史 `data/raw/model_responses.csv` 或 `outputs_real/`。
- 不要把失败调用当成模型回答参与行为分析。
- 不要在复用包、README、报告或配置里写真实 API key。
- 不要无脑提高并发；遇到 429、500、503、timeout 时先降并发或分模型运行。

## 可迁移经验

- 长时间 API 实验首先要设计“可恢复性”，其次才是速度。
- 多策略 Prompt 合并时必须提前解决 ID 冲突。
- 原始行为数据应采用长表结构，便于后续按模型、策略、层级、扰动切片。
- 进度日志不是装饰，它能帮助及时发现某个模型持续失败或网关限流。
