import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from forecast_ai.services.market_search import MarketSearchService, normalize_category
from forecast_ai.kalshi.models import KalshiMarket
from forecast_ai.polymarket.models import PolymarketMarket, PolymarketEvent

@pytest_asyncio.fixture
async def search_service():
    service = MarketSearchService()
    # Mock Kalshi Client
    service.kalshi_client = AsyncMock()
    service.kalshi_client.get_tags_by_categories.return_value = {"Politics": ["US Elections"]}
    service.kalshi_client.get_series.return_value = ["KXPOL"]
    
    # Mock Polymarket Client
    service.gamma_client = AsyncMock()
    
    return service

def test_normalize_category():
    assert normalize_category("Politics") == "Politics"
    assert normalize_category("US Elections") == "Politics"
    assert normalize_category("Bitcoin") == "Crypto"
    assert normalize_category("Random Thing") == "Other"

@pytest.mark.asyncio
async def test_browse_markets_normalized_shape(search_service):
    # Mock Kalshi
    mock_kalshi_market = KalshiMarket(
        ticker="KXTEST",
        title="Will this test pass?",
        subtitle="Yes or No",
        status="open",
        last_price=0.75,
        volume=1000,
        expiration_time="2026-12-31T00:00:00Z",
        event_ticker="KXTEST-EVENT",
        raw_data={"open_time": "2026-01-01"}
    )
    search_service.kalshi_client.fetch_markets.return_value = ([mock_kalshi_market], "next_cursor_xyz")
    
    # Mock Polymarket
    mock_poly_market = PolymarketMarket(
        id="poly_1",
        question="Will polymarket work?",
        condition_id="cond_1",
        slug="poly-slug",
        resolution_source="Source",
        end_date_iso="2026-12-31T00:00:00Z",
        active=True,
        closed=False,
        volume=500,
        liquidity=200,
        category="Politics",
        image="http://image.png",
        event_id="poly_ev_1",
        raw_data={"createdAt": "2026-01-01", "outcomePrices": ["0.65", "0.35"]}
    )
    mock_poly_event = PolymarketEvent(
        id="poly_ev_1",
        title="Event Title",
        slug="poly-event-slug",
        description="Desc",
        markets=[mock_poly_market],
        raw_data={}
    )
    search_service.gamma_client.list_events.return_value = [mock_poly_event]
    
    # Test all venues
    res = await search_service.browse_markets(venue="all", page_size=24)
    
    assert res["page"] == 1
    assert res["page_size"] == 24
    assert res["has_more"] is True
    
    results = res["results"]
    assert len(results) == 2
    
    # Check normalized keys exist in both
    for r in results:
        assert "market_id" in r
        assert "question" in r
        assert "venue" in r
        assert "category" in r
        assert "current_price" in r
        assert "volume" in r
        assert "liquidity" in r
        assert "end_date" in r
        assert "slug" in r
        assert "image" in r
        assert "event_id" in r
        assert "outcomes" in r

@pytest.mark.asyncio
async def test_category_filter(search_service):
    # Mock Kalshi to return two markets with different inferred categories
    m1 = KalshiMarket(ticker="KXP", title="Politics market", status="open", last_price=0.5, volume=100)
    m2 = KalshiMarket(ticker="KXS", title="Sports market", status="open", last_price=0.5, volume=200)
    search_service.kalshi_client.fetch_markets.return_value = ([m1, m2], None)
    
    search_service.gamma_client.list_events.return_value = []
    
    res = await search_service.browse_markets(venue="kalshi", category="Politics")
    results = res["results"]
    
    assert len(results) == 1
    assert results[0]["market_id"] == "KXP"

@pytest.mark.asyncio
async def test_pagination_has_more(search_service):
    # If Polymarket returns fewer than limit, has_more should be False (assuming Kalshi also has no cursor)
    search_service.kalshi_client.fetch_markets.return_value = ([], None)
    search_service.gamma_client.list_events.return_value = []
    
    res = await search_service.browse_markets(venue="polymarket", page_size=10)
    assert res["has_more"] is False
    
    # If Polymarket returns exactly limit, has_more is True
    m = PolymarketEvent(id="1", title="test", slug="test", description="test", markets=[], raw_data={})
    search_service.gamma_client.list_events.return_value = [m] * 10
    res2 = await search_service.browse_markets(venue="polymarket", page_size=10)
    assert res2["has_more"] is True

@pytest.mark.asyncio
async def test_no_hardcoded_prices(search_service):
    # Kalshi market with missing price
    m1 = KalshiMarket(ticker="KXNO", title="No price", status="open", last_price=None, yes_bid=0, yes_ask=0)
    search_service.kalshi_client.fetch_markets.return_value = ([m1], None)
    
    # Polymarket market with missing price
    pm = PolymarketMarket(
        id="p1", question="No price", condition_id="c1", slug="s1", resolution_source="rs",
        end_date_iso="", active=True, closed=False, raw_data={}
    )
    pe = PolymarketEvent(id="e1", title="e1", slug="e1", description="e1", markets=[pm], raw_data={})
    search_service.gamma_client.list_events.return_value = [pe]
    
    res = await search_service.browse_markets(venue="all")
    # Both should be omitted because they lack valid prices
    assert len(res["results"]) == 0

@pytest.mark.asyncio
async def test_no_closed_markets(search_service):
    m1 = KalshiMarket(ticker="KXCLOSED", title="Closed", status="closed", last_price=0.5)
    search_service.kalshi_client.fetch_markets.return_value = ([m1], None)
    
    pm = PolymarketMarket(
        id="p1", question="Closed", condition_id="c1", slug="s1", resolution_source="rs",
        end_date_iso="", active=False, closed=True, raw_data={"outcomePrices": ["0.5"]}
    )
    pe = PolymarketEvent(id="e1", title="e1", slug="e1", description="e1", markets=[pm], raw_data={})
    search_service.gamma_client.list_events.return_value = [pe]
    
    res = await search_service.browse_markets(venue="all")
    assert len(res["results"]) == 0

@pytest.mark.asyncio
async def test_polymarket_event_grouping(search_service):
    search_service.kalshi_client.fetch_markets.return_value = ([], None)
    
    m1 = PolymarketMarket(id="p1", question="Q1", condition_id="c1", slug="s1", resolution_source="rs", end_date_iso="", active=True, closed=False, tokens=[{"outcome": "Option A"}], raw_data={"outcomePrices": ["0.3"]})
    m2 = PolymarketMarket(id="p2", question="Q2", condition_id="c2", slug="s2", resolution_source="rs", end_date_iso="", active=True, closed=False, tokens=[{"outcome": "Option B"}], raw_data={"outcomePrices": ["0.7"]})
    
    pe = PolymarketEvent(id="e1", title="Multi-market event", slug="e1", description="e1", markets=[m1, m2], raw_data={})
    search_service.gamma_client.list_events.return_value = [pe]
    
    res = await search_service.browse_markets(venue="polymarket")
    results = res["results"]
    
    assert len(results) == 1
    assert results[0]["question"] == "Multi-market event"
    assert results[0]["current_price"] is None
    assert len(results[0]["outcomes"]) == 2
    assert results[0]["outcomes"][0]["label"] == "Option A"
    assert results[0]["outcomes"][0]["price"] == 0.3
    assert results[0]["outcomes"][1]["label"] == "Option B"
    assert results[0]["outcomes"][1]["price"] == 0.7
