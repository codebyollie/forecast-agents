"""
API Routes for Forecast AI API Server.
"""

import os
import time
import secrets
import logging
from fastapi import APIRouter, HTTPException, Depends, Request, Query
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from ..pipelines.forecast import ForecastPipeline
from ..polymarket.gamma import GammaClient
from ..services.market_search import MarketSearchService

router = APIRouter()
logger = logging.getLogger(__name__)

# Global reference to pipeline, will be set during server init
_pipeline: Optional[ForecastPipeline] = None

_IP_RATE_LIMITS: Dict[str, List[float]] = {}
MAX_PER_HOUR = max(1, int(os.getenv("PUBLIC_RATE_LIMIT_PER_HOUR", "50")))
WINDOW_SECONDS = 3600.0

def check_ip_rate_limit(request: Request):
    ip = request.client.host if request.client else "unknown"
    now = time.time()
    timestamps = _IP_RATE_LIMITS.setdefault(ip, [])
    _IP_RATE_LIMITS[ip] = [t for t in timestamps if now - t < WINDOW_SECONDS]
    if len(_IP_RATE_LIMITS[ip]) >= MAX_PER_HOUR:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Maximum {MAX_PER_HOUR} requests per hour per IP."
        )
    _IP_RATE_LIMITS[ip].append(now)

def require_server_api_key(request: Request) -> bool:
    """Protect the private production deployment while keeping OSS self-hosting easy."""
    expected = ""
    if _pipeline is not None:
        expected = getattr(_pipeline.config.server, "api_key", "") or ""
    if not expected:
        return False

    provided = request.headers.get("x-api-key", "")
    authorization = request.headers.get("authorization", "")
    if not provided and authorization.lower().startswith("bearer "):
        provided = authorization[7:].strip()
    if not provided or not secrets.compare_digest(provided, expected):
        raise HTTPException(status_code=401, detail="Invalid agents API key.")
    return True

def enforce_request_access(request: Request) -> bool:
    """Authenticate production service calls and rate-limit only public OSS traffic."""
    is_authenticated_service = require_server_api_key(request)
    if not is_authenticated_service:
        check_ip_rate_limit(request)
    return is_authenticated_service


def require_private_access(request: Request) -> None:
    """Keep history, configuration, and reputation endpoints private."""
    expected = ""
    if _pipeline is not None:
        expected = getattr(_pipeline.config.server, "api_key", "") or ""
    if not expected:
        raise HTTPException(
            status_code=503,
            detail="SERVER_API_KEY must be configured to use this endpoint.",
        )
    require_server_api_key(request)

class PredictionRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    market_id: str = Field(default="custom_market", max_length=512)
    model_override: Optional[str] = Field(default=None, max_length=128)
    venue: Optional[str] = Field(default=None, max_length=64)
    source_venue: Optional[str] = Field(default=None, max_length=64)

class CalibrateRequest(BaseModel):
    agent_name: str = Field(min_length=1, max_length=64)
    outcome_correct: bool
    error_delta: float = Field(ge=0.0, le=1.0)

def get_pipeline() -> ForecastPipeline:
    if _pipeline is None:
        raise HTTPException(status_code=500, detail="Forecast pipeline is not initialized.")
    return _pipeline

def get_search_service(pipeline: ForecastPipeline = Depends(get_pipeline)) -> MarketSearchService:
    return MarketSearchService(
        kalshi_base_url=pipeline.config.kalshi.api_base_url,
        gamma_api_url=pipeline.config.polymarket.gamma_api_url
    )

AGENT_METADATA = [
    {"id": "news", "name": "News Agent", "icon": "ti-news", "color": "blue"},
    {"id": "social", "name": "Social Agent", "icon": "ti-message-circle", "color": "pink"},
    {"id": "reddit", "name": "Reddit Agent", "icon": "ti-brand-reddit", "color": "coral"},
    {"id": "research", "name": "Research Agent", "icon": "ti-microscope", "color": "purple"},
    {"id": "macro", "name": "Macro Agent", "icon": "ti-building-bank", "color": "green"},
    {"id": "onchain", "name": "On-Chain Agent", "icon": "ti-link", "color": "teal"},
    {"id": "market", "name": "Market Agent", "icon": "ti-chart-candle", "color": "amber"}
]

@router.get("/healthz")
async def healthz():
    return {"status": "ok", "message": "Forecast AI API Server active."}

@router.get("/agents/meta")
async def get_agents_metadata():
    """
    Returns static metadata for all 7 agents,
    including Tabler icon identifiers and brand color pairings.
    """
    return AGENT_METADATA

