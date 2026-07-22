"""
Polymarket Markets Manager.

Combines Gamma and CLOB APIs to expose a simple interface to find and fetch 
all data related to prediction markets.
"""

from typing import List, Dict, Any, Optional
from .gamma import GammaClient
from .clob import ClobClient
from .models import PolymarketMarket, OrderBookSummary

class PolymarketMarketsManager:
    def __init__(self, gamma: Optional[GammaClient] = None, clob: Optional[ClobClient] = None):
        self.gamma = gamma or GammaClient()
        self.clob = clob or ClobClient()

    async def get_market_details_by_slug(self, slug: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves complete details for a market by slug, including its current orderbook.
        """
        market = await self.gamma.fetch_market_by_slug(slug)
        if not market:
            return None

        details = {
            "market": market,
            "orderbooks": {}
        }

        # Fetch orderbook for each outcome token
        for t in market.tokens:
            token_id = t["token_id"]
            if token_id:
                book = await self.clob.fetch_order_book(token_id)
                if book:
                    details["orderbooks"][t["outcome"]] = book

        return details

    async def get_active_markets_in_category(self, category: str, limit: int = 10) -> List[PolymarketMarket]:
        markets = await self.gamma.list_markets(active=True, limit=100)
        return [m for m in markets if m.category.lower() == category.lower()][:limit]
