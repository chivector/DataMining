# 大语言模型空间建模能力挖掘分析

本项目围绕“电动轮椅在狭窄楼梯/转角处能否顺利转弯”这一空间推理场景，构造多层级 Prompt 数据集，采集不同 LLM 的回答，并对模型的判断稳定性、噪声敏感度、描述层级差异和失效模式进行数据挖掘分析。

## 项目结构

```text
.
├── config/
│   └── experiment.yml              # 实验层级、噪声项、模拟模型、API 参数、FP-Growth 阈值
├── data/
│   ├── prompts.csv                 # Prompt 实验矩阵
│   ├── raw/model_responses.csv     # AI 行为原始回复
│   └── processed/behavior_features.csv
├── outputs/
│   ├── figures/                    # 热力图、雷达图、聚类图等
│   └── tables/                     # 准确率、噪声翻转、失效模式、关联规则等表
├── docs/
│   ├── experiment_design.md        # 实验设计
│   └── how_to_run_experiment.md    # 实验执行说明
├── scripts/
│   ├── run_pipeline.py             # 一键运行 mock 全流程
│   ├── 01_generate_prompts.py
│   ├── 02_collect_responses.py     # 支持 --resume / --limit / --on-error
│   ├── 03_build_features.py
│   └── 04_analyze.py               # 含决策树、K-Means、FP-Growth
├── src/spatial_llm_mining/
│   ├── prompts.py                  # 场景与 Prompt 渲染
│   ├── providers.py                # mock + DF/OpenAI/Anthropic/DeepSeek
│   ├── features.py                 # 行为特征抽取
│   ├── analysis.py                 # 描述性 + 决策树 + 聚类
│   ├── association.py              # FP-Growth 关联规则挖掘
│   └── report.py                   # 可选 PDF 报告
└── tests/
```

## 快速运行（mock 离线模式）

```powershell
python scripts/run_pipeline.py
```

使用确定性 mock 模型生成可复现实验数据，无需 API Key。运行后会生成：

- `data/prompts.csv`
- `data/raw/model_responses.csv`
- `data/processed/behavior_features.csv`
- `outputs/figures/*.png`
- `outputs/tables/*.csv`（含 `frequent_itemsets.csv`、`association_rules.csv`、`outcome_rules.csv`）

## 使用 DF / OpenAI-compatible API

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

> 不要把 API key 写入仓库文件；即使仓库是私有的，也建议只用环境变量注入。

跑一次 1cm 触底通连测试：

```powershell
python scripts/test_api_connection.py --model gpt-4o
```

正式采集（默认从 `df_models` 取模型，可重复采样、可断点续采）：

```powershell
python scripts/01_generate_prompts.py
python scripts/02_collect_responses.py --provider df --models gpt-4o --repeats 3
python scripts/02_collect_responses.py --provider df --models gpt-4o,gpt-4o-mini --repeats 3 --resume
python scripts/03_build_features.py
python scripts/04_analyze.py
```

`02_collect_responses.py` 关键开关：

- `--resume`：跳过 `data/raw/model_responses.csv` 中已有的 `(model, repeat, prompt_id)` 三元组。
- `--limit N`：限制本轮新增的调用次数，便于做小样本冒烟。
- `--on-error skip|abort`：单次失败时跳过（默认）还是终止。
- 重试与超时使用 `experiment.yml > api > max_retries / retry_backoff_seconds / timeout_seconds`。

## 其他真实模型 API

```powershell
python scripts/02_collect_responses.py --provider openai --models gpt-4.1,gpt-4o-mini
python scripts/02_collect_responses.py --provider anthropic --models claude-3-5-sonnet-latest
python scripts/02_collect_responses.py --provider deepseek --models deepseek-chat
```

依赖环境变量：`OPENAI_API_KEY`、`ANTHROPIC_API_KEY`、`DEEPSEEK_API_KEY`。

## 核心挖掘维度

- **判断准确率**：模型最终判断与场景参考标签是否一致。
- **层级一致性**：同一场景从 L1 自然语言、L2 参数描述到 L3 数学建模时，判断是否保持一致。
- **噪声翻转率**：加入材质、噪声、光照、情绪等无关信息后，相对无噪声版本是否翻转。
- **关键词级触发**：`config/noise_keywords.yml` 拆出每类噪声里的具体短语，记录哪些词被模型回复”复述”，FP-Growth 给出 `noise_keyword_hit=催促 → error_category=...` 一类细粒度规则。
- **1cm 微扰逻辑坍塌**：`outputs/tables/perturbation_flip.csv` 与 `perturbation_threshold.png` 展示 borderline 场景下楼梯净宽 / 转弯半径 ±1cm 是否触发判断翻转。
- **推理过程特征**：推理步数、是否使用公式、是否建立坐标系、回复长度。
- **失效模式**：概念混淆、计算崩溃、直觉过拟合、噪声牵引、单位混乱、信息不足。
- **错误回复文本聚类**：`outputs/tables/error_text_clusters.csv` 用 TF-IDF + KMeans 把错误样本聚类，给出每簇的高频 2-gram、主导模型、典型样例，对应任务里”归纳 AI 在轮椅转弯空间逻辑上的典型盲区”。
- **认知边界聚类**：基于上述指标用 K-Means 把模型分为视觉直觉型 / 符号逻辑型 / 噪声敏感型 / 混合稳健型。
- **关联规则（FP-Growth）**：在 `outputs/tables/outcome_rules.csv` 中给出形如 `{level=L3, has_noise=1} → error_category=calculation_collapse` 这类可解释的”扰动 → 失效”规则。
- **自动叙事性发现**：`outputs/findings.md` 自动从描述性表里抽取 top-k 反差并写成 markdown bullet，可直接拷贝进报告。

## 报告（可选）

```powershell
python scripts/04_analyze.py --build-report
```

产生 `reports/analysis_report.pdf`，包含统计摘要、模型边界表、决策树规则、可视化与 FP-Growth 结果。

## 说明

mock 数据用于完成端到端挖掘流程和报告样例，不代表真实模型表现。课程或论文提交建议使用真实 API 重新采集，并在报告中注明模型版本、采样日期、温度参数和重复次数。
