# 📊 Kalshi & Robinhood Predict Integration

## Overview

Forecast AI integrates with **Kalshi's Public Market Data API** as the primary market-data source reflecting **Robinhood Predict** event contracts. 

### Why Kalshi is the Proxy for Robinhood Predict
Robinhood Predict offers regulated binary prediction market contracts (pricing range $0.01 – $0.99, representing implied outcome probabilities). Robinhood Predict contracts settle through Kalshi's exchange infrastructure (as well as partner exchanges ForecastEX and Rothera). Because Robinhood Predict does not provide an independent, anonymous public market-data REST/WebSocket API, Forecast AI programmatically queries Kalshi's public trade API (`https://api.elections.kalshi.com/trade-api/v2`) to pull real-time prices, orderbooks, and event listings.

## Features

- **Public Event Market Discovery**: Search and list active prediction markets across politics, macroeconomics, finance, and entertainment.
- **Orderbook Depth Analysis**: Retrieve live bid/ask spreads (`yes_bid`, `yes_ask`, `no_bid`, `no_ask`) and calculate midpoint implied probabilities.
- **Uniform Consensus Integration**: Kalshi market data is normalized into standard `Evidence` and `Market` models consumable by Forecast AI's Market Agent and Consensus Engine.

## Configuration

In `~/.forecast_ai/config.yaml`:

```yaml
kalshi:
  api_base_url: "https://api.elections.kalshi.com/trade-api/v2"
  api_key: "" # Optional for public market-data endpoints
```

## Python API Example

```python
import asyncio
from forecast_ai.kalshi import KalshiClient

async def main():
    client = KalshiClient()
    markets = await client.fetch_markets(limit=5)
    for m in markets:
        print(f"Market: {m.title} [{m.ticker}] - Implied Prob: {m.midpoint_price:.1%}")

asyncio.run(main())
```
