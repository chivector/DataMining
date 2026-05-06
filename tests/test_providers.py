import pandas as pd
import pytest

from spatial_llm_mining import providers as providers_mod
from spatial_llm_mining.providers import DFCompatibleProvider, MockProvider


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch):
    for key in ("DF_API_URL", "DF_API_KEY", "API_BASE", "API_KEY"):
        monkeypatch.delenv(key, raising=False)


def test_mock_provider_renders_final_judgment() -> None:
    row = pd.Series(
        {
            "prompt_id": "C001_L2_none",
            "level": "L2",
            "noise_label": "none",
            "criticality": "borderline",
            "clearance_margin_cm": 4,
            "reference_judgment": "can_pass",
        }
    )
    text = MockProvider().complete(row, model="GPT-4o-sim")
    assert "最终判断" in text


def test_df_provider_prefers_constructor_args(monkeypatch) -> None:
    monkeypatch.setattr(providers_mod, "_load_api_config", lambda: {"base_url": "http://from-config", "api_key": "config-key"})
    provider = DFCompatibleProvider(api_base="http://override", api_key="override-key")
    assert provider.api_base == "http://override"
    assert provider.api_key == "override-key"


def test_df_provider_falls_back_to_env(monkeypatch) -> None:
    monkeypatch.setattr(providers_mod, "_load_api_config", lambda: {})
    monkeypatch.setenv("DF_API_URL", "http://env-base/v1/")
    monkeypatch.setenv("DF_API_KEY", "env-key")
    provider = DFCompatibleProvider()
    assert provider.api_base == "http://env-base/v1"
    assert provider.api_key == "env-key"


def test_df_provider_falls_back_to_config(monkeypatch) -> None:
    monkeypatch.setattr(
        providers_mod,
        "_load_api_config",
        lambda: {"base_url": "http://cfg/v1", "api_key": "cfg-key", "max_retries": 1},
    )
    provider = DFCompatibleProvider()
    assert provider.api_base == "http://cfg/v1"
    assert provider.api_key == "cfg-key"
    assert provider.max_retries == 1


def test_df_provider_errors_when_no_credentials(monkeypatch) -> None:
    monkeypatch.setattr(providers_mod, "_load_api_config", lambda: {})
    with pytest.raises(RuntimeError):
        DFCompatibleProvider()
