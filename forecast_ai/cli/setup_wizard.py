"""
Interactive setup wizard for Forecast AI.
"""

import os
import click
from pathlib import Path
from ..config import ForecastConfig, ProviderConfig, PolymarketConfig
from ..config_store import ConfigStore

class SetupWizard:
    def __init__(self, config_store: ConfigStore = None):
        self.cs = config_store or ConfigStore()

    def run(self):
        click.secho("=" * 60, fg="cyan")
        click.secho("🔮 Welcome to the Forecast AI Configuration Wizard 🔮", fg="cyan", bold=True)
        click.secho("Set up your prediction market intelligence infrastructure in minutes.", fg="cyan")
        click.secho("=" * 60, fg="cyan")

        # Load config with env overrides
        cfg = self.cs.load_config()

        # 1. Default LLM Provider Selection
        click.echo("\n--- [1] Default LLM Provider Configuration ---")
        choices = ["openai", "anthropic", "gemini", "ollama", "openrouter"]
        provider = click.prompt(
            "Select default LLM provider",
            type=click.Choice(choices),
            default=cfg.default_provider
        )
        cfg.default_provider = provider

        # Configure selected provider keys
        p_cfg = cfg.providers[provider]
        env_var_name = f"{provider.upper()}_API_KEY"
        env_val = os.environ.get(env_var_name)
        if env_val:
            click.secho(f"ℹ️ {provider.capitalize()} API Key currently set via environment variable ({env_var_name}).", fg="yellow")

        api_key = click.prompt(
            f"Enter API key for {provider} (press enter to skip or keep current)",
            default=p_cfg.api_key if p_cfg.api_key else "",
            show_default=False
        )
        if api_key:
            p_cfg.api_key = api_key

        model_id = click.prompt(
            f"Enter model ID for {provider}",
            default=p_cfg.model_id
        )
        p_cfg.model_id = model_id

        # 2. Kalshi & Robinhood Predict Data Configuration
        click.echo("\n--- [2] Kalshi / Robinhood Predict Integration ---")
        kalshi_url = click.prompt(
            "Kalshi API Base URL",
            default=cfg.kalshi.api_base_url
        )
        cfg.kalshi.api_base_url = kalshi_url

        if os.environ.get("KALSHI_API_KEY"):
            click.secho("ℹ️ Kalshi API Key currently set via environment variable (KALSHI_API_KEY).", fg="yellow")

        kalshi_key = click.prompt(
            "Kalshi API Key (optional for public market data)",
            default=cfg.kalshi.api_key,
            show_default=False
        )
        cfg.kalshi.api_key = kalshi_key

        # 3. Polymarket Read-Only Signal Configuration
        click.echo("\n--- [3] Polymarket Integration (Read-Only Signal) ---")
        gamma_url = click.prompt(
            "Polymarket Gamma API URL",
            default=cfg.polymarket.gamma_api_url
        )
        cfg.polymarket.gamma_api_url = gamma_url

        # 4. Robinhood Agentic Trading MCP Info
        click.echo("\n--- [4] Robinhood Agentic Trading MCP Notice ---")
        click.secho("Execution Layer: Trade recommendations are formatted for hand-off to your personal AI agent.", fg="yellow")
        click.secho("Connect your agent (Claude, ChatGPT, Cursor, etc.) to MCP endpoint: https://agent.robinhood.com/mcp/trading", fg="yellow")

        # 5. Server Configuration
        click.echo("\n--- [5] API Server Configuration ---")
        host = click.prompt("Server Host", default=cfg.server.host)
        port = click.prompt("Server Port", default=cfg.server.port, type=int)
        cfg.server.host = host
        cfg.server.port = port

        # Save config
        self.cs.save_config(cfg)
        
        click.secho("\n" + "=" * 60, fg="green")
        click.secho("🎉 Forecast AI Configuration successfully saved! 🎉", fg="green", bold=True)
        click.secho(f"Config path: {self.cs.config_file}", fg="green")
        click.secho("=" * 60, fg="green")
