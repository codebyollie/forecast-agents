"""
Kalshi Evidence Source.

Pulls Kalshi market context (Robinhood Predict proxy) into the Evidence pipeline.
"""

from typing import List
from datetime import datetime, timezone
from .base import BaseSource
from ..models.evidence import Evidence
from ..kalshi.client import KalshiClient

class KalshiSource(BaseSource):
    def __init__(self, api_base_url: str = "https://external-api.kalshi.com/trade-api/v2"):
        self.client = KalshiClient(base_url=api_base_url)

    async def fetch(self, query: str, limit: int = 5) -> List[Evidence]:
        evidences = []
        try:
            markets = await self.client.fetch_markets(limit=limit)
            for m in markets:
                price_str = f"${m.last_price:.2f}" if m.last_price is not None else "N/A"
                content = (
                    f"Kalshi/Robinhood Predict Market [{m.ticker}]: {m.title}. "
                    f"Yes Bid/Ask: ${m.yes_bid:.2f}/${m.yes_ask:.2f}, Last Price: {price_str}, Volume: {m.volume}"
                )
                ev = Evidence(
                    source_name="kalshi",
                    content=content,
                    url=f"https://kalshi.com/markets/{m.ticker}",
                    relevance_score=0.85,
                    metadata={"ticker": m.ticker, "last_price": m.last_price, "volume": m.volume}
                )
                evidences.append(ev)
        except Exception:
            pass
        return evidences
