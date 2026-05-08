from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from spatial_llm_mining.io_utils import ensure_parent, load_yaml, project_path
from spatial_llm_mining.prompts import ADDITIONAL_PROMPT_STRATEGIES, build_prompt_matrix


def main() -> None:
    config = load_yaml(project_path("config", "experiment.yml"))
    manifest_rows = []
    data_dir = project_path("data")
    current_outputs = {f"prompts_{strategy.name}.csv" for strategy in ADDITIONAL_PROMPT_STRATEGIES}
    for stale in data_dir.glob("prompts_*.csv"):
        if stale.name not in current_outputs:
            stale.unlink()
            print(f"removed stale strategy file -> {stale}")

    for strategy in ADDITIONAL_PROMPT_STRATEGIES:
        prompts = build_prompt_matrix(
            levels=config["levels"],
            noise_conditions=config["noise_conditions"],
            num_cases=int(config["num_cases"]),
            strategy=strategy.name,
        )
        out = project_path("data", f"prompts_{strategy.name}.csv")
        ensure_parent(out)
        prompts.to_csv(out, index=False, encoding="utf-8-sig")
        manifest_rows.append(
            {
                "strategy": strategy.name,
                "description": strategy.description,
                "rows": len(prompts),
                "file": str(out.relative_to(project_path())),
            }
        )
        print(f"wrote {len(prompts)} prompts -> {out}")

    manifest = pd.DataFrame(manifest_rows)
    manifest_out = project_path("data", "prompt_strategy_manifest.csv")
    manifest.to_csv(manifest_out, index=False, encoding="utf-8-sig")
    print(f"wrote {len(manifest)} strategy records -> {manifest_out}")


if __name__ == "__main__":
    main()
