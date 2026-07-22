"""
Memory Store for Forecast AI.

Stores historical forecasts, agent reputations, and evidence databases to improve future predictions.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..models.forecast import ForecastResult
from ..config import ForecastConfig

class MemoryStore:
    def __init__(self, config: ForecastConfig):
        self.config = config
        self.store_dir = Path(config.memory.store_dir)
        self.store_dir.mkdir(parents=True, exist_ok=True)
        
        self.forecasts_file = self.store_dir / "forecasts.json"
        self.reputation_file = self.store_dir / "reputation.json"
        self.evidence_file = self.store_dir / "evidence.json"

        self._init_files()

    def _init_files(self):
        for f in [self.forecasts_file, self.reputation_file, self.evidence_file]:
            if not f.exists():
                with open(f, "w", encoding="utf-8") as file_handle:
                    initial_data = {} if f == self.reputation_file else []
                    json.dump(initial_data, file_handle)

    def _load_json(self, path: Path) -> Any:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {} if path == self.reputation_file else []

    def _save_json(self, path: Path, data: Any):
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception:
            pass

    def save_forecast(self, result: ForecastResult):
        forecasts = self._load_json(self.forecasts_file)
        
        # Serialize ForecastResult
        entry = {
            "market_id": result.market_id,
            "probability": result.probability,
            "confidence": {
                "score": result.confidence.score,
                "factors": result.confidence.factors,
                "warnings": result.confidence.warnings
            },
            "timestamp": result.timestamp.isoformat(),
            "predictions": [
                {
                    "agent_name": p.agent_name,
                    "probability": p.probability,
                    "confidence": p.confidence.score,
                    "reasoning": p.reasoning
                } for p in result.individual_predictions
            ],
            "metadata": result.metadata
        }
        
        forecasts.append(entry)
        # Cap limit
        max_entries = self.config.memory.max_history_entries
        if len(forecasts) > max_entries:
            forecasts = forecasts[-max_entries:]
            
        self._save_json(self.forecasts_file, forecasts)

    def get_agent_reputations(self) -> Dict[str, float]:
        return self._load_json(self.reputation_file)

    def get_agent_reputation(self, agent_name: str) -> float:
        rep = self.get_agent_reputations()
        return rep.get(agent_name, self.config.consensus.default_agent_weight)

    def update_agent_reputation(self, agent_name: str, outcome_correct: bool, error_delta: float):
        if not self.config.memory.enable_reputation_updates:
            return

        reps = self.get_agent_reputations()
        current = reps.get(agent_name, self.config.consensus.default_agent_weight)

        alpha = self.config.consensus.calibration_alpha
        if outcome_correct:
            # Boost reputation
            new_rep = current + alpha * (2.0 - current) * (1.0 - error_delta)
        else:
            # Penalty
            new_rep = current - alpha * current * error_delta

        reps[agent_name] = max(0.1, min(2.0, new_rep))
        self._save_json(self.reputation_file, reps)
        
    def list_forecasts(self) -> List[Dict[str, Any]]:
        return self._load_json(self.forecasts_file)
