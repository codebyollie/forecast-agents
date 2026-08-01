from typing import List, Dict
from .base import BaseSource
from .news import NewsSource
from .rss import RssSource
from .twitter import TwitterSource
from .reddit import RedditSource
from .blockchain import BlockchainSource
from .kalshi import KalshiSource
from .facts_ai import FactsAISource, FactsAIError
from ..models.evidence import Evidence
from ..config import ForecastConfig

import os
import asyncio
import logging

logger = logging.getLogger(__name__)

class SourceManager:
    def __init__(self, config: ForecastConfig):
        self.config = config
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
        facts_ai_key = getattr(config.facts_ai, "api_key", "") or os.getenv("FACTSAI_API_KEY", "") or os.getenv("FACTS_AI_API_KEY", "")
        facts_ai_enabled = (
            getattr(config.facts_ai, "enabled", False)
            or (os.getenv("FACTSAI_ENABLED", "false").lower() in ("true", "yes", "1", "on"))
            or (os.getenv("FACTS_AI_ENABLED", "false").lower() in ("true", "yes", "1", "on"))
            or bool(facts_ai_key)
        )
        
        if facts_ai_enabled and facts_ai_key:
            self.sources["facts_ai"] = FactsAISource(
                api_key=facts_ai_key,
                api_url=config.facts_ai.api_url,
                query_max_length=config.facts_ai.query_max_length
            )

    async def _fetch_single_source(self, name: str, source: BaseSource, query: str, limit: int) -> List[Evidence]:
        try:
            return await asyncio.wait_for(source.fetch(query, limit=limit), timeout=8.0)
        except Exception as e:
            logger.warning(f"[SourceManager] Source '{name}' fetch failed or timed out: {e}")
            return []

    async def gather_evidence(self, query: str, limit: int = 5) -> List[Evidence]:
        tasks = [
            asyncio.create_task(self._fetch_single_source(name, source, query, limit))
            for name, source in self.sources.items()
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        all_evidence = []
        for res in results:
            if isinstance(res, list):
                all_evidence.extend(res)
        return all_evidence

__all__ = [
    "BaseSource",
    "NewsSource",
    "RssSource",
    "TwitterSource",
    "RedditSource",
    "BlockchainSource",
    "KalshiSource",
    "SourceManager",
]

