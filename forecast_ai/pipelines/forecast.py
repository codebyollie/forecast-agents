"""
Forecast Pipeline.

Coordinates evidence gathering, agent predictions, consensus aggregation, and memory logging.
"""

import asyncio
from typing import List, Dict, Any, Optional
from ..config import ForecastConfig
from ..models.forecast import ForecastResult
from ..models.evidence import Evidence
from ..sources import SourceManager
from ..providers import ProviderManager
from ..consensus import ConsensusEngine
from ..memory import MemoryStore
from ..agents import NewsAgent, SocialAgent, RedditAgent, ResearchAgent, MacroAgent, OnchainAgent, MarketAgent

class ForecastPipeline:
    def __init__(self, config: ForecastConfig, memory_store: Optional[MemoryStore] = None):
        self.config = config
        self.source_manager = SourceManager(config)
        self.provider_manager = ProviderManager(config)
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
                    # Get provider for agent
                    provider = self.provider_manager.get_provider(a_cfg.provider)
                    self.agents[name] = agent_classes[name](name, provider, self.config)
                except Exception:
                    pass

    async def run_forecast(self, question: str, market_id: str = "custom_market") -> ForecastResult:
        """
        Orchestrates full forecasting process.
        """
        # 1. Gather evidence
        evidence = await self.source_manager.gather_evidence(question)

        # 2. Query active agents in parallel
        tasks = []
        active_agents = list(self.agents.values())
        for agent in active_agents:
            # Filter evidence relevant to agent if needed, or send all
            agent_evidence = [e for e in evidence if e.source_name in (agent.name, "polymarket", "kalshi", "rss", "news")]
            if not agent_evidence:
                agent_evidence = evidence
            tasks.append(agent.forecast(question, agent_evidence))

        predictions = []
        if tasks:
            predictions = await asyncio.gather(*tasks)

        # 3. Apply Consensus Engine
        reputations = self.memory_store.get_agent_reputations()
        result = await self.consensus_engine.aggregate_predictions(market_id, predictions, reputations)

        # 4. Save to Memory
        self.memory_store.save_forecast(result)

        return result
