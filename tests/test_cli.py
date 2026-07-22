"""
Tests for Forecast AI CLI commands.
"""

from click.testing import CliRunner
from forecast_ai.cli.main import forecast

def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(forecast, ["--help"])
    assert result.exit_code == 0
    assert "Multi-Agent Intelligence Infrastructure" in result.output

def test_cli_sources():
    runner = CliRunner()
    result = runner.invoke(forecast, ["sources"])
    assert result.exit_code == 0
    assert "AVAILABLE SOURCES" in result.output
    assert "news" in result.output
    assert "reddit" in result.output

def test_cli_agents():
    runner = CliRunner()
    result = runner.invoke(forecast, ["agents"])
    assert result.exit_code == 0
    assert "ACTIVE AGENTS" in result.output
    assert "news" in result.output
    assert "market" in result.output

def test_cli_providers():
    runner = CliRunner()
    result = runner.invoke(forecast, ["providers"])
    assert result.exit_code == 0
    assert "CONFIGURED PROVIDERS" in result.output
    assert "openai" in result.output
    assert "ollama" in result.output
