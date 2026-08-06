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
    service.kalshi_client = MagicMock()
    service.kalshi_client.get_tags_by_categories = AsyncMock(
        return_value={"Politics": ["US Elections"]}
    )
    service.kalshi_client.get_series = AsyncMock(return_value=["KXPOL"])
    service.kalshi_client.fetch_markets = AsyncMock(return_value=([], None))
    
    # Mock Polymarket Client
    service.gamma_client = MagicMock()
    service.gamma_client.list_events = AsyncMock(return_value=[])
    service.gamma_client.search_events = AsyncMock(return_value=[])
    
    return service

def test_normalize_category():
    assert normalize_category("Politics") == "Politics"
    assert normalize_category("US Elections") == "Politics"
    assert normalize_category("Bitcoin") == "Crypto"
    assert normalize_category("Will the temp in Austin exceed 80 degrees?") == "Climate"
    assert normalize_category("WTI Oil close price") == "Commodities"
    assert normalize_category("Baseball game winner") == "Sports"
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

    search_service.kalshi_client.fetch_markets.assert_awaited_once_with(
        limit=1000, status="open", cursor=None
    )
    
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
    search_service.kalshi_client.get_tags_by_categories.return_value = {}
    m1 = KalshiMarket(ticker="KXP", title="Politics market", status="open", last_price=0.5, volume=100)
    m2 = KalshiMarket(ticker="KXS", title="Sports market", status="open", last_price=0.5, volume=200)
    search_service.kalshi_client.fetch_markets.return_value = ([m1, m2], None)
    
    search_service.gamma_client.list_events.return_value = []
    
    res = await search_service.browse_markets(venue="kalshi", category="Politics")
    results = res["results"]
    
    assert len(results) == 1
    assert results[0]["market_id"] == "KXP"


@pytest.mark.asyncio
async def test_kalshi_category_uses_series_discovery(search_service):
    market = KalshiMarket(
        ticker="KXPOL-1",
        title="Candidate margin",
        status="open",
        last_price=0.55,
        volume=500,
    )
    search_service.kalshi_client.get_tags_by_categories.return_value = {
        "Politics": ["Elections"]
    }
    search_service.kalshi_client.get_series.return_value = ["KXPOL"]
    search_service.kalshi_client.fetch_markets.return_value = ([market], None)

    res = await search_service.browse_markets(
        venue="kalshi",
        category="Politics",
    )

    search_service.kalshi_client.fetch_markets.assert_awaited_once_with(
        limit=250,
        status="open",
        series_ticker="KXPOL",
    )
    assert res["results"][0]["category"] == "Politics"


@pytest.mark.asyncio
async def test_polymarket_category_uses_event_tags(search_service):
    market = PolymarketMarket(
        id="poly-politics",
        question="Who will win?",
        condition_id="cond-politics",
        slug="poly-politics",
        resolution_source="Source",
        end_date_iso="2026-12-31T00:00:00Z",
        active=True,
        closed=False,
        volume=1000,
        raw_data={"outcomePrices": ["0.6"]},
    )
    event = PolymarketEvent(
        id="event-politics",
        title="Candidate margin",
        slug="event-politics",
        description="",
        markets=[market],
        raw_data={"tags": [{"label": "Politics", "slug": "politics"}]},
    )
    search_service.gamma_client.list_events.return_value = [event]

    res = await search_service.browse_markets(
        venue="polymarket",
        category="Politics",
    )

    search_service.gamma_client.list_events.assert_awaited_once_with(
        active=True,
        limit=96,
        offset=0,
        tag_slug="politics",
        related_tags=True,
    )
    assert len(res["results"]) == 1
    assert res["results"][0]["category"] == "Politics"


@pytest.mark.asyncio
async def test_search_respects_venue_and_category_filters(search_service):
    search_service.search_markets = AsyncMock(return_value=[
        {"market_id": "k1", "venue": "Kalshi", "category": "Politics"},
        {"market_id": "k2", "venue": "Kalshi", "category": "Sports"},
        {"market_id": "p1", "venue": "Polymarket", "category": "Politics"},
    ])

    res = await search_service.browse_markets(
        venue="kalshi",
        category="Politics",
        q="candidate",
        page_size=24,
    )

    assert [item["market_id"] for item in res["results"]] == ["k1"]

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


