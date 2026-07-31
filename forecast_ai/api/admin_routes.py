"""
Owner/Admin API Routes for Live Dashboard (`PATCH /admin/featured-market`).

Allows project owner to manually set/update the Featured Market.
Triggers a single, real 7-agent consensus pipeline run using GPT-5.6 Luna model override.
"""

from __future__ import annotations

import logging
import os
import copy
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Header, status
from pydantic import BaseModel

from ..config import ForecastConfig
from ..pipelines.forecast import ForecastPipeline
from ..services.featured_market import FeaturedMarketService
from ..services.market_search import MarketSearchService

logger = logging.getLogger(__name__)

class SetFeaturedMarketRequest(BaseModel):
    market_id: str
    question: str
    venue: Optional[str] = "Kalshi (mirrors Robinhood Predict)"

def verify_admin_secret(x_admin_secret: Optional[str] = Header(None, alias="x-admin-secret"), config: Optional[ForecastConfig] = None):
    """
    Verifies admin shared secret header `x-admin-secret`.
    Compares against `ADMIN_SECRET` environment variable or `config.server.admin_secret`.
    """
    expected = os.getenv("ADMIN_SECRET", "")
    if not expected and config:
        expected = getattr(config.server, "admin_secret", "admin_secret_123")
    if not expected:
        expected = "admin_secret_123"

    if not x_admin_secret or x_admin_secret != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing 'x-admin-secret' header."
        )

def create_admin_router(config: ForecastConfig, pipeline: ForecastPipeline) -> APIRouter:
    router = APIRouter(prefix="/admin", tags=["admin"])

    featured_service = FeaturedMarketService(supabase_config=config.profile.supabase)
    search_service = MarketSearchService(
        kalshi_base_url=config.kalshi.api_base_url,
        gamma_api_url=config.polymarket.gamma_api_url
    )

    @router.patch("/featured-market")
    async def set_featured_market(
        req: SetFeaturedMarketRequest,
        x_admin_secret: Optional[str] = Header(None, alias="x-admin-secret")
    ) -> Dict[str, Any]:
        """
        PATCH /admin/featured-market
        Admin-only endpoint to set the featured market for Live Dashboard.
        Triggers 7-agent consensus forecast ONCE with GPT-5.6 Luna model override.
        """
        verify_admin_secret(x_admin_secret, config)

        logger.info(f"[AdminRoutes] Owner set featured market: '{req.question}' ({req.market_id}) on {req.venue}. Triggering single GPT-5.6 Luna pipeline run...")

        try:
            result = await pipeline.run_forecast(
                question=req.question,
                market_id=req.market_id,
                is_public_feed=False
            )

            live_price = await search_service.get_live_price(req.market_id, req.venue)
            if live_price is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Could not find a live market price for market '{req.market_id}' on venue '{req.venue}'. Check market_id/ticker."
                )

            # Format agent breakdown (full untruncated reasoning)
            agent_breakdown = [
                {
                    "agent_name": p.agent_name,
                    "probability": round(p.probability, 4),
                    "confidence": round(p.confidence.score, 4),
                    "reasoning_summary": p.reasoning,
                    "warnings": p.confidence.warnings
                } for p in result.individual_predictions
            ]

            payload = {
                "market_id": req.market_id,
                "question": req.question,
                "venue": req.venue or "Kalshi (mirrors Robinhood Predict)",
                "consensus_probability": round(result.consensus_probability, 4),
                "consensus_confidence": round(result.consensus_confidence, 4),
                "market_price": live_price,
                "explanation": result.explanation,
                "agent_breakdown": agent_breakdown,
                "model_used": "gpt-5.6-luna"
            }

            saved_payload = featured_service.save_featured_market(payload)
            logger.info(f"[AdminRoutes] Featured market analysis completed and saved successfully.")
            return saved_payload

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"[AdminRoutes] Featured market pipeline execution failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Featured market pipeline error: {e}"
            )

    return router
