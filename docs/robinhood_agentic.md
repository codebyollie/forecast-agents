# Robinhood Agentic Trading MCP Hand-off

Forecast AI includes a recommendation formatter for user-controlled hand-off to Robinhood's Trading MCP.

MCP endpoint:

```text
https://agent.robinhood.com/mcp/trading
```

## Boundary

Forecast AI can:

1. create a consensus forecast;
2. format an action-oriented recommendation;
3. print that recommendation through `forecast recommend`.

Forecast AI does not:

- request or store Robinhood credentials;
- authenticate a Robinhood account;
- embed a Robinhood login flow;
- call MCP tools from this backend;
- guarantee support for prediction-market contracts;
- execute a trade.

The user separately connects a supported AI client to Robinhood, reviews Robinhood's disclosures, authenticates directly with Robinhood, and controls any resulting action.

## CLI

```bash
forecast recommend "Will the Federal Reserve cut rates at the next meeting?"
```

Always verify current Robinhood documentation, product availability, account eligibility, and supported asset types.
