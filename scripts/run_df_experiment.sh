#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

WORKERS="${WORKERS:-12}"
LOG_EVERY="${LOG_EVERY:-5}"
FLUSH_EVERY="${FLUSH_EVERY:-5}"
REPEATS="${REPEATS:-3}"
REPEAT_MODE="${REPEAT_MODE:-copy}"
PROVIDER="${PROVIDER:-df}"

if [[ -f ".env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source ".env"
  set +a
fi

if [[ -z "${DF_API_URL:-}" ]]; then
  export DF_API_URL="http://123.129.219.111:3000/v1"
fi

if [[ -z "${DF_API_KEY:-}" ]]; then
  printf "DF_API_KEY is not set. Paste it now (input hidden): " >&2
  read -rs DF_API_KEY
  printf "\n" >&2
  export DF_API_KEY
fi

if [[ -z "${DF_API_KEY:-}" ]]; then
  echo "DF_API_KEY is still empty; aborting." >&2
  exit 1
fi

echo "Running from: $ROOT_DIR"
echo "Provider: $PROVIDER"
echo "DF_API_URL: $DF_API_URL"
echo "Workers: $WORKERS"
echo "Repeats: $REPEATS"
echo "Repeat mode: $REPEAT_MODE"
echo "Log every: $LOG_EVERY"
echo "Flush every: $FLUSH_EVERY"

if [[ ! -f "data/experiment_prompts.csv" ]]; then
  python scripts/build_experiment_prompts.py
fi

python scripts/collect_experiment_responses.py \
  --provider "$PROVIDER" \
  --repeats "$REPEATS" \
  --repeat-mode "$REPEAT_MODE" \
  --workers "$WORKERS" \
  --log-every "$LOG_EVERY" \
  --flush-every "$FLUSH_EVERY"

python scripts/build_experiment_features.py
python scripts/analyze_experiment.py --provider "$PROVIDER" --repeats "$REPEATS"

echo "Done."
echo "Raw responses: data/raw/model_responses_experiment.csv"
echo "Behavior features: data/processed/behavior_features_experiment.csv"
echo "Analysis outputs: outputs_experiment/"
