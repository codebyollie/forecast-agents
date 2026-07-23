import os
import pytest
from forecast_ai.config_store import ConfigStore
from forecast_ai.config import ForecastConfig

def test_config_store_env_overrides(tmp_path, monkeypatch):
    cfg_file = tmp_path / "config.yaml"
    cs = ConfigStore(cfg_file)

    # Set mock environment variables
    monkeypatch.setenv("OPENAI_API_KEY", "env_sk_openai_test_123")
    monkeypatch.setenv("GEMINI_API_KEY", "env_gemini_test_key_456")
    monkeypatch.setenv("KALSHI_API_KEY", "env_kalshi_key_789")
    monkeypatch.setenv("SERVER_PORT", "30005")

    cfg = cs.load_config()

    assert cfg.providers["openai"].api_key == "env_sk_openai_test_123"
    assert cfg.providers["gemini"].api_key == "env_gemini_test_key_456"
    assert cfg.kalshi.api_key == "env_kalshi_key_789"
    assert cfg.server.port == 30005

def test_default_and_fallback_provider_defaults():
    cfg = ForecastConfig()
    assert cfg.default_provider == "openai"
    assert cfg.fallback_providers == ["gemini"]
