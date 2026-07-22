"""
ConfidenceScore model definition.
"""

from dataclasses import dataclass, field
from typing import Dict, List

@dataclass
class ConfidenceScore:
    score: float = 0.5  # 0.0 to 1.0
    factors: Dict[str, float] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
