#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/codebyollie/forecast-agents.git"
TARGET_DIR="forecast-agents"

if ! command -v python3 >/dev/null 2>&1; then
    echo "Python 3.10 or newer is required." >&2
    exit 1
fi

python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' || {
    echo "Python 3.10 or newer is required." >&2
    exit 1
}

if ! command -v git >/dev/null 2>&1; then
    echo "Git is required." >&2
    exit 1
fi

if [ -f "pyproject.toml" ] && [ -d "forecast_ai" ]; then
    PROJECT_DIR="."
elif [ -d "$TARGET_DIR/.git" ]; then
    PROJECT_DIR="$TARGET_DIR"
else
    git clone "$REPO_URL" "$TARGET_DIR"
    PROJECT_DIR="$TARGET_DIR"
fi

cd "$PROJECT_DIR"
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .

echo "Forecast AI installed in: $(pwd)"
echo "Activate it later with: source $(pwd)/.venv/bin/activate"
echo "Then run: forecast setup"

if [ -t 0 ]; then
    forecast setup
fi
