# 最终自查清单：API 实验采集

## Prompt 输入

- [ ] 使用的是上游已生成 Prompt，不是临时手写 Prompt。
- [ ] `data/experiment_prompts.csv` 存在。
- [ ] 包含 `strategy`、`experiment_id`、`prompt_uid`。
- [ ] `prompt_uid` 全局唯一。
- [ ] 每个纳入策略的 Prompt 数量符合预期。
- [ ] Prompt 字段和实验元数据字段没有丢失。

## API 采集

- [ ] 模型列表与 `config/experiment.yml` 或命令行 `--models` 一致。
- [ ] 重复次数与实验计划一致。
- [ ] 完整调用规模已计算清楚。
- [ ] 采集脚本支持 `--resume`，且默认开启。
- [ ] resume 键为 `(provider, model, repeat, prompt_uid)`。
- [ ] 并发数 `--workers` 没有导致大量限流或失败。
- [ ] 采集过程中定期写盘。
- [ ] Ctrl+C 或异常中断后可继续运行同一命令续跑。

## 原始回复表

- [ ] `data/raw/model_responses_experiment.csv` 存在。
- [ ] 每行保留完整 `response`。
- [ ] 包含 `provider`、`model`、`repeat`、`collected_at`、`temperature`、`max_tokens`、`seed`。
- [ ] 包含 `status`、`error_message`、`latency_seconds`。
- [ ] 不存在重复 `(provider, model, repeat, prompt_uid)`。
- [ ] `status=success` 的记录没有空回复。
- [ ] 失败记录保留错误信息，未被静默删除。

## 特征与分析接口

- [ ] `data/processed/behavior_features_experiment.csv` 存在。
- [ ] 包含 `ai_judgment`、`is_correct`、`reasoning_steps`、`has_formula`、`uses_coordinate`、`error_category`。
- [ ] API 失败样本不会被当成正常模型回答解释。
- [ ] `outputs_experiment/tables/collection_coverage.csv` 存在。
- [ ] 已检查每个 `strategy × model × repeat` 的覆盖率。
- [ ] 后续分析知道哪些模型/策略尚未完成或失败较多。

## 安全与隐私

- [ ] 无真实 API key。
- [ ] 无账号、私人邮箱、个人绝对路径。
- [ ] 本地 `.env` 未被打包进复用包。
- [ ] 复用材料中的 API key 均为 `<API_KEY>` 占位符。
- [ ] 如果分享复用包，已运行关键词检查。

## 交付说明

- [ ] 列出原始模型输出路径。
- [ ] 列出行为特征路径。
- [ ] 列出覆盖率/失败统计路径。
- [ ] 给出继续断点续跑命令。
- [ ] 说明当前成功/失败模型和后续补跑建议。
