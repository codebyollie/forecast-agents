"""
Tests for Polymarket Read-Only Integration.
"""

import pytest
from forecast_ai.polymarket.gamma import GammaClient
from forecast_ai.polymarket.clob import ClobClient

@pytest.mark.asyncio
async def test_gamma_client_parsing():
    client = GammaClient()
    mock_data = {
        "id": "123",
        "question": "Will BTC reach $100k?",
        "conditionId": "0xabc",
        "slug": "will-btc-reach-100k",
        "resolutionSource": "reuters",
        "endDate": "2026-12-31T23:59:59Z",
        "clobTokenIds": '["456", "789"]',
        "outcomes": '["Yes", "No"]',
        "active": True,
        "closed": False,
        "volume": "1000.50",
        "liquidity": "500.00",
        "category": "Crypto"
    }

    parsed = client._parse_market(mock_data)
    assert parsed.id == "123"
    assert parsed.question == "Will BTC reach $100k?"
    assert parsed.volume == 1000.50
    assert parsed.tokens[0]["token_id"] == "456"
    assert parsed.tokens[0]["outcome"] == "Yes"

def test_clob_client_init():
    clob = ClobClient(base_url="https://clob.polymarket.com")
    assert clob.base_url == "https://clob.polymarket.com"
