# FactsAI Integration

FactsAI is an optional deep-research provider for the News, Research, and Macro agents.

It is disabled by default so a self-hosted installation cannot spend FactsAI credits accidentally.

## Enable

```env
FACTSAI_API_KEY=your_key
FACTSAI_ENABLED=true
```

The backend sends the market question to the configured `FACTSAI_API_URL`. API credentials are read only from local configuration or server environment variables; callers cannot submit a FactsAI key through the prediction API.

## Output

When FactsAI succeeds, the agent response includes:

- `providers: ["FactsAI"]`;
- a provider insight when an answer is returned;
- deduplicated citations labelled `FactsAI`;
- provider status `active`.

When it fails or returns no evidence, the status is visible and the agent falls back to configured web research or existing evidence.

## Cost control

Pricing and limits can change. Check FactsAI's current documentation before enabling it.

Forecast AI's optional spend guard is an estimated local circuit breaker and is not a replacement for provider billing limits.
