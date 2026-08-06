# Forecast AI

Self-hosted, bring-your-own-keys multi-agent intelligence for prediction markets.

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template/new?template=https://github.com/codebyollie/forecast-agents)

Forecast AI collects live evidence, asks seven specialized agents for independent probability estimates, and combines them into an explainable consensus forecast.

This repository contains the open-source backend, CLI, REST API, tests, and self-hosting configuration. It does not contain the hosted Forecast AI website, user accounts, token-holder tiers, quotas, or private production infrastructure.

## What it includes

- Live read-only market discovery for Kalshi and Polymarket.
- Search, venue filters, category filters, live prices, outcomes, and orderbook context.
- Seven agents: News, Social, Reddit, Research, Macro, On-chain, and Market.
- Optional Tavily and FactsAI research with visible provider attribution and graceful fallbacks.
- Structured agent output: summary, key drivers, counter-signals, uncertainties, watch items, citations, and provider status.
- Confidence-weighted consensus, local history, and agent reputation memory.
- OpenAI, Anthropic, Gemini, OpenRouter, and local Ollama support.
- Optional recommendation formatting for hand-off to a user-controlled Robinhood Agentic Trading MCP session.

## Agent data sources

| Agent | Primary evidence |
| --- | --- |
| News | News API, RSS, FactsAI or web-search fallback |
| Social | X/Twitter when configured; domain-filtered Tavily/web results |
| Reddit | Reddit public data; Reddit-filtered Tavily/web results |
| Research | FactsAI, Tavily, and cited web research |
| Macro | Macro/news evidence plus FactsAI or web-search fallback |
| On-chain | Configured blockchain explorer data |
| Market | The selected Kalshi or Polymarket market, prices, outcomes, and orderbook |

Disabled or unconfigured paid sources are skipped. FactsAI and Tavily are off by default.

## Quick start

Requirements: Python 3.10 or newer and Git.

```bash
git clone https://github.com/codebyollie/forecast-agents.git
cd forecast-agents
python -m venv .venv
```

Activate the environment:

```bash
# macOS / Linux
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1
```

Install Forecast AI:

```bash
python -m pip install --upgrade pip
python -m pip install -e .
```

Create your local configuration:

```bash
# macOS / Linux
cp .env.example .env

# Windows PowerShell
Copy-Item .env.example .env
```

Open `.env` and add at least one LLM provider key, or configure a local Ollama server. Do not commit `.env`.

You can also use the interactive wizard:

```bash
forecast setup
```

Validate free public market connections without calling paid research or LLM APIs:

```bash
forecast doctor
```

Run only the API server:

```bash
forecast server
```

The default local URLs are:

- API: `http://localhost:30000`
- OpenAPI UI: `http://localhost:30000/docs`
- Health check: `http://localhost:30000/healthz`

Run a one-shot forecast:

```bash
forecast predict "Will the Federal Reserve cut rates before the end of the year?"
```

`forecast run` starts both the API server and the continuous market-watching loop. The loop can make recurring LLM calls, so review your provider costs before using it.

## Environment variables

See [`.env.example`](.env.example) for the complete template.

The important variables are:

| Variable | Required | Purpose |
| --- | --- | --- |
| `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, or `OPENROUTER_API_KEY` | One provider, unless using Ollama | Agent reasoning |
| `TAVILY_API_KEY` + `TAVILY_ENABLED=true` | No | Live web research |
| `FACTSAI_API_KEY` + `FACTSAI_ENABLED=true` | No | Deep research and citations |
| `SERVER_API_KEY` | Recommended for public deployments | Protects API endpoints using `X-API-Key` or Bearer auth |
| `CORS_ALLOW_ORIGINS` | No | Comma-separated browser origins; defaults to `*` |
| `MEMORY_STORE_DIR` | No | Persistent forecast and reputation storage |
| `PUBLIC_RATE_LIMIT_PER_HOUR` | No | Per-IP limit when no server API key is configured |

Kalshi and Polymarket market discovery use public read-only endpoints and do not require trading credentials.

When `SERVER_API_KEY` is blank, market and prediction endpoints use the
per-IP rate limit. History, statistics, configuration, and
reputation-calibration endpoints stay disabled until a server key is set.
Client-supplied model overrides also require authenticated access so public
callers cannot select a more expensive model on the operator's account.

## REST API examples

Browse markets:

```bash
curl "http://localhost:30000/markets/browse?venue=all&category=Politics&page_size=10"
```

Search markets:

```bash
curl "http://localhost:30000/markets/search?q=bitcoin&limit=10"
```

Analyze a selected market:

```bash
curl -X POST "http://localhost:30000/predict" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_SERVER_API_KEY" \
  -d '{
    "question": "Will Bitcoin trade above the selected strike at expiry?",
    "market_id": "MARKET_ID_OR_SLUG",
    "venue": "kalshi"
  }'
```

The response includes the consensus probability, confidence, recommendation, market context, reasoning trace, and a structured breakdown for every agent.

## Docker

```bash
docker build -t forecast-ai .
docker run --rm -p 30000:30000 --env-file .env forecast-ai
```

For persistent memory:

```bash
docker run --rm -p 30000:30000 \
  --env-file .env \
  -e MEMORY_STORE_DIR=/data/memory \
  -v forecast-ai-data:/data \
  forecast-ai
```

## Railway and Render

The repository includes `Dockerfile`, `railway.json`, `render.yaml`, `Procfile`, and a dynamic-port `start.sh`.

For Railway:

1. Create a service from this GitHub repository.
2. Add at least one LLM provider key.
3. Set `SERVER_API_KEY` when exposing the API publicly.
4. Optionally attach a volume at `/data` and set `MEMORY_STORE_DIR=/data/memory`.
5. Deploy and verify `/healthz`.

See [Deployment](docs/deployment.md) for more detail.

## FactsAI, Tavily, and costs

Forecast AI never requires FactsAI or Tavily. They are optional and disabled by default.

The optional spend guard uses estimated cost per call, not provider billing data. Enable it only if you want a local circuit breaker:

```env
LLM_SPEND_GUARD_ENABLED=true
DAILY_LLM_BUDGET_USD=10
MONTHLY_LLM_BUDGET_USD=50
```

## Robinhood scope

Forecast AI can format a forecast as a recommendation for hand-off to a user's separately authenticated Robinhood Trading MCP connection.

This project does not:

- collect Robinhood credentials;
- connect Robinhood accounts inside this backend;
- claim that Kalshi is a complete mirror of Robinhood Predict;
- guarantee that Robinhood MCP supports prediction-market contracts;
- execute trades automatically.

Review Robinhood's current documentation and disclosures before using an AI agent for trading.

## Development

Install development dependencies and run tests:

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
```

Paid APIs are mocked in the test suite. Live public market checks are opt-in through `forecast doctor`.

## Documentation

- [Architecture](docs/architecture.md)
- [Agents](docs/agents.md)
- [Providers](docs/providers.md)
- [Sources](docs/sources.md)
- [Kalshi](docs/kalshi.md)
- [Polymarket](docs/polymarket.md)
- [FactsAI](docs/facts_ai.md)
- [Robinhood Agentic hand-off](docs/robinhood_agentic.md)
- [Memory](docs/memory.md)
- [Consensus](docs/consensus.md)

## License

Forecast AI is distributed under the MIT License. See [LICENSE](LICENSE).
