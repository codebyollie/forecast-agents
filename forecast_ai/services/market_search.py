"""
Market Search Service for Forecast AI.

Queries open prediction markets on Kalshi and Polymarket matching a user query string,
returning a normalized list of market objects.
"""

from __future__ import annotations

import logging
import asyncio
from typing import List, Dict, Any
import httpx
from ..kalshi.client import KalshiClient
from ..polymarket.gamma import GammaClient

logger = logging.getLogger(__name__)

class MarketSearchService:
    def __init__(
        self,
        kalshi_base_url: str = "https://api.elections.kalshi.com/trade-api/v2",
        gamma_api_url: str = "https://gamma-api.polymarket.com"
    ):
        self.kalshi_client = KalshiClient(base_url=kalshi_base_url)
        self.gamma_client = GammaClient(base_url=gamma_api_url)

    async def search_markets(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search open prediction markets across Kalshi and Polymarket matching query text.
        Returns normalized list: [{market_id, question, venue, current_price, category, slug}]
        """
        clean_q = query.strip().lower()
        if not clean_q:
            return []

        results: List[Dict[str, Any]] = []

        # Run Kalshi & Polymarket searches concurrently
        kalshi_task = asyncio.create_task(self._search_kalshi(clean_q, limit=limit))
        poly_task = asyncio.create_task(self._search_polymarket(clean_q, limit=limit))

        kalshi_res, poly_res = await asyncio.gather(kalshi_task, poly_task, return_exceptions=True)

        if isinstance(kalshi_res, list):
            results.extend(kalshi_res)
        if isinstance(poly_res, list):
            results.extend(poly_res)

        return results[:limit]

    async def _search_kalshi(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        matched = []
        try:
            markets = await self.kalshi_client.fetch_markets(limit=200, status="open")
            for m in markets:
                comb = f"{m.ticker} {m.title} {m.subtitle} {m.category}".lower()
                if any(kw in comb for kw in query.split()):
                    matched.append({
                        "market_id": m.ticker,
                        "question": m.title,
                        "venue": "Kalshi / Robinhood Predict",
                        "current_price": round(float(m.last_price), 4),
                        "category": m.category or "General",
                        "slug": m.event_ticker.lower()
                    })
                    if len(matched) >= limit:
                        break
        except Exception as e:
            logger.warning(f"[MarketSearchService] Kalshi search failed for query '{query}': {e}")
        return matched

    async def _search_polymarket(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        matched = []
        try:
            markets = await self.gamma_client.list_markets(active=True, limit=100)
            for m in markets:
                comb = f"{m.question} {m.slug} {m.category}".lower()
                if any(kw in comb for kw in query.split()):
                    matched.append({
                        "market_id": m.slug or m.id,
                        "question": m.question,
                        "venue": "Polymarket",
                        "current_price": round(float(m.outcome_prices[0]), 4) if m.outcome_prices else 0.50,
                        "category": m.category or "General",
                        "slug": m.slug
                    })
                    if len(matched) >= limit:
                        break
        except Exception as e:
            logger.warning(f"[MarketSearchService] Polymarket search failed for query '{query}': {e}")
        return matched
