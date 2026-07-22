"""
API Routes for Forecast AI API Server.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from ..pipelines.forecast import ForecastPipeline
from ..polymarket.gamma import GammaClient
from ..config import ForecastConfig

router = APIRouter()

# Global reference to pipeline, will be set during server init
_pipeline: Optional[ForecastPipeline] = None

class PredictionRequest(BaseModel):
    question: str
    market_id: str = "custom_market"

class CalibrateRequest(BaseModel):
    agent_name: str
    outcome_correct: bool
    error_delta: float

def get_pipeline() -> ForecastPipeline:
    if _pipeline is None:
        raise HTTPException(status_code=500, detail="Forecast pipeline is not initialized.")
    return _pipeline

@router.get("/healthz")
async def healthz():
    return {"status": "ok", "message": "Forecast AI API Server active."}

@router.post("/predict")
async def predict(req: PredictionRequest, pipeline: ForecastPipeline = Depends(get_pipeline)):
    try:
        result = await pipeline.run_forecast(req.question, req.market_id)
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

@router.get("/markets")
async def get_markets(category: Optional[str] = None):
    try:
        gamma = GammaClient()
        markets = await gamma.list_markets(active=True, limit=20)
        if category:
            markets = [m for m in markets if m.category.lower() == category.lower()]
        
        return [
            {
                "id": m.id,
                "question": m.question,
                "slug": m.slug,
                "volume": m.volume,
                "liquidity": m.liquidity,
                "category": m.category,
                "end_date": m.end_date_iso
            } for m in markets
        ]
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