@pytest.mark.asyncio
async def test_kalshi_browse_prefers_live_midpoint_and_liquid_market(search_service):
    stale_zero_volume = KalshiMarket(
        ticker="KXEMPTY",
        title="Empty market",
        status="open",
        last_price=0.5,
        yes_bid=0.5,
        yes_ask=0.5,
        volume=0,
    )
    liquid = KalshiMarket(
        ticker="KXLIQUID",
        title="Liquid market",
        status="open",
        last_price=0.2,
        yes_bid=0.6,
        yes_ask=0.64,
        volume=500,
    )
    search_service.kalshi_client.fetch_markets.return_value = (
        [stale_zero_volume, liquid],
        None,
    )
    search_service.gamma_client.list_events.return_value = []

    res = await search_service.browse_markets(
        venue="kalshi", page_size=1, sort="volume"
    )

    assert res["results"][0]["market_id"] == "KXLIQUID"
    assert res["results"][0]["current_price"] == 0.62
    assert res["results"][0]["yes_bid"] == 0.6
    assert res["results"][0]["yes_ask"] == 0.64
    assert res["results"][0]["spread"] == 0.04


@pytest.mark.asyncio
async def test_all_venues_keeps_kalshi_visible_when_polymarket_volume_is_larger(search_service):
    kalshi_markets = [
        KalshiMarket(
            ticker=f"KX{i}", title=f"Kalshi {i}", status="open",
            last_price=0.4, volume=100 + i, event_ticker=f"KXE{i}"
        )
        for i in range(2)
    ]
    search_service.kalshi_client.fetch_markets.return_value = (kalshi_markets, None)

    poly_markets = [
        PolymarketMarket(
            id=f"p{i}", question=f"Polymarket {i}", condition_id=f"c{i}",
            slug=f"p-{i}", resolution_source="Source", active=True, closed=False,
            end_date_iso="2026-12-31T00:00:00Z",
            volume=100000 + i, raw_data={"outcomePrices": ["0.6"]}
        )
        for i in range(4)
    ]
    search_service.gamma_client.list_events.return_value = [
        PolymarketEvent(
            id=f"e{i}", title=f"Event {i}", slug=f"event-{i}",
            description="", markets=[poly_markets[i]], raw_data={}
        )
        for i in range(4)
    ]

    res = await search_service.browse_markets(venue="all", page_size=4)
    venues = [item["venue"] for item in res["results"]]

    assert venues.count("Kalshi") == 2
    assert venues.count("Polymarket") == 2


@pytest.mark.asyncio
async def test_all_venues_quota_uses_top_market_from_each_venue(search_service):
    search_service.kalshi_client.fetch_markets.return_value = (
        [
            KalshiMarket(ticker="KXLOW", title="Low", status="open", last_price=0.4, volume=1),
            KalshiMarket(ticker="KXTOP", title="Top", status="open", last_price=0.4, volume=100),
        ],
        None,
    )
    poly_events = []
    for market_id, volume in (("PLOW", 2), ("PTOP", 200)):
        market = PolymarketMarket(
            id=market_id,
            question=market_id,
            condition_id=f"condition-{market_id}",
            slug=market_id.lower(),
            resolution_source="Source",
            active=True,
            closed=False,
            end_date_iso="2026-12-31T00:00:00Z",
            volume=volume,
            raw_data={"outcomePrices": ["0.6"]},
        )
        poly_events.append(
            PolymarketEvent(
                id=f"event-{market_id}",
                title=market_id,
                slug=f"event-{market_id.lower()}",
                description="",
                markets=[market],
                raw_data={},
            )
        )
    search_service.gamma_client.list_events.return_value = poly_events

    result = await search_service.browse_markets(venue="all", page_size=2, sort="volume")

    assert {item["market_id"] for item in result["results"]} == {"KXTOP", "ptop"}
