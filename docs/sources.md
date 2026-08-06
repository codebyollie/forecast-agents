# Data Sources

## Always available without paid research keys

- Kalshi public market data.
- Polymarket public Gamma and read-only CLOB data.
- RSS feeds.
- Reddit public endpoints where available.

## Optional keys

- `NEWS_API_KEY`: News API headlines.
- `TWITTER_BEARER_TOKEN`: X/Twitter API results.
- `POLYGONSCAN_API_KEY`: blockchain explorer data.
- `TAVILY_API_KEY` with `TAVILY_ENABLED=true`: live web research.
- `FACTSAI_API_KEY` with `FACTSAI_ENABLED=true`: deep research and citations.
- `OPENAI_API_KEY`: agent reasoning and web-search fallback when supported.

## Provenance

Evidence carries provider and source-type metadata. Citations are canonicalized and deduplicated before being returned.

Social and Reddit agents accept platform-specific URLs for their source cards. Generic news citations are not presented as native Reddit or social posts.
