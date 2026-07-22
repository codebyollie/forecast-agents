"""
Tests for Consensus Engine.
"""

from forecast_ai.config import ForecastConfig
from forecast_ai.models.prediction import Prediction
from forecast_ai.models.confidence import ConfidenceScore
from forecast_ai.consensus.weighted import WeightedConsensusCalculator
from forecast_ai.consensus.confidence import ConsensusConfidenceCalculator
from forecast_ai.intelligence.probability_calibration import ProbabilityCalibrator

def test_weighted_consensus():
    calc = WeightedConsensusCalculator()
    
    # 2 predictions: Agent A (prob=0.8, conf=0.9), Agent B (prob=0.4, conf=0.1)
    p1 = Prediction(
        agent_name="news",
        probability=0.8,
        confidence=ConfidenceScore(score=0.9),
        reasoning="bullish news"
    )
    p2 = Prediction(
        agent_name="social",
        probability=0.4,
        confidence=ConfidenceScore(score=0.1),
        reasoning="bearish retail"
    )
    
    weights = {"news": 1.0, "social": 1.0}
    
    consensus = calc.calculate_weighted_probability([p1, p2], weights)
    # Combined weight p1 = 1.0 * (0.2 + 0.8 * 0.9) = 0.92
    # Combined weight p2 = 1.0 * (0.2 + 0.8 * 0.1) = 0.28
    # Consensus = (0.8 * 0.92 + 0.4 * 0.28) / (0.92 + 0.28) = (0.736 + 0.112) / 1.2 = 0.848 / 1.2 = 0.706
    assert round(consensus, 3) == 0.707

def test_probability_calibrator():
    calibrator = ProbabilityCalibrator()
    # High confidence (1.0) retains original prob, low confidence pulls to 0.5
    raw_p = 0.9
    cal_high = calibrator.calibrate(raw_p, 1.0)
    cal_low = calibrator.calibrate(raw_p, 0.0)
    
    assert cal_high == 0.9
    assert cal_low == 0.62  # 0.5 + (0.9 - 0.5) * 0.3 = 0.5 + 0.12 = 0.62
