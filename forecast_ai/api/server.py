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
from ..pipelines.forecast import ForecastPipeline
from ..config import ForecastConfig
from ..config_store import ConfigStore

logger = logging.getLogger(__name__)

class ApiServer:
    def __init__(self, config: ForecastConfig, pipeline: ForecastPipeline):
        self.config = config
        self.pipeline = pipeline
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

    def stop(self):
        if self._server_task:
            self._server_task.cancel()
            logger.info("API Server stopped.")

# Default top-level ASGI application instance for Uvicorn / Gunicorn / Railway / Render
# IMPORTANT: must use ConfigStore().load_config() — NOT ForecastConfig() directly —
# so that Railway/Render environment variables (OPENAI_API_KEY etc.) are applied.
_default_config = ConfigStore().load_config()
_default_pipeline = ForecastPipeline(_default_config)
_default_server = ApiServer(_default_config, _default_pipeline)
app = _default_server.app
