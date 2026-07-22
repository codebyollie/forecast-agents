"""
Consensus Engine.

The main coordinator of Forecast AI's consensus algorithm, merging all agent 
predictions into a single, calibrated, explainable forecast.
"""

from typing import List, Dict, Any, Optional
from ..models.prediction import Prediction
from ..models.forecast import ForecastResult
from ..config import ForecastConfig

from .weighted import WeightedConsensusCalculator
from .confidence import ConsensusConfidenceCalculator
from .reasoning import ConsensusReasoningSynthesizer
from ..intelligence.anomaly_detection import AnomalyDetector
from ..intelligence.probability_calibration import ProbabilityCalibrator
from ..intelligence.reasoning import ReasoningTraceBuilder

class ConsensusEngine:
    def __init__(self, config: ForecastConfig):
        self.config = config
        self.weighted_calc = WeightedConsensusCalculator()
        self.conf_calc = ConsensusConfidenceCalculator()
        self.synthesizer = ConsensusReasoningSynthesizer()
        self.detector = AnomalyDetector()
        self.calibrator = ProbabilityCalibrator()
        self.trace_builder = ReasoningTraceBuilder()

    async def aggregate_predictions(
        self,
        market_id: str,
        predictions: List[Prediction],
        agent_reputations: Optional[Dict[str, float]] = None
    ) -> ForecastResult:
        # Load agent weights from config or historical reputation
        agent_weights = {}
        for name, a_cfg in self.config.agents.items():
            agent_weights[name] = a_cfg.weight

        if agent_reputations:
            for name, rep in agent_reputations.items():
                # Blend config weight with reputation
                agent_weights[name] = (agent_weights.get(name, 1.0) + rep) / 2.0

        # 1. Detect conflicts or warnings
        warnings = self.detector.detect_conflict_narratives(predictions)

        # 2. Weighted consensus probability
        raw_prob = self.weighted_calc.calculate_weighted_probability(predictions, agent_weights)

        # 3. Consensus confidence scoring
        confidence = self.conf_calc.calculate_confidence(predictions, agent_weights, warnings)

        # 4. Calibrate final probability
        calibrated_prob = self.calibrator.calibrate(raw_prob, confidence.score)

        # 5. Synthesis reasoning and building trace
        summary_reasoning = self.synthesizer.synthesize_reasoning(predictions, calibrated_prob, confidence.score)
        trace = self.trace_builder.build_trace(predictions, agent_weights, warnings)

        return ForecastResult(
            market_id=market_id,
            probability=calibrated_prob,
            confidence=confidence,
            reasoning_trace=trace,
            individual_predictions=predictions,
            metadata={
                "raw_probability": raw_prob,
                "summary_reasoning": summary_reasoning
            }
        )
