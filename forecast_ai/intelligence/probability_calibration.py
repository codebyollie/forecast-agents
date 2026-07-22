"""
Probability Calibration Engine.

Adjusts the combined probability estimates to reduce bias and handle low confidence.
"""

import math
from typing import List

class ProbabilityCalibrator:
    def __init__(self, default_confidence: float = 0.5):
        self.default_confidence = default_confidence

    def calibrate(self, raw_prob: float, confidence_score: float) -> float:
        """
        Calibrate raw probability. If confidence is low, pull probability closer to 0.5 (maximum uncertainty).
        If confidence is high, allow extreme probabilities.
        """
        # Clamp inputs
        raw_prob = max(0.01, min(0.99, raw_prob))
        confidence_score = max(0.0, min(1.0, confidence_score))

        # Pull towards 0.5 if confidence is low
        # calibrated = 0.5 + (raw_prob - 0.5) * confidence_score
        calibrated = 0.5 + (raw_prob - 0.5) * (0.3 + 0.7 * confidence_score)

        return float(max(0.0, min(1.0, calibrated)))

    def brier_score(self, forecast_prob: float, outcome: float) -> float:
        """
        Calculate Brier Score to measure accuracy of past prediction.
        Outcome is 1.0 (true) or 0.0 (false).
        """
        return (forecast_prob - outcome) ** 2
