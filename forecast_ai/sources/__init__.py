from typing import List, Dict
from .base import BaseSource
from .news import NewsSource
from .rss import RssSource
from .twitter import TwitterSource
from .reddit import RedditSource
from .blockchain import BlockchainSource
from .kalshi import KalshiSource
from .tavily_search import TavilySearchSource
from ..models.evidence import Evidence
from ..config import ForecastConfig
from .cache import SourceCache
from ..kalshi.client import KalshiClient
from ..polymarket.gamma import GammaClient
from ..polymarket.clob import ClobClient

import os
import asyncio
import logging
from pathlib import Path
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class SourceManager:
    def __init__(self, config: ForecastConfig):
        self.config = config
        self.cache = SourceCache(
            cache_dir=Path(config.memory.store_dir) / "cache"
        )
        self.kalshi_client = KalshiClient(
            base_url=config.kalshi.api_base_url,
        )
        self.gamma_client = GammaClient(base_url=config.polymarket.gamma_api_url)
        self.clob_client = ClobClient(base_url=config.polymarket.clob_api_url)
        
        news_key = getattr(config.sources, "news_api_key", "") or os.getenv("NEWS_API_KEY", "")
        twitter_token = getattr(config.sources, "twitter_bearer_token", "") or os.getenv("TWITTER_BEARER_TOKEN", "")
        polygonscan_key = getattr(config.sources, "polygonscan_key", "") or os.getenv("POLYGONSCAN_API_KEY", "")

        self.sources: Dict[str, BaseSource] = {
            "news": NewsSource(api_key=news_key),
            "rss": RssSource(),
            "twitter": TwitterSource(bearer_token=twitter_token),
            "reddit": RedditSource(),
            "blockchain": BlockchainSource(polygonscan_key=polygonscan_key),
            "kalshi": KalshiSource(api_base_url=config.kalshi.api_base_url),
        }
        tavily_key = getattr(config.tavily, "api_key", "") or os.getenv("TAVILY_API_KEY", "")
        if getattr(config.tavily, "enabled", False) or os.getenv("TAVILY_ENABLED", "").lower() in ("true", "1", "yes"):
            self.sources["tavily"] = TavilySearchSource(
                api_key=tavily_key,
                enabled=True
            )

    async def _fetch_single_source(self, name: str, source: BaseSource, query: str, limit: int) -> List[Evidence]:
        # Check Cache first
        cached = self.cache.get(name, query)
        if cached is not None:
            return cached

        try:
            results = await asyncio.wait_for(source.fetch(query, limit=limit), timeout=15.0)
            if results:
                self.cache.set(name, query, results)
            return results
        except Exception as e:
            logger.warning(f"[SourceManager] Source '{name}' fetch failed or timed out: {e}")
            return []

    async def gather_evidence(
        self,
        query: str,
        limit: int = 5,
        market_id: Optional[str] = None,
        venue: Optional[str] = None,
    ) -> List[Evidence]:
        """
        Gathers evidence from all configured and enabled sources.
        Relies on the Caching layer to prevent redundant API calls.
        """
        tasks = []
        if market_id and market_id != "custom_market":
            market_evidence = await self.gather_market_evidence(
                market_id=market_id,
                venue=venue,
                limit=limit,
            )
        else:
            market_evidence = []
        for name, source in self.sources.items():
            tasks.append(
                asyncio.create_task(self._fetch_single_source(name, source, query, limit))
            )
                
        if not tasks:
            logger.warning("[SourceManager] No sources configured for gathering.")
            return []

        results = await asyncio.gather(*tasks, return_exceptions=True)
        all_evidence = list(market_evidence)
        for res in results:
            if isinstance(res, list):
                all_evidence.extend(res)
                
        return all_evidence

    async def gather_market_evidence(
        self,
        market_id: str,
        venue: Optional[str] = None,
        limit: int = 5,
    ) -> List[Evidence]:
        """Fetch the exact selected market and its live orderbook context."""
        venue_name = (venue or "").lower()
        evidence: List[Evidence] = []

        async def fetch_polymarket() -> List[Evidence]:
            event = await self.gamma_client.fetch_event_by_slug(market_id)
            markets = event.markets if event and event.markets else []
            if not markets:
                market = await self.gamma_client.fetch_market_by_slug(market_id)
                if market:
                    markets = [market]
            if not markets:
                return []

            selected = [m for m in markets if m.active and not m.closed]
            if not selected:
                return []

            outcome_parts = []
            orderbook_parts = []
            orderbook_metadata = []
            for market in selected[:limit]:
                prices = market.outcome_prices
                if prices:
                    outcome_parts.append(
                        f"{market.question or market.slug}: "
                        + ", ".join(f"{p:.4f}" for p in prices)
                    )
                for token in market.tokens[:2]:
                    token_id = token.get("token_id") or token.get("tokenId")
                    if not token_id:
                        continue
                    book = await self.clob_client.fetch_order_book(token_id)
                    if not book:
                        continue
                    best_bid = book.bids[0].price if book.bids else None
                    best_ask = book.asks[0].price if book.asks else None
                    orderbook_parts.append(
                        f"{market.question or market.slug} {token.get('outcome', 'outcome')}: "
                        f"bid={best_bid}, ask={best_ask}, spread={book.spread:.4f}"
                    )
                    orderbook_metadata.append({
                        "token_id": token_id,
                        "outcome": token.get("outcome"),
                        "best_bid": best_bid,
                        "best_ask": best_ask,
                        "spread": book.spread,
                    })

            first = selected[0]
            display_title = first.question or (event.title if event else first.slug)
            content = (
                f"Polymarket selected market/event: {display_title}. "
                f"Active={first.active}, Closed={first.closed}, End={first.end_date_iso}, "
                f"Volume={first.volume}, Liquidity={first.liquidity}. "
                f"Outcome prices: {'; '.join(outcome_parts) or 'unavailable'}. "
                f"CLOB order book: {'; '.join(orderbook_parts) or 'unavailable'}."
            )
            metadata = {
                "market_id": market_id,
                "venue": "Polymarket",
                "outcomes": [
                    {"label": token.get("outcome"), "price": price}
                    for market in selected[:limit]
                    for token, price in zip(market.tokens, market.outcome_prices)
                ],
                "order_books": orderbook_metadata,
            }
            return [Evidence(
                source_name="polymarket",
                content=content,
                title=first.question or (event.title if event else first.slug),
                url=f"https://polymarket.com/event/{event.slug}" if event else "",
                relevance_score=1.0,
                metadata=metadata,
            )]

        async def fetch_kalshi() -> List[Evidence]:
            market = await self.kalshi_client.fetch_market_by_ticker(market_id.upper())
            if not market or market.status not in ("open", "active"):
                return []
            orderbook = await self.kalshi_client.fetch_orderbook(market.ticker)
            orderbook_text = ""
            if orderbook:
                orderbook_text = (
                    f" Orderbook midpoint={orderbook.midpoint}, spread={orderbook.spread}, "
                    f"YES bids={len(orderbook.yes_bids)}, YES asks={len(orderbook.yes_asks)}."
                )
            content = (
                f"Kalshi selected market: {market.title}. Status={market.status}, "
                f"Last price={market.last_price}, YES bid/ask={market.yes_bid}/{market.yes_ask}, "
                f"Volume={market.volume}, Open interest={market.open_interest}, "
                f"Expiration={market.expiration_time}.{orderbook_text}"
            )
            return [Evidence(
                source_name="kalshi",
                content=content,
                title=market.title,
                url=f"https://kalshi.com/markets/{market.ticker}",
                relevance_score=1.0,
                metadata={
                    "market_id": market.ticker,
                    "venue": "Kalshi",
                    "current_price": market.midpoint_price,
                    "volume": market.volume,
                    "expiration_time": market.expiration_time,
                },
            )]

        if "polymarket" in venue_name:
            return await fetch_polymarket()
        if "kalshi" in venue_name or "robinhood" in venue_name:
            return await fetch_kalshi()

        # Custom/legacy callers may omit the venue. Resolve deterministically by
        # trying Polymarket slug resolution first, then Kalshi ticker resolution.
        evidence = await fetch_polymarket()
        return evidence or await fetch_kalshi()

__all__ = [
    "BaseSource",
    "NewsSource",
    "RssSource",
    "TwitterSource",
    "RedditSource",
    "BlockchainSource",
    "KalshiSource",
    "TavilySearchSource",
    "SourceManager",
]
