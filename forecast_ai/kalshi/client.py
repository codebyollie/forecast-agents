"""
Kalshi API Client.

Provides public read-only access to Kalshi event contracts and orderbooks.
Kalshi data represents Kalshi-listed contracts and is not treated as a complete
mirror of another broker's prediction-market catalog.
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
    def __init__(self, base_url: str = "https://external-api.kalshi.com/trade-api/v2"):
        self.base_url = base_url.rstrip('/')

    def _headers(self) -> Dict[str, str]:
        headers = {
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        }
        # Read-only market and orderbook endpoints are public. Kalshi private
        # endpoints use signed request headers, not bearer-token authentication.
        return headers

    def _parse_market(self, data: Dict[str, Any]) -> KalshiMarket:
        # Kalshi has kept the endpoint stable but has progressively moved from
        # integer-cent fields to *_dollars / *_fp fields.  Accept both shapes
        # so a schema refresh does not make the market browser silently empty.
        def first_value(*keys: str, default: Any = None) -> Any:
            for key in keys:
                value = data.get(key)
                if value is not None and value != "":
                    return value
            return default

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

        title = first_value(
            "title", "market_title", "question", "yes_sub_title", "subtitle",
            default=data.get("ticker", "")
        )
        subtitle = first_value("subtitle", "no_sub_title", default="")

        def parse_number(*keys: str) -> float:
            value = first_value(*keys, default=0)
            try:
                return float(value or 0)
            except (TypeError, ValueError):
                return 0.0

        volume = parse_number("volume", "volume_fp", "volume_24h_fp")
        open_interest = parse_number("open_interest", "open_interest_fp")
        expiration_time = first_value(
            "expiration_time", "latest_expiration_time", "close_time", default=""
        )

        return KalshiMarket(
            ticker=data.get("ticker", ""),
            title=str(title or data.get("ticker", "")),
            subtitle=str(subtitle or ""),
            category="", # Deprecated by Kalshi, use series discovery instead
            event_ticker=data.get("event_ticker", ""),
            status=data.get("status", "active"),
            yes_bid=yes_bid,
            yes_ask=yes_ask,
            no_bid=no_bid,
            no_ask=no_ask,
            last_price=last_price,
            volume=volume,
            open_interest=open_interest,
            expiration_time=str(expiration_time or ""),
            result=data.get("result"),
            raw_data=data
        )

    async def fetch_markets(self, limit: int = 20, status: str = "open", series_ticker: Optional[str] = None, cursor: Optional[str] = None) -> Tuple[List[KalshiMarket], Optional[str]]:
        """Fetch list of open markets from Kalshi. Returns (markets, next_cursor)."""
        # A full 1,000-market discovery page can take longer than httpx's
        # default timeout during exchange rollovers.
        async with httpx.AsyncClient(verify=True, timeout=20.0) as client:
            try:
                params = {
                    "limit": limit,
                    "status": status,
                    # Kalshi's newest pages are often dominated by zero-price
                    # multi-leg contracts. They made the browse endpoint look
                    # empty after our real-price filter was applied.
                    "mve_filter": "exclude",
                }
                if series_ticker:
                    params["series_ticker"] = series_ticker
                if cursor:
                    params["cursor"] = cursor
                resp = await client.get(
                    f"{self.base_url}/markets",
                    params=params,
                    headers=self._headers()
                )
                if resp.status_code == 200:
                    data = resp.json()
                    markets_raw = data.get("markets", [])
                    next_cursor = data.get("cursor")

                    # Keep the browser useful if Kalshi temporarily returns
                    # no rows for the status filter during a market rollover.
                    # The unfiltered public endpoint still contains the live
                    # contracts and we filter active rows in the service.
                    if not markets_raw and status == "open" and not cursor:
                        fallback = await client.get(
                            f"{self.base_url}/markets",
                            params={"limit": limit, "mve_filter": "exclude"},
                            headers=self._headers(),
                        )
                        if fallback.status_code == 200:
                            fallback_data = fallback.json()
                            markets_raw = fallback_data.get("markets", [])
                            next_cursor = fallback_data.get("cursor")

                    return [self._parse_market(m) for m in markets_raw], next_cursor
            except Exception as e:
                logger.warning(f"[KalshiClient] fetch_markets error: {e}")
                pass
        return [], None

    async def get_tags_by_categories(self) -> Dict[str, Any]:
        """Fetch all tags grouped by categories from Kalshi."""
        async with httpx.AsyncClient(verify=True) as client:
            try:
                resp = await client.get(
                    f"{self.base_url}/search/tags_by_categories",
                    headers=self._headers()
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return data.get("tags_by_categories", data)
            except Exception as e:
                logger.warning(f"[KalshiClient] get_tags_by_categories error: {e}")
        return {}

    async def get_series(self, category: str, limit: int = 200) -> List[str]:
        """Fetch series tickers for a given category."""
        series_rows = []
        cursor = None
        scan_limit = max(limit, 200)
        async with httpx.AsyncClient(verify=True) as client:
            try:
                while True:
                    params = {
                        "category": category,
                        "limit": 100,
                        "include_volume": "true",
                    }
                    if cursor:
                        params["cursor"] = cursor
                    resp = await client.get(
                        f"{self.base_url}/series",
                        params=params,
                        headers=self._headers()
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        for s in data.get("series", []):
                            ticker = s.get("ticker")
                            if ticker:
                                try:
                                    volume = float(s.get("volume") or s.get("volume_fp") or 0)
                                except (TypeError, ValueError):
                                    volume = 0.0
                                series_rows.append((ticker, volume))
                        cursor = data.get("cursor")
                        if not cursor or len(series_rows) >= scan_limit:
                            break
                    else:
                        break
            except Exception as e:
                logger.warning(f"[KalshiClient] get_series error: {e}")
        series_rows.sort(key=lambda item: item[1], reverse=True)
        return [ticker for ticker, _ in series_rows[:limit]]

    async def fetch_market_by_ticker(self, ticker: str) -> Optional[KalshiMarket]:
        """Fetch a specific Kalshi market by ticker symbol."""
        async with httpx.AsyncClient(verify=True) as client:
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
        async with httpx.AsyncClient(verify=True) as client:
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
        async with httpx.AsyncClient(verify=True) as client:
            try:
                resp = await client.get(
                    f"{self.base_url}/markets/{ticker}/orderbook",
                    headers=self._headers()
                )
                if resp.status_code == 200:
                    data = resp.json()
                    ob_data = data.get("orderbook", data)
                    
                    def parse_price(raw: Any) -> float:
                        value = float(raw)
                        return value / 100.0 if value > 1.0 else value

                    yes_bids = [
                        KalshiBookLevel(price=parse_price(b[0]), size=float(b[1]))
                        for b in ob_data.get("yes", []) if len(b) >= 2
                    ]
                    no_bids = [
                        KalshiBookLevel(price=parse_price(b[0]), size=float(b[1]))
                        for b in ob_data.get("no", []) if len(b) >= 2
                    ]
                    # Kalshi exposes YES and NO bids. A YES ask is the
                    # complement of a NO bid, and vice versa.
                    yes_asks = [
                        KalshiBookLevel(price=round(1.0 - level.price, 4), size=level.size)
                        for level in no_bids
                    ]
                    no_asks = [
                        KalshiBookLevel(price=round(1.0 - level.price, 4), size=level.size)
                        for level in yes_bids
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
                        no_bids=no_bids,
                        no_asks=no_asks,
                        spread=spread,
                        midpoint=midpoint,
                        raw_data=data
                    )
            except Exception:
                pass
        return None
