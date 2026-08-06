"""
Forecast Pipeline.

Coordinates evidence gathering, agent predictions, consensus aggregation, and memory logging.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from ..config import ForecastConfig
from ..models.forecast import ForecastResult
from ..models.evidence import Evidence
from ..sources import SourceManager
from ..providers import ProviderManager, ProviderError
from ..consensus import ConsensusEngine
from ..memory import MemoryStore
from ..agents import NewsAgent, SocialAgent, RedditAgent, ResearchAgent, MacroAgent, OnchainAgent, MarketAgent

logger = logging.getLogger(__name__)

class ForecastPipeline:
    def __init__(self, config: ForecastConfig, memory_store: Optional[MemoryStore] = None):
        self.config = config
        self.provider_manager = ProviderManager(config)
        self.source_manager = SourceManager(config)
        self.consensus_engine = ConsensusEngine(config)
        self.memory_store = memory_store or MemoryStore(config)
        self._init_agents()

    def _init_agents(self):
        self.agents = {}
        agent_classes = {
            "news": NewsAgent,
            "social": SocialAgent,
            "reddit": RedditAgent,
            "research": ResearchAgent,
            "macro": MacroAgent,
            "onchain": OnchainAgent,
            "market": MarketAgent
        }

        for name, a_cfg in self.config.agents.items():
            if a_cfg.enabled and name in agent_classes:
                try:
                    primary_name = a_cfg.provider or self.config.default_provider
                    provider = self.provider_manager.get_provider(primary_name)
                    self.agents[name] = agent_classes[name](
                        name=name,
                        provider=provider,
                        config=self.config,
                        provider_manager=self.provider_manager,
                        primary_provider_name=primary_name
                    )
                except Exception as e:
                    logger.warning(f"[ForecastPipeline] Could not initialize agent '{name}': {e}")

    async def run_forecast(
        self,
        question: str,
        market_id: str = "custom_market",
        model_override: Optional[str] = None,
        venue: Optional[str] = None,
    ) -> ForecastResult:
        """
        Orchestrates full forecasting process.
        """
        # 1. Gather evidence
        evidence = await self.source_manager.gather_evidence(
            question,
            market_id=market_id,
            venue=venue,
        )

        # 2. Query active agents in parallel
        active_agents = list(self.agents.values())
        predictions = []

        agent_source_map = {
            "news": ["news", "rss", "facts_ai", "tavily"],
            "social": ["twitter", "social"],
            "reddit": ["reddit"],
            "research": ["facts_ai", "arxiv", "research", "tavily"],
            "macro": ["macro", "cme", "fred", "news", "rss", "tavily"],
            "onchain": ["blockchain", "onchain", "polygonscan"],
            "market": ["kalshi", "polymarket", "market", "robinhood"]
        }

        async def _query_agent(agent):
            allowed = agent_source_map.get(agent.name.lower(), [agent.name.lower()])
            agent_evidence = [e for e in evidence if any(s in e.source_name.lower() for s in allowed)]
            if not agent_evidence and agent.name.lower() not in ("social", "reddit"):
                agent_evidence = evidence
            try:
                return await agent.forecast(
                    question,
                    agent_evidence,
                    model_override=model_override,
                )
            except ProviderError as pe:
                logger.error(f"[ForecastPipeline] Agent '{agent.name}' failed after provider fallbacks: {pe}")
                return None
            except Exception as e:
                logger.error(f"[ForecastPipeline] Unexpected error querying agent '{agent.name}': {e}")
                return None

        if active_agents:
            raw_predictions = await asyncio.gather(*[_query_agent(a) for a in active_agents])
            predictions = [p for p in raw_predictions if p is not None]

        if not predictions:
            raise ProviderError("pipeline", f"All active agents failed to generate predictions for '{question}'")

        # 3. Apply Consensus Engine
        reputations = self.memory_store.get_agent_reputations()
        result = await self.consensus_engine.aggregate_predictions(market_id, predictions, reputations)
        
        # 4. Attach model_used metadata reflecting reality
        default_provider = self.config.providers.get(self.config.default_provider)
        result.metadata["model_used"] = (
            model_override
            or (default_provider.model_id if default_provider else self.config.default_provider)
        )
        result.metadata["market_context"] = [
            {
                "source": item.source_name,
                "title": item.title,
                "url": item.url,
                "metadata": item.metadata,
            }
            for item in evidence
            if item.source_name in ("kalshi", "polymarket")
        ]

        # 5. Save to the self-hosted memory store.
        self.memory_store.save_forecast(result)

        return result
