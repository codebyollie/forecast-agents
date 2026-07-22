"""
Weighted Consensus Formulas.
"""

from typing import List, Dict
from ..models.prediction import Prediction

class WeightedConsensusCalculator:
    def calculate_weighted_probability(
        self,
        predictions: List[Prediction],
        agent_weights: Dict[str, float]
    ) -> float:
        """
        Calculates consensus probability using weighted combination of predictions,
        incorporating both agent reliability weight and prediction confidence.
        """
        if not predictions:
            return 0.5

        total_weight = 0.0
        weighted_sum = 0.0

        for p in predictions:
            # Combined weight = agent reliability * confidence score
            agent_weight = agent_weights.get(p.agent_name, 1.0)
            conf = p.confidence.score
            combined_weight = agent_weight * (0.2 + 0.8 * conf)

            weighted_sum += p.probability * combined_weight
            total_weight += combined_weight

        if total_weight == 0.0:
            return 0.5

        return weighted_sum / total_weight
