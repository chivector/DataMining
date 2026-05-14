from __future__ import annotations

import argparse
import json
import sys
import warnings
from pathlib import Path
from typing import Any

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

warnings.filterwarnings(
    "ignore",
    message=r"Pandas requires version .* of 'numexpr'.*",
    category=UserWarning,
)

from spatial_llm_mining.providers import DFCompatibleProvider


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="List models from the configured DF/OpenAI-compatible API.")
    parser.add_argument("--raw", action="store_true", help="Print the raw JSON response as well.")
    return parser.parse_args()


def _model_ids(payload: Any) -> list[str]:
    if isinstance(payload, dict) and isinstance(payload.get("data"), list):
        values = payload["data"]
    elif isinstance(payload, list):
        values = payload
    else:
        values = []

    ids: list[str] = []
    for item in values:
        if isinstance(item, dict):
            model_id = item.get("id") or item.get("name") or item.get("model")
            if model_id:
                ids.append(str(model_id))
        elif isinstance(item, str):
            ids.append(item)
    return sorted(set(ids))


def main() -> None:
    try:
        provider = DFCompatibleProvider(max_tokens=1, temperature=0.0, timeout=60)
    except RuntimeError as exc:
        raise SystemExit(
            f"{exc}\n\n"
            "Set credentials first. In PowerShell:\n"
            '  $env:DF_API_URL="http://123.129.219.111:3000/v1"\n'
            '  $env:DF_API_KEY="your-key"\n\n'
            "Or create a project-root .env file:\n"
            "  export DF_API_URL=http://123.129.219.111:3000/v1\n"
            "  export DF_API_KEY=your-key\n"
        ) from exc
    if any(ord(ch) > 127 for ch in provider.api_key) or "你的" in provider.api_key:
        raise SystemExit(
            "DF_API_KEY contains non-ASCII placeholder text. In PowerShell, reset it with:\n"
            '  Remove-Item Env:DF_API_KEY -ErrorAction SilentlyContinue\n'
            '  $env:DF_API_KEY="your-real-key"\n\n'
            "Also check the variable name: it must be DF_API_KEY, not DF_API_UEY."
        )

    url = f"{provider.api_base}/models"
    try:
        response = requests.get(
            url,
            headers={"Authorization": f"Bearer {provider.api_key}"},
            timeout=provider.timeout,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise SystemExit(f"failed to query {url}: {exc}") from exc
    payload = response.json()
    ids = _model_ids(payload)

    print(f"base_url: {provider.api_base}")
    print(f"models: {len(ids)}")
    for model_id in ids:
        print(model_id)

    if args.raw:
        print("\nraw:")
        print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    args = parse_args()
    main()
