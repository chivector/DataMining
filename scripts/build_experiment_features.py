from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from spatial_llm_mining.experiment import mark_api_failures
from spatial_llm_mining.features import extract_features
from spatial_llm_mining.io_utils import ensure_parent, project_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract behavior features for the multi-strategy experiment.")
    parser.add_argument(
        "--input",
        default=str(project_path("data", "raw", "model_responses_experiment.csv")),
    )
    parser.add_argument(
        "--output",
        default=str(project_path("data", "processed", "behavior_features_experiment.csv")),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    responses = pd.read_csv(args.input)
    features = mark_api_failures(extract_features(responses))
    out = Path(args.output)
    ensure_parent(out)
    features.to_csv(out, index=False, encoding="utf-8-sig")
    print(f"wrote {len(features)} experiment behavior rows -> {out}")


if __name__ == "__main__":
    main()
