from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STEPS = [
    ["scripts/01_generate_prompts.py"],
    ["scripts/02_collect_responses.py", "--provider", "mock"],
    ["scripts/03_build_features.py"],
    ["scripts/04_analyze.py"],
]


def main() -> None:
    for step in STEPS:
        cmd = [sys.executable, *step]
        print("running:", " ".join(step), flush=True)
        subprocess.run(cmd, cwd=ROOT, check=True)


if __name__ == "__main__":
    main()
