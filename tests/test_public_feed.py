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
