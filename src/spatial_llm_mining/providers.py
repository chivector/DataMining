from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import pandas as pd

from .io_utils import load_yaml, project_path
from .prompts import stable_int


class ModelProvider(Protocol):
    def complete(self, prompt_row: pd.Series, model: str, repeat: int = 0) -> str:
        ...


@dataclass(frozen=True)
class MockProfile:
    l1_accuracy: float
    l2_accuracy: float
    l3_accuracy: float
    noise_penalty: float
    borderline_penalty: float
    formula_rate: float
    coordinate_rate: float
    intuition_bias: float


MOCK_PROFILES: dict[str, MockProfile] = {
    "GPT-4o-sim": MockProfile(0.84, 0.80, 0.72, 0.09, 0.15, 0.70, 0.45, 0.18),
    "Claude-Sonnet-sim": MockProfile(0.87, 0.78, 0.69, 0.06, 0.12, 0.55, 0.32, 0.24),
    "DeepSeek-V3-sim": MockProfile(0.76, 0.82, 0.80, 0.12, 0.17, 0.82, 0.66, 0.11),
    "Small-LLM-sim": MockProfile(0.63, 0.58, 0.47, 0.18, 0.23, 0.33, 0.16, 0.36),
}


def _load_api_config() -> dict[str, Any]:
    cfg_path: Path = project_path("config", "experiment.yml")
    if not cfg_path.exists():
        return {}
    full = load_yaml(cfg_path) or {}
    return dict(full.get("api") or {})


class MockProvider:
    """Deterministic offline provider for reproducible end-to-end analysis."""

    def complete(self, prompt_row: pd.Series, model: str, repeat: int = 0) -> str:
        profile = MOCK_PROFILES.get(model, MOCK_PROFILES["Small-LLM-sim"])
        level = str(prompt_row["level"])
        base_accuracy = {
            "L1": profile.l1_accuracy,
            "L2": profile.l2_accuracy,
            "L3": profile.l3_accuracy,
        }[level]
        if prompt_row["noise_label"] != "none":
            base_accuracy -= profile.noise_penalty
        if prompt_row["criticality"] == "borderline":
            base_accuracy -= profile.borderline_penalty
        if level == "L3" and model in {"GPT-4o-sim", "Claude-Sonnet-sim"}:
            base_accuracy -= 0.04

        score = stable_int(model, prompt_row["prompt_id"], repeat, modulo=10_000) / 10_000
        correct = score < max(0.05, min(0.95, base_accuracy))
        reference = prompt_row["reference_judgment"]
        if correct:
            judgment = reference
        else:
            judgment = "cannot_pass" if reference == "can_pass" else "can_pass"

        failure_mode = "none" if correct else self._failure_mode(prompt_row, model, repeat)
        use_formula = (
            level in {"L2", "L3"}
            and stable_int("formula", model, prompt_row["prompt_id"], modulo=10_000) / 10_000 < profile.formula_rate
        )
        use_coordinate = (
            level == "L3"
            and stable_int("coord", model, prompt_row["prompt_id"], modulo=10_000) / 10_000 < profile.coordinate_rate
        )
        return self._render_response(prompt_row, judgment, failure_mode, use_formula, use_coordinate)

    def _failure_mode(self, row: pd.Series, model: str, repeat: int) -> str:
        if row["noise_label"] != "none":
            r = stable_int("noise", model, row["prompt_id"], repeat, modulo=100)
            if r < 42:
                return "noise_distraction"
        if row["level"] == "L3":
            return "calculation_collapse"
        if row["level"] == "L2":
            r = stable_int("l2", model, row["prompt_id"], repeat, modulo=100)
            return "unit_confusion" if r < 24 else "concept_confusion"
        return "intuition_overfit"

    def _render_response(
        self,
        row: pd.Series,
        judgment: str,
        failure_mode: str,
        use_formula: bool,
        use_coordinate: bool,
    ) -> str:
        final = {
            "can_pass": "能通过",
            "cannot_pass": "不能通过",
            "uncertain": "不确定",
        }[judgment]
        steps: list[str] = []
        steps.append("1. 先识别这是一个 90 度 L 形转弯，需要同时考虑通道净宽和旋转扫过空间。")
        if use_formula:
            margin = row["clearance_margin_cm"]
            steps.append(
                f"2. 用保守余量 m=min(W-w, D-R) 估算，当前 m≈{margin}cm；"
                "m 越小，越容易在内角处发生碰撞。"
            )
        else:
            steps.append("2. 从描述看，关键不只是轮椅宽度，还包括转弯时前后端扫过的空间。")
        if use_coordinate:
            steps.append("3. 若建立 x-y 坐标系，可把轮椅包络看成随角度 theta 旋转的矩形外接区域。")
        else:
            steps.append("3. 我会把转弯半径视作保守约束，而不是只比较轮椅宽和楼梯宽。")

        if failure_mode == "noise_distraction":
            steps.append("4. 但现场扶手颜色、噪声或催促信息会增加操作风险，因此我倾向于更保守判断。")
        elif failure_mode == "calculation_collapse":
            steps.append("4. 形式化参数较多，半径、矩形包络和墙体边界之间可能出现算式链条不稳定。")
        elif failure_mode == "concept_confusion":
            steps.append("4. 这里容易把通道净宽直接等同于转弯半径，导致概念混淆。")
        elif failure_mode == "unit_confusion":
            steps.append("4. 若把厘米余量和米制尺度混用，最终结论可能被单位换算带偏。")
        elif failure_mode == "intuition_overfit":
            steps.append("4. 在缺少精确尺寸时，我更多依赖日常空间直觉进行判断。")
        else:
            steps.append("4. 无关环境信息不改变几何约束，最终仍应围绕宽度、平台进深和转弯半径判断。")

        return "\n".join(steps) + f"\n最终判断：{final}"


