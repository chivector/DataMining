# 实验执行说明

## 1. 准备环境

```powershell
pip install -r requirements.txt
```

`config/experiment.yml` 只保留 API 地址和采样参数，不提交真实密钥：

```yaml
api:
  base_url: "http://123.129.219.111:3000/v1"
  api_key: ""
```

运行真实 API 采集前，通过环境变量提供密钥：

```powershell
$env:DF_API_URL="http://123.129.219.111:3000/v1"
$env:DF_API_KEY="你的密钥"
```

`bash` 同名变量也兼容；以及 `ResearchAgent` 风格的 `API_BASE` / `API_KEY`。优先级：构造参数 → 环境变量 → `config/experiment.yml`。请不要把 API key 写入仓库文件。

## 2. 生成 Prompt 实验矩阵

```powershell
python scripts/01_generate_prompts.py
```

输出 `data/prompts.csv`，默认 `20 场景 × 3 层级 × 5 干扰 = 300 条 Prompt`。

## 3. 测试 API 连通性

```powershell
python scripts/test_api_connection.py --model gpt-4o
```

接口正常会输出模型短回复。

## 4. 采集真实模型回答

最小冒烟（10 次调用，验证流程）：

```powershell
python scripts/02_collect_responses.py --provider df --models gpt-4o --repeats 1 --limit 10
```

正式采集：

```powershell
python scripts/02_collect_responses.py --provider df --models gpt-4o --repeats 3
```

多模型对比（可断点续采，已有的不会重复调）：

```powershell
python scripts/02_collect_responses.py --provider df --models gpt-4o,gpt-4o-mini,claude-3-5-sonnet-latest,deepseek-chat --repeats 3 --resume
```

输出 `data/raw/model_responses.csv`。脚本每 25 次调用增量写盘，中途断网/中断不会丢已采集到的样本，再次以 `--resume` 即可续跑。

## 5. 抽取行为特征

```powershell
python scripts/03_build_features.py
```

输出 `data/processed/behavior_features.csv`，关键列：`ai_judgment`、`is_correct`、`reasoning_steps`、`has_formula`、`uses_coordinate`、`error_category`。

## 6. 数据挖掘分析

```powershell
python scripts/04_analyze.py
```

产物：

```text
outputs/tables/accuracy_by_level.csv
outputs/tables/noise_flip_rate.csv
outputs/tables/level_consistency.csv
outputs/tables/failure_modes.csv
outputs/tables/model_boundaries.csv
outputs/tables/decision_tree_rules.json
outputs/tables/frequent_itemsets.csv
outputs/tables/association_rules.csv
outputs/tables/outcome_rules.csv
outputs/figures/accuracy_heatmap.png
outputs/figures/noise_flip_rate.png
outputs/figures/level_consistency.png
outputs/figures/failure_modes.png
outputs/figures/model_radar.png
outputs/figures/cluster_map.png
```

`outcome_rules.csv` 即任务要求里点名的 FP-Growth 关联规则结果（仅保留结果项位于规则右端的子集，便于解释“在何种条件下模型最容易给出某种判断或失效模式”）。

如需 PDF 报告：

```powershell
python scripts/04_analyze.py --build-report
```

## 7. 离线自测

```powershell
python scripts/run_pipeline.py
```

mock 模型走完整套流程，所有 csv/png 都会有可复现内容，便于确认环境是否就绪。

## 8. 实验记录规范

每次真实实验建议记录：日期时间、模型名、API 地址、`temperature`、`max_tokens`、`repeats`、是否改动 `config/experiment.yml`、采集失败和重试情况。**不要**把 API Key 与数据一起提交到仓库。
