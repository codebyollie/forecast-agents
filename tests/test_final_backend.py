import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from forecast_ai.services.spend_guard import SpendGuard, SpendCapExceededError
from forecast_ai.services.market_search import MarketSearchService
from forecast_ai.sources.facts_ai import FactsAISource
from forecast_ai.config import ForecastConfig

def test_spend_guard_circuit_breaker(tmp_path):
    store_file = tmp_path / "spend.json"
    guard = SpendGuard(store_path=str(store_file), daily_cap_usd=0.005, monthly_cap_usd=50.0)
    
    # First call records spend of 0.006 (>= 0.005)
    guard.check_and_record_call("openai", "gpt-4o", estimated_cost=0.006)
    
    # Second call sees daily_spend = 0.006 >= 0.005 -> raises SpendCapExceededError
    with pytest.raises(SpendCapExceededError) as exc_info:
        guard.check_and_record_call("openai", "gpt-4o", estimated_cost=0.006)
    
    assert "HARD CIRCUIT BREAKER TRIGGERED" in str(exc_info.value)

def test_market_search_url_parsing():
    service = MarketSearchService()
    
    poly_url = "https://polymarket.com/event/will-solana-hit-150-in-2026"
    poly_match = service.parse_market_url(poly_url)
    assert poly_match is not None
    assert poly_match["platform"] == "polymarket"
    assert poly_match["identifier"] == "will-solana-hit-150-in-2026"
    
    kalshi_url = "https://kalshi.com/markets/kxratecut/will-fed-cut-rates"
    kalshi_match = service.parse_market_url(kalshi_url)
    assert kalshi_match is not None
    assert kalshi_match["platform"] == "kalshi"

@pytest.mark.asyncio
async def test_facts_ai_user_agent_header():
    source = FactsAISource(api_key="test_key")
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"answer": "Test answer", "citations": []}
        mock_post.return_value = mock_resp
        
        res = await source.fetch_deep_research("test query")
        assert res["answer"] == "Test answer"
        
        # Verify User-Agent header
        call_kwargs = mock_post.call_args.kwargs
        assert call_kwargs["headers"]["User-Agent"] == "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
