"""
Cross-Venue Market Search & URL Resolution Service for Forecast AI.

Queries open prediction markets on Kalshi and Polymarket matching a user query string or pasted URL,
returning a normalized list of market objects with live prices and honest venue tags.

# DO NOT ADD A HARDCODED 0.50 (OR ANY OTHER FABRICATED) PRICE FALLBACK HERE — this has been a recurring bug.
# If a real price cannot be found, fail loudly, return None, or omit the item.
"""

from __future__ import annotations

import logging
import asyncio
import re
from urllib.parse import urlparse
from typing import List, Dict, Any, Optional
import httpx
from ..kalshi.client import KalshiClient
from ..polymarket.gamma import GammaClient

logger = logging.getLogger(__name__)

STOPWORDS = {
    "will", "the", "a", "an", "is", "are", "in", "on", "at", "by", "for", "to", "of",
    "and", "or", "trade", "above", "below", "before", "after", "this", "that",
    "year", "month", "day", "with", "from", "be", "occur", "happen", "does", "do"
}

# Known key Kalshi macro/crypto series tickers for quick discovery
KNOWN_SERIES_MAP = {
    "recession": ["KXQRECESS", "RECSS"],
    "bitcoin": ["BTCMAXY", "KXBTCMAXM", "BITCOINMAXY", "KXBTCVSETH"],
    "btc": ["BTCMAXY", "KXBTCMAXM", "BITCOINMAXY"],
    "fed": ["KXRATEHIKE", "KXFEDDISSENT", "KXFEDCONF"],
    "inflation": ["CPI", "KXCPICORE220", "KXLCPIYOY"],
    "cpi": ["CPI", "KXCPICORE220", "KXLCPIYOY"],
    "solana": ["KXBTCVSSOL"],
    "eth": ["KXBTCVSETH"]
}

