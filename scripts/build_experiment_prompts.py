from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from spatial_llm_mining.experiment import build_experiment_prompts, parse_prompt_sources
from spatial_llm_mining.io_utils import ensure_parent, project_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the multi-strategy experiment prompt table.")
    parser.add_argument(
        "--source",
        action="append",
        default=None,
        help="Prompt source in strategy=path form. Defaults to the curated five-source experiment set.",
    )
    parser.add_argument(
        "--output",
        default=str(project_path("data", "experiment_prompts.csv")),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    sources = parse_prompt_sources(args.source)
    prompts = build_experiment_prompts(sources=sources)
    out = Path(args.output)
    ensure_parent(out)
    prompts.to_csv(out, index=False, encoding="utf-8-sig")
    strategy_count = prompts["strategy"].nunique() if not prompts.empty else 0
    print(
        f"wrote {len(prompts)} prompts across {strategy_count} strategies "
        f"({prompts['prompt_uid'].nunique()} unique prompt_uid) -> {out}"
    )


if __name__ == "__main__":
    main()
