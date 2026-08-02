from typing import List, Dict
from .base import BaseSource
from .news import NewsSource
from .rss import RssSource
from .twitter import TwitterSource
from .reddit import RedditSource
from .blockchain import BlockchainSource
from .kalshi import KalshiSource
from .facts_ai import FactsAISource, FactsAIError
from .tavily_search import TavilySearchSource
from ..models.evidence import Evidence
from ..config import ForecastConfig
from .cache import SourceCache

import os
import asyncio
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class SourceManager:
    def __init__(self, config: ForecastConfig, provider_manager=None):
        self.config = config
        self.provider_manager = provider_manager
        self.cache = SourceCache()
        
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
        facts_ai_key = getattr(config.facts_ai, "api_key", "") or os.getenv("FACTSAI_API_KEY", "") or os.getenv("FACTS_AI_API_KEY", "") or "facts_ai_public_access"
        facts_ai_enabled = True  # Always enabled for testing phase
        
        self.sources["facts_ai"] = FactsAISource(
            api_key=facts_ai_key,
            api_url=config.facts_ai.api_url,
            query_max_length=config.facts_ai.query_max_length
        )

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

    async def gather_evidence(self, query: str, limit: int = 5) -> List[Evidence]:
        """
        Gathers evidence from all configured and enabled sources.
        Relies on the Caching layer to prevent redundant API calls.
        """
        tasks = []
        for name, source in self.sources.items():
            tasks.append(
                asyncio.create_task(self._fetch_single_source(name, source, query, limit))
            )
                
        if not tasks:
            logger.warning("[SourceManager] No sources configured for gathering.")
            return []

        results = await asyncio.gather(*tasks, return_exceptions=True)
        all_evidence = []
        for res in results:
            if isinstance(res, list):
                all_evidence.extend(res)
                
        # Optional: Synthesis Layer (if provider_manager is attached)
        if self.provider_manager and all_evidence:
            all_evidence = await self.synthesize_evidence(query, all_evidence)

        return all_evidence

    async def synthesize_evidence(self, query: str, evidence: List[Evidence]) -> List[Evidence]:
        """
        Uses the default LLM to deduplicate and synthesize the gathered evidence into one master document.
        """
        if not evidence:
            return []
            
        raw_text = "\n\n".join([f"[{e.source_name}] {e.title}\n{e.content}" for e in evidence])
        
        sys_prompt = "You are a Research Synthesizer. Deduplicate, verify, and summarize the provided search results into a clean, highly factual Markdown report. Include specific numbers, dates, and preserve all critical context."
        user_prompt = f"Query: {query}\n\nRaw Search Results:\n{raw_text}\n\nProvide the synthesized summary."
        
        try:
            summary = await self.provider_manager.generate_with_fallback(
                primary_name=self.config.default_provider,
                system_prompt=sys_prompt,
                user_prompt=user_prompt,
                max_tokens=2000
            )
            
            return [
                Evidence(
                    source_name="Smart Synthesizer",
                    content=summary,
                    relevance_score=1.0,
                    title=f"Synthesized Research: {query[:50]}",
                    url=""
                )
            ]
        except Exception as e:
            logger.error(f"[SourceManager] Synthesis failed: {e}")
            return evidence  # Fallback to raw evidence

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

