#!/usr/bin/env bash
# ==============================================================================
# Forecast AI One-Line Installer Script
# ==============================================================================
# Usage:
#   curl -sSL https://raw.githubusercontent.com/codebyollie/forecast-agents/main/install.sh | bash
# ==============================================================================

set -euo pipefail

echo "======================================================================"
echo "🔮 Installing Forecast AI — Multi-Agent Intelligence Infrastructure 🔮"
echo "======================================================================"

# 1. Check Python 3.10+ requirement
echo "[INFO] Checking Python version..."
if ! command -v python3 >/dev/null 2>&1; then
    echo "[ERROR] python3 is required but not installed. Please install Python 3.10+ and retry." >&2
    exit 1
fi

PY_CHECK=$(python3 -c "import sys; print(1 if sys.version_info >= (3, 10) else 0)" 2>/dev/null || echo 0)
if [ "$PY_CHECK" -ne 1 ]; then
    echo "[ERROR] Python 3.10 or higher is required. Found: $(python3 -V 2>&1)" >&2
    exit 1
fi
echo "[INFO] Python version check passed: $(python3 -V 2>&1)"

# 2. Check Git availability
if ! command -v git >/dev/null 2>&1; then
    echo "[ERROR] git is required but not installed. Please install git and retry." >&2
    exit 1
fi

# 3. Idempotent Repository directory navigation / clone check
REPO_URL="https://github.com/codebyollie/forecast-agents.git"
TARGET_DIR="forecast-agents"

if [ -f "pyproject.toml" ] && [ -d "forecast_ai" ]; then
    echo "[INFO] Already inside forecast-agents repository directory."
elif [ -d "$TARGET_DIR" ]; then
    echo "[INFO] Existing '$TARGET_DIR' directory found. Navigating into project..."
    cd "$TARGET_DIR"
else
    echo "[INFO] Cloning Forecast AI repository from $REPO_URL..."
    git clone "$REPO_URL" "$TARGET_DIR"
    cd "$TARGET_DIR"
fi

# 4. Install package in editable mode with WebSocket extras
echo "[INFO] Installing Forecast AI package and dependencies (pip install -e '.[ws]')..."
python3 -m pip install --upgrade pip
python3 -m pip install -e ".[ws]"

echo "[SUCCESS] Forecast AI package successfully installed!"

# 5. Launch interactive setup wizard if terminal is interactive
if [ -t 0 ]; then
    echo "[INFO] Launching Forecast AI configuration wizard..."
    forecast setup
else
    echo "[INFO] Non-interactive installation complete. Run 'forecast setup' to configure API keys."
fi

echo "======================================================================"
echo "🎉 Forecast AI installation complete! Run 'forecast --help' for CLI. 🎉"
echo "======================================================================"
