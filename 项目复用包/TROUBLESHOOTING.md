# 常见问题与解决办法：API 实验采集

## 读不到 API key

症状：

- 报错 `DF provider requires DF_API_URL/DF_API_KEY`。

处理：

- PowerShell 中应使用 `$env:DF_API_KEY`，不是 `export`。
- 检查是否误写成 `DF_API_UEY`。当前 provider 已兼容这个误拼写，但推荐改回标准变量名。
- 也可以在项目根目录 `.env` 中写：

```bash
export DF_API_URL=<DF_API_URL>
export DF_API_KEY=<API_KEY>
```

## 不同策略的 Prompt 被误跳过

症状：

- 多个策略文件中都有 `C001_L1_none`，但采集时只跑了一个。
- `--resume` 后显示大量已完成，实际策略没有覆盖。

处理：

- 不要只用 `prompt_id` 做唯一键。
- 合并 Prompt 时生成 `prompt_uid = strategy + "__" + prompt_id`。
- 断点续跑键必须是 `(provider, model, repeat, prompt_uid)`。

## 早期结果只覆盖一个模型或一个策略

症状：

- 中途查看 CSV，发现只有 `gpt-4o` 或只有 baseline。

处理：

- 使用默认 `--schedule interleaved`。
- 如果脚本版本较旧，更新后中断并续跑。
- 已经采集的数据不会丢，resume 会跳过已完成键。

## 429 Too Many Requests

症状：

- `error_message` 中出现 429。
- 失败集中在高并发运行时。

处理：

- 降低 `--workers`，例如从 12 降到 4 或 2。
- 增大 `retry_backoff_seconds`。
- 分模型运行，避免同时请求多个高成本模型。

## 500/503 或 timeout

症状：

- `status=failed`，错误为 500、503、RemoteDisconnected 或 read timeout。

处理：

- 先确认不是全部模型都失败。
- 对持续失败模型单独小样本测试。
- 降低并发后重跑。
- 如模型长期不可用，保留失败记录并在覆盖率表中说明。

## 401 Unauthorized

症状：

- 某些模型返回 401。

处理：

- API key 有效，但该 key 可能无权调用该模型。
- 从 `/models` 列表只能说明模型存在，不一定说明当前 key 有权限。
- 将该模型从正式列表移除，或更换有权限的 key。

## 输出文件在哪里

原始模型回复：

```text
data/raw/model_responses_experiment.csv
```

结构化行为特征：

```text
data/processed/behavior_features_experiment.csv
```

覆盖率和分析表：

```text
outputs_experiment/tables/
```

## CSV 太大或 Excel 打开慢

处理：

- 用 Pandas 读取和筛选。
- 只查看必要列：`strategy`、`prompt_uid`、`model`、`repeat`、`status`、`latency_seconds`、`response`。
- 不要手动编辑原始 CSV，以免破坏断点续跑键。

## 真实密钥进入复用材料

症状：

- 复用包、README、配置或报告中出现真实 key。

处理：

- 立即改成 `<API_KEY>`。
- 本地使用 `.env` 或 PowerShell 环境变量。
- 打包前运行：

```powershell
rg "sk-|DF_API_KEY|API_KEY" 项目复用包
```

## PowerShell 中文或进度条显示混乱

症状：

- 终端中文乱码或 tqdm 进度条重复刷屏。

处理：

- 文件内容一般仍是 UTF-8 正常保存。
- 不把终端乱码复制到报告或复用材料。
- 如需干净日志，可把 `--log-every` 调大或设为 `0`。
