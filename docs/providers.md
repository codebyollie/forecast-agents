# LLM Providers

Forecast AI supports OpenAI, Anthropic, Gemini, OpenRouter, and local Ollama.

Provider credentials and model IDs are user-controlled. Defaults may become outdated, so deployments should set the model ID they intend to use through `forecast setup` or `~/.forecast_ai/config.yaml`.

## Fallbacks

Each agent has a primary provider and can use configured fallback providers when the primary provider fails.

Fallbacks are deduplicated and only initialized providers are attempted. A complete provider-chain failure is returned as an error; Forecast AI does not fabricate an agent response.

## Optional spend guard

The spend guard is disabled by default. When enabled, it tracks estimated per-call cost in the memory directory and stops new calls after configured daily or monthly limits.

It does not read actual billing data and should be treated only as a safety circuit breaker.
