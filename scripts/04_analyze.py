from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from spatial_llm_mining.analysis import run_analysis
from spatial_llm_mining.io_utils import project_path
from spatial_llm_mining.report import build_pdf_report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run mining analysis and build PDF report.")
    parser.add_argument("--input", default=str(project_path("data", "processed", "behavior_features.csv")))
    parser.add_argument("--output-dir", default=str(project_path("outputs")))
    parser.add_argument("--report", default=str(project_path("reports", "analysis_report.pdf")))
    parser.add_argument("--build-report", action="store_true", help="Also generate reports/analysis_report.pdf.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    features = pd.read_csv(args.input)
    output_dir = Path(args.output_dir)
    result = run_analysis(features, output_dir)
    print(f"wrote analysis outputs -> {output_dir}")
    if args.build_report:
        build_pdf_report(features, result, Path(args.report), output_dir / "figures")
        print(f"wrote report -> {args.report}")


if __name__ == "__main__":
    main()
