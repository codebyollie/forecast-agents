"""
$FORAI Token Balance Checker & Holder Tier Evaluator.

Queries standard ERC-20 balanceOf via EVM JSON-RPC with in-memory TTL caching.
"""

from __future__ import annotations

import logging
import time
from typing import Dict, Tuple, Optional, List, Union
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

    async def fetch_onchain_balance(self, wallet_address: Union[str, List[str]]) -> float:
        """
        Executes an eth_call JSON-RPC request for ERC-20 balanceOf(address).
        `0x70a08231` is the function selector for `balanceOf(address)`.
        Supports querying a single address string or list of linked addresses.
        """
        addresses: List[str] = []
        if isinstance(wallet_address, str):
            addresses = [a.strip() for a in wallet_address.split(",") if a.strip()]
        elif isinstance(wallet_address, list):
            addresses = [str(a).strip() for a in wallet_address if a]

        total_balance = 0.0
        now = time.time()

        for addr in addresses:
            if not addr.startswith("0x") or len(addr) != 42:
                continue

            # Check cache
            cached = _BALANCE_CACHE.get(addr.lower())
            if cached and (now - cached[1]) < self.config.balance_cache_ttl_seconds:
                total_balance += cached[0]
                continue

            # Build ERC-20 balanceOf data: selector (4 bytes) + 32-byte padded address
            clean_addr = addr[2:].zfill(64).lower()
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

            req_headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Content-Type": "application/json"
            }

            async with httpx.AsyncClient(headers=req_headers) as client:
                try:
                    resp = await client.post(self.config.rpc_url, json=payload, timeout=10.0)
                    if resp.status_code == 200:
                        res_json = resp.json()
                        hex_val = res_json.get("result", "0x0")
                        if hex_val and hex_val != "0x":
                            raw_int = int(hex_val, 16)
                            # Standard 18 decimals ERC-20
                            balance = raw_int / 1e18
                            _BALANCE_CACHE[addr.lower()] = (balance, now)
                            total_balance += balance
                    else:
                        logger.warning(f"[BalanceChecker] RPC returned status {resp.status_code}")
                except Exception as e:
                    logger.warning(f"[BalanceChecker] Exception checking balance for {addr}: {e}")
                    if cached:
                        total_balance += cached[0]

        return total_balance

    def evaluate_holder_tier(self, balance: float) -> str:
        """
        Maps $FORAI token balance to holder tier ("Free", "Holder", "Pro Holder").
        """
        if balance >= self.config.pro_holder_threshold:
            return "Pro Holder"
        elif balance >= self.config.holder_threshold:
            return "Holder"
        return "Free"
