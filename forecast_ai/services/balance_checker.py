"""
$FORAI Token Balance Checker & Holder Tier Evaluator.

Queries standard ERC-20 balanceOf via EVM JSON-RPC with in-memory TTL caching.
"""

from __future__ import annotations

import logging
import time
from typing import Dict, Tuple, Optional
import httpx
from ..config import HolderTierConfig

logger = logging.getLogger(__name__)

# Cache structure: wallet_address -> (balance, timestamp)
_BALANCE_CACHE: Dict[str, Tuple[float, float]] = {}

class BalanceChecker:
    def __init__(self, config: HolderTierConfig):
        self.config = config

    def clear_cache(self):
        """Clears in-memory balance cache."""
        _BALANCE_CACHE.clear()

    async def fetch_onchain_balance(self, wallet_address: str) -> float:
        """
        Executes an eth_call JSON-RPC request for ERC-20 balanceOf(address).
        `0x70a08231` is the function selector for `balanceOf(address)`.
        """
        if not wallet_address or not wallet_address.startswith("0x") or len(wallet_address) != 42:
            return 0.0

        # Check cache
        now = time.time()
        cached = _BALANCE_CACHE.get(wallet_address.lower())
        if cached:
            cached_bal, cached_time = cached
            if (now - cached_time) < self.config.balance_cache_ttl_seconds:
                return cached_bal

        # Build ERC-20 balanceOf data: selector (4 bytes) + 32-byte padded address
        clean_addr = wallet_address[2:].zfill(64).lower()
        call_data = f"0x70a08231{clean_addr}"

        payload = {
            "jsonrpc": "2.0",
            "method": "eth_call",
            "params": [
                {
                    "to": self.config.token_contract_address,
                    "data": call_data
                },
                "latest"
            ],
            "id": 1
        }

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(self.config.rpc_url, json=payload, timeout=10.0)
                if resp.status_code == 200:
                    res_json = resp.json()
                    hex_val = res_json.get("result", "0x0")
                    if hex_val and hex_val != "0x":
                        raw_int = int(hex_val, 16)
                        # Standard 18 decimals ERC-20
                        balance = raw_int / 1e18
                        _BALANCE_CACHE[wallet_address.lower()] = (balance, now)
                        return balance
                else:
                    logger.warning(f"[BalanceChecker] RPC returned status {resp.status_code}")
            except Exception as e:
                logger.warning(f"[BalanceChecker] Exception checking balance for {wallet_address}: {e}")

        # Fallback to cache if RPC fails
        if cached:
            return cached[0]
        return 0.0

    def evaluate_holder_tier(self, balance: float) -> str:
        """
        Maps $FORAI token balance to holder tier ("Free", "Holder", "Pro Holder").
        """
        if balance >= self.config.pro_holder_threshold:
            return "Pro Holder"
        elif balance >= self.config.holder_threshold:
            return "Holder"
        return "Free"
