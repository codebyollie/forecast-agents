import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from forecast_ai.config import ForecastConfig
from forecast_ai.pipelines.public_feed import PublicFeedRunner
from forecast_ai.public_feed_topics import CURATED_TOPICS
from forecast_ai.api.public_routes import create_public_router
from fastapi import FastAPI

@pytest.fixture
def mock_runner(tmp_path):
    cfg = ForecastConfig()
    cfg.memory.store_dir = str(tmp_path)
    cfg.server.public_feed_monthly_budget_usd = 50.0
    runner = PublicFeedRunner(cfg)
    return runner

@pytest.fixture
def client(mock_runner):
    app = FastAPI()
    router = create_public_router(mock_runner)
    app.include_router(router)
    return TestClient(app)

def test_get_public_forecasts(client):
    response = client.get("/public/forecasts")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == len(CURATED_TOPICS)
    
    first = data[0]
    assert "topic_id" in first
    assert "consensus_probability" in first
    assert "market_price" in first
    assert "price_delta" in first
    assert "agent_breakdown" in first
    assert "last_updated" in first

def test_get_public_forecast_by_id_success(client):
    response = client.get("/public/forecasts/fed-rate-q3-2026")
    assert response.status_code == 200
    data = response.json()
    assert data["topic_id"] == "fed-rate-q3-2026"
    assert data["tier"] == "long"

def test_get_public_forecast_by_id_not_found(client):
    response = client.get("/public/forecasts/non_existent_topic")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

def test_spend_guard_trigger(mock_runner):
    current_month = datetime.now(timezone.utc).strftime("%Y-%m")
    mock_runner._save_store({
        "monthly_spend_usd": 55.0,
        "last_spend_reset_month": current_month,
        "topics": {}
    })
    assert mock_runner.is_spend_guard_triggered() is True

def test_spend_guard_not_triggered(mock_runner):
    current_month = datetime.now(timezone.utc).strftime("%Y-%m")
    mock_runner._save_store({
        "monthly_spend_usd": 10.0,
        "last_spend_reset_month": current_month,
        "topics": {}
    })
    assert mock_runner.is_spend_guard_triggered() is False

@pytest.mark.asyncio
async def test_fetch_live_market_price_kalshi(mock_runner):
    class MockKalshiClient:
        async def fetch_market_by_ticker(self, ticker):
            from forecast_ai.kalshi.models import KalshiMarket
            return KalshiMarket(
                ticker=ticker, title="Test", subtitle="", category="", event_ticker="",
                status="open", yes_bid=0.60, yes_ask=0.64, no_bid=0.36, no_ask=0.40,
                last_price=0.62, volume=100.0, open_interest=500.0, expiration_time="", result=None, raw_data={}
            )
        async def fetch_orderbook(self, ticker):
            return None

    mock_runner.kalshi_client = MockKalshiClient()
    topic = CURATED_TOPICS[0]  # fed-rate-q3-2026 (Kalshi)
    price = await mock_runner.fetch_live_market_price(topic)
    assert price == 0.62  # (0.60 + 0.64) / 2

@pytest.mark.asyncio
async def test_fetch_live_market_price_retains_last_known_good_on_failure(mock_runner):
    class FailingKalshiClient:
        async def fetch_market_by_ticker(self, ticker):
            raise Exception("API Connection Timeout")
        async def fetch_orderbook(self, ticker):
            raise Exception("API Connection Timeout")

    mock_runner.kalshi_client = FailingKalshiClient()
    topic = CURATED_TOPICS[0]

    # Pre-populate last known good price 0.68
    mock_runner._save_store({
        "monthly_spend_usd": 0.0,
        "topics": {
            topic.topic_id: {
                "market_price": 0.68
            }
        }
    })

    live_price = await mock_runner.fetch_live_market_price(topic)
    assert live_price is None

    # Verify last-known-good price 0.68 exists in store
    store = mock_runner._load_store()
    existing_price = store.get("topics", {}).get(topic.topic_id, {}).get("market_price")
    assert existing_price == 0.68
