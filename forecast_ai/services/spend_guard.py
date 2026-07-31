"""
LLM Spend Guard & Hard Circuit Breaker for Forecast AI.

Tracks cumulative daily and monthly LLM spend across OpenAI, Gemini, Anthropic, and OpenRouter calls.
Persists spend state to `memory_data/llm_spend_log.json` to prevent runaway LLM costs across process restarts.
Raises `SpendCapExceededError` if configured budget caps are reached.
"""

from __future__ import annotations

import logging
import json
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Estimated cost per 1,000 tokens / calls for circuit breaker
ESTIMATED_COST_PER_LLM_CALL_USD = 0.005  # Average cost per prompt + generation

class SpendCapExceededError(Exception):
    """Raised when in-app LLM spend circuit breaker triggers."""
    pass

class SpendGuard:
    def __init__(
        self,
        store_path: str = "memory_data/llm_spend_log.json",
        daily_cap_usd: float = 10.0,
        monthly_cap_usd: float = 50.0
    ):
        self.store_path = Path(store_path)
        self.daily_cap_usd = daily_cap_usd
        self.monthly_cap_usd = monthly_cap_usd
        self._ensure_store()

    def _ensure_store(self):
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.store_path.exists():
            self._save_store({
                "last_reset_day": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "last_reset_month": datetime.now(timezone.utc).strftime("%Y-%m"),
                "daily_spend_usd": 0.0,
                "monthly_spend_usd": 0.0,
                "total_calls_today": 0
            })

    def _load_store(self) -> Dict[str, Any]:
        try:
            if self.store_path.exists():
                return json.loads(self.store_path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.error(f"[SpendGuard] Failed to read spend store: {e}")
        return {
            "last_reset_day": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "last_reset_month": datetime.now(timezone.utc).strftime("%Y-%m"),
            "daily_spend_usd": 0.0,
            "monthly_spend_usd": 0.0,
            "total_calls_today": 0
        }

    def _save_store(self, data: Dict[str, Any]):
        try:
            self.store_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as e:
            logger.error(f"[SpendGuard] Failed to save spend store: {e}")

    def check_and_record_call(self, provider: str, model_id: str, agent_name: Optional[str] = None, estimated_cost: float = ESTIMATED_COST_PER_LLM_CALL_USD):
        """
        Evaluates current spend against daily and monthly caps.
        Raises SpendCapExceededError if spend cap is reached.
        """
        now = datetime.now(timezone.utc)
        today_str = now.strftime("%Y-%m-%d")
        month_str = now.strftime("%Y-%m")

        store = self._load_store()

        # Reset daily if new day
        if store.get("last_reset_day") != today_str:
            store["last_reset_day"] = today_str
            store["daily_spend_usd"] = 0.0
            store["total_calls_today"] = 0

        # Reset monthly if new month
        if store.get("last_reset_month") != month_str:
            store["last_reset_month"] = month_str
            store["monthly_spend_usd"] = 0.0

        daily_spend = float(store.get("daily_spend_usd", 0.0))
        monthly_spend = float(store.get("monthly_spend_usd", 0.0))

        # Check circuit breaker
        if daily_spend >= self.daily_cap_usd:
            msg = f"HARD CIRCUIT BREAKER TRIGGERED! Daily LLM spend limit reached (${daily_spend:.2f} >= ${self.daily_cap_usd:.2f}). Refusing LLM call for agent='{agent_name or 'global'}'."
            logger.error(f"[SpendGuard] {msg}")
            raise SpendCapExceededError(msg)

        if monthly_spend >= self.monthly_cap_usd:
            msg = f"HARD CIRCUIT BREAKER TRIGGERED! Monthly LLM spend limit reached (${monthly_spend:.2f} >= ${self.monthly_cap_usd:.2f}). Refusing LLM call for agent='{agent_name or 'global'}'."
            logger.error(f"[SpendGuard] {msg}")
            raise SpendCapExceededError(msg)

        # Update spend
        store["daily_spend_usd"] = round(daily_spend + estimated_cost, 4)
        store["monthly_spend_usd"] = round(monthly_spend + estimated_cost, 4)
        store["total_calls_today"] = int(store.get("total_calls_today", 0)) + 1
        self._save_store(store)

        # Structured log
        logger.info(
            f"[LLM_CALL] Timestamp={now.isoformat()} | Provider={provider} | Model={model_id} | "
            f"Agent={agent_name or 'global'} | DailySpend=${store['daily_spend_usd']:.4f} | CallsToday={store['total_calls_today']}"
        )
