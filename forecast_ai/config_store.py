"""
Configuration Store for Forecast AI.

Reads and writes configuration options to/from ~/.forecast_ai/config.yaml
and bridges to the ForecastConfig class with Environment Variable override support.
"""

from __future__ import annotations

import os
import yaml
from dotenv import load_dotenv
from pathlib import Path
from typing import Any, Dict, List

from .config import (
    ForecastConfig,
    ProviderConfig,
    PolymarketConfig,
    KalshiConfig,
    RobinhoodAgenticConfig,
    AgentSettings,
    ConsensusConfig,
    MemoryConfig,
    ServerConfig
)

CONFIG_DIR = Path.home() / ".forecast_ai"
CONFIG_FILE = CONFIG_DIR / "config.yaml"

# Local self-hosted installs commonly use a .env file. Platform-provided
# environment variables keep precedence because override=False is the default.
load_dotenv()

def _coerce(value: Any) -> Any:
    """Coerce string representations into native types."""
    if not isinstance(value, str):
        return value
    val_lower = value.lower()
    if val_lower == "true":
        return True
    if val_lower == "false":
        return False
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    return value

class ConfigStore:
    """Read/write ForecastConfig to/from yaml with environment variable overrides."""

    def __init__(self, config_file: Path = CONFIG_FILE):
        self.config_file = config_file

    def exists(self) -> bool:
        return self.config_file.exists()

    def load_raw(self) -> dict:
        if not self.config_file.exists():
            return {}
        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception:
            return {}

    def save_raw(self, data: dict):
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
        except Exception as e:
            raise RuntimeError(f"Failed to write config file: {e}")

    def apply_env_overrides(self, config: ForecastConfig) -> ForecastConfig:
        """
        Apply environment variable overrides to ForecastConfig.
        Environment variables take precedence over config.yaml file settings.
        """
        # Provider API Key & Base URL overrides
        if os.environ.get("OPENAI_API_KEY"):
            config.providers["openai"].api_key = os.environ["OPENAI_API_KEY"]
        if os.environ.get("GEMINI_API_KEY"):
            config.providers["gemini"].api_key = os.environ["GEMINI_API_KEY"]
        if os.environ.get("ANTHROPIC_API_KEY"):
            config.providers["anthropic"].api_key = os.environ["ANTHROPIC_API_KEY"]
        if os.environ.get("OPENROUTER_API_KEY"):
            config.providers["openrouter"].api_key = os.environ["OPENROUTER_API_KEY"]
        if os.environ.get("OLLAMA_API_BASE"):
            config.providers["ollama"].api_base = os.environ["OLLAMA_API_BASE"]

        # Kalshi overrides
        if os.environ.get("KALSHI_API_BASE_URL"):
            config.kalshi.api_base_url = os.environ["KALSHI_API_BASE_URL"]

        # Polymarket overrides
        if os.environ.get("POLYMARKET_GAMMA_API_URL"):
            config.polymarket.gamma_api_url = os.environ["POLYMARKET_GAMMA_API_URL"]
        if os.environ.get("POLYMARKET_CLOB_API_URL"):
            config.polymarket.clob_api_url = os.environ["POLYMARKET_CLOB_API_URL"]

        # Robinhood Agentic overrides
        if os.environ.get("ROBINHOOD_MCP_ENDPOINT"):
            config.robinhood_agentic.mcp_endpoint = os.environ["ROBINHOOD_MCP_ENDPOINT"]

        # Server overrides
        if os.environ.get("SERVER_HOST"):
            config.server.host = os.environ["SERVER_HOST"]
        if os.environ.get("PORT"):
            try:
                config.server.port = int(os.environ["PORT"])
            except ValueError:
                pass
        if os.environ.get("SERVER_PORT"):
            try:
                config.server.port = int(os.environ["SERVER_PORT"])
            except ValueError:
                pass
        if os.environ.get("SERVER_API_KEY"):
            config.server.api_key = os.environ["SERVER_API_KEY"]
        if os.environ.get("MEMORY_STORE_DIR"):
            config.memory.store_dir = os.environ["MEMORY_STORE_DIR"]
        if os.environ.get("LLM_SPEND_GUARD_ENABLED"):
            config.server.spend_guard_enabled = os.environ["LLM_SPEND_GUARD_ENABLED"].lower() in ("true", "1", "yes")
        if os.environ.get("DAILY_LLM_BUDGET_USD"):
            try:
                config.server.daily_llm_budget_usd = float(os.environ["DAILY_LLM_BUDGET_USD"])
            except ValueError:
                pass
        if os.environ.get("MONTHLY_LLM_BUDGET_USD"):
            try:
                config.server.monthly_llm_budget_usd = float(os.environ["MONTHLY_LLM_BUDGET_USD"])
            except ValueError:
                pass

        # Default provider override
        if os.environ.get("DEFAULT_PROVIDER"):
            config.default_provider = os.environ["DEFAULT_PROVIDER"]

        # FactsAI Deep Research overrides
        if os.environ.get("FACTSAI_API_KEY"):
            config.facts_ai.api_key = os.environ["FACTSAI_API_KEY"]
        if os.environ.get("FACTSAI_ENABLED"):
            config.facts_ai.enabled = os.environ["FACTSAI_ENABLED"].lower() in ("true", "1", "yes")
        if os.environ.get("FACTSAI_API_URL"):
            config.facts_ai.api_url = os.environ["FACTSAI_API_URL"]

        # Tavily overrides
        if os.environ.get("TAVILY_API_KEY"):
            config.tavily.api_key = os.environ["TAVILY_API_KEY"]
        if os.environ.get("TAVILY_ENABLED"):
            config.tavily.enabled = os.environ["TAVILY_ENABLED"].lower() in ("true", "1", "yes")

        return config

    def load_config(self) -> ForecastConfig:
        raw = self.load_raw()
        config = ForecastConfig()

        # Load Providers
        if "providers" in raw:
            for name, p_data in raw["providers"].items():
                if name in config.providers:
                    prov = config.providers[name]
                    prov.provider = p_data.get("provider", prov.provider)
                    prov.api_key = p_data.get("api_key", prov.api_key)
                    prov.api_base = p_data.get("api_base", prov.api_base)
                    prov.model_id = p_data.get("model_id", prov.model_id)
                    prov.temperature = float(p_data.get("temperature", prov.temperature))
                    prov.max_tokens = int(p_data.get("max_tokens", prov.max_tokens))

        # Load Polymarket
        if "polymarket" in raw:
            pm = raw["polymarket"]
            config.polymarket.gamma_api_url = pm.get("gamma_api_url", config.polymarket.gamma_api_url)
            config.polymarket.clob_api_url = pm.get("clob_api_url", config.polymarket.clob_api_url)

        # Load Kalshi
        if "kalshi" in raw:
            k = raw["kalshi"]
            config.kalshi.api_base_url = k.get("api_base_url", config.kalshi.api_base_url)

        # Load Robinhood Agentic
        if "robinhood_agentic" in raw:
            ra = raw["robinhood_agentic"]
            config.robinhood_agentic.mcp_endpoint = ra.get("mcp_endpoint", config.robinhood_agentic.mcp_endpoint)
            config.robinhood_agentic.enabled = bool(ra.get("enabled", config.robinhood_agentic.enabled))

        # Load Agents
        if "agents" in raw:
            for name, a_data in raw["agents"].items():
                if name in config.agents:
                    agent = config.agents[name]
                    agent.enabled = bool(a_data.get("enabled", agent.enabled))
                    agent.provider = a_data.get("provider", agent.provider)
                    if "fallback_providers" in a_data and isinstance(a_data["fallback_providers"], list):
                        agent.fallback_providers = a_data["fallback_providers"]
                    agent.temperature = float(a_data.get("temperature", agent.temperature))
                    agent.max_sources_to_query = int(a_data.get("max_sources_to_query", agent.max_sources_to_query))
                    agent.weight = float(a_data.get("weight", agent.weight))

        # Load Consensus
        if "consensus" in raw:
            con = raw["consensus"]
            config.consensus.min_evidence_score = float(con.get("min_evidence_score", config.consensus.min_evidence_score))
            config.consensus.uncertainty_penalty = float(con.get("uncertainty_penalty", config.consensus.uncertainty_penalty))
            config.consensus.default_agent_weight = float(con.get("default_agent_weight", config.consensus.default_agent_weight))
            config.consensus.calibration_alpha = float(con.get("calibration_alpha", config.consensus.calibration_alpha))

        # Load Memory
        if "memory" in raw:
            mem = raw["memory"]
            config.memory.store_dir = mem.get("store_dir", config.memory.store_dir)
            config.memory.max_history_entries = int(mem.get("max_history_entries", config.memory.max_history_entries))
            config.memory.enable_reputation_updates = bool(mem.get("enable_reputation_updates", config.memory.enable_reputation_updates))

        # Load Server
        if "server" in raw:
            srv = raw["server"]
            config.server.host = srv.get("host", config.server.host)
            config.server.port = int(srv.get("port", config.server.port))
            config.server.api_key = srv.get("api_key", config.server.api_key)
            config.server.spend_guard_enabled = bool(srv.get("spend_guard_enabled", config.server.spend_guard_enabled))
            config.server.daily_llm_budget_usd = float(srv.get("daily_llm_budget_usd", config.server.daily_llm_budget_usd))
            config.server.monthly_llm_budget_usd = float(srv.get("monthly_llm_budget_usd", config.server.monthly_llm_budget_usd))

        # Load FactsAI
        if "facts_ai" in raw:
            facts = raw["facts_ai"]
            config.facts_ai.enabled = bool(facts.get("enabled", config.facts_ai.enabled))
            config.facts_ai.api_key = facts.get("api_key", config.facts_ai.api_key)
            config.facts_ai.api_url = facts.get("api_url", config.facts_ai.api_url)

        # Load Tavily
        if "tavily" in raw:
            t = raw["tavily"]
            config.tavily.enabled = bool(t.get("enabled", config.tavily.enabled))
            config.tavily.api_key = t.get("api_key", config.tavily.api_key)

        config.default_provider = raw.get("default_provider", config.default_provider)
        if "fallback_providers" in raw and isinstance(raw["fallback_providers"], list):
            config.fallback_providers = raw["fallback_providers"]

        # Apply environment variable overrides (takes precedence over config.yaml)
        config = self.apply_env_overrides(config)

        return config

    def save_config(self, config: ForecastConfig):
        data = {
            "default_provider": config.default_provider,
            "fallback_providers": config.fallback_providers,
            "providers": {
                name: {
                    "provider": p.provider,
                    "api_key": p.api_key,
                    "api_base": p.api_base,
                    "model_id": p.model_id,
                    "temperature": p.temperature,
                    "max_tokens": p.max_tokens,
                } for name, p in config.providers.items()
            },
            "polymarket": {
                "gamma_api_url": config.polymarket.gamma_api_url,
                "clob_api_url": config.polymarket.clob_api_url,
            },
            "kalshi": {
                "api_base_url": config.kalshi.api_base_url,
            },
            "robinhood_agentic": {
                "mcp_endpoint": config.robinhood_agentic.mcp_endpoint,
                "enabled": config.robinhood_agentic.enabled,
            },
            "agents": {
                name: {
                    "enabled": a.enabled,
                    "provider": a.provider,
                    "fallback_providers": a.fallback_providers,
                    "temperature": a.temperature,
                    "max_sources_to_query": a.max_sources_to_query,
                    "weight": a.weight,
                } for name, a in config.agents.items()
            },
            "consensus": {
                "min_evidence_score": config.consensus.min_evidence_score,
                "uncertainty_penalty": config.consensus.uncertainty_penalty,
                "default_agent_weight": config.consensus.default_agent_weight,
                "calibration_alpha": config.consensus.calibration_alpha,
            },
            "memory": {
                "store_dir": config.memory.store_dir,
                "max_history_entries": config.memory.max_history_entries,
                "enable_reputation_updates": config.memory.enable_reputation_updates,
            },
            "server": {
                "host": config.server.host,
                "port": config.server.port,
                "api_key": config.server.api_key,
                "spend_guard_enabled": config.server.spend_guard_enabled,
                "daily_llm_budget_usd": config.server.daily_llm_budget_usd,
                "monthly_llm_budget_usd": config.server.monthly_llm_budget_usd,
            },
            "facts_ai": {
                "enabled": config.facts_ai.enabled,
                "api_key": config.facts_ai.api_key,
                "api_url": config.facts_ai.api_url,
            },
            "tavily": {
                "enabled": config.tavily.enabled,
                "api_key": config.tavily.api_key,
            }
        }
        self.save_raw(data)

    def set_val(self, dotpath: str, value: Any):
        raw = self.load_raw()
        parts = dotpath.split(".")
        d = raw
        for p in parts[:-1]:
            d = d.setdefault(p, {})
        d[parts[-1]] = _coerce(value)
        self.save_raw(raw)

    def get_val(self, dotpath: str) -> Any:
        raw = self.load_raw()
        parts = dotpath.split(".")
        d = raw
        for p in parts:
            if not isinstance(d, dict):
                return None
            d = d.get(p)
        return d
