import pytest
import asyncio
from forecast_ai.config import ForecastConfig, ProviderConfig, AgentSettings
from forecast_ai.providers import BaseProvider, ProviderError, ProviderManager

class MockFailingProvider(BaseProvider):
    def __init__(self, name: str):
        self.name = name

    async def generate(self, system_prompt: str, user_prompt: str, temperature=None, max_tokens=None) -> str:
        raise ProviderError(self.name, f"Mock failure for provider {self.name}")

class MockSucceedingProvider(BaseProvider):
    def __init__(self, name: str, response_text: str = "Mock SUCCESS"):
        self.name = name
        self.response_text = response_text

    async def generate(self, system_prompt: str, user_prompt: str, temperature=None, max_tokens=None) -> str:
        return self.response_text

@pytest.mark.asyncio
async def test_fallback_primary_fails_secondary_succeeds():
    cfg = ForecastConfig()
    cfg.fallback_providers = ["anthropic", "gemini"]
    pm = ProviderManager(cfg)

    # Inject mock providers
    pm.providers["openai"] = MockFailingProvider("openai")
    pm.providers["anthropic"] = MockSucceedingProvider("anthropic", "Anthropic Success!")

    res = await pm.generate_with_fallback(
        primary_name="openai",
        system_prompt="sys",
        user_prompt="user"
    )
    assert res == "Anthropic Success!"

@pytest.mark.asyncio
async def test_fallback_deduplicates_and_excludes_primary():
    cfg = ForecastConfig()
    cfg.fallback_providers = ["openai", "anthropic", "openai", "gemini"]
    pm = ProviderManager(cfg)

    failed_attempts = []
    class TrackingFailingProvider(BaseProvider):
        def __init__(self, name: str):
            self.name = name
        async def generate(self, system_prompt: str, user_prompt: str, temperature=None, max_tokens=None) -> str:
            failed_attempts.append(self.name)
            raise ProviderError(self.name, "Failed")

    pm.providers["openai"] = TrackingFailingProvider("openai")
    pm.providers["anthropic"] = TrackingFailingProvider("anthropic")
    pm.providers["gemini"] = MockSucceedingProvider("gemini", "Gemini Success!")

    res = await pm.generate_with_fallback(
        primary_name="openai",
        system_prompt="sys",
        user_prompt="user"
    )
    assert res == "Gemini Success!"
    # Primary 'openai' attempted once at start, not retried in fallback
    assert failed_attempts == ["openai", "anthropic"]

@pytest.mark.asyncio
async def test_fallback_excludes_ollama_for_public_feed():
    cfg = ForecastConfig()
    cfg.fallback_providers = ["openai", "ollama", "anthropic"]
    pm = ProviderManager(cfg)

    attempted = []
    class TrackingFailingProvider(BaseProvider):
        def __init__(self, name: str):
            self.name = name
        async def generate(self, system_prompt: str, user_prompt: str, temperature=None, max_tokens=None) -> str:
            attempted.append(self.name)
            raise ProviderError(self.name, "Failed")

    pm.providers["openai"] = TrackingFailingProvider("openai")
    pm.providers["ollama"] = TrackingFailingProvider("ollama")
    pm.providers["anthropic"] = MockSucceedingProvider("anthropic", "Anthropic Success!")

    res = await pm.generate_with_fallback(
        primary_name="openai",
        system_prompt="sys",
        user_prompt="user",
        is_public_feed=True
    )
    assert res == "Anthropic Success!"
    assert "ollama" not in attempted
    assert attempted == ["openai"]

@pytest.mark.asyncio
async def test_fallback_full_chain_failure_raises_provider_error():
    cfg = ForecastConfig()
    pm = ProviderManager(cfg)

    pm.providers["openai"] = MockFailingProvider("openai")
    pm.providers["anthropic"] = MockFailingProvider("anthropic")
    pm.providers["gemini"] = MockFailingProvider("gemini")
    pm.providers["openrouter"] = MockFailingProvider("openrouter")
    pm.providers["ollama"] = MockFailingProvider("ollama")

    with pytest.raises(ProviderError) as exc_info:
        await pm.generate_with_fallback(
            primary_name="openai",
            system_prompt="sys",
            user_prompt="user"
        )
    assert "All LLM providers in fallback chain failed" in str(exc_info.value)
