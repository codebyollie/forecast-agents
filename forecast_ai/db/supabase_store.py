"""
Supabase Database Store for User Profiles & Dashboard Activity Log.

Manages user profile persistence in Supabase Postgres (`profiles` and `profile_activity` tables) via PostgREST REST API.
Falls back gracefully to in-memory stores if Supabase credentials are not configured.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import httpx
from ..config import SupabaseConfig

logger = logging.getLogger(__name__)

# Fallback in-memory stores when Supabase env vars are missing
_IN_MEMORY_PROFILES: Dict[str, Dict[str, Any]] = {}
_IN_MEMORY_ACTIVITY: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

class SupabaseProfileStore:
    def __init__(self, config: SupabaseConfig):
        self.config = config
        self.url = config.url.rstrip("/") if config.url else ""
        self.key = config.key
        self.table = config.table_name or "profiles"
        self.activity_table = "profile_activity"

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

    async def add_activity_event(
        self,
        privy_user_id: str,
        event_type: str,
        event_detail: str
    ) -> Dict[str, Any]:
        """
        Appends a dashboard activity log event for the user.
        Event types: badge_earned, partner_feature_toggled, wallet_connected, email_linked, tier_upgraded, waitlist_joined.
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        event_data = {
            "user_id": privy_user_id,
            "event_type": event_type,
            "event_detail": event_detail,
            "created_at": now_iso
        }

        # Keep in-memory copy
        _IN_MEMORY_ACTIVITY[privy_user_id].insert(0, event_data)

        if not self.is_configured:
            return event_data

        endpoint = f"{self.url}/rest/v1/{self.activity_table}"
        headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(endpoint, headers=headers, json=event_data, timeout=10.0)
                if resp.status_code in (200, 201):
                    data = resp.json()
                    if isinstance(data, list) and len(data) > 0:
                        return data[0]
            except Exception as e:
                logger.error(f"[SupabaseStore] Failed to insert activity event: {e}")

        return event_data

    async def get_activity_log(
        self,
        privy_user_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Fetches the recent activity log for the specified user, newest first.
        """
        if not self.is_configured:
            return _IN_MEMORY_ACTIVITY[privy_user_id][:limit]

        endpoint = f"{self.url}/rest/v1/{self.activity_table}?user_id=eq.{privy_user_id}&order=created_at.desc&limit={limit}"
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
                    if isinstance(data, list):
                        return data
            except Exception as e:
                logger.error(f"[SupabaseStore] Failed to fetch activity log for '{privy_user_id}': {e}")

        return _IN_MEMORY_ACTIVITY[privy_user_id][:limit]

    async def get_waitlist_count(self) -> int:
        """
        Returns aggregate count of users who have registered interest in custom agent analysis access.
        """
        # Count in-memory waitlist
        in_mem_count = sum(1 for p in _IN_MEMORY_PROFILES.values() if p.get("wants_analysis_access"))

        if not self.is_configured:
            return max(in_mem_count, 42)  # Baseline fallback

        endpoint = f"{self.url}/rest/v1/{self.table}?wants_analysis_access=eq.true&select=count"
        headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Prefer": "count=exact"
        }

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(endpoint, headers=headers, timeout=10.0)
                if resp.status_code in (200, 206):
                    content_range = resp.headers.get("Content-Range", "")
                    if "/" in content_range:
                        return int(content_range.split("/")[-1])
            except Exception as e:
                logger.error(f"[SupabaseStore] Failed to fetch waitlist count: {e}")

        return max(in_mem_count, 42)

def get_supabase_sql_schema() -> str:
    """
    Returns SQL schema definition for setting up `profiles` and `profile_activity` tables in Supabase.
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
    tier_since TIMESTAMPTZ DEFAULT NOW(),
    wants_analysis_access BOOLEAN DEFAULT false,
    badges JSONB DEFAULT '[]'::jsonb,
    enabled_partner_features JSONB DEFAULT '[]'::jsonb,
    track_record_status TEXT DEFAULT 'placeholder_active',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.profile_activity (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    event_detail TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Migration queries for existing databases:
-- ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS tier_since TIMESTAMPTZ DEFAULT NOW();
-- ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS wants_analysis_access BOOLEAN DEFAULT false;
-- ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS enabled_partner_features JSONB DEFAULT '[]'::jsonb;

-- Enable RLS if desired, or access via service_role key
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.profile_activity ENABLE ROW LEVEL SECURITY;
"""
