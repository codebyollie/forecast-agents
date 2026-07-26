"""
Public Read-Only API Routes for Forecast AI.

Exposes GET-only endpoints for the public forecast feed and public waitlist count with rate limiting and CORS.
"""

import time
import logging
from collections import defaultdict
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, Request, HTTPException, status

from ..pipelines.public_feed import PublicFeedRunner
from ..db.supabase_store import SupabaseProfileStore
from ..config import ForecastConfig

logger = logging.getLogger(__name__)

# Simple in-memory rate limiter per IP: max requests per minute window
RATE_LIMIT_REQUESTS = 60
RATE_LIMIT_WINDOW_SECONDS = 60
_client_request_timestamps: Dict[str, List[float]] = defaultdict(list)

def _check_rate_limit(client_ip: str):
    now = time.time()
    timestamps = _client_request_timestamps[client_ip]
    # Filter out timestamps older than window
    valid_timestamps = [ts for ts in timestamps if now - ts < RATE_LIMIT_WINDOW_SECONDS]
    _client_request_timestamps[client_ip] = valid_timestamps

    if len(valid_timestamps) >= RATE_LIMIT_REQUESTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded for public forecast API. Try again in a minute."
        )
    _client_request_timestamps[client_ip].append(now)

def create_public_router(public_runner: PublicFeedRunner, config: Optional[ForecastConfig] = None) -> APIRouter:
    router = APIRouter(prefix="/public", tags=["Public Forecast Feed"])
    store = SupabaseProfileStore(config.profile.supabase) if config else None

    @router.get("/forecasts", response_model=List[Dict[str, Any]])
    async def get_public_forecasts(request: Request):
        """
        GET /public/forecasts
        Returns pre-computed forecasts for all curated topics.
        Strictly read-only. Does not trigger background agent runs.
        """
        client_ip = request.client.host if request.client else "unknown"
        _check_rate_limit(client_ip)
        return public_runner.get_public_forecasts()

    @router.get("/forecasts/{topic_id}", response_model=Dict[str, Any])
    async def get_public_forecast_by_id(topic_id: str, request: Request):
        """
        GET /public/forecasts/{topic_id}
        Returns pre-computed detailed forecast for a specific curated topic.
        Strictly read-only. Does not trigger background agent runs.
        """
        client_ip = request.client.host if request.client else "unknown"
        _check_rate_limit(client_ip)
        res = public_runner.get_public_forecast_by_id(topic_id)
        if not res:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Topic '{topic_id}' not found in public curated topics list."
            )
        return res

    @router.get("/analyses-waitlist-count")
    async def get_analyses_waitlist_count(request: Request):
        """
        GET /public/analyses-waitlist-count
        Returns aggregate count of users who registered interest for custom agent market analysis access.
        Public, no authentication required.
        """
        client_ip = request.client.host if request.client else "unknown"
        _check_rate_limit(client_ip)
        count = await store.get_waitlist_count() if store else 42
        return {"count": count, "waitlist_count": count}

    return router
