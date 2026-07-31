"""
Authenticated Custom Analyses & Market Search API Routes.

Provides:
- GET /markets/search?q=<query> — Search open prediction markets across Kalshi & Polymarket.
- POST /analyses/run — Trigger custom 7-agent consensus analysis (tier-gated).
- GET /analyses/history — Fetch user's past custom analyses for Track Record.
- GET /analyses/usage — Fetch current daily analysis usage & remaining limit.
"""

from __future__ import annotations

import logging
import time
import copy
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from pydantic import BaseModel

from ..config import ForecastConfig
from .auth import get_current_privy_user
from ..db.supabase_store import SupabaseProfileStore
from ..services.balance_checker import BalanceChecker
from ..services.market_search import MarketSearchService
from ..pipelines.forecast import ForecastPipeline

logger = logging.getLogger(__name__)

# Search rate limiter per user: 30 searches per hour
_SEARCH_RATE_LIMITS: Dict[str, List[float]] = {}
SEARCH_MAX_PER_HOUR = 30
SEARCH_WINDOW_SECONDS = 3600.0

def check_search_rate_limit(user_id: str):
    now = time.time()
    timestamps = _SEARCH_RATE_LIMITS.setdefault(user_id, [])
    _SEARCH_RATE_LIMITS[user_id] = [t for t in timestamps if now - t < SEARCH_WINDOW_SECONDS]
    if len(_SEARCH_RATE_LIMITS[user_id]) >= SEARCH_MAX_PER_HOUR:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Search rate limit exceeded. Maximum {SEARCH_MAX_PER_HOUR} market searches per hour."
        )
    _SEARCH_RATE_LIMITS[user_id].append(now)

class RunAnalysisRequest(BaseModel):
    market_id: str
    question: str
    venue: Optional[str] = "Kalshi / Robinhood Predict"

