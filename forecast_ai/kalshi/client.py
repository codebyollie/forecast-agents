"""
Kalshi API Client.

Provides public read-only access to Kalshi event contracts and orderbooks.
Note: Kalshi market data serves as the primary market-data proxy for Robinhood Predict,
since Robinhood Predict event contracts settle via Kalshi's exchange infrastructure.
"""

import httpx
from typing import List, Optional, Dict, Any
from .models import KalshiMarket, KalshiOrderbook, KalshiBookLevel, KalshiSeries

class KalshiClient:
    def __init__(self, base_url: str = "https://api.elections.kalshi.com/trade-api/v2", api_key: Optional[str] = None):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key

    def _headers(self) -> Dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _parse_market(self, data: Dict[str, Any]) -> KalshiMarket:
        yes_bid = float(data.get("yes_bid", 0) or 0) / 100.0 if data.get("yes_bid") and data.get("yes_bid") > 1 else float(data.get("yes_bid", 0) or 0)
        yes_ask = float(data.get("yes_ask", 0) or 0) / 100.0 if data.get("yes_ask") and data.get("yes_ask") > 1 else float(data.get("yes_ask", 0) or 0)
        no_bid = float(data.get("no_bid", 0) or 0) / 100.0 if data.get("no_bid") and data.get("no_bid") > 1 else float(data.get("no_bid", 0) or 0)
        no_ask = float(data.get("no_ask", 0) or 0) / 100.0 if data.get("no_ask") and data.get("no_ask") > 1 else float(data.get("no_ask", 0) or 0)
        last_price = float(data.get("last_price", 0) or 0) / 100.0 if data.get("last_price") and data.get("last_price") > 1 else float(data.get("last_price", 0.5) or 0.5)

        return KalshiMarket(
            ticker=data.get("ticker", ""),
            title=data.get("title", "") or data.get("subtitle", ""),
            subtitle=data.get("subtitle", ""),
            category=data.get("category", ""),
            event_ticker=data.get("event_ticker", ""),
            status=data.get("status", "active"),
            yes_bid=yes_bid,
            yes_ask=yes_ask,
            no_bid=no_bid,
            no_ask=no_ask,
            last_price=last_price,
            volume=float(data.get("volume", 0) or 0),
            open_interest=float(data.get("open_interest", 0) or 0),
            expiration_time=data.get("expiration_time", ""),
            result=data.get("result"),
            raw_data=data
        )

    async def fetch_markets(self, limit: int = 20, status: str = "open") -> List[KalshiMarket]:
        """Fetch list of open markets from Kalshi."""
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(
                    f"{self.base_url}/markets",
                    params={"limit": limit, "status": status},
                    headers=self._headers()
                )
                if resp.status_code == 200:
                    data = resp.json()
                    markets_raw = data.get("markets", [])
                    return [self._parse_market(m) for m in markets_raw]
            except Exception:
                pass
        return []

    async def fetch_market_by_ticker(self, ticker: str) -> Optional[KalshiMarket]:
        """Fetch a specific Kalshi market by ticker symbol."""
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(
                    f"{self.base_url}/markets/{ticker}",
                    headers=self._headers()
                )
                if resp.status_code == 200:
                    data = resp.json()
                    market_raw = data.get("market", data)
                    return self._parse_market(market_raw)
            except Exception:
                pass
        return None

    async def fetch_orderbook(self, ticker: str) -> Optional[KalshiOrderbook]:
        """Fetch orderbook depth for a market ticker."""
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(
                    f"{self.base_url}/markets/{ticker}/orderbook",
                    headers=self._headers()
                )
                if resp.status_code == 200:
                    data = resp.json()
                    ob_data = data.get("orderbook", data)
                    
                    yes_bids = [
                        KalshiBookLevel(price=float(b[0])/100.0 if b[0] > 1 else float(b[0]), size=float(b[1]))
                        for b in ob_data.get("yes", []) if len(b) >= 2
                    ]
                    yes_asks = [
                        KalshiBookLevel(price=float(a[0])/100.0 if a[0] > 1 else float(a[0]), size=float(a[1]))
                        for a in ob_data.get("no", []) if len(a) >= 2
                    ]

                    spread = 0.0
                    midpoint = 0.5
                    if yes_bids and yes_asks:
                        spread = abs(yes_asks[0].price - yes_bids[0].price)
                        midpoint = round((yes_bids[0].price + yes_asks[0].price) / 2.0, 4)

                    return KalshiOrderbook(
                        ticker=ticker,
                        yes_bids=yes_bids,
                        yes_asks=yes_asks,
                        spread=spread,
                        midpoint=midpoint,
                        raw_data=data
                    )
            except Exception:
                pass
        return None
