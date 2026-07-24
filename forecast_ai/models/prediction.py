"""
Prediction model definition.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional
from .evidence import Evidence
from .confidence import ConfidenceScore

@dataclass
class Prediction:
    agent_name: str
    probability: float  # 0.0 to 1.0
    confidence: ConfidenceScore
    reasoning: str
    evidence_used: List[Evidence] = field(default_factory=list)
    citations: List[Dict[str, str]] = field(default_factory=list)  # Top citations (title + url)
    timestamp: datetime = field(default_factory=datetime.utcnow)
