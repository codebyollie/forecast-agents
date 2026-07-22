"""
Tests for Robinhood Agentic Trading MCP Recommendation Formatter.
"""

from forecast_ai.models.forecast import ForecastResult, ReasoningTrace
from forecast_ai.models.confidence import ConfidenceScore
from forecast_ai.robinhood_agentic.recommendation import RobinhoodRecommendationEngine, RobinhoodTradeRecommendation

def test_recommendation_engine_buy_yes():
    engine = RobinhoodRecommendationEngine()
    
    forecast = ForecastResult(
        market_id="fed-rate-cut-2026",
        probability=0.75,
        confidence=ConfidenceScore(score=0.85),
        reasoning_trace=ReasoningTrace(),
        individual_predictions=[]
    )

    rec = engine.generate_recommendation(forecast)
    assert rec.action == "BUY_YES"
    assert rec.target_probability == 0.75
    assert rec.confidence_score == 0.85
    assert rec.recommended_position_pct > 0
    assert "BUY_YES" in rec.to_formatted_prompt()
    assert "https://agent.robinhood.com/mcp/trading" in rec.to_formatted_prompt()

def test_recommendation_engine_hold():
    engine = RobinhoodRecommendationEngine()
    
    forecast = ForecastResult(
        market_id="custom-market",
        probability=0.52,
        confidence=ConfidenceScore(score=0.40),
        reasoning_trace=ReasoningTrace(),
        individual_predictions=[]
    )

    rec = engine.generate_recommendation(forecast)
    assert rec.action == "HOLD"
    assert rec.recommended_position_pct == 0.0

