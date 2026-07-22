"""
Polymarket Events Manager.
"""

from typing import List, Dict, Any, Optional
from .gamma import GammaClient
from .models import PolymarketEvent

class PolymarketEventsManager:
    def __init__(self, gamma: Optional[GammaClient] = None):
        self.gamma = gamma or GammaClient()

    async def get_event_with_markets(self, event_id: str) -> Optional[PolymarketEvent]:
        return await self.gamma.fetch_event(event_id)

    async def get_event_by_slug(self, slug: str) -> Optional[PolymarketEvent]:
        return await self.gamma.fetch_event_by_slug(slug)

    async def list_active_events(self, limit: int = 15) -> List[PolymarketEvent]:
        return await self.gamma.list_events(active=True, limit=limit)
