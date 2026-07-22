"""
Robinhood Agentic Trading Recommendation Formatter.

Formats Consensus Engine forecast results into structured execution recommendations
ready to be handed off to a user's own Robinhood Agentic Trading MCP session (https://agent.robinhood.com/mcp/trading).
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from ..models.forecast import ForecastResult

@dataclass
class RobinhoodTradeRecommendation:
    market_id: str
    action: str              # "BUY_YES" | "BUY_NO" | "HOLD"
    target_probability: float
    confidence_score: float
    recommended_position_pct: float
    rationale: str
    mcp_endpoint: str = "https://agent.robinhood.com/mcp/trading"
    mcp_payload: Dict[str, Any] = field(default_factory=dict)

    def to_formatted_prompt(self) -> str:
        """
        Formats recommendation into a clear, agent-ready text prompt for hand-off to Claude/ChatGPT/Cursor MCP session.
        """
        return (
            f"🎯 ROBINHOOD AGENTIC TRADE RECOMMENDATION\n"
            f"=========================================\n"
            f"Target Market: {self.market_id}\n"
            f"Recommended Action: {self.action}\n"
            f"Calibrated Implied Probability: {self.target_probability:.1%}\n"
            f"Confidence Score: {self.confidence_score:.2f}\n"
            f"Suggested Size: {self.recommended_position_pct:.1f}% of allocation\n"
            f"Rationale: {self.rationale}\n"
            f"\n"
            f"🤖 MCP Integration Endpoint: {self.mcp_endpoint}\n"
            f"Instructions for Agent: Execute '{self.action}' on contract '{self.market_id}' via Robinhood Agentic account."
        )

class RobinhoodRecommendationEngine:
    def __init__(self, mcp_endpoint: str = "https://agent.robinhood.com/mcp/trading"):
        self.mcp_endpoint = mcp_endpoint

    def generate_recommendation(
        self,
        forecast: ForecastResult,
        threshold_buy_yes: float = 0.60,
        threshold_buy_no: float = 0.40,
        max_allocation_pct: float = 5.0
    ) -> RobinhoodTradeRecommendation:
        """
        Translates a ForecastResult into an executable Robinhood Predict trade recommendation.
        """
        prob = forecast.probability
        conf = forecast.confidence.score

        if prob >= threshold_buy_yes and conf >= 0.5:
            action = "BUY_YES"
            # Scaling position size based on edge over 50% and confidence
            edge = prob - 0.5
            pos_pct = round(min(edge * 2.0 * conf * max_allocation_pct, max_allocation_pct), 2)
            rationale = f"High consensus probability ({prob:.1%}) with strong confidence ({conf:.2f})."
        elif prob <= threshold_buy_no and conf >= 0.5:
            action = "BUY_NO"
            edge = 0.5 - prob
            pos_pct = round(min(edge * 2.0 * conf * max_allocation_pct, max_allocation_pct), 2)
            rationale = f"Low consensus probability ({prob:.1%}) favoring NO outcome with confidence ({conf:.2f})."
        else:
            action = "HOLD"
            pos_pct = 0.0
            rationale = f"Probability ({prob:.1%}) or confidence ({conf:.2f}) does not meet execution threshold."

        mcp_payload = {
            "tool": "robinhood_trade_order",
            "params": {
                "market_ticker": forecast.market_id,
                "action": action,
                "confidence": conf,
                "implied_probability": prob,
                "suggested_position_pct": pos_pct,
            }
        }

        return RobinhoodTradeRecommendation(
            market_id=forecast.market_id,
            action=action,
            target_probability=prob,
            confidence_score=conf,
            recommended_position_pct=pos_pct,
            rationale=rationale,
            mcp_endpoint=self.mcp_endpoint,
            mcp_payload=mcp_payload
        )
