#!/usr/bin/env bash
# Launch MetaClaw in OPD (On-Policy Distillation) mode.
#
# Prerequisites:
#   1. A Tinker API key for the student model (cloud RL training).
#   2. A teacher model served behind an OpenAI-compatible /v1/completions
#      endpoint (e.g., vLLM or SGLang serving Qwen3-32B).
#
# Usage:
#   bash scripts/run_openclaw_tinker_opd.sh

set -euo pipefail

# ── API keys ──────────────────────────────────────────────────────────
export TINKER_API_KEY="${TINKER_API_KEY:-}"
export OPENAI_API_KEY="${OPENAI_API_KEY:-}"

# ── Teacher model endpoint ────────────────────────────────────────────
# Point this to the teacher model's OpenAI-compatible completions server.
# Example: vLLM serving Qwen3-32B on port 8082.
export TEACHER_URL="${TEACHER_URL:-http://localhost:8082/v1}"
export TEACHER_MODEL="${TEACHER_MODEL:-Qwen/Qwen3-32B}"
export TEACHER_API_KEY="${TEACHER_API_KEY:-}"

# ── Run ───────────────────────────────────────────────────────────────
python3 examples/run_conversation_opd.py
