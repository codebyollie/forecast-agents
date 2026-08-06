"""
Forecast models: ReasoningTrace and ForecastResult.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Any
from .prediction import Prediction
from .confidence import ConfidenceScore

@dataclass
class ReasoningTrace:
    agent_contributions: Dict[str, float] = field(default_factory=dict)  # Agent weights
    agent_reasonings: Dict[str, str] = field(default_factory=dict)       # Individual agent reasoning
    aggregation_steps: List[str] = field(default_factory=list)           # Consensus steps log
    conflicts_resolved: List[str] = field(default_factory=list)          # Conflict descriptions

@dataclass
class ForecastResult:
    market_id: str                      # Polymarket token ID or custom market slug
    probability: float                  # Final consensus probability (0.0 to 1.0)
    confidence: ConfidenceScore         # Consensus confidence
    reasoning_trace: ReasoningTrace     # Explainable trace of consensus
    individual_predictions: List[Prediction] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def consensus_probability(self) -> float:
        return self.probability

    @property
    def consensus_confidence(self) -> float:
        if isinstance(self.confidence, (int, float)):
            return float(self.confidence)
        if hasattr(self.confidence, "score"):
            return float(self.confidence.score)
        return 0.5
    
    @property
    def explanation(self) -> str:
        if hasattr(self.reasoning_trace, "aggregation_steps") and self.reasoning_trace.aggregation_steps:
            return " ".join(self.reasoning_trace.aggregation_steps)
        if self.individual_predictions:
            return self.individual_predictions[0].reasoning
        return "7-Agent consensus prediction generated."
