from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from spatial_llm_mining.io_utils import ensure_parent, load_yaml, project_path
from spatial_llm_mining.prompts import build_prompt_matrix


def main() -> None:
    config = load_yaml(project_path("config", "experiment.yml"))
    prompts = build_prompt_matrix(
        levels=config["levels"],
        noise_conditions=config["noise_conditions"],
        num_cases=int(config["num_cases"]),
    )
    out = project_path("data", "prompts.csv")
    ensure_parent(out)
    prompts.to_csv(out, index=False, encoding="utf-8-sig")
    print(f"wrote {len(prompts)} prompts -> {out}")


if __name__ == "__main__":
    main()
