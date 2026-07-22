"""
Gamma API Client for Polymarket.

Provides metadata, market lists, discovery, and search functionality.
"""

from typing import List, Optional, Dict, Any
import httpx
from .models import PolymarketMarket, PolymarketEvent

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

    async def fetch_market(self, market_id: str) -> Optional[PolymarketMarket]:
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(f"{self.base_url}/markets/{market_id}")
                if resp.status_code == 200:
                    return self._parse_market(resp.json())
            except Exception:
                pass
        return None

    async def fetch_market_by_slug(self, slug: str) -> Optional[PolymarketMarket]:
        # Fetching markets filter by slug
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(f"{self.base_url}/markets", params={"slug": slug})
                if resp.status_code == 200:
                    data = resp.json()
                    if isinstance(data, list) and len(data) > 0:
                        return self._parse_market(data[0])
            except Exception:
                pass
        return None

    async def list_markets(self, active: bool = True, limit: int = 20, offset: int = 0) -> List[PolymarketMarket]:
        async with httpx.AsyncClient() as client:
            try:
                params = {
                    "active": "true" if active else "false",
                    "limit": limit,
                    "offset": offset
                }
                resp = await client.get(f"{self.base_url}/markets", params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    if isinstance(data, list):
                        return [self._parse_market(m) for m in data]
            except Exception:
                pass
        return []

    async def fetch_event(self, event_id: str) -> Optional[PolymarketEvent]:
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(f"{self.base_url}/events/{event_id}")
                if resp.status_code == 200:
                    return self._parse_event(resp.json())
            except Exception:
                pass
        return None

    async def fetch_event_by_slug(self, slug: str) -> Optional[PolymarketEvent]:
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(f"{self.base_url}/events", params={"slug": slug})
                if resp.status_code == 200:
                    data = resp.json()
                    if isinstance(data, list) and len(data) > 0:
                        return self._parse_event(data[0])
            except Exception:
                pass
        return None

    async def list_events(self, active: bool = True, limit: int = 20, offset: int = 0) -> List[PolymarketEvent]:
        async with httpx.AsyncClient() as client:
            try:
                params = {
                    "active": "true" if active else "false",
                    "limit": limit,
                    "offset": offset
                }
                resp = await client.get(f"{self.base_url}/events", params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    if isinstance(data, list):
                        return [self._parse_event(e) for e in data]
            except Exception:
                pass
        return []

    async def search(self, query: str) -> List[Dict[str, Any]]:
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(f"{self.base_url}/public-search", params={"q": query})
                if resp.status_code == 200:
                    data = resp.json()
                    if isinstance(data, list):
                        return data
            except Exception:
                pass
        return []
