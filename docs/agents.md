# Specialized Agents

Forecast AI runs seven agents independently and then combines their probability estimates.

| Agent | Focus | Typical sources |
| --- | --- | --- |
| News | Current reporting and official announcements | News API, RSS, FactsAI or web fallback |
| Social | Fast-moving public sentiment | X/Twitter, domain-filtered Tavily/web results |
| Reddit | Community arguments and emerging narratives | Reddit public data, Reddit-filtered Tavily/web results |
| Research | Deep factual background | FactsAI, Tavily, cited web research |
| Macro | Monetary policy and economic conditions | News, RSS, FactsAI or web fallback |
| On-chain | Blockchain activity | Configured blockchain explorer data |
| Market | Implied probability and liquidity | Selected Kalshi or Polymarket market and orderbook |

Each agent returns structured fields:

- probability and confidence;
- short summary;
- key drivers;
- counter-signals;
- uncertainties;
- what to watch next;
- citations with provider attribution;
- research-provider status.

An unavailable optional source does not stop the forecast. The agent continues with available evidence and records the provider as unavailable or as a fallback.
