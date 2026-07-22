"""
Evidence Ranking Engine.
"""

from typing import List
from ..models.evidence import Evidence
from .signal_scoring import SignalScorer

class EvidenceRanker:
    def __init__(self, scorer: SignalScorer = None):
        self.scorer = scorer or SignalScorer()

    def rank_evidence(self, items: List[Evidence], min_score: float = 0.2) -> List[Evidence]:
        # Compute and assign score
        ranked = []
        for item in items:
            score = self.scorer.score_signal(item)
            if score >= min_score:
                item.relevance_score = score
                ranked.append(item)

        # Sort descending by score
        ranked.sort(key=lambda x: x.relevance_score, reverse=True)
        return ranked
