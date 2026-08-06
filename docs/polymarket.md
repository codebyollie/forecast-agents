# Polymarket Integration

Forecast AI uses Polymarket as a read-only market-data source.

## APIs

- Gamma API for events, markets, metadata, tags, search, volume, and liquidity.
- CLOB API for orderbooks, midpoint, spread, and last-trade price.
- Optional WebSocket support for public orderbook updates.

Defaults:

```env
POLYMARKET_GAMMA_API_URL=https://gamma-api.polymarket.com
POLYMARKET_CLOB_API_URL=https://clob.polymarket.com
```

## Supported behavior

- active-market browsing;
- public search;
- category discovery using Polymarket tags;
- event grouping and multi-outcome display;
- selected-event evidence and live orderbook context;
- retries for temporary HTTP failures.

No wallet, private key, signature, or Polymarket order execution is used.
