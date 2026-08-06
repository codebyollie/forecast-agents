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

CATEGORY_MAP = {
    "politics": "Politics",
    "political": "Politics",
    "elections": "Politics",
    "election": "Politics",
    "president": "Politics",
    "congress": "Politics",
    "senate": "Politics",
    "governor": "Politics",
    "white house": "Politics",
    "trump": "Politics",
    "biden": "Politics",
    "crypto": "Crypto",
    "bitcoin": "Crypto",
    "ethereum": "Crypto",
    "solana": "Crypto",
    "blockchain": "Crypto",
    "economics": "Economy",
    "economic": "Economy",
    "economy": "Economy",
    "financials": "Economy",
    "finance": "Economy",
    "business": "Economy",
    "federal reserve": "Economy",
    "interest rate": "Economy",
    "inflation": "Economy",
    "recession": "Economy",
    "unemployment": "Economy",
    "gdp": "Economy",
    "climate": "Climate",
    "weather": "Climate",
    "temperature": "Climate",
    "temp ": "Climate",
    "hurricane": "Climate",
    "rainfall": "Climate",
    "snowfall": "Climate",
    "commodities": "Commodities",
    "commodity": "Commodities",
    "oil": "Commodities",
    "gold": "Commodities",
    "silver": "Commodities",
    "sports": "Sports",
    "baseball": "Sports",
    "basketball": "Sports",
    "football": "Sports",
    "soccer": "Sports",
    "tennis": "Sports",
    "entertainment": "Entertainment",
    "pop culture": "Entertainment",
    "movies": "Entertainment",
    "music": "Entertainment",
    "awards": "Entertainment",
    "science & technology": "Tech",
    "technology": "Tech",
    "artificial intelligence": "Tech",
    "science": "Tech",
    "tech": "Tech",
    "world": "World",
    "geopolitics": "World",
    "ukraine": "World",
    "russia": "World",
    "israel": "World",
    "iran": "World",
    "ceasefire": "World",
    "news": "World"
}

POLYMARKET_CATEGORY_TAGS = {
    "Politics": ["politics"],
    "Crypto": ["crypto"],
    "Economy": ["business", "economy", "finance"],
    "Climate": ["climate", "weather"],
    "Commodities": ["commodities"],
    "Sports": ["sports"],
    "Entertainment": ["pop-culture", "entertainment"],
    "Tech": ["technology", "science", "ai"],
    "World": ["world", "geopolitics"],
}

def normalize_category(raw_cat: str) -> str:
    if not raw_cat:
        return "Other"
    raw_lower = raw_cat.lower()
    for k, v in CATEGORY_MAP.items():
        if k in raw_lower:
            return v
    return "Other"

def _poly_outcomes(market: Any) -> List[Dict[str, Any]]:
    prices = market.outcome_prices or []
    labels = [token.get("outcome") for token in market.tokens]
    return [
        {"label": labels[index] if index < len(labels) else f"Outcome {index + 1}", "price": round(float(price), 4)}
        for index, price in enumerate(prices)
    ]

def _kalshi_category(market: Any) -> str:
    return normalize_category(f"{market.category} {market.title} {market.subtitle}")

def _polymarket_category(event: Any, market: Any = None) -> str:
    raw = event.raw_data or {}
    tag_parts = []
    for tag in raw.get("tags", []) or []:
        if isinstance(tag, dict):
            tag_parts.extend([str(tag.get("label") or ""), str(tag.get("slug") or "")])
        elif tag:
            tag_parts.append(str(tag))
    market_parts = ""
    if market is not None:
        market_parts = f"{getattr(market, 'category', '')} {getattr(market, 'question', '')}"
    else:
        market_parts = " ".join(
            f"{getattr(item, 'category', '')} {getattr(item, 'question', '')}"
            for item in (getattr(event, "markets", []) or [])
        )
    return normalize_category(
        " ".join([
            str(raw.get("category") or ""),
            str(raw.get("subcategory") or ""),
            *tag_parts,
            str(event.title or ""),
            market_parts,
        ])
    )

_KALSHI_CURSORS: Dict[str, str] = {}  # session_key -> cursor

