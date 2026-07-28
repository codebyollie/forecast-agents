import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from forecast_ai.config import ForecastConfig
from forecast_ai.api.server import ApiServer
from forecast_ai.pipelines.forecast import ForecastPipeline
from forecast_ai.api.auth import get_current_privy_user

@pytest.fixture
def mock_pipeline():
    pipeline = MagicMock(spec=ForecastPipeline)
    pipeline.config = ForecastConfig()
    
    # Mock run_forecast response
    mock_prediction = MagicMock()
    mock_prediction.consensus_probability = 0.75
    mock_prediction.consensus_confidence = 0.85
    mock_prediction.explanation = "Test custom forecast explanation."
    mock_prediction.individual_predictions = []
    
    pipeline.run_forecast = AsyncMock(return_value=mock_prediction)
    return pipeline

@pytest.fixture
def client(mock_pipeline):
    config = ForecastConfig()
    server = ApiServer(config, mock_pipeline)
    app = server.app

    # Override Privy Auth dependency for tests
    app.dependency_overrides[get_current_privy_user] = lambda: {
        "privy_user_id": "test_privy_user_123",
        "email": "test@forecast.ai",
        "wallet_address": "0x1234567890123456789012345678901234567890"
    }

    return TestClient(app)

def test_market_search(client):
    with patch("forecast_ai.services.market_search.MarketSearchService.search_markets", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = [
            {
                "market_id": "KXBTC-100K",
                "question": "Will Bitcoin reach $100,000?",
                "venue": "Kalshi / Robinhood Predict",
                "current_price": 0.75,
                "category": "Crypto",
                "slug": "kxbtc-100k"
            }
        ]
        resp = client.get("/markets/search?q=bitcoin")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["market_id"] == "KXBTC-100K"

def test_get_analysis_usage(client):
    resp = client.get("/analyses/usage")
    assert resp.status_code == 200
    data = resp.json()
    assert "tier" in data
    assert "daily_limit" in data
    assert "daily_count" in data

def test_run_custom_analysis_and_history(client):
    payload = {
        "market_id": "KXBTC-100K",
        "question": "Will Bitcoin reach $100,000?",
        "venue": "Kalshi / Robinhood Predict"
    }
    resp = client.post("/analyses/run", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["market_id"] == "KXBTC-100K"
    assert data["consensus_probability"] == 0.75

    # Check history endpoint
    hist_resp = client.get("/analyses/history")
    assert hist_resp.status_code == 200
    hist_data = hist_resp.json()
    assert len(hist_data) >= 1
    assert hist_data[0]["market_id"] == "KXBTC-100K"
