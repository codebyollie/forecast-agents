"""
WebSocket API implementation for Polymarket.

Allows real-time connection to the Polymarket Market and User WS feeds.
"""

import asyncio
import json
import logging
from typing import Callable, List, Optional

logger = logging.getLogger(__name__)

class PolymarketWebSocket:
    def __init__(self, uri: str = "wss://clob.polymarket.com/ws"):
        self.uri = uri
        self._ws = None
        self._running = False

    async def connect_and_listen(
        self,
        token_ids: List[str],
        on_message_callback: Callable[[dict], None],
        channels: Optional[List[str]] = None
    ):
        """
        Connect to CLOB WebSocket and subscribe to specific channels (e.g. market, user).
        """
        try:
            import websockets
        except ImportError as e:
            raise ImportError(
                "The websockets package is required for real-time market data. "
                "Install it with: pip install websockets"
            ) from e

        if channels is None:
            channels = ["market"]

        self._running = True
        while self._running:
            try:
                async with websockets.connect(self.uri) as ws:
                    self._ws = ws
                    logger.info("Connected to Polymarket WebSocket feed.")
                    
                    # Subscribe payload
                    subscribe_payload = {
                        "type": "subscribe",
                        "channels": channels,
                        "token_ids": token_ids
                    }
                    await ws.send(json.dumps(subscribe_payload))
                    
                    while self._running:
                        msg_str = await ws.recv()
                        msg_data = json.loads(msg_str)
                        on_message_callback(msg_data)
                        
            except websockets.exceptions.ConnectionClosed:
                logger.warning("Polymarket WebSocket disconnected. Retrying in 5 seconds...")
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                await asyncio.sleep(5)

    def stop(self):
        self._running = False
        if self._ws:
            # Schedule closure
            asyncio.create_task(self._ws.close())
