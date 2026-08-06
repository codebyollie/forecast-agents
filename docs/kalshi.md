# Kalshi Integration

Forecast AI uses Kalshi's public Trade API for read-only market discovery and analysis.

Default production endpoint:

```text
https://external-api.kalshi.com/trade-api/v2
```

Public market, series, event, and orderbook requests do not require authentication.

## Supported behavior

- active-market discovery;
- keyword search;
- category-to-series discovery;
- current Yes bid/ask midpoint;
- support for cents, `*_dollars`, and `*_fp` response fields;
- multi-leg market exclusion in the default browser;
- live Yes/No orderbook normalization;
- selected-market evidence for the Market agent.

## Configuration

```env
KALSHI_API_BASE_URL=https://external-api.kalshi.com/trade-api/v2
```

Forecast AI does not implement Kalshi private order signing or trade execution.

## Robinhood distinction

Kalshi data represents Kalshi-listed contracts only. Forecast AI does not claim that Kalshi is a complete mirror of the markets displayed by Robinhood Predict.
