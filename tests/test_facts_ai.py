import os
import pytest
import httpx
from unittest.mock import AsyncMock, patch

from forecast_ai.config import ForecastConfig
from forecast_ai.config_store import ConfigStore
from forecast_ai.sources.facts_ai import FactsAISource, FactsAIError
from forecast_ai.agents.research import ResearchAgent
from forecast_ai.agents.macro import MacroAgent
from forecast_ai.providers.base import BaseProvider
from forecast_ai.models.evidence import Evidence

class DummyProvider(BaseProvider):
    async def generate(self, system_prompt: str, user_prompt: str, temperature: float = 0.3) -> str:
        return '{"probability": 0.75, "confidence": 0.8, "reasoning": "Test reasoning based on evidence.", "warnings": []}'

@pytest.mark.asyncio
async def test_facts_ai_source_success():
    source = FactsAISource(api_key="test_key", api_url="https://mock.factsai.org/answer")
    mock_resp_data = {
        "data": {
            "answer": "Federal Reserve is expected to lower interest rates due to falling CPI.",
            "citations": [
                {"title": "Fed Rate Cut Analysis", "url": "https://example.com/fed-analysis", "author": "Analyst", "publishedDate": "2026-07-01"}
            ]
        }
    }

    mock_resp = AsyncMock()
    mock_resp.status_code = 200
    mock_resp.json = lambda: mock_resp_data

    with patch("httpx.AsyncClient.post", return_value=mock_resp):
        res = await source.fetch_deep_research("Will FED cut interest rates?")
        assert res["answer"].startswith("Federal Reserve")
        assert len(res["citations"]) == 1
        assert res["citations"][0]["title"] == "Fed Rate Cut Analysis"
        assert res["citations"][0]["url"] == "https://example.com/fed-analysis"

@pytest.mark.asyncio
async def test_facts_ai_source_error_handling():
    source = FactsAISource(api_key="invalid_key", api_url="https://mock.factsai.org/answer")

    # Test 401 Unauthorized
    mock_resp_401 = AsyncMock()
    mock_resp_401.status_code = 401
    mock_resp_401.text = "Unauthorized"
    with patch("httpx.AsyncClient.post", return_value=mock_resp_401):
        with pytest.raises(FactsAIError) as exc_info_401:
            await source.fetch_deep_research("Test Query")
        assert exc_info_401.value.status_code == 401

    # Test 402 Insufficient Credits
    mock_resp_402 = AsyncMock()
    mock_resp_402.status_code = 402
    mock_resp_402.text = "Payment Required"
    with patch("httpx.AsyncClient.post", return_value=mock_resp_402):
        with pytest.raises(FactsAIError) as exc_info_402:
            await source.fetch_deep_research("Test Query")
        assert exc_info_402.value.status_code == 402

    # Test 429 Rate Limit
    mock_resp_429 = AsyncMock()
    mock_resp_429.status_code = 429
    mock_resp_429.text = "Too Many Requests"
    with patch("httpx.AsyncClient.post", return_value=mock_resp_429):
        with pytest.raises(FactsAIError) as exc_info_429:
            await source.fetch_deep_research("Test Query")
        assert exc_info_429.value.status_code == 429

@pytest.mark.asyncio
async def test_facts_ai_agent_graceful_fallback():
    cfg = ForecastConfig()
    cfg.facts_ai.enabled = True
    cfg.facts_ai.api_key = "invalid_key"

    agent = ResearchAgent(name="research", provider=DummyProvider(), config=cfg)

    # When FactsAI fails (e.g. 401 error), agent should NOT crash, but fall back gracefully
    with patch("forecast_ai.sources.facts_ai.FactsAISource.fetch_deep_research", side_effect=FactsAIError(401, "Invalid key")):
        pred = await agent.forecast("Will CPI drop?", evidence=[])
        assert pred.probability == 0.75
        assert pred.agent_name == "research"
        assert "Test reasoning" in pred.reasoning

def test_facts_ai_config_env_overrides():
    os.environ["FACTSAI_API_KEY"] = "forecast_test_key_123"
    os.environ["FACTSAI_ENABLED"] = "true"

    cs = ConfigStore()
    cfg = cs.load_config()

    assert cfg.facts_ai.api_key == "forecast_test_key_123"
    assert cfg.facts_ai.enabled is True

    # Clean up
    del os.environ["FACTSAI_API_KEY"]
    del os.environ["FACTSAI_ENABLED"]
