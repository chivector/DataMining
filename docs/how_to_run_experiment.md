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

也可以在项目根目录创建不会被 git 提交的 `.env` 文件：

```bash
export DF_API_URL=http://123.129.219.111:3000/v1
export DF_API_KEY=你的密钥
```

`bash` 同名变量也兼容；以及 `ResearchAgent` 风格的 `API_BASE` / `API_KEY`。优先级：构造参数 → 环境变量 → 本地 `.env` → `config/experiment.yml`。请不要把 API key 写入仓库代码或已跟踪配置文件。

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

多策略正式实验的 `collect_experiment_responses.py` 会打印更详细的运行状态：启动时输出实验规模、模型列表、断点续跑跳过数量和输出路径；运行中输出当前 `model/repeat/strategy/level/noise/prompt_uid`、成功失败数、平均耗时和预计剩余时间。

```powershell
python scripts/collect_experiment_responses.py --provider df --workers 4 --log-every 5 --flush-every 5
```

- `--workers N`：并发 API 调用数量。建议先用 `2` 或 `4`；如果接口限流或失败变多，就降回 `1`。
- `--schedule interleaved|sequential`：默认 `interleaved`，让早期结果尽快覆盖多个模型、重复轮次和策略；`sequential` 保持旧的模型优先顺序。
- `--log-every N`：每 N 次调用打印一条详细进度，`0` 表示关闭详细日志。
- `--flush-every N`：每 N 次调用写盘一次；数值越小，中断时未写入的尾部进度越少。

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

## 9. 多策略正式实验流程

如果要跑本轮“分层主样本”实验，先把 baseline 和 4 个重点策略合并为统一长表：

```powershell
python scripts/build_experiment_prompts.py
```

输出 `data/experiment_prompts.csv`，会新增：

- `strategy`：prompt 来源策略。
- `experiment_id`：本轮实验编号。
- `prompt_uid`：`strategy + "__" + prompt_id`，用于避免不同策略中的 `prompt_id` 冲突。

先做 mock 冒烟：

```powershell
python scripts/collect_experiment_responses.py --provider mock --models GPT-4o-sim --repeats 1 --limit 20 --output data/raw/model_responses_experiment_smoke.csv
python scripts/build_experiment_features.py --input data/raw/model_responses_experiment_smoke.csv --output data/processed/behavior_features_experiment_smoke.csv
python scripts/analyze_experiment.py --provider mock --models GPT-4o-sim --repeats 1 --responses data/raw/model_responses_experiment_smoke.csv --input data/processed/behavior_features_experiment_smoke.csv --output-dir outputs_experiment_smoke
```

正式采集使用 DF 统一网关，默认读取 `config/experiment.yml` 里的 12 个 `df_models`，默认 `repeats=3`、`--repeat-mode copy` 且开启断点续跑：

```powershell
python scripts/collect_experiment_responses.py --provider df
python scripts/build_experiment_features.py
python scripts/analyze_experiment.py
```

`--repeat-mode copy` 只对每个 `(provider, model, prompt_uid)` 调用一次 API，然后复制成 repeat 0/1/2 三行，保留三重复表结构但避免三倍额度消耗。如果需要真实三次独立采样，改用：

```powershell
python scripts/collect_experiment_responses.py --provider df --repeat-mode api
```

如果希望终端输出更密集一些，可以调小详细日志和写盘间隔：

```powershell
python scripts/collect_experiment_responses.py --provider df --workers 4 --log-every 5 --flush-every 5
```

主要输出：

```text
data/raw/model_responses_experiment.csv
data/processed/behavior_features_experiment.csv
outputs_experiment/tables/accuracy_by_strategy_level.csv
outputs_experiment/tables/noise_flip_rate_by_strategy.csv
outputs_experiment/tables/level_consistency_by_strategy.csv
outputs_experiment/tables/failure_modes_by_strategy.csv
outputs_experiment/tables/collection_coverage.csv
```

默认特征构建会丢弃 `status != success` 的 API 失败行，避免网络错误、鉴权错误和超时记录进入挖掘统计。如果需要保留失败行做采集诊断，可运行：

```powershell
python scripts/build_experiment_features.py --keep-failed
```
