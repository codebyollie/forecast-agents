import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from forecast_ai.config import ForecastConfig
from forecast_ai.api.server import ApiServer
from forecast_ai.pipelines.forecast import ForecastPipeline

@pytest.fixture
def mock_pipeline():
    pipeline = MagicMock(spec=ForecastPipeline)
    pipeline.config = ForecastConfig()
    
    mock_prediction = MagicMock()
    mock_prediction.consensus_probability = 0.65
    mock_prediction.consensus_confidence = 0.80
    mock_prediction.explanation = "Live Dashboard GPT-5.6 Luna analysis."
    
    mock_agent_pred = MagicMock()
    mock_agent_pred.agent_name = "news"
    mock_agent_pred.probability = 0.65
    mock_agent_pred.confidence.score = 0.8
    mock_agent_pred.reasoning = "Test reasoning"
    mock_agent_pred.confidence.warnings = []
    
    mock_prediction.individual_predictions = [mock_agent_pred]
    pipeline.run_forecast = AsyncMock(return_value=mock_prediction)
    return pipeline

@pytest.fixture
def client(mock_pipeline, tmp_path):
    config = ForecastConfig()
    config.server.admin_secret = "test_admin_secret_999"
    
    # Redirect featured market file path in tests to avoid overwriting workspace files
    temp_file = str(tmp_path / "featured_market.json")
    from forecast_ai.services.featured_market import FeaturedMarketService
    original_init = FeaturedMarketService.__init__
    
    def mock_init(self, *args, **kwargs):
        kwargs["file_path"] = temp_file
        original_init(self, *args, **kwargs)
        
    with patch("forecast_ai.services.market_search.MarketSearchService.get_live_price", new=AsyncMock(return_value=0.22)), \
         patch("forecast_ai.services.featured_market.FeaturedMarketService.__init__", mock_init):
        server = ApiServer(config, mock_pipeline)
        app = server.app
        yield TestClient(app)

def test_admin_featured_market_auth_failure(client):
    payload = {
        "market_id": "KXBTC-100K",
        "question": "Will Bitcoin trade above $100,000?",
        "venue": "Kalshi (mirrors Robinhood Predict)"
    }
    resp = client.patch("/admin/featured-market", json=payload, headers={"x-admin-secret": "wrong_secret"})
    assert resp.status_code == 401

def test_admin_featured_market_success_and_public_get(client):
    payload = {
        "market_id": "KXBTC-100K",
        "question": "Will Bitcoin trade above $100,000?",
        "venue": "Kalshi (mirrors Robinhood Predict)"
    }
    with patch("forecast_ai.services.market_search.MarketSearchService.get_live_price", new=AsyncMock(return_value=0.22)):
        # 1. Owner updates featured market
        patch_resp = client.patch(
            "/admin/featured-market",
            json=payload,
            headers={"x-admin-secret": "test_admin_secret_999"}
        )
        assert patch_resp.status_code == 200
    patch_data = patch_resp.json()
    assert patch_data["market_id"] == "KXBTC-100K"
    assert patch_data["model_used"] == "gpt-5.6-luna"

    # 2. Public user fetches featured market
    get_resp = client.get("/public/featured-market")
    assert get_resp.status_code == 200
    get_data = get_resp.json()
    assert get_data["market_id"] == "KXBTC-100K"
    assert get_data["consensus_probability"] == 0.65
