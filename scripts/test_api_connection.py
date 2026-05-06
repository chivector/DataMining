from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from spatial_llm_mining.providers import DFCompatibleProvider


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Test DF/OpenAI-compatible API connectivity.")
    parser.add_argument("--model", default="gpt-4o")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    provider = DFCompatibleProvider(max_tokens=80, temperature=0.0, timeout=60)
    row = pd.Series(
        {
            "prompt": (
                "请用一句中文回答：你能收到这条测试消息吗？"
                "最后写“最终判断：不确定”。"
            )
        }
    )
    text = provider.complete(row, model=args.model)
    print(text[:500])


if __name__ == "__main__":
    main()
