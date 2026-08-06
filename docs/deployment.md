# Deployment

Forecast AI is designed to run as a stateless API container with an optional persistent memory volume.

## Required variables

Set at least one LLM provider key, unless you use Ollama:

```env
OPENAI_API_KEY=
SERVER_API_KEY=
```

Copy the rest from [`.env.example`](../.env.example).

## Docker

```bash
docker build -t forecast-ai .
docker run --rm -p 30000:30000 --env-file .env forecast-ai
```

The container starts `uvicorn` through `start.sh` and uses the platform-provided `PORT` when present.

## Railway

1. Create a service from the GitHub repository.
2. Railway will use `railway.json` and the Dockerfile.
3. Add your provider keys in **Variables**.
4. Set `SERVER_API_KEY` for a public deployment.
5. Add a volume mounted at `/data` if you want persistent history.
6. Set `MEMORY_STORE_DIR=/data/memory`.
7. Verify `https://YOUR_DOMAIN/healthz`.

Do not set a custom command containing a quoted literal `$PORT`; `start.sh` handles port expansion.

## Render

The included `render.yaml` uses the same Dockerfile. Add provider keys and `SERVER_API_KEY` in the Render environment settings.

## CORS

Local and API-only deployments can leave:

```env
CORS_ALLOW_ORIGINS=*
```

For a browser application, use an exact comma-separated allowlist:

```env
CORS_ALLOW_ORIGINS=https://example.com,https://app.example.com
```

## Health and API documentation

- `GET /healthz`
- `GET /docs`
- `GET /openapi.json`

## Continuous watcher warning

Use `forecast server` or the supplied container for API-only operation. `forecast run` also starts a recurring watcher and can generate repeated LLM charges.