class OpenAIProvider:
    def __init__(self) -> None:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("openai package is required for --provider openai") from exc
        self.client = OpenAI()

    def complete(self, prompt_row: pd.Series, model: str, repeat: int = 0) -> str:
        response = self.client.responses.create(
            model=model,
            input=str(prompt_row["prompt"]),
            temperature=0.2,
        )
        return response.output_text


class AnthropicProvider:
    def __init__(self) -> None:
        try:
            import anthropic
        except ImportError as exc:
            raise RuntimeError("anthropic package is required for --provider anthropic") from exc
        self.client = anthropic.Anthropic()

    def complete(self, prompt_row: pd.Series, model: str, repeat: int = 0) -> str:
        message = self.client.messages.create(
            model=model,
            max_tokens=800,
            temperature=0.2,
            messages=[{"role": "user", "content": str(prompt_row["prompt"])}],
        )
        return "\n".join(block.text for block in message.content if getattr(block, "type", "") == "text")


class DeepSeekProvider:
    def __init__(self) -> None:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("openai package is required for --provider deepseek") from exc
        self.client = OpenAI(
            api_key=os.environ.get("DEEPSEEK_API_KEY"),
            base_url="https://api.deepseek.com",
        )

    def complete(self, prompt_row: pd.Series, model: str, repeat: int = 0) -> str:
        response = self.client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": str(prompt_row["prompt"])}],
            temperature=0.2,
        )
        return response.choices[0].message.content or ""


class DFCompatibleProvider:
    """OpenAI-compatible chat-completions provider used by the local ResearchAgent project.

    Resolution order for credentials and parameters:

    1. Constructor arguments.
    2. Environment variables: ``DF_API_URL`` / ``DF_API_KEY`` (or ``API_BASE`` / ``API_KEY``).
    3. ``api`` block in ``config/experiment.yml``.
    """

    def __init__(
        self,
        api_base: str | None = None,
        api_key: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        timeout: int | None = None,
        seed: int | None = None,
        max_retries: int | None = None,
        retry_backoff_seconds: float | None = None,
    ) -> None:
        cfg = _load_api_config()

        self.api_base = (
            api_base
            or os.environ.get("DF_API_URL")
            or os.environ.get("API_BASE")
            or cfg.get("base_url")
            or ""
        ).rstrip("/")
        self.api_key = (
            api_key
            or os.environ.get("DF_API_KEY")
            or os.environ.get("API_KEY")
            or cfg.get("api_key")
            or ""
        )
        self.max_tokens = int(max_tokens if max_tokens is not None else cfg.get("max_tokens", 900))
        self.temperature = float(temperature if temperature is not None else cfg.get("temperature", 0.2))
        self.timeout = int(timeout if timeout is not None else cfg.get("timeout_seconds", 300))
        self.seed = int(seed if seed is not None else cfg.get("seed", 42))
        self.max_retries = int(max_retries if max_retries is not None else cfg.get("max_retries", 3))
        self.retry_backoff_seconds = float(
            retry_backoff_seconds
            if retry_backoff_seconds is not None
            else cfg.get("retry_backoff_seconds", 4)
        )
        if not self.api_base or not self.api_key:
            raise RuntimeError(
                "DF provider requires DF_API_URL/DF_API_KEY (or api.base_url/api.api_key in config/experiment.yml)."
            )

    def complete(self, prompt_row: pd.Series, model: str, repeat: int = 0) -> str:
        import requests

        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "你是空间推理实验的被试模型。请严格回答用户问题，"
                        "不要说明自己正在参加实验。最后必须给出“最终判断：能通过/不能通过/不确定”。"
                    ),
                },
                {"role": "user", "content": str(prompt_row["prompt"])},
            ],
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "seed": self.seed + int(repeat),
        }
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                response = requests.post(
                    f"{self.api_base}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=self.timeout,
                )
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
            except Exception as exc:  # noqa: BLE001 - network errors are diverse
                last_error = exc
                if attempt >= self.max_retries:
                    break
                time.sleep(self.retry_backoff_seconds * (attempt + 1))
        raise RuntimeError(f"DF API call failed after {self.max_retries + 1} attempts: {last_error}")


def build_provider(name: str) -> ModelProvider:
    normalized = name.lower()
    if normalized == "mock":
        return MockProvider()
    if normalized in {"df", "openai-compatible", "compatible"}:
        return DFCompatibleProvider()
    if normalized == "openai":
        return OpenAIProvider()
    if normalized == "anthropic":
        return AnthropicProvider()
    if normalized == "deepseek":
        return DeepSeekProvider()
    raise ValueError(f"Unknown provider: {name}")
