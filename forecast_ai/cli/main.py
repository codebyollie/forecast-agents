"""
Forecast AI CLI commands.
"""

from __future__ import annotations

import asyncio
import click
import json
import sys
from pathlib import Path

from ..config_store import ConfigStore
from ..pipelines.forecast import ForecastPipeline
from ..polymarket.gamma import GammaClient
from ..polymarket.clob import ClobClient
from ..polymarket.markets import PolymarketMarketsManager
from ..launcher import ForecastLauncher

@click.group()
def forecast():
    """Forecast AI — Multi-Agent Intelligence Infrastructure for Prediction Markets."""
    pass

@forecast.command()
def setup():
    """Interactive first-time configuration wizard."""
    from .setup_wizard import SetupWizard
    SetupWizard().run()

@forecast.command()
@click.option("--category", default="crypto", help="Prediction market category to track.")
@click.option("--no-server", is_flag=True, help="Disable launching the API server alongside watch loops.")
def run(category: str, no_server: bool):
    """Start Forecast AI watching loops and API server services."""
    cs = ConfigStore()
    if not cs.exists():
        click.secho("No configuration found. Please run 'forecast setup' first.", fg="yellow")
        sys.exit(1)

    launcher = ForecastLauncher(cs)
    click.echo(f"Starting Forecast AI launcher for category: {category}...")
    try:
        asyncio.run(launcher.start(category=category, run_server=not no_server))
    except KeyboardInterrupt:
        click.echo("\nInterrupted. Stopping services...")
        launcher.stop()

@forecast.command()
@click.argument("query")
@click.option("--market-id", default="custom_market", help="Associated market identifier.")
def predict(query: str, market_id: str):
    """Run a one-shot forecast for a specific query."""
    cs = ConfigStore()
    cfg = cs.load_config()
    pipeline = ForecastPipeline(cfg)
    
    click.echo(f"Analyzing query: '{query}'...")
    
    async def _predict():
        res = await pipeline.run_forecast(query, market_id)
        click.secho("\n=== FORECAST RESULT ===", fg="cyan", bold=True)
        click.secho(f"Probability: {res.probability * 100:.1f}%", fg="green", bold=True)
        click.secho(f"Confidence:  {res.confidence.score * 100:.1f}%", fg="yellow")
        if res.confidence.warnings:
            click.secho(f"Warnings:    {', '.join(res.confidence.warnings)}", fg="red")
        
        click.echo("\nConsensus Trace:")
        for step in res.reasoning_trace.aggregation_steps:
            click.echo(f"  * {step}")

        click.echo("\nSummary Reasoning:")
        click.echo(res.metadata.get("summary_reasoning", "No reasoning summary produced."))

    asyncio.run(_predict())

@forecast.command()
@click.option("--category", default="crypto", help="Market category.")
@click.option("--interval", default=60, help="Interval in seconds between evaluations.")
def watch(category: str, interval: int):
    """Start watching prediction markets directly (no API server)."""
    cs = ConfigStore()
    cfg = cs.load_config()
    pipeline = ForecastPipeline(cfg)
    
    from ..pipelines.watch import WatchPipeline
    watcher = WatchPipeline(cfg, pipeline)
    
    click.echo(f"Watching markets in category: {category} (interval: {interval}s)...")
    try:
        asyncio.run(watcher.watch_markets(category=category, interval_seconds=interval))
    except KeyboardInterrupt:
        click.echo("\nStopping watcher...")
        watcher.stop()

