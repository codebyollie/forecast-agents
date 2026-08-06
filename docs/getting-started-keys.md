# API Keys and Local Configuration

Forecast AI loads configuration in this order:

1. environment variables supplied by the host;
2. values from a local `.env` file;
3. `~/.forecast_ai/config.yaml`;
4. built-in defaults.

Environment variables take precedence.

## Required

Configure at least one LLM provider, unless you use a local Ollama server:

```env
DEFAULT_PROVIDER=openai
OPENAI_API_KEY=your_key
```

Alternative keys are `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, and `OPENROUTER_API_KEY`.

## Optional research

```env
TAVILY_API_KEY=
TAVILY_ENABLED=false

FACTSAI_API_KEY=
FACTSAI_ENABLED=false
```

A key alone does not enable Tavily or FactsAI. The corresponding enabled flag must be `true`.

## Market data

Kalshi and Polymarket discovery are public and read-only. No trading API keys are required.

## Server protection

```env
SERVER_API_KEY=generate_a_long_random_value
PUBLIC_RATE_LIMIT_PER_HOUR=50
```

When `SERVER_API_KEY` is set, protected endpoints accept either:

- `X-API-Key: ...`
- `Authorization: Bearer ...`

When it is blank, public endpoints use the per-IP rate limit.

`/forecasts`, `/stats`, `/config`, and `/reputation/calibrate` remain
disabled until a server API key is configured.

## Security

- Never commit `.env` or `~/.forecast_ai/config.yaml`.
- Rotate any key that has appeared in a screenshot, log, issue, or commit.
- Use deployment-platform secret variables in production.
- Use a dedicated key with the lowest necessary quota.
