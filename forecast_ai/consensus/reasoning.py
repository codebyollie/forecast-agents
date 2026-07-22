"""
Consensus Reasoning Synthesizer.
"""

from typing import List, Dict
from ..models.prediction import Prediction
from ..models.forecast import ReasoningTrace

class ConsensusReasoningSynthesizer:
    def synthesize_reasoning(
        self,
        predictions: List[Prediction],
        consensus_prob: float,
        consensus_conf: float
    ) -> str:
        """
        Create a concise public summary showing why this consensus was reached.
        """
        if not predictions:
            return "No agents provided reasoning."

        summary_parts = [
            f"Consensus Probability: {consensus_prob * 100:.1f}% (Confidence: {consensus_conf * 100:.1f}%)"
        ]

        summary_parts.append("\nAgent breakdowns:")
        for p in predictions:
            summary_parts.append(
                f"- **{p.agent_name}** ({p.probability * 100:.1f}%): "
                f"\"{p.reasoning[:200]}...\""
            )

        return "\n".join(summary_parts)
