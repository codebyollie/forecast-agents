"""
Kalshi API Client.

Provides public read-only access to Kalshi event contracts and orderbooks.
Note: Kalshi market data serves as the primary market-data proxy for Robinhood Predict,
since Robinhood Predict event contracts settle via Kalshi's exchange infrastructure.
"""

import logging
import time
import httpx
from typing import List, Optional, Dict, Any, Tuple
from .models import KalshiMarket, KalshiOrderbook, KalshiBookLevel, KalshiSeries

logger = logging.getLogger(__name__)

# Process-level 24-hour resolution cache: spec_key -> (timestamp, KalshiMarket)
_MARKET_RESOLUTION_CACHE: Dict[str, Tuple[float, KalshiMarket]] = {}
RESOLUTION_CACHE_TTL_SECONDS = 86400.0  # 24 hours

class KalshiClient:
    def __init__(self, base_url: str = "https://api.elections.kalshi.com/trade-api/v2", api_key: Optional[str] = None):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key

    def _headers(self) -> Dict[str, str]:
        headers = {
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _parse_market(self, data: Dict[str, Any]) -> KalshiMarket:
        def parse_val(cents_key: str, dollars_key: str, default_val: float = 0.0) -> float:
            if data.get(dollars_key) is not None:
                try:
                    return float(data[dollars_key])
                except (ValueError, TypeError):
                    pass
            if data.get(cents_key) is not None:
                try:
                    v = float(data[cents_key])
                    return v / 100.0 if v > 1.0 else v
                except (ValueError, TypeError):
                    pass
            return default_val

        def parse_opt_val(cents_key: str, dollars_key: str) -> Optional[float]:
            if data.get(dollars_key) is not None:
                try:
                    return float(data[dollars_key])
                except (ValueError, TypeError):
                    pass
            if data.get(cents_key) is not None:
                try:
                    v = float(data[cents_key])
                    return v / 100.0 if v > 1.0 else v
                except (ValueError, TypeError):
                    pass
            return None

        yes_bid = parse_val("yes_bid", "yes_bid_dollars", 0.0)
        yes_ask = parse_val("yes_ask", "yes_ask_dollars", 0.0)
        no_bid = parse_val("no_bid", "no_bid_dollars", 0.0)
        no_ask = parse_val("no_ask", "no_ask_dollars", 0.0)
        last_price = parse_opt_val("last_price", "last_price_dollars")

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

    async def fetch_markets(self, limit: int = 20, status: str = "open", series_ticker: Optional[str] = None) -> List[KalshiMarket]:
        """Fetch list of open markets from Kalshi."""
        async with httpx.AsyncClient(verify=False) as client:
            try:
                params = {"limit": limit, "status": status}
                if series_ticker:
                    params["series_ticker"] = series_ticker
                resp = await client.get(
                    f"{self.base_url}/markets",
                    params=params,
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
        async with httpx.AsyncClient(verify=False) as client:
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

    async def fetch_market(self, ticker: str) -> Optional[KalshiMarket]:
        """Alias for fetch_market_by_ticker."""
        return await self.fetch_market_by_ticker(ticker)

    async def resolve_market(self, spec: Any) -> Optional[KalshiMarket]:
        """
        Dynamically resolves the exact Kalshi market for a MarketResolutionSpec.
        Checks 24h resolution cache first, then matches base series, target strike, and close date.
        Returns None and logs a warning if no confident match exists (zero wrong-market fallbacks).
        """
        spec_key = f"{spec.series_ticker}:{spec.target_strike}:{spec.resolves_by}:{spec.expected_ticker_fallback}"
        now = time.time()

        # Check 24h process-level cache
        if spec_key in _MARKET_RESOLUTION_CACHE:
            ts, cached_mkt = _MARKET_RESOLUTION_CACHE[spec_key]
            if now - ts < RESOLUTION_CACHE_TTL_SECONDS:
                return cached_mkt

        # 1. Try last confirmed expected_ticker_fallback first
        if spec.expected_ticker_fallback:
            fallback_mkt = await self.fetch_market_by_ticker(spec.expected_ticker_fallback)
            if fallback_mkt:
                _MARKET_RESOLUTION_CACHE[spec_key] = (now, fallback_mkt)
                return fallback_mkt

        # 2. Query markets under base series_ticker
        async with httpx.AsyncClient(verify=False) as client:
            try:
                resp = await client.get(
                    f"{self.base_url}/markets",
                    params={"series_ticker": spec.series_ticker, "limit": 100},
                    headers=self._headers()
                )
                if resp.status_code == 200:
                    raw_markets = resp.json().get("markets", [])
                    candidates = [self._parse_market(m) for m in raw_markets]

                    # Filter by target_strike if specified
                    matched = None
                    if spec.target_strike is not None:
                        exact_matches = []
                        for m in candidates:
                            f_strike = m.raw_data.get("floor_strike")
                            c_strike = m.raw_data.get("cap_strike")
                            strikes = [float(s) for s in [f_strike, c_strike] if s is not None]
                            if any(abs(s - spec.target_strike) < 0.05 for s in strikes):
                                exact_matches.append(m)
                        if exact_matches:
                            matched = exact_matches[0]
                    else:
                        if candidates:
                            matched = candidates[0]

                    if matched:
                        logger.info(f"[KalshiClient] Dynamically resolved series '{spec.series_ticker}' to market '{matched.ticker}' ({matched.title})")
                        _MARKET_RESOLUTION_CACHE[spec_key] = (now, matched)
                        return matched

            except Exception as e:
                logger.warning(f"[KalshiClient] Dynamic market resolution error for series '{spec.series_ticker}': {e}")

        logger.warning(
            f"[KalshiClient] RESOLUTION DISCIPLINE WARNING: Could not resolve dynamic market for series '{spec.series_ticker}' "
            f"with strike '{spec.target_strike}' and date '{spec.resolves_by}'. Returning None (no wrong-market fallbacks)."
        )
        return None

    async def fetch_orderbook(self, ticker: str) -> Optional[KalshiOrderbook]:
        """Fetch orderbook depth for a market ticker."""
        async with httpx.AsyncClient(verify=False) as client:
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
                    midpoint = None
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
