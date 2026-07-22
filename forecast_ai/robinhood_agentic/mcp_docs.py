"""
Robinhood Agentic Trading MCP Connection Guidance.
"""

ROBINHOOD_MCP_ENDPOINT = "https://agent.robinhood.com/mcp/trading"

MCP_SETUP_GUIDE = """
# Robinhood Agentic Trading MCP Integration Guide

Forecast AI generates explainable multi-agent consensus probability forecasts.
To execute trades based on Forecast AI recommendations in your own Robinhood account:

1. Connect your AI client (Claude Code, Claude Desktop, ChatGPT, Cursor, Grok, etc.) to the official Robinhood Agentic Trading MCP server:
   - Endpoint: https://agent.robinhood.com/mcp/trading
2. Authenticate your personal Robinhood Agentic account via OAuth/MCP prompt.
3. Pass Forecast AI's structured recommendation output to your MCP-connected agent.

Note: Forecast AI backend never stores or accesses your Robinhood credentials or private keys.
Execution is strictly managed by your personal MCP agent session.
"""

def get_mcp_info() -> dict:
    return {
        "mcp_endpoint": ROBINHOOD_MCP_ENDPOINT,
        "description": "Official Robinhood Agentic Trading MCP Server",
        "supported_clients": ["Claude Code", "Claude Desktop", "ChatGPT", "Cursor", "Codex", "Grok"],
        "setup_guide": MCP_SETUP_GUIDE
    }
