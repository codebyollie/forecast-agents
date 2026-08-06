"""
Gamma API Client for Polymarket.

Provides metadata, market lists, discovery, and search functionality.
"""

import asyncio
from typing import List, Optional, Dict, Any
import logging
import httpx
from .models import PolymarketMarket, PolymarketEvent

logger = logging.getLogger(__name__)


class GammaClient:
    def __init__(self, base_url: str = "https://gamma-api.polymarket.com"):
        self.base_url = base_url.rstrip('/')

    def _parse_market(self, data: Dict[str, Any]) -> PolymarketMarket:
        # Extract token_id and outcomes if available
        tokens = []
        if "clobTokenIds" in data:
            try:
                import json
                token_ids = data["clobTokenIds"]
                if isinstance(token_ids, str):
                    token_ids = json.loads(token_ids)
                outcomes = data.get("outcomes", [])
                if isinstance(outcomes, str):
                    outcomes = json.loads(outcomes)
                for i, token_id in enumerate(token_ids):
                    outcome = outcomes[i] if i < len(outcomes) else f"Outcome {i}"
                    tokens.append({"token_id": str(token_id), "outcome": str(outcome)})
            except Exception:
                pass
        
        # If tokens list is empty, build from custom properties
        if not tokens and "outcomePrices" in data:
            try:
                import json
                prices = data["outcomePrices"]
                if isinstance(prices, str):
                    prices = json.loads(prices)
                outcomes = data.get("outcomes", [])
                if isinstance(outcomes, str):
                    outcomes = json.loads(outcomes)
                for i, outcome in enumerate(outcomes):
                    tokens.append({"token_id": f"token_{i}", "outcome": str(outcome)})
            except Exception:
                pass

        return PolymarketMarket(
            id=str(data.get("id", "")),
            question=str(data.get("question", "")),
            condition_id=str(data.get("conditionId", "")),
            slug=str(data.get("slug", "")),
            resolution_source=str(data.get("resolutionSource", "")),
            end_date_iso=str(data.get("endDate", "")),
            tokens=tokens,
            active=bool(data.get("active", True)),
            closed=bool(data.get("closed", False)),
            volume=float(data.get("volume", 0.0) or 0.0),
            liquidity=float(data.get("liquidity", 0.0) or 0.0),
            category=str(data.get("category", "")),
            event_id=str(data.get("eventId", "")),
            image=data.get("image") or data.get("icon") or None,
            raw_data=data
        )

    def _parse_event(self, data: Dict[str, Any]) -> PolymarketEvent:
        markets = []
        if "markets" in data and isinstance(data["markets"], list):
            markets = [self._parse_market(m) for m in data["markets"]]
        return PolymarketEvent(
            id=str(data.get("id", "")),
            title=str(data.get("title", "")),
            slug=str(data.get("slug", "")),
            description=str(data.get("description", "")),
            markets=markets,
            raw_data=data
        )

    def _get_client(self) -> httpx.AsyncClient:
        headers = {
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        }
        # Keep httpx's default transport so standard proxy and certificate
        # environment settings continue to work in hosted/self-hosted setups.
        return httpx.AsyncClient(headers=headers, timeout=20.0)

    async def _get_json(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        last_error: Optional[Exception] = None
        for attempt in range(1, 4):
            try:
                async with self._get_client() as client:
                    response = await client.get(f"{self.base_url}{path}", params=params)
                    response.raise_for_status()
                    return response.json()
            except (httpx.HTTPError, ValueError) as exc:
                last_error = exc
                logger.warning(
                    "[GammaClient] GET %s failed (attempt %s/3): %s",
                    path,
                    attempt,
                    exc,
                )
                if attempt < 3:
                    await asyncio.sleep(0.25 * attempt)
        logger.error("[GammaClient] GET %s failed after retries: %s", path, last_error)
        return None

    async def fetch_market(self, market_id: str) -> Optional[PolymarketMarket]:
        async with self._get_client() as client:
            try:
                resp = await client.get(f"{self.base_url}/markets/{market_id}")
                if resp.status_code == 200:
                    return self._parse_market(resp.json())
            except Exception:
                pass
        return None

    async def fetch_market_by_slug(self, slug: str) -> Optional[PolymarketMarket]:
        data = await self._get_json("/events", {"slug": slug})
        if isinstance(data, list) and data:
            event = self._parse_event(data[0])
            if event.markets:
                return event.markets[0]

        market_data = await self._get_json("/markets", {"slug": slug})
        if isinstance(market_data, list) and market_data:
            return self._parse_market(market_data[0])
        return None

    async def list_markets(self, active: bool = True, limit: int = 20, offset: int = 0) -> List[PolymarketMarket]:
        params = {
            "active": "true" if active else "false",
            "closed": "false" if active else "true",
            "limit": limit,
            "offset": offset
        }
        data = await self._get_json("/markets", params)
        if isinstance(data, list):
            return [self._parse_market(m) for m in data]
        return []

    async def fetch_event(self, event_id: str) -> Optional[PolymarketEvent]:
        async with self._get_client() as client:
            try:
                resp = await client.get(f"{self.base_url}/events/{event_id}")
                if resp.status_code == 200:
                    return self._parse_event(resp.json())
            except Exception:
                pass
        return None

    async def fetch_event_by_slug(self, slug: str) -> Optional[PolymarketEvent]:
        data = await self._get_json("/events", {"slug": slug})
        if isinstance(data, list) and data:
            return self._parse_event(data[0])
        return None

    async def list_events(
        self,
        active: bool = True,
        limit: int = 20,
        offset: int = 0,
        order: Optional[str] = None,
        ascending: Optional[bool] = None,
        tag_slug: Optional[str] = None,
        related_tags: Optional[bool] = None,
    ) -> List[PolymarketEvent]:
        params = {
            "active": "true" if active else "false",
            "closed": "false" if active else "true",
            "limit": limit,
            "offset": offset
        }
        if order:
            params["order"] = order
        if ascending is not None:
            params["ascending"] = "true" if ascending else "false"
        if tag_slug:
            params["tag_slug"] = tag_slug
        if related_tags is not None:
            params["related_tags"] = "true" if related_tags else "false"
        data = await self._get_json("/events", params)
        if isinstance(data, list):
            return [self._parse_event(e) for e in data]
        return []

    async def search(self, query: str) -> List[Dict[str, Any]]:
        async with self._get_client() as client:
            try:
                resp = await client.get(f"{self.base_url}/public-search", params={"q": query})
                if resp.status_code == 200:
                    data = resp.json()
                    if isinstance(data, list):
                        return data
                    elif isinstance(data, dict):
                        return data.get("events", [])
            except Exception:
                pass
        return []

    async def search_events(self, query: str) -> List[PolymarketEvent]:
        data = await self._get_json("/public-search", {"q": query})
        raw_events = []
        if isinstance(data, dict):
            raw_events = data.get("events", [])
        elif isinstance(data, list):
            raw_events = data
        if raw_events:
            return [self._parse_event(e) for e in raw_events if isinstance(e, dict)]
        return []
