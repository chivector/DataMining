---
name: "prompt-api-experiment-runner"
description: "Use when the user has existing Prompt CSV files and wants Codex to run or repair a multi-model API collection pipeline, including prompt_uid construction, resume-safe response collection, feature extraction, and coverage checks."
---

# Prompt API Experiment Runner Skill

## When to Use

Use this skill when:

- Prompt files already exist.
- The task is to call model APIs over those prompts.
- The user needs raw model responses and structured behavior data.
- The collection may be long-running and must support resume, progress logs, and failure tracking.

Do not use this skill as a Prompt generation workflow. Treat Prompt generation as upstream input unless the user explicitly asks to change it.

## Workflow

1. Inspect prompt sources:
   - `data/prompts.csv`
   - selected `data/prompts_<strategy>.csv`
   - `data/prompt_strategy_manifest.csv` when present.
2. Build or verify the experiment prompt table:
   - add `strategy`;
   - add `experiment_id`;
   - add globally unique `prompt_uid`;
   - confirm no duplicate `prompt_uid`.
3. Inspect model/provider config:
   - `config/experiment.yml`;
   - API base URL;
   - model list;
   - repeats;
   - temperature/max_tokens/timeout/retries.
4. Run a smoke test:
   - mock provider first when possible;
   - real API with `--limit` before full collection.
5. Run collection:
   - use `(provider, model, repeat, prompt_uid)` as resume key;
   - use controlled `--workers`;
   - keep `--flush-every` low enough for long runs;
   - keep detailed progress logs.
6. Build features:
   - extract final judgment;
   - count reasoning steps;
   - detect formula and coordinate usage;
   - classify errors;
   - mark API failures separately.
7. Check coverage:
   - no duplicate keys;
   - no empty successful responses;
   - coverage per `strategy × model × repeat`;
   - failure concentration by model/status/error.
8. Return a concise status summary and exact resume command.

## Quality Rules

- Never write real API keys into tracked files or reusable materials.
- Never silently drop failed API calls.
- Never use `prompt_id` alone as the resume key when multiple strategies exist.
- Preserve full raw `response` text.
- Do not interpret partial raw responses as final data-mining conclusions.
- If a model returns repeated 401/429/500/503/timeouts, recommend lowering concurrency, splitting by model, replacing the model, or treating it as incomplete.

## Common Commands

```powershell
python scripts/build_experiment_prompts.py
python scripts/list_api_models.py
python scripts/collect_experiment_responses.py --provider df --workers 8 --log-every 5 --flush-every 5
python scripts/build_experiment_features.py
python scripts/analyze_experiment.py
python -m pytest tests/test_experiment.py tests/test_providers.py
```

## Final Response

Keep the final response concise. Include:

- raw response path;
- behavior feature path;
- coverage/analysis path;
- current success/failure state;
- exact command to continue resume;
- any model/API risks.
