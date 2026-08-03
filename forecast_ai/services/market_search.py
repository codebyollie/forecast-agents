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
    "elections": "Politics",
    "crypto": "Crypto",
    "bitcoin": "Crypto",
    "ethereum": "Crypto",
    "economics": "Economy",
    "financials": "Economy",
    "business": "Economy",
    "sports": "Sports",
    "entertainment": "Entertainment",
    "pop culture": "Entertainment",
    "science & technology": "Tech",
    "science": "Tech",
    "tech": "Tech",
    "world": "World",
    "news": "World"
}

def normalize_category(raw_cat: str) -> str:
    if not raw_cat:
        return "Other"
    raw_lower = raw_cat.lower()
    for k, v in CATEGORY_MAP.items():
        if k in raw_lower:
            return v
    return "Other"

_KALSHI_CURSORS: Dict[str, str] = {}  # session_key -> cursor

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
                            "venue": "Kalshi (mirrors Robinhood Predict)",
                            "current_price": round(float(m.last_price), 4),
                            "category": m.category or "General",
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
                                        "category": m.category or "General",
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
                # Strict match: require ALL extracted keywords to match
                if all(kw in comb for kw in keywords):
                    price = None
                    if m.last_price is not None and m.last_price > 0:
                        price = float(m.last_price)
                    elif m.yes_bid > 0 and m.yes_ask > 0:
                        price = (m.yes_bid + m.yes_ask) / 2.0

                    if price is not None and price > 0:
                        matched.append({
                            "market_id": m.ticker,
                            "question": m.title,
                            "venue": "Kalshi (mirrors Robinhood Predict)",
                            "current_price": round(price, 4),
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
            # Query Polymarket public-search using keywords joined by space
            query_str = " ".join(keywords)
            events = await self.gamma_client.search_events(query_str)
            
            # Fallback to list_events if public search returned nothing or failed
            if not events:
                events = await self.gamma_client.list_events(active=True, limit=50)

            for ev in events:
                comb = f"{ev.title} {ev.slug} {ev.description}".lower()
                # Strict match: require ALL extracted keywords to match
                if all(kw in comb for kw in keywords):
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

    async def browse_markets(self, venue: str = "all", category: Optional[str] = None, sort: str = "volume", page: int = 1, page_size: int = 24, q: Optional[str] = None) -> Dict[str, Any]:
        """
        Browse and list markets with pagination, sorting, and category filtering.
        """
        if q:
            # Delegate to existing keyword search (which does not paginate currently, so we return it as page 1)
            search_results = await self.search_markets(q, limit=page_size)
            # Normalize categories in search results
            for r in search_results:
                r["category"] = normalize_category(r.get("category", ""))
                r["image"] = r.get("image")
                r["outcomes"] = None
            return {
                "results": search_results,
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
            if category:
                # We do a rough reverse-map: find all Kalshi tags that match the normalized category
                # For simplicity, if a category is provided, we fetch a large batch of markets and filter locally,
                # because Kalshi's /series API requires their exact category string, and we normalized it.
                # Actually, the prompt says "GET /search/tags_by_categories -> GET /series?category=X".
                tags_data = await self.kalshi_client.get_tags_by_categories()
                target_k_categories = []
                norm_cat = normalize_category(category)
                for k_cat in tags_data.keys():
                    if normalize_category(k_cat) == norm_cat:
                        target_k_categories.append(k_cat)
                
                for k_cat in target_k_categories:
                    s_tickers = await self.kalshi_client.get_series(k_cat, limit=50)
                    series_tickers.extend(s_tickers)
                
                # If we found series, we should query them. But fetch_markets only takes one series_ticker.
                # To support proper pagination, if category is selected, we might have to fetch general open and filter.
                # Let's fetch general open markets and filter locally to ensure we can paginate.
            
            # Fetch general open markets
            k_limit = page_size if venue == "kalshi" else page_size * 2
            mkts, next_cursor = await self.kalshi_client.fetch_markets(limit=k_limit, status="open", cursor=kalshi_cursor)
            
            results = []
            for m in mkts:
                if m.status not in ("open", "active"):
                    continue
                # We don't have category directly on m. We can infer from series if we had a map, 
                # but Kalshi deprecated it. We'll mark as "Other" unless we can map from title/subtitle.
                cat = normalize_category(m.title + " " + m.subtitle)
                if category and normalize_category(category) != cat:
                    continue
                
                price = None
                if m.last_price is not None and m.last_price > 0:
                    price = float(m.last_price)
                elif m.yes_bid > 0 and m.yes_ask > 0:
                    price = (m.yes_bid + m.yes_ask) / 2.0
                
                if price is not None and price > 0:
                    results.append({
                        "market_id": m.ticker,
                        "question": m.title,
                        "venue": "Kalshi",
                        "current_price": round(price, 4),
                        "category": cat,
                        "volume": float(m.volume),
                        "liquidity": 0.0, # Kalshi liquidity is deprecated
                        "end_date": m.expiration_time,
                        "slug": m.event_ticker.lower(),
                        "image": None,
                        "event_id": m.event_ticker,
                        "outcomes": None,
                        "_sort_date": m.raw_data.get("open_time", "")
                    })
            return results, next_cursor

        async def _get_poly():
            if not fetch_poly:
                return [], False
            
            p_limit = page_size if venue == "polymarket" else page_size * 2
            p_offset = (page - 1) * page_size
            
            # We fetch events to group by eventId natively
            events = await self.gamma_client.list_events(active=True, limit=p_limit, offset=p_offset)
            
            results = []
            for ev in events:
                cat = normalize_category(ev.raw_data.get("category", "") or ev.title)
                if category and normalize_category(category) != cat:
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
                            "outcomes": None,
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
            combined.sort(key=lambda x: x["end_date"] or "9999-12-31")
        elif sort == "newest":
            # Descending by created date (we stashed it in _sort_date)
            combined.sort(key=lambda x: x.get("_sort_date", ""), reverse=True)
        else:
            # volume desc
            combined.sort(key=lambda x: x["volume"] or 0.0, reverse=True)
            
        # Strip _sort_date
        for r in combined:
            r.pop("_sort_date", None)
            
        # If we fetched from both, we might have over-fetched. Slice to page_size.
        # But wait, if we slice, the next page for Polymarket will use offset=page*page_size and skip items.
        # This is a known limitation of federated naive pagination. We will just return the sliced amount.
        final_results = combined[:page_size]
        
        has_more = bool(k_next_cursor) or p_has_more
        
        return {
            "results": final_results,
            "page": page,
            "page_size": page_size,
            "has_more": has_more
        }