class MarketSearchService:
    def __init__(
        self,
        kalshi_base_url: str = "https://api.elections.kalshi.com/trade-api/v2",
        gamma_api_url: str = "https://gamma-api.polymarket.com"
    ):
        self.kalshi_client = KalshiClient(base_url=kalshi_base_url)
        self.gamma_client = GammaClient(base_url=gamma_api_url)

    def extract_keywords(self, query: str) -> List[str]:
        """
        Strips common English stopwords and punctuation from query text.
        Returns list of meaningful search terms.
        """
        clean = re.sub(r'[^\w\s]', ' ', query.lower())
        words = clean.split()
        keywords = [w for w in words if w not in STOPWORDS and len(w) > 1]
        if not keywords:
            keywords = [w for w in words if len(w) > 1]
        return keywords

    def parse_market_url(self, raw_input: str) -> Optional[Dict[str, str]]:
        """
        Parses pasted market URLs from Polymarket, Kalshi, or Robinhood Predict.
        Returns dict with platform and extracted slug/ticker, or None if not a URL.
        """
        text = raw_input.strip()
        if not (text.startswith("http://") or text.startswith("https://") or "polymarket.com" in text or "kalshi.com" in text or "robinhood.com" in text):
            return None

        try:
            parsed = urlparse(text if text.startswith("http") else f"https://{text}")
            host = parsed.netloc.lower()
            path = parsed.path.strip("/")

            if "polymarket.com" in host:
                parts = path.split("/")
                slug = parts[-1] if parts else text
                return {"platform": "polymarket", "identifier": slug}

            elif "kalshi.com" in host:
                parts = path.split("/")
                identifier = parts[1] if len(parts) > 1 else parts[0]
                return {"platform": "kalshi", "identifier": identifier.upper()}

            elif "robinhood.com" in host:
                parts = path.split("/")
                identifier = parts[-1] if parts else text
                return {"platform": "kalshi", "identifier": identifier.upper()}

        except Exception as e:
            logger.warning(f"[MarketSearchService] Failed to parse URL '{raw_input}': {e}")

        return None

    async def get_live_price(self, market_id: str, venue: Optional[str] = None) -> Optional[float]:
        """
        Fetches the exact real live market price for a given market_id.
        Returns None if no real price can be found (NO hardcoded 0.50 fallback).
        """
        # 1. Try Kalshi first if ticker format
        try:
            k_mkt = await self.kalshi_client.fetch_market_by_ticker(market_id)
            if k_mkt and k_mkt.last_price is not None and k_mkt.last_price > 0:
                return round(float(k_mkt.last_price), 4)
        except Exception:
            pass

        # 2. Try Polymarket Gamma
        try:
            p_mkt = await self.gamma_client.fetch_market(market_id)
            if p_mkt and p_mkt.outcome_prices and len(p_mkt.outcome_prices) > 0:
                return round(float(p_mkt.outcome_prices[0]), 4)

            # Try by slug
            ev = await self.gamma_client.fetch_event_by_slug(market_id)
            if ev and ev.markets and ev.markets[0].raw_data:
                op = ev.markets[0].raw_data.get("outcomePrices")
                if isinstance(op, list) and len(op) > 0:
                    return round(float(op[0]), 4)
        except Exception:
            pass

        return None

    async def search_markets(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search open prediction markets across Kalshi and Polymarket matching query text or URL.
        Returns normalized list: [{market_id, question, venue, current_price, category, slug}]
        """
        clean_q = query.strip()
        if not clean_q:
            return []

        # 1. URL resolution if input is a URL
        url_match = self.parse_market_url(clean_q)
        if url_match:
            resolved = await self._resolve_url_market(url_match)
            if resolved:
                return [resolved]

        # 2. Keyword search across both Kalshi and Polymarket using all() distinct terms
        keywords = self.extract_keywords(clean_q)
        if not keywords:
            return []

        results: List[Dict[str, Any]] = []
        kalshi_task = asyncio.create_task(self._search_kalshi(keywords, limit=limit))
        poly_task = asyncio.create_task(self._search_polymarket(keywords, limit=limit))

        kalshi_res, poly_res = await asyncio.gather(kalshi_task, poly_task, return_exceptions=True)

        if isinstance(kalshi_res, list):
            results.extend(kalshi_res)
        if isinstance(poly_res, list):
            results.extend(poly_res)

        return results[:limit]

    async def _resolve_url_market(self, match: Dict[str, str]) -> Optional[Dict[str, Any]]:
        platform = match["platform"]
        identifier = match["identifier"]

        if platform == "polymarket":
            try:
                ev = await self.gamma_client.fetch_event_by_slug(identifier)
                if ev and ev.markets:
                    m = ev.markets[0]
                    price = None
                    if m.raw_data and m.raw_data.get("outcomePrices"):
                        op = m.raw_data.get("outcomePrices")
                        if isinstance(op, list) and len(op) > 0:
                            price = float(op[0])
                    
                    if price is None:
                        return None

                    return {
                        "market_id": m.slug or m.id,
                        "question": m.question,
                        "venue": "Polymarket",
                        "current_price": round(price, 4),
                        "category": m.category or "General",
                        "slug": m.slug
                    }
            except Exception as e:
                logger.warning(f"[MarketSearchService] URL resolution failed for Polymarket '{identifier}': {e}")

        elif platform == "kalshi":
            try:
                k_mkt = await self.kalshi_client.fetch_market_by_ticker(identifier)
                if k_mkt and k_mkt.last_price is not None and k_mkt.last_price > 0:
                    return {
                        "market_id": k_mkt.ticker,
                        "question": k_mkt.title,
                        "venue": "Kalshi (mirrors Robinhood Predict)",
                        "current_price": round(float(k_mkt.last_price), 4),
                        "category": k_mkt.category or "General",
                        "slug": k_mkt.event_ticker.lower()
                    }
            except Exception as e:
                logger.warning(f"[MarketSearchService] URL resolution failed for Kalshi '{identifier}': {e}")

        return None

    async def _search_kalshi(self, keywords: List[str], limit: int = 10) -> List[Dict[str, Any]]:
        matched = []
        try:
            # Query known series if keywords match
            series_to_query = []
            for kw in keywords:
                if kw in KNOWN_SERIES_MAP:
                    series_to_query.extend(KNOWN_SERIES_MAP[kw])

            markets_to_check = []
            if series_to_query:
                for s_ticker in series_to_query[:3]:
                    s_mkts = await self.kalshi_client.fetch_markets(limit=20, status="open", series_ticker=s_ticker)
                    markets_to_check.extend(s_mkts)

            # Also fetch general open markets
            gen_mkts = await self.kalshi_client.fetch_markets(limit=100, status="open")
            markets_to_check.extend(gen_mkts)

            seen_tickers = set()
            for m in markets_to_check:
                if m.ticker in seen_tickers:
                    continue
                seen_tickers.add(m.ticker)

                # Skip multi-game sports parlays unless explicitly queried
                if m.ticker.startswith("KXMVESPORTS") or m.ticker.startswith("KXMVECROSS"):
                    if not any("sport" in kw or "game" in kw for kw in keywords):
                        continue

                comb = f"{m.ticker} {m.title} {m.subtitle} {m.category}".lower()
                # Strict match: require ALL extracted keywords to match (NO loose OR-fallback)
                if all(kw in comb for kw in keywords):
                    if m.last_price is not None and m.last_price > 0:
                        matched.append({
                            "market_id": m.ticker,
                            "question": m.title,
                            "venue": "Kalshi (mirrors Robinhood Predict)",
                            "current_price": round(float(m.last_price), 4),
                            "category": m.category or "General",
                            "slug": m.event_ticker.lower()
                        })
                        if len(matched) >= limit:
                            break
        except Exception as e:
            logger.warning(f"[MarketSearchService] Kalshi search failed: {e}")
        return matched

    async def _search_polymarket(self, keywords: List[str], limit: int = 10) -> List[Dict[str, Any]]:
        matched = []
        try:
            events = await self.gamma_client.list_events(active=True, limit=50)
            for ev in events:
                comb = f"{ev.title} {ev.slug} {ev.description}".lower()
                # Strict match: require ALL extracted keywords to match (NO loose OR-fallback)
                if all(kw in comb for kw in keywords):
                    for m in ev.markets:
                        if m.outcome_prices and len(m.outcome_prices) > 0:
                            try:
                                price = round(float(m.outcome_prices[0]), 4)
                                if price > 0:
                                    matched.append({
                                        "market_id": m.slug or m.id,
                                        "question": m.question or ev.title,
                                        "venue": "Polymarket",
                                        "current_price": price,
                                        "category": m.category or "General",
                                        "slug": m.slug or ev.slug
                                    })
                                    if len(matched) >= limit:
                                        break
                            except (ValueError, TypeError):
                                pass
                    if len(matched) >= limit:
                        break
        except Exception as e:
            logger.warning(f"[MarketSearchService] Polymarket search failed: {e}")
        return matched
