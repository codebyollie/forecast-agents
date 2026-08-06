"""Interactive setup wizard for Forecast AI."""

import os

import click

from ..config_store import ConfigStore


class SetupWizard:
    def __init__(self, config_store: ConfigStore = None):
        self.cs = config_store or ConfigStore()

    def run(self):
        click.secho("=" * 60, fg="cyan")
        click.secho("Forecast AI self-hosted configuration", fg="cyan", bold=True)
        click.secho("=" * 60, fg="cyan")

        cfg = self.cs.load_config()

        click.echo("\n--- [1] LLM Provider ---")
        choices = ["openai", "anthropic", "gemini", "ollama", "openrouter"]
        provider = click.prompt(
            "Select default LLM provider",
            type=click.Choice(choices),
            default=cfg.default_provider,
        )
        cfg.default_provider = provider

        p_cfg = cfg.providers[provider]
        env_var_name = f"{provider.upper()}_API_KEY"
        if os.environ.get(env_var_name):
            click.secho(
                f"{provider.capitalize()} key is already set through {env_var_name}.",
                fg="yellow",
            )
        elif provider != "ollama":
            api_key = click.prompt(
                f"Enter API key for {provider}",
                default=p_cfg.api_key,
                show_default=False,
            )
            if api_key:
                p_cfg.api_key = api_key

        p_cfg.model_id = click.prompt(
            f"Model ID for {provider}",
            default=p_cfg.model_id,
        )

        click.echo("\n--- [2] Kalshi Public Market Data ---")
        cfg.kalshi.api_base_url = click.prompt(
            "Kalshi API base URL",
            default=cfg.kalshi.api_base_url,
        )
        click.echo("Kalshi public market discovery does not require an API key.")

        click.echo("\n--- [3] Polymarket Read-Only Data ---")
        cfg.polymarket.gamma_api_url = click.prompt(
            "Polymarket Gamma API URL",
            default=cfg.polymarket.gamma_api_url,
        )
        cfg.polymarket.clob_api_url = click.prompt(
            "Polymarket CLOB API URL",
            default=cfg.polymarket.clob_api_url,
        )

        click.echo("\n--- [4] Optional Research Providers ---")
        cfg.tavily.enabled = click.confirm(
            "Enable Tavily web research?",
            default=cfg.tavily.enabled,
        )
        if cfg.tavily.enabled and not os.environ.get("TAVILY_API_KEY"):
            cfg.tavily.api_key = click.prompt(
                "Tavily API key",
                default=cfg.tavily.api_key,
                show_default=False,
            )

        cfg.facts_ai.enabled = click.confirm(
            "Enable FactsAI deep research?",
            default=cfg.facts_ai.enabled,
        )
        if cfg.facts_ai.enabled and not os.environ.get("FACTSAI_API_KEY"):
            cfg.facts_ai.api_key = click.prompt(
                "FactsAI API key",
                default=cfg.facts_ai.api_key,
                show_default=False,
            )

        click.echo("\n--- [5] Robinhood Agentic Trading MCP ---")
        click.echo(
            "Forecast AI only formats a recommendation for hand-off to the user's "
            "personal AI agent."
        )
        click.echo("MCP endpoint: https://agent.robinhood.com/mcp/trading")
        click.echo(
            "Forecast AI does not authenticate Robinhood accounts or execute trades itself."
        )

        click.echo("\n--- [6] API Server ---")
        cfg.server.host = click.prompt("Server host", default=cfg.server.host)
        cfg.server.port = click.prompt(
            "Server port",
            default=cfg.server.port,
            type=int,
        )
        cfg.server.api_key = click.prompt(
            "Server API key (recommended for public deployments; blank leaves rate limiting enabled)",
            default=cfg.server.api_key,
            show_default=False,
        )

        self.cs.save_config(cfg)

        click.secho("\nConfiguration saved.", fg="green", bold=True)
        click.secho(f"Config path: {self.cs.config_file}", fg="green")
