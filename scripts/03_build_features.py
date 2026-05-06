from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from spatial_llm_mining.features import extract_features
from spatial_llm_mining.io_utils import ensure_parent, project_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract behavior features from model responses.")
    parser.add_argument("--input", default=str(project_path("data", "raw", "model_responses.csv")))
    parser.add_argument("--output", default=str(project_path("data", "processed", "behavior_features.csv")))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    responses = pd.read_csv(args.input)
    features = extract_features(responses)
    out = Path(args.output)
    ensure_parent(out)
    features.to_csv(out, index=False, encoding="utf-8-sig")
    print(f"wrote {len(features)} behavior rows -> {out}")


if __name__ == "__main__":
    main()
