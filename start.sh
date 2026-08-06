#!/bin/sh
set -eu

exec uvicorn forecast_ai.api.server:app --host 0.0.0.0 --port "${PORT:-30000}"
