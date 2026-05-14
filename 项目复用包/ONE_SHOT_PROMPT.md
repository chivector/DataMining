# 下次直接复制给 Codex 的完整 Prompt

```text
这个项目类型是：已有 Prompt 的多模型 API 实验采集。请你直接执行，不要只给计划。

【工作边界】
- Prompt 生成部分已经由其他同学/上游脚本完成，本阶段不要重写 Prompt 生成逻辑。
- 重点是复用已有 Prompt，调用不同模型 API 跑实验，保存原始回复，并生成后续数据挖掘可用的数据表。
- 不要 git commit，不要新建分支。
- 不要把真实 API key、账号、私人邮箱、个人绝对路径写进代码、配置、复用包或报告。

【必须先读】
请先阅读当前项目的说明文件、配置文件、主要目录结构、已有数据和最近修改：
1. README.md、任务书、docs
2. config/experiment.yml
3. data/prompts*.csv 和 data/prompt_strategy_manifest.csv
4. scripts/build_experiment_prompts.py
5. scripts/collect_experiment_responses.py
6. scripts/build_experiment_features.py
7. scripts/analyze_experiment.py
8. src/spatial_llm_mining/experiment.py
9. src/spatial_llm_mining/providers.py
10. tests/test_experiment.py、tests/test_providers.py
11. git status

阅读后先建立事实表，明确：
- 当前复用哪些 Prompt 文件；
- 合并后 Prompt 总数是多少；
- 如何生成并使用 prompt_uid；
- 模型列表和重复次数是多少；
- API 调用总规模是多少；
- 输出文件有哪些；
- 哪些是原始回复，哪些是后续特征或分析表；
- 哪些模型或调用已经失败，需要重跑或过滤。

【实现任务】
请把已有 Prompt 接入 API 实验采集流程，确保：
- 生成或更新 data/experiment_prompts.csv；
- 每条 Prompt 有 strategy、experiment_id、prompt_uid；
- 采集脚本支持多模型、多 repeat、断点续跑；
- resume 键为 (provider, model, repeat, prompt_uid)；
- 支持 workers 并发、log-every 进度日志、flush-every 定期写盘；
- 失败调用记录 status=failed 和 error_message；
- 原始输出写入 data/raw/model_responses_experiment.csv；
- 行为特征写入 data/processed/behavior_features_experiment.csv；
- 分析输出写入 outputs_experiment/；
- 不覆盖历史 data/raw/model_responses.csv 和 outputs_real/。

【验收要求】
完成后必须：
1. 做 mock 小样本或真实 API 小样本 smoke test；
2. 检查 prompt_uid 唯一；
3. 检查无重复 (provider, model, repeat, prompt_uid)；
4. 检查 response 非空和 status 分布；
5. 运行 python -m pytest 或相关测试；
6. 汇总当前覆盖率、失败模型、失败原因和后续补跑建议。

【最终回复】
请简洁列出：
- 修改了哪些文件；
- 原始模型输出在哪里；
- 行为特征在哪里；
- 运行什么命令继续断点续跑；
- 做过哪些验证；
- 是否有模型失败、限流或权限问题需要处理。
```
