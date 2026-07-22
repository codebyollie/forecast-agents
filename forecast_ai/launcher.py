"""
Forecast AI Service Launcher.

Orchestrates starting/stopping the Watch Pipeline and API server.
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import threading
from pathlib import Path
from typing import Optional

from .config import ForecastConfig
from .config_store import ConfigStore
from .pipelines.forecast import ForecastPipeline
from .pipelines.watch import WatchPipeline
from .api.server import ApiServer

logger = logging.getLogger(__name__)

_PID_FILE = Path.home() / ".forecast_ai" / "forecast.pid"

class ForecastLauncher:
    def __init__(self, config_store: ConfigStore):
        self.cs = config_store
        self._watch_task: Optional[asyncio.Task] = None
        self._server: Optional[ApiServer] = None
        self._stop_event = threading.Event()

    async def start(self, category: str = "crypto", run_server: bool = True):
        cfg = self.cs.load_config()
        logger.info("[Launcher] Starting Forecast AI services...")
        self._write_pid()
        self._setup_signal_handlers()

        # Initialize Pipeline
        forecast_pipeline = ForecastPipeline(cfg)
        self.watch_pipeline = WatchPipeline(cfg, forecast_pipeline)

        # Launch Watch Pipeline
        self._watch_task = asyncio.create_task(
            self.watch_pipeline.watch_markets(category=category, interval_seconds=120)
        )

        # Launch server if enabled
        if run_server:
            self._server = ApiServer(cfg, forecast_pipeline)
            await self._server.start()

        # Keep running
        while not self._stop_event.is_set():
            await asyncio.sleep(1.0)

    def stop(self):
        self._stop_event.set()
        if self._watch_task:
            self._watch_task.cancel()
        if self._server:
            self._server.stop()
        _PID_FILE.unlink(missing_ok=True)
        logger.info("[Launcher] Stopped all Forecast AI services.")

    def _write_pid(self):
        _PID_FILE.parent.mkdir(parents=True, exist_ok=True)
        _PID_FILE.write_text(str(os.getpid()))

    def _setup_signal_handlers(self):
        def _handler(signum, frame):
            logger.info("[Launcher] Signal %s received. Stopping...", signum)
            self.stop()

        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                signal.signal(sig, _handler)
            except (OSError, ValueError):
                pass
