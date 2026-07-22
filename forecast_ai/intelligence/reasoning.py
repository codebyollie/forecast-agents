"""
Reasoning Trace Aggregator.
"""

from typing import List, Dict
from ..models.prediction import Prediction
from ..models.forecast import ReasoningTrace

class ReasoningTraceBuilder:
    def build_trace(
        self,
        predictions: List[Prediction],
        agent_weights: Dict[str, float],
        conflicts: List[str]
    ) -> ReasoningTrace:
        contributions = {}
        reasonings = {}
        steps = []

        for p in predictions:
            contributions[p.agent_name] = agent_weights.get(p.agent_name, 1.0)
            reasonings[p.agent_name] = p.reasoning
            steps.append(f"Parsed {p.agent_name} prediction: Prob={p.probability:.2f}, Conf={p.confidence.score:.2f}")

        steps.append(f"Applying weighted consensus using agent weight mapping: {contributions}")
        if conflicts:
            steps.append(f"Identified narrative divergence. Conflicts detected: {conflicts}")

        return ReasoningTrace(
            agent_contributions=contributions,
            agent_reasonings=reasonings,
            aggregation_steps=steps,
            conflicts_resolved=conflicts
        )
