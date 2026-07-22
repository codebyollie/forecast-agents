"""
Anomaly Detection Engine.
"""

from typing import List, Dict, Any, Tuple
from ..models.evidence import Evidence

class AnomalyDetector:
    def detect_market_anomalies(
        self,
        bids: List[Any],
        asks: List[Any],
        last_price: float,
        volume_24h: float
    ) -> List[str]:
        warnings = []
        # If bids/asks are empty
        if not bids and not asks:
            warnings.append("Liquidity warning: Market has empty order book.")
            return warnings

        # Volatility check if spread is large
        if bids and asks:
            best_bid = bids[0].price if hasattr(bids[0], "price") else bids[0]
            best_ask = asks[0].price if hasattr(asks[0], "price") else asks[0]
            spread = best_ask - best_bid
            if spread > 0.15:
                warnings.append(f"Spread anomaly: Large bid-ask spread of {spread:.2f}.")

        # Check pricing limits
        if last_price < 0.02 or last_price > 0.98:
            warnings.append(f"Extreme pricing: Market pricing implies near-certainty ({last_price:.2f}).")

        return warnings

    def detect_conflict_narratives(self, predictions: List[Any]) -> List[str]:
        """
        Check if different specialized agents have highly conflicting probabilities.
        """
        conflicts = []
        if len(predictions) < 2:
            return conflicts

        probs = [p.probability for p in predictions if hasattr(p, "probability")]
        if not probs:
            return conflicts

        max_prob = max(probs)
        min_prob = min(probs)
        if (max_prob - min_prob) > 0.4:
            conflicts.append(
                f"Narrative conflict: Agent forecasts diverge significantly (range: {min_prob:.2f} to {max_prob:.2f})."
            )

        return conflicts
