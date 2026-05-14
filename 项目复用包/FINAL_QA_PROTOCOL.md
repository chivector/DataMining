# 最终交付前质量验证流程：API 实验采集

## 1. 基础检查

```powershell
git status --short
Get-ChildItem -Force
rg --files
```

检查：

- 是否只修改了允许范围内的文件。
- 是否没有误改上游 Prompt 生成逻辑。
- 是否没有把本地 `.env`、缓存或临时文件打包。

## 2. Prompt 表检查

```powershell
python scripts/build_experiment_prompts.py
```

```powershell
$prompts = Import-Csv data\experiment_prompts.csv
$prompts.Count
$prompts | Group-Object strategy | Select-Object Name,Count
$prompts | Group-Object prompt_uid | Where-Object Count -gt 1
```

必须确认：

- `prompt_uid` 无重复。
- 策略数量和每个策略样本数符合计划。
- `prompt` 字段非空。

## 3. 小样本采集检查

mock：

```powershell
python scripts/collect_experiment_responses.py --provider mock --models GPT-4o-sim --repeats 1 --limit 20 --output data/raw/model_responses_experiment_smoke.csv
```

真实 API：

```powershell
python scripts/collect_experiment_responses.py --provider df --models gpt-4o --repeats 1 --limit 20 --workers 2 --output data/raw/model_responses_experiment_smoke.csv
```

检查：

```powershell
$rows = Import-Csv data\raw\model_responses_experiment_smoke.csv
$rows | Group-Object status | Select-Object Name,Count
$rows | Where-Object { $_.status -eq "success" -and [string]::IsNullOrWhiteSpace($_.response) }
```

## 4. 正式采集状态检查

```powershell
$rows = Import-Csv data\raw\model_responses_experiment.csv
$rows.Count
$rows | Group-Object model,status | Select-Object Name,Count
$rows | Group-Object provider,model,repeat,prompt_uid | Where-Object Count -gt 1
```

必须确认：

- 无重复采集键。
- 成功记录有非空回复。
- 失败记录包含 `error_message`。
- 失败是否集中于某些模型或权限问题。

## 5. 特征和覆盖率检查

```powershell
python scripts/build_experiment_features.py
python scripts/analyze_experiment.py
```

```powershell
Import-Csv outputs_experiment\tables\collection_coverage.csv |
  Sort-Object success_rate |
  Select-Object -First 20 |
  Format-Table -AutoSize
```

检查：

- 覆盖率表存在。
- 特征表存在。
- API 失败样本不会被解释为正常模型判断。
- 后续数据挖掘知道哪些组合缺失。

## 6. 测试

```powershell
python -m pytest tests/test_experiment.py tests/test_providers.py
python -m pytest
```

## 7. 复用包 zip 检查

```powershell
Compress-Archive -Path "项目复用包" -DestinationPath "项目复用包.zip" -Force
```

验证：

```powershell
Add-Type -AssemblyName System.IO.Compression.FileSystem
$zip = [IO.Compression.ZipFile]::OpenRead("项目复用包.zip")
$zip.Entries | Select-Object FullName, Length
$zip.Dispose()
```

必须包含：

- `README.md`
- `AGENTS.md`
- `PLAN.md`
- `ONE_SHOT_PROMPT.md`
- `PROJECT_INTAKE.md`
- `REVIEW_CHECKLIST.md`
- `FINAL_QA_PROTOCOL.md`
- `SUMMARY_THIS_PROJECT.md`
- `COMMANDS.md`
- `CODEBASE_MAP.md`
- `TROUBLESHOOTING.md`

## 8. 安全检查

```powershell
rg "sk-|DF_API_KEY=|API_KEY=" 项目复用包
```

若出现真实密钥，必须删除或替换成 `<API_KEY>` 后重新打包。
