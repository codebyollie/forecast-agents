"""
Supabase Database Store for User Profiles.

Manages user profile persistence in Supabase Postgres (`profiles` table) via PostgREST REST API.
Falls back gracefully to an in-memory store if Supabase credentials are not configured.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import httpx
from ..config import SupabaseConfig

logger = logging.getLogger(__name__)

# Fallback in-memory profile store when Supabase env vars are missing
_IN_MEMORY_PROFILES: Dict[str, Dict[str, Any]] = {}

class SupabaseProfileStore:
    def __init__(self, config: SupabaseConfig):
        self.config = config
        self.url = config.url.rstrip("/") if config.url else ""
        self.key = config.key
        self.table = config.table_name or "profiles"

    @property
    def is_configured(self) -> bool:
        return bool(self.url and self.key)

    async def get_profile(self, privy_user_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch a user profile by privy_user_id.
        Returns dict if found, None if not found.
        """
        if not self.is_configured:
            return _IN_MEMORY_PROFILES.get(privy_user_id)

        endpoint = f"{self.url}/rest/v1/{self.table}?privy_user_id=eq.{privy_user_id}"
        headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Accept": "application/json"
        }

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(endpoint, headers=headers, timeout=10.0)
                if resp.status_code == 200:
                    data = resp.json()
                    if isinstance(data, list) and len(data) > 0:
                        return data[0]
                    return None
                else:
                    logger.warning(f"[SupabaseStore] Failed to fetch profile: HTTP {resp.status_code} {resp.text}")
                    return _IN_MEMORY_PROFILES.get(privy_user_id)
            except Exception as e:
                logger.error(f"[SupabaseStore] Exception fetching profile for '{privy_user_id}': {e}")
                return _IN_MEMORY_PROFILES.get(privy_user_id)

    async def upsert_profile(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create or update a user profile in the database.
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        if "created_at" not in profile or not profile["created_at"]:
            profile["created_at"] = now_iso
        profile["updated_at"] = now_iso

        privy_user_id = profile["privy_user_id"]
        _IN_MEMORY_PROFILES[privy_user_id] = dict(profile)

        if not self.is_configured:
            return _IN_MEMORY_PROFILES[privy_user_id]

        endpoint = f"{self.url}/rest/v1/{self.table}"
        headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates,return=representation"
        }

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(endpoint, headers=headers, json=profile, timeout=10.0)
                if resp.status_code in (200, 201):
                    data = resp.json()
                    if isinstance(data, list) and len(data) > 0:
                        return data[0]
                    return profile
                else:
                    logger.warning(f"[SupabaseStore] Failed to upsert profile: HTTP {resp.status_code} {resp.text}")
                    return profile
            except Exception as e:
                logger.error(f"[SupabaseStore] Exception upserting profile: {e}")
                return profile

def get_supabase_sql_schema() -> str:
    """
    Returns SQL schema definition for setting up the `profiles` table in Supabase.
    """
    return """
-- SQL Schema for Supabase Postgres
CREATE TABLE IF NOT EXISTS public.profiles (
    privy_user_id TEXT PRIMARY KEY,
    email TEXT,
    wallet_address TEXT,
    holder_tier TEXT DEFAULT 'Free',
    forai_balance NUMERIC DEFAULT 0,
    balance_last_checked_at TIMESTAMPTZ,
    badges JSONB DEFAULT '[]'::jsonb,
    track_record_status TEXT DEFAULT 'placeholder_active',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable RLS if desired, or access via service_role key
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
"""
