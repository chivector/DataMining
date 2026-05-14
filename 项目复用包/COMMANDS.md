# 常用命令：已有 Prompt 的 API 实验采集

## 项目审阅

```powershell
Get-ChildItem -Force
rg --files
git status --short
```

## 环境安装

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 配置 API key

PowerShell 当前窗口临时设置：

```powershell
$env:DF_API_URL="<DF_API_URL>"
$env:DF_API_KEY="<API_KEY>"
```

或项目根目录 `.env`：

```bash
export DF_API_URL=<DF_API_URL>
export DF_API_KEY=<API_KEY>
```

## 查看 API 支持模型

```powershell
python scripts/list_api_models.py
```

## 构建实验 Prompt 长表

```powershell
python scripts/build_experiment_prompts.py
```

检查总行数和 `prompt_uid`：

```powershell
(Import-Csv data\experiment_prompts.csv | Measure-Object).Count
Import-Csv data\experiment_prompts.csv |
  Group-Object prompt_uid |
  Where-Object Count -gt 1
```

## 小样本冒烟

mock 冒烟：

```powershell
python scripts/collect_experiment_responses.py --provider mock --models GPT-4o-sim --repeats 1 --limit 20 --output data/raw/model_responses_experiment_smoke.csv
python scripts/build_experiment_features.py --input data/raw/model_responses_experiment_smoke.csv --output data/processed/behavior_features_experiment_smoke.csv
```

真实 API 小样本：

```powershell
python scripts/collect_experiment_responses.py --provider df --models gpt-4o --repeats 1 --limit 20 --workers 2 --log-every 5 --flush-every 5 --output data/raw/model_responses_experiment_smoke.csv
```

## 正式采集与断点续跑

使用配置中的 12 个模型：

```powershell
python scripts/collect_experiment_responses.py --provider df --workers 8 --log-every 5 --flush-every 5
```

如果网关稳定，可以提高并发：

```powershell
python scripts/collect_experiment_responses.py --provider df --workers 12 --log-every 5 --flush-every 5
```

如果出现 429、500、503 或 timeout，降低并发：

```powershell
python scripts/collect_experiment_responses.py --provider df --workers 2 --log-every 10 --flush-every 10
```

只补某些模型：

```powershell
python scripts/collect_experiment_responses.py --provider df --models gpt-5.5,deepseek-v4-pro --repeats 3 --workers 4 --log-every 5 --flush-every 5
```

## 构建行为特征与分析输出

```powershell
python scripts/build_experiment_features.py
python scripts/analyze_experiment.py
```

主要输出：

```text
data/raw/model_responses_experiment.csv
data/processed/behavior_features_experiment.csv
outputs_experiment/tables/collection_coverage.csv
outputs_experiment/tables/accuracy_by_strategy_level.csv
outputs_experiment/tables/noise_flip_rate_by_strategy.csv
outputs_experiment/tables/level_consistency_by_strategy.csv
outputs_experiment/tables/failure_modes_by_strategy.csv
```

## 快速检查采集状态

行数、状态和模型覆盖：

```powershell
$rows = Import-Csv data\raw\model_responses_experiment.csv
$rows.Count
$rows | Group-Object status | Select-Object Name,Count
$rows | Group-Object model,status | Select-Object Name,Count
```

重复键检查：

```powershell
Import-Csv data\raw\model_responses_experiment.csv |
  Group-Object provider,model,repeat,prompt_uid |
  Where-Object Count -gt 1
```

空回复检查：

```powershell
Import-Csv data\raw\model_responses_experiment.csv |
  Where-Object { $_.status -eq "success" -and [string]::IsNullOrWhiteSpace($_.response) }
```

覆盖率检查：

```powershell
Import-Csv outputs_experiment\tables\collection_coverage.csv |
  Sort-Object success_rate |
  Select-Object -First 20 |
  Format-Table -AutoSize
```

## 运行测试

```powershell
python -m pytest tests/test_experiment.py tests/test_providers.py
python -m pytest
```

## 打包复用包

```powershell
Compress-Archive -Path 项目复用包 -DestinationPath 项目复用包.zip -Force
```

## 安全提醒

- API key 只放环境变量或本地 `.env`。
- 不把真实 key 写入 `config/`、README、CSV、报告或复用包。
- 如果要分享复用包，先用 `rg "sk-|API_KEY|DF_API_KEY" 项目复用包` 检查。
