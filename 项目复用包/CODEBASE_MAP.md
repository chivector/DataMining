# 本项目 API 采集代码结构说明

## 顶层目录

```text
config/                 模型列表、API 参数、重试参数、分析阈值
data/                   上游 Prompt、实验 Prompt、原始回复、行为特征
docs/                   实验设计与运行说明
outputs_experiment/     API 实验阶段分析表和图
scripts/                命令行入口脚本
src/spatial_llm_mining/ 核心包
tests/                  单元测试
项目复用包/             本次沉淀的 API 实验采集复用材料
```

## 上游 Prompt 输入

- `data/prompts.csv`：baseline Prompt。
- `data/prompts_real_world_archetype_matrix.csv`：现实原型策略 Prompt。
- `data/prompts_halton_space_filling.csv`：Halton 空间填充策略 Prompt。
- `data/prompts_dimensionless_ratio_design.csv`：无量纲比例策略 Prompt。
- `data/prompts_constraint_boundary_solver.csv`：约束边界求解策略 Prompt。
- 其他 `data/prompts_<strategy>.csv`：后续可扩展纳入的 Prompt 源。

## API 采集脚本入口

- `scripts/build_experiment_prompts.py`：合并 5 组 Prompt 源，输出 `data/experiment_prompts.csv`，新增 `strategy`、`experiment_id`、`prompt_uid`。
- `scripts/collect_experiment_responses.py`：调用 DF/OpenAI-compatible API，支持多模型、多重复、断点续跑、多线程、定期写盘、详细进度日志。
- `scripts/build_experiment_features.py`：从原始回复抽取 `ai_judgment`、`reasoning_steps`、`has_formula`、`uses_coordinate`、`error_category` 等行为特征。
- `scripts/analyze_experiment.py`：输出实验级统计表、覆盖率表和聚合图表。
- `scripts/list_api_models.py`：调用 `/models` 接口列出 API 网关支持模型。
- `scripts/run_df_experiment.ps1` / `scripts/run_df_experiment.sh`：一键运行采集、特征和分析流程。

## 核心模块

- `experiment.py`：实验 Prompt 合并、断点续跑键、采集计划、覆盖率、按策略统计。
- `providers.py`：mock、DF/OpenAI-compatible、OpenAI、Anthropic、DeepSeek provider；支持环境变量和本地 `.env`。
- `features.py`：最终判断解析、推理步数统计、公式/坐标系检测、错误类型分类。
- `analysis.py`：准确率、噪声翻转、层级一致性、模型边界、图表生成。
- `association.py`：FP-Growth 或 fallback 关联规则挖掘。
- `perturbation.py`：微扰翻转分析。
- `text_cluster.py`：错误回答文本聚类。

## 主要数据产物

- `data/experiment_prompts.csv`：本阶段统一 Prompt 输入表，1500 行。
- `data/raw/model_responses_experiment.csv`：API 原始回复表，一行对应一次 `(provider, model, repeat, prompt_uid)` 调用。
- `data/processed/behavior_features_experiment.csv`：结构化行为特征表。
- `outputs_experiment/tables/collection_coverage.csv`：采集覆盖率和失败情况。
- `outputs_experiment/tables/accuracy_by_strategy_level.csv`：按策略和层级聚合的正确率。
- `outputs_experiment/tables/noise_flip_rate_by_strategy.csv`：按策略聚合的噪声翻转率。
- `outputs_experiment/tables/level_consistency_by_strategy.csv`：按策略聚合的层级一致性。
- `outputs_experiment/tables/failure_modes_by_strategy.csv`：按策略聚合的失效模式。

## 测试重点

- `tests/test_experiment.py`：
  - 合并后 `prompt_uid` 唯一。
  - 不同策略中相同 `prompt_id` 不会被 resume 误跳过。
  - mock provider 下采集结果保留 `strategy` 和 `prompt_uid`。
  - 覆盖率表能正确计数。
- `tests/test_providers.py`：
  - provider 参数优先级。
  - 环境变量与 `.env` 加载。
  - 兼容常见误拼写 `DF_API_UEY`。

## 后续分析接口

本阶段只保证模型行为数据可采集、可恢复、可追踪。后续数据挖掘阶段应基于 `behavior_features_experiment.csv` 和 `outputs_experiment/tables/*.csv` 继续完成：

- 层级一致性分析。
- 噪声敏感度分析。
- 失效模式分类和聚类。
- 关联规则挖掘。
- 模型认知边界比较。
