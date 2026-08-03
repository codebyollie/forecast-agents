"""
API Routes for Forecast AI API Server.
"""

import time
from fastapi import APIRouter, HTTPException, Depends, Request, Query
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from ..pipelines.forecast import ForecastPipeline
from ..polymarket.gamma import GammaClient
from ..services.market_search import MarketSearchService

router = APIRouter()

# Global reference to pipeline, will be set during server init
_pipeline: Optional[ForecastPipeline] = None

_IP_RATE_LIMITS: Dict[str, List[float]] = {}
MAX_PER_HOUR = 50
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

class PredictionRequest(BaseModel):
    question: str
    market_id: str = "custom_market"
    model_override: Optional[str] = None
    facts_key: Optional[str] = None
    venue: Optional[str] = "Kalshi / Robinhood Predict"

class CalibrateRequest(BaseModel):
    agent_name: str
    outcome_correct: bool
    error_delta: float

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
    q: Optional[str] = Query(None, description="Optional keyword search"),
    search_service: MarketSearchService = Depends(get_search_service)
) -> Dict[str, Any]:
    """
    GET /markets/browse
    Full browse endpoint for markets with pagination, sorting, and unified categories.
    """
    check_ip_rate_limit(request)
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
    q: Optional[str] = Query(None, description="Query text to search across prediction markets"),
    limit: int = Query(10, ge=1, le=50),
    search_service: MarketSearchService = Depends(get_search_service)
) -> List[Dict[str, Any]]:
    """
    GET /markets/search?q=<query>
    Searches open prediction markets on Kalshi & Polymarket matching the query text.
    IP-based rate limited.
    """
    check_ip_rate_limit(request)
    return await search_service.search_markets(query=q, limit=limit)

@router.post("/predict")
async def predict(
    request: Request,
    req: PredictionRequest, 
    pipeline: ForecastPipeline = Depends(get_pipeline)
):
    check_ip_rate_limit(request)
    try:
        result = await pipeline.run_forecast(
            question=req.question, 
            market_id=req.market_id,
            is_public_feed=False,
            model_override=req.model_override,
            facts_key=req.facts_key
        )
        return {
            "market_id": result.market_id,
            "probability": result.probability,
            "confidence": {
                "score": result.confidence.score,
                "warnings": result.confidence.warnings
            },
            "reasoning": result.metadata.get("summary_reasoning", ""),
            "timestamp": result.timestamp.isoformat(),
            "individual_predictions": [
                {
                    "agent": p.agent_name,
                    "probability": p.probability,
                    "confidence": p.confidence.score,
                    "reasoning": p.reasoning
                } for p in result.individual_predictions
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/forecasts")
async def get_forecasts(pipeline: ForecastPipeline = Depends(get_pipeline)):
    try:
        return pipeline.memory_store.list_forecasts()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats")
async def get_stats(pipeline: ForecastPipeline = Depends(get_pipeline)):
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/reputation/calibrate")
async def calibrate_reputation(req: CalibrateRequest, pipeline: ForecastPipeline = Depends(get_pipeline)):
    try:
        pipeline.memory_store.update_agent_reputation(
            agent_name=req.agent_name,
            outcome_correct=req.outcome_correct,
            error_delta=req.error_delta
        )
        return {"status": "success", "new_reputation": pipeline.memory_store.get_agent_reputation(req.agent_name)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/config")
async def get_config(pipeline: ForecastPipeline = Depends(get_pipeline)):
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
            "wallet_address": cfg.polymarket.wallet_address,
            "builder_code": cfg.polymarket.builder_code
        },
        "agents": {
            name: {
                "enabled": a.enabled,
                "provider": a.provider,
                "weight": a.weight
            } for name, a in cfg.agents.items()
        }
    }
