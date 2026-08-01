"""
Featured Market Service for Live Dashboard.

Manages saving and reading the owner-selected featured market forecast.
Persists forecast payload to Supabase table `featured_market` and persistent file `memory_data/featured_market.json`.
Provides zero-recomputation read serving for `GET /public/featured-market`.
"""

from __future__ import annotations

import logging
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import httpx
from ..config import SupabaseConfig

logger = logging.getLogger(__name__)

class FeaturedMarketService:
    def __init__(
        self,
        supabase_config: Optional[SupabaseConfig] = None,
        file_path: str = "memory_data/featured_market.json"
    ):
        self.supabase_config = supabase_config
        self.file_path = Path(file_path)
        self._ensure_store()

    def _ensure_store(self):
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

    def get_stored_featured_market(self) -> Optional[Dict[str, Any]]:
        """
        Reads stored featured market forecast payload.
        Returns dict if present, None if no featured market is set.
        """
        # 1. Try reading Supabase first if configured (primary source of truth)
        if self.supabase_config and self.supabase_config.url and self.supabase_config.key:
            endpoint = f"{self.supabase_config.url.rstrip('/')}/rest/v1/featured_market?id=eq.1"
            headers = {
                "apikey": self.supabase_config.key,
                "Authorization": f"Bearer {self.supabase_config.key}",
                "Accept": "application/json"
            }
            try:
                with httpx.Client() as client:
                    resp = client.get(endpoint, headers=headers, timeout=5.0)
                    if resp.status_code == 200:
                        data = resp.json()
                        if isinstance(data, list) and len(data) > 0:
                            payload = data[0].get("payload")
                            if isinstance(payload, dict) and payload.get("question"):
                                return payload
            except Exception as e:
                logger.warning(f"[FeaturedMarketService] Failed to read Supabase featured_market: {e}")

        # 2. Fall back to reading persistent JSON file
        try:
            if self.file_path.exists():
                content = self.file_path.read_text(encoding="utf-8")
                if content.strip():
                    return json.loads(content)
        except Exception as e:
            logger.warning(f"[FeaturedMarketService] Failed to read file store: {e}")

        return None

    def save_featured_market(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Saves updated featured market forecast payload. Overwrites previous featured market.
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        payload["featured_at"] = now_iso

        # Write file store
        try:
            self.file_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            logger.error(f"[FeaturedMarketService] Failed to write file store: {e}")

        # Write Supabase store if configured
        if self.supabase_config and self.supabase_config.url and self.supabase_config.key:
            endpoint = f"{self.supabase_config.url.rstrip('/')}/rest/v1/featured_market"
            headers = {
                "apikey": self.supabase_config.key,
                "Authorization": f"Bearer {self.supabase_config.key}",
                "Content-Type": "application/json",
                "Prefer": "resolution=merge-duplicates,return=representation"
            }
            db_record = {
                "id": 1,
                "market_id": payload.get("market_id", ""),
                "question": payload.get("question", ""),
                "payload": payload,
                "updated_at": now_iso
            }
            try:
                with httpx.Client() as client:
                    client.post(endpoint, headers=headers, json=db_record, timeout=5.0)
            except Exception as e:
                logger.error(f"[FeaturedMarketService] Failed to upsert Supabase featured_market: {e}")

        return payload
