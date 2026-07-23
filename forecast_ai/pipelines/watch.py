"""
Watch Pipeline.

Regularly monitors active prediction markets and updates public feed & forecasts.
"""

import asyncio
import logging
from typing import List
from ..config import ForecastConfig
from .forecast import ForecastPipeline
from .public_feed import PublicFeedRunner
from ..polymarket.gamma import GammaClient
from ..kalshi.client import KalshiClient

logger = logging.getLogger(__name__)

class WatchPipeline:
    def __init__(self, config: ForecastConfig, forecast_pipeline: ForecastPipeline):
        self.config = config
        self.forecast_pipeline = forecast_pipeline
        self.public_feed_runner = PublicFeedRunner(config, forecast_pipeline=forecast_pipeline)
        self.gamma_client = GammaClient(config.polymarket.gamma_api_url)
        self.kalshi_client = KalshiClient(config.kalshi.api_base_url)
        self._running = False

    async def watch_markets(self, category: str = "crypto", interval_seconds: int = 300):
        self._running = True
        logger.info(f"WatchPipeline started for category: {category} (Interval: {interval_seconds}s)")
        
        while self._running:
            try:
                # 1. Update Public Feed topics due for tiered refresh
                logger.info("[WatchPipeline] Checking public feed topic refresh status...")
                await self.public_feed_runner.refresh_all_due_topics()

                # 2. Fetch active markets from Polymarket & Kalshi for general watch
                pm_markets = await self.gamma_client.list_markets(active=True, limit=5)
                kalshi_markets = await self.kalshi_client.fetch_markets(limit=5)
                
                tasks = []
                for market in pm_markets:
                    tasks.append(self.forecast_pipeline.run_forecast(market.question, market.id))
                for km in kalshi_markets:
                    tasks.append(self.forecast_pipeline.run_forecast(km.title, km.ticker))

                if tasks:
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    for res in results:
                        if not isinstance(res, Exception):
                            logger.info(f"Forecast updated: Prob={res.probability * 100:.1f}%, Conf={res.confidence.score * 100:.1f}%")

            except Exception as e:
                logger.error(f"Error in watch loop: {e}")

            await asyncio.sleep(interval_seconds)

    def stop(self):
        self._running = False