@forecast.command()
@click.argument("slug")
def market(slug: str):
    """Inspect metadata and orderbooks for a Polymarket slug."""
    async def _inspect():
        gamma = GammaClient()
        clob = ClobClient()
        manager = PolymarketMarketsManager(gamma, clob)
        
        click.echo(f"Fetching market info for: {slug}...")
        details = await manager.get_market_details_by_slug(slug)
        if not details:
            click.secho(f"Market slug '{slug}' not found on Polymarket.", fg="red")
            return
            
        m = details["market"]
        click.secho(f"\nQuestion: {m.question}", fg="cyan", bold=True)
        click.echo(f"Volume:   ${m.volume:,.2f}")
        click.echo(f"Liquidity:${m.liquidity:,.2f}")
        click.echo(f"Category: {m.category}")
        click.echo(f"End Date: {m.end_date_iso}")
        
        click.echo("\nOrder Book Summaries:")
        for outcome, book in details["orderbooks"].items():
            click.secho(f"  Outcome: {outcome} (Token: {book.token_id})", bold=True)
            click.echo(f"    Spread: {book.spread:.3f}")
            if book.bids:
                click.echo(f"    Best Bid: {book.bids[0].price:.2f} (Size: {book.bids[0].size:.1f})")
            if book.asks:
                click.echo(f"    Best Ask: {book.asks[0].price:.2f} (Size: {book.asks[0].size:.1f})")

    asyncio.run(_inspect())

@forecast.command()
def sources():
    """List all available data sources."""
    cs = ConfigStore()
    cfg = cs.load_config()
    from ..sources import SourceManager
    mgr = SourceManager(cfg)
    click.secho("\n=== AVAILABLE SOURCES ===", fg="cyan", bold=True)
    for name in mgr.sources.keys():
        click.echo(f"  * {name}")

@forecast.command()
def agents():
    """List all specialized intelligence agents."""
    cs = ConfigStore()
    cfg = cs.load_config()
    click.secho("\n=== ACTIVE AGENTS ===", fg="cyan", bold=True)
    for name, s in cfg.agents.items():
        status = "ENABLED" if s.enabled else "DISABLED"
        fg_color = "green" if s.enabled else "red"
        click.echo(f"  * {name:<10} [")
        click.secho(f"{status}", fg=fg_color, nl=False)
        click.echo(f"]  Weight: {s.weight:.1f}  Provider: {s.provider}")

@forecast.command()
def providers():
    """List configured LLM providers."""
    cs = ConfigStore()
    cfg = cs.load_config()
    click.secho("\n=== CONFIGURED PROVIDERS ===", fg="cyan", bold=True)
    for name, p in cfg.providers.items():
        status = "Configured" if p.api_key or name == "ollama" else "Keys Missing"
        fg_color = "green" if status == "Configured" else "red"
        click.echo(f"  * {name:<12} [")
        click.secho(f"{status}", fg=fg_color, nl=False)
        click.echo(f"]  Model: {p.model_id}")

@forecast.command()
@click.argument("query")
@click.option("--market-id", default="custom_market", help="Associated market identifier.")
def recommend(query: str, market_id: str):
    """Generate a formatted Robinhood Agentic MCP trade recommendation for a query."""
    cs = ConfigStore()
    cfg = cs.load_config()
    pipeline = ForecastPipeline(cfg)
    
    from ..robinhood_agentic import RobinhoodRecommendationEngine
    engine = RobinhoodRecommendationEngine(cfg.robinhood_agentic.mcp_endpoint)
    
    click.echo(f"Analyzing query: '{query}'...")
    
    async def _recommend():
        res = await pipeline.run_forecast(query, market_id)
        rec = engine.generate_recommendation(res)
        click.echo("\n" + rec.to_formatted_prompt())

    asyncio.run(_recommend())

@forecast.command()
def server():
    """Start the API server manually."""
    cs = ConfigStore()
    cfg = cs.load_config()
    pipeline = ForecastPipeline(cfg)
    
    from ..api.server import ApiServer
    srv = ApiServer(cfg, pipeline)
    
    click.echo(f"Starting API Server on {cfg.server.host}:{cfg.server.port}...")
    try:
        asyncio.run(srv.start())
        # Run event loop to keep server alive
        asyncio.run(asyncio.Event().wait())
    except KeyboardInterrupt:
        click.echo("\nStopping API server...")
        srv.stop()

