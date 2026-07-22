# Polymarket Integration (Read-Only Signal)

Forecast AI includes Polymarket integration as a read-only data source for multi-venue prediction market consensus.

## Features

* **Gamma Client**: Queries public market metadata, resolution sources, and event listings (`/markets`, `/events`).
* **CLOB Client (Read-Only)**: Fetches orderbooks (`/book`), midpoint prices (`/prices/midpoint`), last trade prices, and spreads without requiring wallet signature credentials.
* **WebSocket**: Maintains real-time feeds for public orderbook updates.

Order execution occurs via user-connected Robinhood Agentic Trading MCP sessions rather than server-side wallet signers.
