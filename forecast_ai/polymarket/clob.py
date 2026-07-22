"""
CLOB API Client for Polymarket (Read-Only).

Enables order book retrieval, midpoint price checks, and market depth metrics.
"""

from typing import List, Optional, Dict, Any
import httpx
from .models import OrderBookSummary, BookLevel

class ClobClient:
    def __init__(self, base_url: str = "https://clob.polymarket.com"):
        self.base_url = base_url.rstrip('/')

    async def fetch_order_book(self, token_id: str) -> Optional[OrderBookSummary]:
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(f"{self.base_url}/book", params={"token_id": token_id})
                if resp.status_code == 200:
                    data = resp.json()
                    bids = [BookLevel(price=float(b.get("price", 0)), size=float(b.get("size", 0))) for b in data.get("bids", [])]
                    asks = [BookLevel(price=float(a.get("price", 0)), size=float(a.get("size", 0))) for a in data.get("asks", [])]
                    
                    # Spread
                    spread = 0.0
                    if bids and asks:
                        spread = asks[0].price - bids[0].price

                    return OrderBookSummary(
                        token_id=token_id,
                        bids=bids,
                        asks=asks,
                        spread=spread,
                        raw_data=data
                    )
            except Exception:
                pass
        return None

    async def fetch_midpoint_price(self, token_id: str) -> Optional[float]:
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(f"{self.base_url}/prices/midpoint", params={"token_id": token_id})
                if resp.status_code == 200:
                    data = resp.json()
                    return float(data.get("midpoint", 0.5))
            except Exception:
                pass
        return None

    async def fetch_last_trade_price(self, token_id: str) -> Optional[float]:
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(f"{self.base_url}/prices/last", params={"token_id": token_id})
                if resp.status_code == 200:
                    data = resp.json()
                    return float(data.get("price", 0.5))
            except Exception:
                pass
        return None

    async def fetch_spread(self, token_id: str) -> Optional[float]:
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(f"{self.base_url}/prices/spread", params={"token_id": token_id})
                if resp.status_code == 200:
                    data = resp.json()
                    return float(data.get("spread", 0.0))
            except Exception:
                pass
        return None

