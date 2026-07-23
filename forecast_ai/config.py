"""
Unified Configuration for Forecast AI.

Dataclass-based configuration settings for LLMs, Polymarket endpoints,
Consensus Engine calibration, specialized agents, and memory.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List

@dataclass
class ProviderConfig:
    provider: str = "openai"  # "openai" | "anthropic" | "gemini" | "ollama" | "openrouter"
    api_key: str = ""
    api_base: str = ""
    model_id: str = "gpt-4o"
    temperature: float = 0.2
    max_tokens: int = 2000

@dataclass
class PolymarketConfig:
    gamma_api_url: str = "https://gamma-api.polymarket.com"
    clob_api_url: str = "https://clob.polymarket.com"

@dataclass
class KalshiConfig:
    api_base_url: str = "https://api.elections.kalshi.com/trade-api/v2"
    api_key: str = ""   # Optional, for authenticated endpoints

@dataclass
class RobinhoodAgenticConfig:
    mcp_endpoint: str = "https://agent.robinhood.com/mcp/trading"
    enabled: bool = False  # Per-user manual connection

@dataclass
class AgentSettings:
    enabled: bool = True
    provider: str = "openai"    # Provider name to route queries to
    fallback_providers: List[str] = field(default_factory=list)
    temperature: float = 0.3
    max_sources_to_query: int = 5
    weight: float = 1.0         # Default reliability weight for consensus

@dataclass
class ConsensusConfig:
    min_evidence_score: float = 0.3
    uncertainty_penalty: float = 0.1
    default_agent_weight: float = 1.0
    calibration_alpha: float = 0.05  # Learning rate to adjust agent weight based on historical error

@dataclass
class MemoryConfig:
    store_dir: str = "memory_data"
    max_history_entries: int = 1000
    enable_reputation_updates: bool = True

@dataclass
class ServerConfig:
    host: str = "0.0.0.0"
    port: int = 30000
    api_key: str = ""
    public_feed_monthly_budget_usd: float = 50.0

@dataclass
class ForecastConfig:
    providers: Dict[str, ProviderConfig] = field(default_factory=lambda: {
        "openai": ProviderConfig(provider="openai", model_id="gpt-4o"),
        "anthropic": ProviderConfig(provider="anthropic", model_id="claude-3-5-sonnet-latest"),
        "gemini": ProviderConfig(provider="gemini", model_id="gemini-2.5-flash"),
        "ollama": ProviderConfig(provider="ollama", api_base="http://localhost:11434", model_id="llama3"),
        "openrouter": ProviderConfig(provider="openrouter", model_id="meta-llama/llama-3.1-405b"),
    })
    polymarket: PolymarketConfig = field(default_factory=PolymarketConfig)
    kalshi: KalshiConfig = field(default_factory=KalshiConfig)
    robinhood_agentic: RobinhoodAgenticConfig = field(default_factory=RobinhoodAgenticConfig)
    agents: Dict[str, AgentSettings] = field(default_factory=lambda: {
        "news": AgentSettings(enabled=True, weight=1.2),
        "social": AgentSettings(enabled=True, weight=0.8),
        "reddit": AgentSettings(enabled=True, weight=0.6),
        "research": AgentSettings(enabled=True, weight=1.4),
        "macro": AgentSettings(enabled=True, weight=1.1),
        "onchain": AgentSettings(enabled=True, weight=1.3),
        "market": AgentSettings(enabled=True, weight=1.5),
    })
    consensus: ConsensusConfig = field(default_factory=ConsensusConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    server: ServerConfig = field(default_factory=ServerConfig)
    default_provider: str = "openai"
    fallback_providers: List[str] = field(default_factory=lambda: [
        "gemini"
    ])

