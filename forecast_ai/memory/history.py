"""
Memory History Engine.
"""

from typing import List, Dict, Any
from .store import MemoryStore

class MemoryHistory:
    def __init__(self, store: MemoryStore):
        self.store = store

    def get_forecast_history_for_market(self, market_id: str) -> List[Dict[str, Any]]:
        history = self.store.list_forecasts()
        return [f for f in history if f.get("market_id") == market_id]

    def get_aggregate_stats(self) -> Dict[str, Any]:
        forecasts = self.store.list_forecasts()
        if not forecasts:
            return {"total_forecasts": 0, "average_confidence": 0.0}

        conf_sum = sum(f.get("confidence", {}).get("score", 0.5) for f in forecasts)
        return {
            "total_forecasts": len(forecasts),
            "average_confidence": conf_sum / len(forecasts),
            "reputations": self.store.get_agent_reputations()
        }
