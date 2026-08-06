# Architecture

Forecast AI is a self-hosted Python backend and CLI.

```text
Kalshi / Polymarket / News / RSS / Social / Research
                         |
                    SourceManager
                         |
          Seven independent forecast agents
                         |
                  Consensus Engine
                         |
           Memory + REST API + CLI output
```

## Modules

- `forecast_ai/kalshi/`: public Kalshi market and orderbook client.
- `forecast_ai/polymarket/`: public Gamma and read-only CLOB clients.
- `forecast_ai/sources/`: news, social, research, blockchain, and market adapters.
- `forecast_ai/agents/`: the seven specialized agents.
- `forecast_ai/providers/`: LLM provider adapters and fallback routing.
- `forecast_ai/consensus/`: weighted aggregation and confidence calculation.
- `forecast_ai/memory/`: local forecast history and reputation state.
- `forecast_ai/pipelines/`: one-shot forecasts and continuous watching.
- `forecast_ai/api/`: FastAPI application.
- `forecast_ai/cli/`: setup, diagnostics, forecasting, and server commands.
- `forecast_ai/robinhood_agentic/`: recommendation formatting only.

## Forecast flow

1. Resolve the selected market and venue.
2. Gather exact market data plus configured external evidence.
3. Give each agent only relevant evidence.
4. Run agents concurrently.
5. Deduplicate and label citations.
6. Aggregate predictions using confidence and reputation weights.
7. Save the result under `MEMORY_STORE_DIR`.
8. Return a structured API response.

The open-source backend has no dependency on the hosted Forecast AI website, Supabase, Privy, token-holder tiers, or production user accounts.
