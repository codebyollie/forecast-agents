"""
Configuration Store for Forecast AI.

Reads and writes configuration options to/from ~/.forecast_ai/config.yaml
and bridges to the ForecastConfig class.
"""

from __future__ import annotations

import os
import yaml
from pathlib import Path
from typing import Any, Dict

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
    """Read/write ForecastConfig to/from yaml."""

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
            config.kalshi.api_key = k.get("api_key", config.kalshi.api_key)

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

        config.default_provider = raw.get("default_provider", config.default_provider)

        return config

    def save_config(self, config: ForecastConfig):
        # Convert to dictionary representation for yaml serialization
        data = {
            "default_provider": config.default_provider,
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
                "api_key": config.kalshi.api_key,
            },
            "robinhood_agentic": {
                "mcp_endpoint": config.robinhood_agentic.mcp_endpoint,
                "enabled": config.robinhood_agentic.enabled,
            },
            "agents": {
                name: {
                    "enabled": a.enabled,
                    "provider": a.provider,
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
