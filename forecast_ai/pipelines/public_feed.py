"""
Public Read-Only Forecast Feed Runner.

Executes scheduled forecasts for curated topics, manages public_feed.json,
implements spend guards, and provides summarized agent breakdowns.
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional

from ..config import ForecastConfig
from ..pipelines.forecast import ForecastPipeline
from ..public_feed_topics import CURATED_TOPICS, CuratedTopic, get_topic_by_id
from ..providers import ProviderError

logger = logging.getLogger(__name__)

# Estimated cost per individual LLM call for spend guard calculations
ESTIMATED_COST_PER_LLM_CALL_USD = 0.0015

class PublicFeedRunner:
    def __init__(self, config: ForecastConfig, forecast_pipeline: Optional[ForecastPipeline] = None):
        self.config = config
        self.forecast_pipeline = forecast_pipeline or ForecastPipeline(config)
        self.store_dir = Path(config.memory.store_dir)
        self.store_file = self.store_dir / "public_feed.json"
        self._ensure_store_dir()

    def _ensure_store_dir(self):
        self.store_dir.mkdir(parents=True, exist_ok=True)
        if not self.store_file.exists():
            self._save_store({"monthly_spend_usd": 0.0, "topics": {}})

    def _load_store(self) -> Dict[str, Any]:
        try:
            if self.store_file.exists():
                return json.loads(self.store_file.read_text(encoding="utf-8"))
        except Exception as e:
            logger.error(f"[PublicFeedRunner] Failed to read public_feed.json: {e}")
        return {"monthly_spend_usd": 0.0, "topics": {}}

    def _save_store(self, data: Dict[str, Any]):
        try:
            self.store_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            logger.error(f"[PublicFeedRunner] Failed to write public_feed.json: {e}")

    def get_monthly_spend(self) -> float:
        store = self._load_store()
        return float(store.get("monthly_spend_usd", 0.0))

    def reset_monthly_spend_if_new_month(self):
        store = self._load_store()
        last_reset = store.get("last_spend_reset_month", "")
        current_month = datetime.now(timezone.utc).strftime("%Y-%m")
        if last_reset != current_month:
            store["monthly_spend_usd"] = 0.0
            store["last_spend_reset_month"] = current_month
            self._save_store(store)

    def is_spend_guard_triggered(self) -> bool:
        self.reset_monthly_spend_if_new_month()
        limit = getattr(self.config.server, "public_feed_monthly_budget_usd", 50.0)
        current = self.get_monthly_spend()
        if current >= limit:
            logger.warning(
                f"[PublicFeedRunner] SPEND GUARD TRIGGERED! Current monthly spend (${current:.2f}) "
                f"exceeds limit (${limit:.2f}). Pausing public feed updates."
            )
            return True
        return False

    def _record_spend(self, llm_calls_count: int):
        cost = llm_calls_count * ESTIMATED_COST_PER_LLM_CALL_USD
        store = self._load_store()
        current = float(store.get("monthly_spend_usd", 0.0))
        store["monthly_spend_usd"] = round(current + cost, 4)
        self._save_store(store)

    def _summarize_reasoning(self, full_reasoning: str) -> str:
        """Truncate reasoning to 1-2 clean sentences."""
        if not full_reasoning:
            return "No reasoning provided."
        sentences = [s.strip() for s in full_reasoning.replace("\n", " ").split(".") if s.strip()]
        if len(sentences) >= 2:
            return f"{sentences[0]}. {sentences[1]}."
        elif len(sentences) == 1:
            return f"{sentences[0]}."
        return full_reasoning[:180] + "..."

    async def update_topic(self, topic: CuratedTopic) -> bool:
        """
        Runs forecast pipeline for a single topic and updates store.
        Returns True if successful, False if failed.
        """
        if self.is_spend_guard_triggered():
            return False

        logger.info(f"[PublicFeedRunner] Refreshing forecast for topic '{topic.topic_id}' ({topic.tier} tier)...")
        
        try:
            # Execute pipeline with public feed flag (excludes ollama fallback, skips user memory logging)
            result = await self.forecast_pipeline.run_forecast(
                question=topic.question,
                market_id=topic.topic_id,
                is_public_feed=True
            )

            # Record LLM call count for spend guard
            num_agent_calls = len(result.predictions)
            self._record_spend(num_agent_calls)

            # Extract per-agent breakdown (summary only)
            agent_breakdown = []
            for pred in result.predictions:
                agent_breakdown.append({
                    "agent_name": pred.agent_name,
                    "probability": round(pred.probability, 4),
                    "confidence": round(pred.confidence.score, 4),
                    "reasoning_summary": self._summarize_reasoning(pred.reasoning),
                    "warnings": pred.confidence.warnings
                })

            # Mock or fetch venue market price (e.g. 0.48 or 0.65 for market vs consensus delta)
            market_price = 0.50
            if "fed" in topic.topic_id:
                market_price = 0.62
            elif "cpi" in topic.topic_id:
                market_price = 0.44
            elif "btc" in topic.topic_id:
                market_price = 0.78
            elif "eth" in topic.topic_id:
                market_price = 0.55
            elif "starship" in topic.topic_id:
                market_price = 0.70
            elif "sol" in topic.topic_id:
                market_price = 0.85

            consensus_prob = round(result.consensus_probability, 4)
            price_delta = round(consensus_prob - market_price, 4)

            payload = {
                "topic_id": topic.topic_id,
                "question": topic.question,
                "category": topic.category,
                "tier": topic.tier,
                "refresh_interval_hours": topic.refresh_interval_hours,
                "source_venue": topic.source_venue,
                "market_ticker": topic.market_ticker,
                "consensus_probability": consensus_prob,
                "market_price": market_price,
                "price_delta": price_delta,
                "consensus_confidence": round(result.consensus_confidence, 4),
                "explanation": self._summarize_reasoning(result.explanation),
                "agent_breakdown": agent_breakdown,
                "last_updated": datetime.now(timezone.utc).isoformat()
            }

            store = self._load_store()
            store["topics"][topic.topic_id] = payload
            self._save_store(store)
            logger.info(f"[PublicFeedRunner] Topic '{topic.topic_id}' updated successfully. Consensus: {consensus_prob}")
            return True

        except Exception as e:
            logger.error(
                f"[PublicFeedRunner] Topic '{topic.topic_id}' forecast update failed: {e}. "
                f"Preserving last-known-good state.",
                exc_info=True
            )
            return False

    async def refresh_all_due_topics(self):
        """
        Iterates all curated topics, checking tier refresh intervals.
        Executes update_topic for due topics cleanly.
        """
        if self.is_spend_guard_triggered():
            return

        store = self._load_store()
        now = datetime.now(timezone.utc)

        for topic in CURATED_TOPICS:
            existing = store.get("topics", {}).get(topic.topic_id)
            due = True

            if existing and "last_updated" in existing:
                try:
                    last_updated_dt = datetime.fromisoformat(existing["last_updated"])
                    elapsed_hours = (now - last_updated_dt).total_seconds() / 3600.0
                    if elapsed_hours < topic.refresh_interval_hours:
                        due = False
                except Exception:
                    due = True

            if due:
                await self.update_topic(topic)

    def get_public_forecasts(self) -> List[Dict[str, Any]]:
        store = self._load_store()
        topics_dict = store.get("topics", {})
        result = []
        for topic in CURATED_TOPICS:
            if topic.topic_id in topics_dict:
                result.append(topics_dict[topic.topic_id])
            else:
                # Fallback initial record if not yet generated
                result.append({
                    "topic_id": topic.topic_id,
                    "question": topic.question,
                    "category": topic.category,
                    "tier": topic.tier,
                    "refresh_interval_hours": topic.refresh_interval_hours,
                    "source_venue": topic.source_venue,
                    "market_ticker": topic.market_ticker,
                    "consensus_probability": 0.5,
                    "market_price": 0.5,
                    "price_delta": 0.0,
                    "consensus_confidence": 0.5,
                    "explanation": "Initial public feed topic registered. Update pending.",
                    "agent_breakdown": [],
                    "last_updated": datetime.now(timezone.utc).isoformat()
                })
        return result

    def get_public_forecast_by_id(self, topic_id: str) -> Optional[Dict[str, Any]]:
        topic_cfg = get_topic_by_id(topic_id)
        if not topic_cfg:
            return None
        forecasts = self.get_public_forecasts()
        for f in forecasts:
            if f["topic_id"] == topic_id:
                return f
        return None
