"""
FastAPI Server for Forecast AI.
"""

import asyncio
import logging
from typing import Optional
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from . import routes
from .public_routes import create_public_router
from ..config import ForecastConfig
from ..pipelines.forecast import ForecastPipeline
from ..pipelines.public_feed import PublicFeedRunner

logger = logging.getLogger(__name__)

class ApiServer:
    def __init__(self, config: ForecastConfig, pipeline: ForecastPipeline):
        self.config = config
        self.pipeline = pipeline
        self.public_runner = PublicFeedRunner(config, forecast_pipeline=pipeline)
        self.app = FastAPI(title="Forecast AI API", version="0.2.0")
        self._server_task: Optional[asyncio.Task] = None
        self._init_app()

    def _init_app(self):
        # Enable CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Set pipeline reference in routes
        routes._pipeline = self.pipeline
        self.app.include_router(routes.router)

        # Mount Public Read-Only Router
        public_router = create_public_router(self.public_runner)
        self.app.include_router(public_router)

        # Mount Authenticated Profile Router (/profile/me)
        from .profile_routes import create_profile_router
        profile_router = create_profile_router(self.config)
        self.app.include_router(profile_router)

    async def start(self):
        """
        Starts the API server asynchronously and launches the public feed update loop.
        """
        host = self.config.server.host
        port = self.config.server.port
        logger.info(f"Starting API Server on {host}:{port}...")

        config = uvicorn.Config(
            app=self.app,
            host=host,
            port=port,
            log_level="info",
            loop="asyncio"
        )
        server = uvicorn.Server(config)
        self._server_task = asyncio.create_task(server.serve())

        # Launch background public feed update loop
        self._feed_task = asyncio.create_task(self._run_public_feed_loop())

    async def _run_public_feed_loop(self):
        """
        Background loop that refreshes due public feed topics on startup
        and periodically every 15 minutes.
        """
        logger.info("[ApiServer] Starting Public Feed background runner loop...")
        await asyncio.sleep(2.0)  # Short delay for server bind
        while True:
            try:
                await self.public_runner.refresh_all_due_topics()
            except Exception as e:
                logger.error(f"[ApiServer] Error in public feed update loop: {e}")
            await asyncio.sleep(900)  # Check every 15 minutes

    def stop(self):
        if self._feed_task:
            self._feed_task.cancel()
        if self._server_task:
            self._server_task.cancel()
            logger.info("API Server stopped.")