class MarketSearchService:
    def __init__(
        self,
        kalshi_base_url: str = "https://external-api.kalshi.com/trade-api/v2",
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
        venue_name = (venue or "").lower()

        # Do not resolve an identifier against the wrong venue: slugs and
        # tickers can both be opaque strings and a cross-venue guess can return
        # a valid but unrelated market.
        if not venue_name or "kalshi" in venue_name or "robinhood" in venue_name:
            try:
                k_mkt = await self.kalshi_client.fetch_market_by_ticker(market_id.upper())
                if k_mkt and k_mkt.status in ("open", "active") and k_mkt.last_price is not None and k_mkt.last_price > 0:
                    return round(float(k_mkt.last_price), 4)
            except Exception:
                pass

        if not venue_name or "polymarket" in venue_name:
            try:
                p_mkt = await self.gamma_client.fetch_market(market_id)
                if p_mkt and p_mkt.active and not p_mkt.closed and p_mkt.outcome_prices:
                    return round(float(p_mkt.outcome_prices[0]), 4)

                ev = await self.gamma_client.fetch_event_by_slug(market_id)
                if ev:
                    active_markets = [m for m in ev.markets if m.active and not m.closed and m.outcome_prices]
                    if active_markets:
                        return round(float(active_markets[0].outcome_prices[0]), 4)
            except Exception:
                pass

        return None

    async def search_markets(self, query: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search open prediction markets across Kalshi and Polymarket matching query text or URL.
        If query is empty/None, returns a list of top active/open markets on both platforms.
        Returns normalized list: [{market_id, question, venue, current_price, category, slug}]
        """
        if not query or not query.strip():
            # Return active/popular open markets from both venues
            results = []
            try:
                # 1. Fetch top 10 general open markets from Kalshi
                k_mkts, _ = await self.kalshi_client.fetch_markets(limit=15, status="open")
                for m in k_mkts:
                    if m.last_price is not None and m.last_price > 0:
                        results.append({
                            "market_id": m.ticker,
                            "question": m.title,
                            "venue": "Kalshi",
                            "current_price": round(float(m.last_price), 4),
                            "category": _kalshi_category(m),
                            "volume": float(m.volume),
                            "end_date": m.expiration_time,
                            "image": None,
                            "outcomes": ([
                                {"label": "Yes", "price": round(float(m.last_price), 4)},
                                {"label": "No", "price": round(1.0 - float(m.last_price), 4)},
                            ] if m.last_price is not None else []),
                            "slug": m.event_ticker.lower()
                        })
            except Exception as e:
                logger.warning(f"[MarketSearchService] Failed to load active Kalshi markets: {e}")

            try:
                # 2. Fetch top active events from Polymarket Gamma
                p_events = await self.gamma_client.list_events(active=True, limit=15)
                for ev in p_events:
                    for m in ev.markets:
                        if m.outcome_prices and len(m.outcome_prices) > 0:
                            try:
                                price = round(float(m.outcome_prices[0]), 4)
                                if price > 0:
                                    results.append({
                                        "market_id": m.slug or m.id,
                                        "question": m.question or ev.title,
                                        "venue": "Polymarket",
                                        "current_price": price,
                                        "category": normalize_category(m.category or ev.raw_data.get("category", "") or ev.title),
                                        "volume": float(m.volume),
                                        "end_date": m.end_date_iso,
                                        "image": m.image,
                                        "outcomes": _poly_outcomes(m),
                                        "slug": m.slug or ev.slug
                                    })
                                    break # Only take one market per event for diversity
                            except Exception:
                                pass
            except Exception as e:
                logger.warning(f"[MarketSearchService] Failed to load active Polymarket events: {e}")

            return results[:limit]

        clean_q = query.strip()

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
                        "category": normalize_category(m.category or ""),
                        "volume": float(m.volume),
                        "end_date": m.end_date_iso,
                        "image": m.image,
                        "outcomes": _poly_outcomes(m),
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
                        "venue": "Kalshi",
                        "current_price": round(float(k_mkt.last_price), 4),
                        "category": _kalshi_category(k_mkt),
                        "volume": float(k_mkt.volume),
                        "end_date": k_mkt.expiration_time,
                        "image": None,
                        "outcomes": [
                            {"label": "Yes", "price": round(float(k_mkt.last_price), 4)},
                            {"label": "No", "price": round(1.0 - float(k_mkt.last_price), 4)},
                        ],
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
                    s_mkts, _ = await self.kalshi_client.fetch_markets(limit=20, status="open", series_ticker=s_ticker)
                    markets_to_check.extend(s_mkts)

            # Also fetch general open markets
            gen_mkts, _ = await self.kalshi_client.fetch_markets(limit=100, status="open")
            markets_to_check.extend(gen_mkts)

            seen_tickers = set()
            for m in markets_to_check:
                if m.ticker in seen_tickers:
                    continue
                seen_tickers.add(m.ticker)

                # Skip closed or inactive markets
                if m.status not in ("open", "active"):
                    continue

                # Skip multi-game sports parlays unless explicitly queried
                if m.ticker.startswith("KXMVESPORTS") or m.ticker.startswith("KXMVECROSS"):
                    if not any("sport" in kw or "game" in kw for kw in keywords):
                        continue

                comb = f"{m.ticker} {m.title} {m.subtitle} {m.category}".lower()
                match_score = sum(1 for kw in keywords if kw in comb)
                if match_score > 0:
                    price = None
                    if m.last_price is not None and m.last_price > 0:
                        price = float(m.last_price)
                    elif m.yes_bid > 0 and m.yes_ask > 0:
                        price = (m.yes_bid + m.yes_ask) / 2.0

                    if price is not None and price > 0:
                        matched.append({
                            "market_id": m.ticker,
                            "question": m.title,
                            "venue": "Kalshi",
                            "current_price": round(price, 4),
                            "category": _kalshi_category(m),
                            "volume": float(m.volume),
                            "end_date": m.expiration_time,
                            "image": None,
                            "outcomes": [
                                {"label": "Yes", "price": round(float(price), 4)},
                                {"label": "No", "price": round(1.0 - float(price), 4)},
                            ],
                            "slug": m.event_ticker.lower(),
                            "_match_score": match_score,
                        })
        except Exception as e:
            logger.warning(f"[MarketSearchService] Kalshi search failed: {e}")
        matched.sort(key=lambda item: item.pop("_match_score", 0), reverse=True)
        return matched[:limit]

    async def _search_polymarket(self, keywords: List[str], limit: int = 10) -> List[Dict[str, Any]]:
        matched = []
        try:
            # Query Polymarket public-search using keywords joined by space
            query_str = " ".join(keywords)
            events = await self.gamma_client.search_events(query_str)
            
            # Fallback to list_events if public search returned nothing or failed
            if not events:
                events = await self.gamma_client.list_events(active=True, limit=50)

            for ev in events:
                comb = " ".join([
                    ev.title,
                    ev.slug,
                    ev.description,
                    *[
                        f"{m.question} {m.slug} {m.category}"
                        for m in ev.markets
                    ],
                ]).lower()
                match_score = sum(1 for kw in keywords if kw in comb)
                if match_score > 0:
                    for m in ev.markets:
                        # Exclude closed or inactive markets
                        if m.closed or not m.active:
                            continue
                        if m.outcome_prices and len(m.outcome_prices) > 0:
                            try:
                                price = round(float(m.outcome_prices[0]), 4)
                                if price > 0:
                                    matched.append({
                                        "market_id": m.slug or m.id,
                                        "question": m.question or ev.title,
                                        "venue": "Polymarket",
                                        "current_price": price,
                                        "category": normalize_category(m.category or ev.raw_data.get("category", "") or ev.title),
                                        "volume": float(m.volume),
                                        "end_date": m.end_date_iso,
                                        "image": m.image,
                                        "outcomes": _poly_outcomes(m),
                                        "slug": m.slug or ev.slug,
                                        "_match_score": match_score,
                                    })
                            except (ValueError, TypeError):
                                pass
        except Exception as e:
            logger.warning(f"[MarketSearchService] Polymarket search failed: {e}")
        matched.sort(key=lambda item: item.pop("_match_score", 0), reverse=True)
        return matched[:limit]

    async def browse_markets(self, venue: str = "all", category: Optional[str] = None, sort: str = "volume", page: int = 1, page_size: int = 24, q: Optional[str] = None) -> Dict[str, Any]:
        """
        Browse and list markets with pagination, sorting, and category filtering.
        """
        category = category if category and category.lower() != "all" else None

        if q:
            # Delegate to existing keyword search (which does not paginate currently, so we return it as page 1)
            search_results = await self.search_markets(q, limit=max(50, page_size * 3))
            # Normalize categories in search results
            for r in search_results:
                r["category"] = normalize_category(r.get("category", ""))
                r["image"] = r.get("image")
            if venue != "all":
                search_results = [
                    r for r in search_results
                    if str(r.get("venue") or "").lower() == venue
                ]
            if category:
                target_category = normalize_category(category)
                search_results = [
                    r for r in search_results
                    if normalize_category(r.get("category", "")) == target_category
                ]
            return {
                "results": search_results[:page_size],
                "page": page,
                "page_size": page_size,
                "has_more": False
            }

        tasks = []
        fetch_kalshi = venue in ("all", "kalshi")
        fetch_poly = venue in ("all", "polymarket")

        # Kalshi Pagination State
        kalshi_cursor = None
        kalshi_cache_key = f"{category or 'all'}_{sort}_{page}"
        if page > 1:
            kalshi_cursor = _KALSHI_CURSORS.get(kalshi_cache_key)
            if fetch_kalshi and not kalshi_cursor:
                # We don't have the cursor for this page, which means they skipped pages. 
                # Kalshi cannot jump pages without cursor. We will just fetch from beginning or return empty.
                pass

        async def _get_kalshi():
            if not fetch_kalshi:
                return [], None
            
            # If category is provided, we must first discover series for that category
            series_tickers = []
            target_category = normalize_category(category or "") if category else None
            if category:
                # Resolve our normalized UI category to Kalshi's canonical
                # category, then discover the most active series in it.
                tags_data = await self.kalshi_client.get_tags_by_categories()
                target_k_categories = []
                for k_cat in tags_data.keys():
                    if normalize_category(k_cat) == target_category:
                        target_k_categories.append(k_cat)
                
                for k_cat in target_k_categories:
                    s_tickers = await self.kalshi_client.get_series(k_cat, limit=12)
                    series_tickers.extend(s_tickers)
            
            # Kalshi returns markets in API order rather than by liquidity.
            # The first ~100 rows are frequently newly-created, zero-volume
            # hourly contracts, which made the UI look as if Kalshi had no
            # useful markets. Pull the full supported page and sort locally.
            k_limit = 1000
            if series_tickers:
                batches = await asyncio.gather(*[
                    self.kalshi_client.fetch_markets(
                        limit=250,
                        status="open",
                        series_ticker=series_ticker,
                    )
                    for series_ticker in dict.fromkeys(series_tickers)
                ])
                market_by_ticker = {
                    market.ticker: market
                    for markets, _ in batches
                    for market in markets
                }
                mkts = list(market_by_ticker.values())
                next_cursor = None
            else:
                mkts, next_cursor = await self.kalshi_client.fetch_markets(
                    limit=k_limit,
                    status="open",
                    cursor=kalshi_cursor,
                )
            
            results = []
            for m in mkts:
                if m.status not in ("open", "active"):
                    continue
                # We don't have category directly on m. We can infer from series if we had a map, 
                # but Kalshi deprecated it. We'll mark as "Other" unless we can map from title/subtitle.
                cat = target_category if series_tickers and target_category else _kalshi_category(m)
                if target_category and target_category != cat:
                    continue
                
                # Prefer the current quoted midpoint over a stale last trade.
                price = m.midpoint_price
                
                if price is not None and price > 0:
                    results.append({
                        "market_id": m.ticker,
                        "question": m.title,
                        "venue": "Kalshi",
                        "current_price": round(price, 4),
                        "category": cat,
                        "volume": float(m.volume),
                        "liquidity": 0.0, # Kalshi liquidity is deprecated
                        "yes_bid": round(float(m.yes_bid), 4),
                        "yes_ask": round(float(m.yes_ask), 4),
                        "spread": round(float(m.yes_ask - m.yes_bid), 4) if m.yes_bid > 0 and m.yes_ask > 0 else None,
                        "end_date": m.expiration_time,
                        "slug": m.event_ticker.lower(),
                        "image": None,
                        "event_id": m.event_ticker,
                        "outcomes": [
                            {"label": "Yes", "price": round(price, 4)},
                            {"label": "No", "price": round(1.0 - price, 4)},
                        ],
                        "_sort_date": m.raw_data.get("open_time", "")
                    })
            return results, next_cursor

        async def _get_poly():
            if not fetch_poly:
                return [], False

            target_category = normalize_category(category or "") if category else None
            tag_slugs = POLYMARKET_CATEGORY_TAGS.get(target_category or "", [])
            used_tag_filter = False
            if tag_slugs:
                tag_batches = await asyncio.gather(*[
                    self.gamma_client.list_events(
                        active=True,
                        limit=max(page_size * 4, 50),
                        offset=0,
                        tag_slug=tag_slug,
                        related_tags=True,
                    )
                    for tag_slug in tag_slugs
                ])
                event_by_id = {
                    event.id: event
                    for batch in tag_batches
                    for event in batch
                }
                events = list(event_by_id.values())
                used_tag_filter = bool(events)
            else:
                events = []

            # Fall back to broad discovery when Polymarket has no canonical
            # tag for the requested category or a tag temporarily returns no
            # events. This also powers the unfiltered directory.
            if not events:
                p_limit = max(100, min(500, page_size * 10)) if category else (page_size if venue == "polymarket" else page_size * 2)
                p_offset = 0 if category else (page - 1) * page_size
                events = await self.gamma_client.list_events(
                    active=True,
                    limit=p_limit,
                    offset=p_offset,
                )
            else:
                p_limit = max(page_size * 4, 50)
            
            results = []
            for ev in events:
                cat = target_category if used_tag_filter and target_category else _polymarket_category(ev)
                if target_category and target_category != cat:
                    continue
                
                valid_markets = [m for m in ev.markets if m.active and not m.closed and m.outcome_prices]
                if not valid_markets:
                    continue
                
                # Grouping logic
                if len(valid_markets) == 1:
                    m = valid_markets[0]
                    price = float(m.outcome_prices[0]) if m.outcome_prices else None
                    if price:
                        results.append({
                            "market_id": m.slug or m.id,
                            "question": m.question or ev.title,
                            "venue": "Polymarket",
                            "current_price": round(price, 4),
                            "category": cat,
                            "volume": float(m.volume),
                            "liquidity": float(m.liquidity),
                            "end_date": m.end_date_iso,
                            "slug": m.slug or ev.slug,
                            "image": m.image,
                            "event_id": m.event_id or ev.id,
                            "outcomes": _poly_outcomes(m),
                            "_sort_date": m.raw_data.get("createdAt", "")
                        })
                else:
                    # Multiple markets in one event -> group them
                    m_main = valid_markets[0]
                    outcomes = []
                    total_vol = 0.0
                    total_liq = 0.0
                    for m in valid_markets:
                        price = float(m.outcome_prices[0]) if m.outcome_prices else None
                        if price:
                            label = "Yes"
                            if m.tokens and len(m.tokens) > 0:
                                label = m.tokens[0].get("outcome", "Yes")
                            outcomes.append({"label": label, "price": round(price, 4)})
                        total_vol += float(m.volume)
                        total_liq += float(m.liquidity)
                    
                    if outcomes:
                        results.append({
                            "market_id": ev.slug or ev.id,
                            "question": ev.title,
                            "venue": "Polymarket",
                            "current_price": None,
                            "category": cat,
                            "volume": total_vol,
                            "liquidity": total_liq,
                            "end_date": m_main.end_date_iso,
                            "slug": ev.slug,
                            "image": m_main.image,
                            "event_id": ev.id,
                            "outcomes": outcomes,
                            "_sort_date": m_main.raw_data.get("createdAt", "")
                        })
            
            has_more = len(events) == p_limit
            return results, has_more

        kalshi_task = asyncio.create_task(_get_kalshi())
        poly_task = asyncio.create_task(_get_poly())
        
        (k_res, k_next_cursor), (p_res, p_has_more) = await asyncio.gather(kalshi_task, poly_task)
        
        if k_next_cursor:
            _KALSHI_CURSORS[f"{category or 'all'}_{sort}_{page + 1}"] = k_next_cursor
            
        combined = k_res + p_res
        
        # Sorting
        if sort == "ending_soon":
            # Ascending by end_date, nulls last
            sort_key = lambda item: item["end_date"] or "9999-12-31"
            reverse_sort = False
        elif sort == "newest":
            # Descending by created date (we stashed it in _sort_date)
            sort_key = lambda item: item.get("_sort_date", "")
            reverse_sort = True
        else:
            # volume desc
            sort_key = lambda item: item["volume"] or 0.0
            reverse_sort = True

        # Sort each venue as well as the combined list. Venue quotas below must
        # select the best rows, not whichever order an upstream API returned.
        k_res.sort(key=sort_key, reverse=reverse_sort)
        p_res.sort(key=sort_key, reverse=reverse_sort)
        combined.sort(key=sort_key, reverse=reverse_sort)
            
        # If both venues are requested, a global volume sort can let
        # Polymarket's much larger notional volumes fill the entire page and
        # hide Kalshi completely. Keep the directory useful by reserving
        # roughly half of the first page for each venue, then fill any spare
        # slots from the remaining globally sorted results.
        if venue == "all" and k_res and p_res:
            kalshi_quota = max(1, page_size // 2)
            polymarket_quota = max(1, page_size - kalshi_quota)
            selected = k_res[:kalshi_quota] + p_res[:polymarket_quota]
            selected_keys = {(r.get("venue"), r.get("market_id")) for r in selected}
            if len(selected) < page_size:
                selected.extend(
                    r for r in combined
                    if (r.get("venue"), r.get("market_id")) not in selected_keys
                )
            selected.sort(key=sort_key, reverse=reverse_sort)
            final_results = selected[:page_size]
        else:
            final_results = combined[:page_size]

        for result in final_results:
            result.pop("_sort_date", None)
        
        has_more = bool(k_next_cursor) or p_has_more
        
        return {
            "results": final_results,
            "page": page,
            "page_size": page_size,
            "has_more": has_more
        }
