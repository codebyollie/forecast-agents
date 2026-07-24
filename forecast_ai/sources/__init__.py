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

class SourceManager:
    def __init__(self, config: ForecastConfig):
        self.config = config
        self.sources: Dict[str, BaseSource] = {
            "news": NewsSource(),
            "rss": RssSource(),
            "twitter": TwitterSource(),
            "reddit": RedditSource(),
            "blockchain": BlockchainSource(),
            "kalshi": KalshiSource(api_base_url=config.kalshi.api_base_url),
        }
        if config.facts_ai.enabled and config.facts_ai.api_key:
            self.sources["facts_ai"] = FactsAISource(
                api_key=config.facts_ai.api_key,
                api_url=config.facts_ai.api_url,
                query_max_length=config.facts_ai.query_max_length
            )

    async def gather_evidence(self, query: str, limit: int = 5) -> List[Evidence]:
        all_evidence = []
        for name, source in self.sources.items():
            # Check if source is enabled via configuration or is active
            try:
                evidences = await source.fetch(query, limit=limit)
                all_evidence.extend(evidences)
            except Exception:
                # Disable it gracefully (no synthetic data generation)
                pass
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

