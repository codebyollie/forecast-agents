"""
Tests for Kalshi Market Data Integration (Robinhood Predict Proxy).
"""

import pytest
from forecast_ai.kalshi.client import KalshiClient
from forecast_ai.kalshi.models import KalshiMarket, KalshiOrderbook, KalshiBookLevel

def test_kalshi_market_parsing():
    client = KalshiClient()
    mock_data = {
        "ticker": "FED-CUT-26SEP",
        "title": "Will the Fed cut interest rates in September?",
        "subtitle": "Federal Reserve Monetary Policy",
        "category": "Economics",
        "event_ticker": "FED-2026",
        "status": "open",
        "yes_bid": 65,
        "yes_ask": 67,
        "no_bid": 33,
        "no_ask": 35,
        "last_price": 66,
        "volume": 50000,
        "open_interest": 120000,
        "expiration_time": "2026-09-18T18:00:00Z"
    }

    market = client._parse_market(mock_data)
    assert market.ticker == "FED-CUT-26SEP"
    assert market.title == "Will the Fed cut interest rates in September?"
    assert market.yes_bid == 0.65
    assert market.yes_ask == 0.67
    assert market.midpoint_price == 0.66

def test_kalshi_orderbook_midpoint():
    ob = KalshiOrderbook(
        ticker="FED-CUT-26SEP",
        yes_bids=[KalshiBookLevel(price=0.64, size=100.0)],
        yes_asks=[KalshiBookLevel(price=0.66, size=150.0)],
        spread=0.02,
        midpoint=0.65
    )
    assert ob.ticker == "FED-CUT-26SEP"
    assert ob.spread == 0.02
    assert ob.midpoint == 0.65
