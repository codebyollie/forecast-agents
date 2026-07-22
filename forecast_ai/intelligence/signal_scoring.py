"""
Signal Scoring Engine.

Analyzes individual pieces of evidence and computes a strength score based on source credibility,
recency, and sentiment alignment.
"""

from typing import Dict, Any
from datetime import datetime, UTC
from ..models.evidence import Evidence

class SignalScorer:
    def __init__(self, source_credibility: Dict[str, float] = None):
        self.source_credibility = source_credibility or {
            "polymarket": 1.0,
            "blockchain": 0.9,
            "news": 0.8,
            "rss": 0.7,
            "twitter": 0.5,
            "reddit": 0.4
        }

    def score_signal(self, evidence: Evidence) -> float:
        # 1. Source Credibility
        cred = self.source_credibility.get(evidence.source_name, 0.5)

        # 2. Recency decay (decays over 7 days)
        now = datetime.now(UTC)
        evidence_time = evidence.timestamp
        if evidence_time.tzinfo is None:
            # Assume UTC
            evidence_time = evidence_time.replace(tzinfo=UTC)
        
        age_seconds = (now - evidence_time).total_seconds()
        age_days = max(0.0, age_seconds / (24 * 3600))
        
        # Exponential decay: half-life of 3 days
        recency = 0.5 ** (age_days / 3.0)

        # Combine
        score = cred * recency * evidence.relevance_score
        return float(max(0.1, min(1.0, score)))
