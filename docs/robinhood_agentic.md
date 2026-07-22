# 🤖 Robinhood Agentic Trading MCP Integration

## Architecture & Security Boundary

Forecast AI serves as an **open-source reasoning and consensus forecasting layer**. It does **not** store private user credentials, session tokens, or trade execution keys server-side.

Execution of trades based on Forecast AI consensus probabilities is managed using the official **Robinhood Agentic Trading MCP** protocol.

### MCP Endpoint
`https://agent.robinhood.com/mcp/trading`

## How It Works

1. **Forecast & Consensus Generation**: Forecast AI orchestrates multi-agent intelligence (News, Social, Reddit, Research, Macro, On-chain, and Market Agents) to produce calibrated event probability estimates and confidence scores.
2. **Structured Recommendation Formatting**: The `RobinhoodRecommendationEngine` formats the forecast into a `RobinhoodTradeRecommendation` containing target contracts, action (`BUY_YES`, `BUY_NO`, `HOLD`), recommended allocation percentage, and rationale.
3. **User Agent Hand-off**: The user presents the recommendation to their personal, authenticated AI client (Claude Code, Claude Desktop, ChatGPT, Cursor, Grok, etc.) connected to the Robinhood Agentic Trading MCP server.
4. **Account-Scoped Execution**: The trade is executed inside the user's personal Robinhood Agentic account under their explicit control.

## CLI Usage

Generate an executable recommendation directly from the command line:

```bash
forecast recommend "Will the Fed lower interest rates in the next FOMC meeting?"
```