def create_analysis_router(config: ForecastConfig, pipeline: ForecastPipeline) -> APIRouter:
    router = APIRouter(prefix="", tags=["custom_analyses"])

    store = SupabaseProfileStore(config.profile.supabase)
    balance_checker = BalanceChecker(config.profile.tier)
    search_service = MarketSearchService(
        kalshi_base_url=config.kalshi.api_base_url,
        gamma_api_url=config.polymarket.gamma_api_url
    )

    async def _get_user_tier(privy_user_id: str, user_claims: Dict[str, Any]) -> str:
        """Helper to resolve current holder tier for user."""
        existing = await store.get_profile(privy_user_id) or {}
        primary_wallet = user_claims.get("wallet_address") or existing.get("wallet_address") or ""
        wallets_list = user_claims.get("wallet_addresses") or ([primary_wallet] if primary_wallet else [])
        
        forai_balance = 0.0
        if wallets_list:
            forai_balance = await balance_checker.fetch_onchain_balance(wallets_list)
        elif existing.get("forai_balance"):
            forai_balance = float(existing["forai_balance"])

        return balance_checker.evaluate_holder_tier(forai_balance)

    def _get_tier_limits(tier: str) -> tuple[int, str]:
        """Returns (daily_limit, model_override) for given tier. Currently using gpt-5.6-luna for all tiers."""
        tier_cfg = config.profile.custom_analysis
        luna_model = "gpt-5.6-luna"
        if tier == "Pro":
            return tier_cfg.pro_daily_limit, luna_model
        elif tier == "Holder":
            return tier_cfg.holder_daily_limit, luna_model
        else:
            return tier_cfg.free_daily_limit, luna_model

    @router.get("/markets/search")
    async def search_markets(
        q: Optional[str] = Query(None, description="Query text to search across prediction markets"),
        limit: int = Query(10, ge=1, le=50),
        user: Dict[str, Any] = Depends(get_current_privy_user)
    ) -> List[Dict[str, Any]]:
        """
        GET /markets/search?q=<query>
        Searches open prediction markets on Kalshi & Polymarket matching the query text.
        If q is omitted or empty, returns popular active open contracts.
        Auth required. Rate-limited to 30 searches/hour per user.
        """
        privy_user_id = user["privy_user_id"]
        check_search_rate_limit(privy_user_id)

        results = await search_service.search_markets(query=q, limit=limit)
        return results

    @router.get("/analyses/usage")
    async def get_analysis_usage(
        user: Dict[str, Any] = Depends(get_current_privy_user)
    ) -> Dict[str, Any]:
        """
        GET /analyses/usage
        Returns user's current tier, today's usage count, daily limit, and remaining analyses.
        """
        privy_user_id = user["privy_user_id"]
        tier = await _get_user_tier(privy_user_id, user)
        daily_limit, model_override = _get_tier_limits(tier)
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        current_count = await store.get_daily_analysis_count(privy_user_id, today_str)

        return {
            "tier": tier,
            "usage_date": today_str,
            "daily_count": current_count,
            "daily_limit": daily_limit,
            "remaining": max(0, daily_limit - current_count),
            "model_override": model_override
        }

    @router.post("/analyses/run")
    async def run_custom_analysis(
        req: RunAnalysisRequest,
        user: Dict[str, Any] = Depends(get_current_privy_user)
    ) -> Dict[str, Any]:
        """
        POST /analyses/run
        Triggers a custom 7-agent consensus forecast run for the specified market.
        Auth required & tier-gated.
        """
        privy_user_id = user["privy_user_id"]
        tier = await _get_user_tier(privy_user_id, user)
        daily_limit, model_override = _get_tier_limits(tier)

        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        current_count = await store.get_daily_analysis_count(privy_user_id, today_str)

        if current_count >= daily_limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Daily custom analysis limit reached for your '{tier}' tier ({daily_limit}/day). Resets at 00:00 UTC."
            )

        logger.info(f"[AnalysisRoutes] User '{privy_user_id}' ({tier} tier) running analysis for '{req.question}' with model '{model_override}'")

        try:
            result = await pipeline.run_forecast(
                question=req.question,
                market_id=req.market_id,
                is_public_feed=False,
                model_override=model_override
            )

            # Atomically increment usage
            await store.increment_daily_analysis_count(privy_user_id, today_str)

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

            consensus_prob = round(result.consensus_probability, 4)
            consensus_conf = round(result.consensus_confidence, 4)

            # Fetch real live market price for market_id
            live_mkt_price = await search_service.get_live_price(req.market_id, req.venue)

            analysis_record = {
                "market_id": req.market_id,
                "question": req.question,
                "venue": req.venue or "Kalshi (mirrors Robinhood Predict)",
                "consensus_probability": consensus_prob,
                "consensus_confidence": consensus_conf,
                "market_price_at_time": live_mkt_price,
                "explanation": result.explanation,
                "agent_breakdown": agent_breakdown,
                "tier_used": tier,
                "model_used": model_override
            }

            saved_record = await store.save_user_analysis(privy_user_id, analysis_record)
            
            # Log activity event
            await store.add_activity_event(
                privy_user_id=privy_user_id,
                event_type="analysis_run",
                event_detail=f"Ran 7-agent consensus for '{req.question[:40]}...'"
            )

            return saved_record

        except Exception as e:
            logger.error(f"[AnalysisRoutes] Custom analysis execution failed for '{privy_user_id}': {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Analysis pipeline execution error: {e}"
            )

    @router.get("/analyses/history")
    async def get_analysis_history(
        limit: int = Query(10, ge=1, le=50),
        offset: int = Query(0, ge=0),
        user: Dict[str, Any] = Depends(get_current_privy_user)
    ) -> List[Dict[str, Any]]:
        """
        GET /analyses/history?limit=10&offset=0
        Returns the authenticated user's past custom analyses ordered newest first.
        Powers the 'Track Record' tab.
        """
        privy_user_id = user["privy_user_id"]
        return await store.get_user_analyses(privy_user_id, limit=limit, offset=offset)

    return router