@router.get("/markets/browse")
async def browse_markets_route(
    request: Request,
    venue: str = Query("all", description="Venue filter: kalshi, polymarket, or all"),
    category: Optional[str] = Query(None, description="Category filter"),
    sort: str = Query("volume", description="Sort by: volume, ending_soon, newest"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(24, ge=1, le=50, description="Page size"),
    q: Optional[str] = Query(None, max_length=200, description="Optional keyword search"),
    search_service: MarketSearchService = Depends(get_search_service)
) -> Dict[str, Any]:
    """
    GET /markets/browse
    Full browse endpoint for markets with pagination, sorting, and unified categories.
    """
    enforce_request_access(request)
    return await search_service.browse_markets(
        venue=venue.lower(),
        category=category,
        sort=sort.lower(),
        page=page,
        page_size=page_size,
        q=q
    )

@router.get("/markets/search")
async def search_markets(
    request: Request,
    q: Optional[str] = Query(None, max_length=200, description="Query text to search across prediction markets"),
    limit: int = Query(10, ge=1, le=50),
    search_service: MarketSearchService = Depends(get_search_service)
) -> List[Dict[str, Any]]:
    """
    GET /markets/search?q=<query>
    Searches open prediction markets on Kalshi & Polymarket matching the query text.
    IP-based rate limited.
    """
    enforce_request_access(request)
    return await search_service.search_markets(query=q, limit=limit)

@router.post("/predict")
async def predict(
    request: Request,
    req: PredictionRequest, 
    pipeline: ForecastPipeline = Depends(get_pipeline)
):
    is_authenticated = enforce_request_access(request)
    if req.model_override and not is_authenticated:
        raise HTTPException(
            status_code=403,
            detail="Model overrides require SERVER_API_KEY authentication.",
        )
    try:
        selected_venue = req.source_venue or req.venue
        result = await pipeline.run_forecast(
            question=req.question, 
            market_id=req.market_id,
            model_override=req.model_override,
            venue=selected_venue,
        )
        agent_breakdown = [
            {
                "id": p.agent_name,
                "name": p.agent_name,
                "agent": p.agent_name,
                "probability": p.probability,
                "confidence": p.confidence.score,
                "reasoning": p.reasoning,
                "summary": p.summary,
                "key_drivers": p.key_drivers,
                "counter_signals": p.counter_signals,
                "uncertainties": p.uncertainties,
                "watch_next": p.watch_next,
                "warnings": p.confidence.warnings,
                "citations": p.citations,
                "providers": p.research_providers,
                "provider_insights": p.provider_insights,
                "provider_statuses": p.provider_statuses,
            }
            for p in result.individual_predictions
        ]
        return {
            "question": req.question,
            "market_id": result.market_id,
            "venue": selected_venue,
            "source_venue": selected_venue,
            "probability": result.probability,
            "recommendation": "YES" if result.probability >= 0.5 else "NO",
            "confidence": {
                "score": result.confidence.score,
                "warnings": result.confidence.warnings
            },
            "reasoning": result.metadata.get("summary_reasoning", ""),
            "reasoning_trace": {
                "agent_contributions": result.reasoning_trace.agent_contributions,
                "aggregation_steps": result.reasoning_trace.aggregation_steps,
                "conflicts_resolved": result.reasoning_trace.conflicts_resolved,
            },
            "market_context": result.metadata.get("market_context", []),
            "timestamp": result.timestamp.isoformat(),
            "agent_breakdown": agent_breakdown,
            "individual_predictions": agent_breakdown,
        }
    except Exception:
        logger.exception("Forecast execution failed")
        raise HTTPException(status_code=500, detail="Forecast execution failed. Check server logs.")

@router.get("/forecasts")
async def get_forecasts(request: Request, pipeline: ForecastPipeline = Depends(get_pipeline)):
    require_private_access(request)
    try:
        return pipeline.memory_store.list_forecasts()
    except Exception:
        logger.exception("Could not read forecast history")
        raise HTTPException(status_code=500, detail="Could not read forecast history.")

@router.get("/stats")
async def get_stats(request: Request, pipeline: ForecastPipeline = Depends(get_pipeline)):
    require_private_access(request)
    try:
        forecasts = pipeline.memory_store.list_forecasts()
        reputations = pipeline.memory_store.get_agent_reputations()
        
        avg_conf = 0.0
        if forecasts:
            avg_conf = sum(f.get("confidence", {}).get("score", 0.5) for f in forecasts) / len(forecasts)

        return {
            "total_forecasts": len(forecasts),
            "average_confidence": avg_conf,
            "agent_reputations": reputations
        }
    except Exception:
        logger.exception("Could not compute forecast statistics")
        raise HTTPException(status_code=500, detail="Could not compute forecast statistics.")

@router.post("/reputation/calibrate")
async def calibrate_reputation(request: Request, req: CalibrateRequest, pipeline: ForecastPipeline = Depends(get_pipeline)):
    require_private_access(request)
    try:
        pipeline.memory_store.update_agent_reputation(
            agent_name=req.agent_name,
            outcome_correct=req.outcome_correct,
            error_delta=req.error_delta
        )
        return {"status": "success", "new_reputation": pipeline.memory_store.get_agent_reputation(req.agent_name)}
    except Exception:
        logger.exception("Could not update agent reputation")
        raise HTTPException(status_code=500, detail="Could not update agent reputation.")

@router.get("/config")
async def get_config(request: Request, pipeline: ForecastPipeline = Depends(get_pipeline)):
    require_private_access(request)
    # Redact sensitive keys
    cfg = pipeline.config
    providers_redacted = {}
    for name, p in cfg.providers.items():
        providers_redacted[name] = {
            "provider": p.provider,
            "model_id": p.model_id,
            "api_key": "********" if p.api_key else ""
        }
    return {
        "default_provider": cfg.default_provider,
        "providers": providers_redacted,
        "polymarket": {
            "gamma_api_url": cfg.polymarket.gamma_api_url,
            "clob_api_url": cfg.polymarket.clob_api_url,
            "wallet_address": getattr(cfg.polymarket, "wallet_address", ""),
            "builder_code": getattr(cfg.polymarket, "builder_code", "")
        },
        "agents": {
            name: {
                "enabled": a.enabled,
                "provider": a.provider,
                "weight": a.weight
            } for name, a in cfg.agents.items()
        }
    }
