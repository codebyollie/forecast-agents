"""
Prediction model definition.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from .evidence import Evidence
from .confidence import ConfidenceScore

@dataclass
class Prediction:
    agent_name: str
    probability: float  # 0.0 to 1.0
    confidence: ConfidenceScore
    reasoning: str
    summary: str = ""
    key_drivers: List[str] = field(default_factory=list)
    counter_signals: List[str] = field(default_factory=list)
    uncertainties: List[str] = field(default_factory=list)
    watch_next: List[str] = field(default_factory=list)
    evidence_used: List[Evidence] = field(default_factory=list)
    citations: List[Dict[str, str]] = field(default_factory=list)
    research_providers: List[str] = field(default_factory=list)
    provider_insights: Dict[str, str] = field(default_factory=dict)
    provider_statuses: Dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
