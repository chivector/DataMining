from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from spatial_llm_mining.analysis import run_analysis
from spatial_llm_mining.experiment import (
    accuracy_by_strategy_level,
    collection_coverage,
    failure_modes_by_strategy,
    level_consistency_by_strategy,
    noise_flip_rate_by_strategy,
)
from spatial_llm_mining.io_utils import ensure_dir, load_yaml, project_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run aggregate and strategy-level analysis for the experiment.")
    parser.add_argument(
        "--input",
        default=str(project_path("data", "processed", "behavior_features_experiment.csv")),
    )
    parser.add_argument(
        "--responses",
        default=str(project_path("data", "raw", "model_responses_experiment.csv")),
    )
    parser.add_argument("--prompts", default=str(project_path("data", "experiment_prompts.csv")))
    parser.add_argument("--output-dir", default=str(project_path("outputs_experiment")))
    parser.add_argument("--provider", default="df")
    parser.add_argument("--models", default=None, help="Comma-separated model names. Defaults to config df_models.")
    parser.add_argument("--repeats", type=int, default=3)
    return parser.parse_args()


def _models_from_config(raw: str | None) -> list[str]:
    if raw:
        return [m.strip() for m in raw.split(",") if m.strip()]
    config = load_yaml(project_path("config", "experiment.yml"))
    return list(config["df_models"])


def main() -> None:
    args = parse_args()
    features = pd.read_csv(args.input)
    analysis_features = features.copy()
    if "status" in analysis_features.columns:
        analysis_features = analysis_features[analysis_features["status"].astype(str) == "success"].copy()
    if analysis_features.empty:
        raise SystemExit("no successful experiment rows available for analysis")

    output_dir = Path(args.output_dir)
    table_dir = output_dir / "tables"
    ensure_dir(table_dir)

    run_analysis(analysis_features, output_dir)

    accuracy_by_strategy_level(analysis_features).to_csv(
        table_dir / "accuracy_by_strategy_level.csv", index=False, encoding="utf-8-sig"
    )
    noise_flip_rate_by_strategy(analysis_features).to_csv(
        table_dir / "noise_flip_rate_by_strategy.csv", index=False, encoding="utf-8-sig"
    )
    level_consistency_by_strategy(analysis_features).to_csv(
        table_dir / "level_consistency_by_strategy.csv", index=False, encoding="utf-8-sig"
    )
    failure_modes_by_strategy(analysis_features).to_csv(
        table_dir / "failure_modes_by_strategy.csv", index=False, encoding="utf-8-sig"
    )

    responses = pd.read_csv(args.responses) if Path(args.responses).exists() else features
    prompts = pd.read_csv(args.prompts)
    models = _models_from_config(args.models)
    coverage = collection_coverage(
        responses=responses,
        prompts=prompts,
        models=models,
        repeats=args.repeats,
        provider_name=args.provider,
    )
    coverage.to_csv(table_dir / "collection_coverage.csv", index=False, encoding="utf-8-sig")

    print(f"wrote experiment analysis outputs -> {output_dir}")


if __name__ == "__main__":
    main()
