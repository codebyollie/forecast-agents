"""
Authenticated Profile API Routes (`/profile/me`).

Provides user profile data, $FORAI token balance holder tier, badges,
and track-record placeholder status.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel

class PartnerFeatureToggleRequest(BaseModel):
    feature: str
    enabled: bool

from ..config import ForecastConfig
from .auth import get_current_privy_user
from ..db.supabase_store import SupabaseProfileStore
from ..services.balance_checker import BalanceChecker
from ..services.badge_evaluator import BadgeEvaluator

logger = logging.getLogger(__name__)

# Per-user rate limiting dictionary: user_id -> list of request timestamps
_USER_RATE_LIMITS: Dict[str, List[float]] = {}
RATE_LIMIT_MAX_REQUESTS = 30
RATE_LIMIT_WINDOW_SECONDS = 60.0

def check_user_rate_limit(user_id: str):
    """Simple sliding window rate limiter for profile endpoints."""
    now = time.time()
    timestamps = _USER_RATE_LIMITS.setdefault(user_id, [])
    # Remove timestamps outside the window
    _USER_RATE_LIMITS[user_id] = [t for t in timestamps if now - t < RATE_LIMIT_WINDOW_SECONDS]
    
    if len(_USER_RATE_LIMITS[user_id]) >= RATE_LIMIT_MAX_REQUESTS:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Maximum {RATE_LIMIT_MAX_REQUESTS} requests per minute."
        )
    _USER_RATE_LIMITS[user_id].append(now)

def create_profile_router(config: ForecastConfig) -> APIRouter:
    router = APIRouter(prefix="/profile", tags=["profile"])

    store = SupabaseProfileStore(config.profile.supabase)
    balance_checker = BalanceChecker(config.profile.tier)
    badge_evaluator = BadgeEvaluator(config.profile.early_adopter_cutoff)

    @router.get("/me")
    async def get_my_profile(
        response: Response,
        user: Dict[str, Any] = Depends(get_current_privy_user)
    ) -> Dict[str, Any]:
        """
        Returns authenticated user profile:
        - Privy user ID
        - Linked email & wallet address
        - Cached $FORAI token balance & holder tier (Free / Holder / Pro Holder)
        - Badges (holder, early_adopter, etc.)
        - Track-record status placeholder
        """
        privy_user_id = user["privy_user_id"]
        check_user_rate_limit(privy_user_id)

        # 1. Fetch existing profile from Supabase store
        existing = await store.get_profile(privy_user_id) or {}

        # Merge linked accounts
        email = user.get("email") or existing.get("email") or ""
        wallet_address = user.get("wallet_address") or existing.get("wallet_address") or ""

        # 2. Check $FORAI token balance (cached)
        forai_balance = 0.0
        if wallet_address:
            forai_balance = await balance_checker.fetch_onchain_balance(wallet_address)
        elif existing.get("forai_balance"):
            forai_balance = float(existing["forai_balance"])

        # 3. Map balance -> holder tier
        holder_tier = balance_checker.evaluate_holder_tier(forai_balance)

        # 4. Evaluate badges and partner features map
        created_at_iso = existing.get("created_at") or datetime.now(timezone.utc).isoformat()
        existing_badges = existing.get("badges") or []
        badge_ids = badge_evaluator.evaluate_badges(holder_tier, created_at_iso, existing_badges)
        structured_badges = badge_evaluator.evaluate_structured_badges(
            holder_tier=holder_tier,
            created_at_iso=created_at_iso,
            existing_badges=existing_badges,
            mcp_connected=bool(config.robinhood_agentic.enabled)
        )

        enabled_features = existing.get("enabled_partner_features") or []
        partner_features_map = {
            "facts_ai": "facts_ai" in enabled_features
        }

        # 5. Assemble updated profile dict
        now_iso = datetime.now(timezone.utc).isoformat()
        profile_data = {
            "id": privy_user_id,
            "privy_user_id": privy_user_id,
            "email": email,
            "wallet_address": wallet_address,
            "tier": holder_tier,
            "holder_tier": holder_tier,
            "balance": round(forai_balance, 4),
            "forai_balance": round(forai_balance, 4),
            "balance_last_checked_at": now_iso,
            "partner_features": partner_features_map,
            "enabled_partner_features": enabled_features,
            "badges": structured_badges,
            "badge_ids": badge_ids,
            "track_record_status": existing.get("track_record_status", "placeholder_active"),
            "created_at": created_at_iso,
            "updated_at": now_iso
        }

        # 6. Save updated profile state to Supabase store
        saved_profile = await store.upsert_profile(profile_data)

        # Add CORS and Cache headers
        response.headers["Cache-Control"] = "private, max-age=60"
        return saved_profile

    @router.patch("/partner-features")
    async def toggle_partner_feature(
        req: PartnerFeatureToggleRequest,
        response: Response,
        user: Dict[str, Any] = Depends(get_current_privy_user)
    ) -> Dict[str, Any]:
        """
        Toggles a partner feature (e.g. 'facts_ai') on or off for the authenticated user.
        Body: {"feature": "facts_ai", "enabled": true}
        """
        privy_user_id = user["privy_user_id"]
        check_user_rate_limit(privy_user_id)

        existing = await store.get_profile(privy_user_id) or {}
        features_set = set(existing.get("enabled_partner_features") or [])

        if req.enabled:
            features_set.add(req.feature)
        else:
            features_set.discard(req.feature)

        updated_features = sorted(list(features_set))
        existing["enabled_partner_features"] = updated_features
        existing["privy_user_id"] = privy_user_id
        if "created_at" not in existing or not existing["created_at"]:
            existing["created_at"] = datetime.now(timezone.utc).isoformat()
        existing["updated_at"] = datetime.now(timezone.utc).isoformat()

        # Update partner_features map in response
        existing["id"] = privy_user_id
        existing["partner_features"] = {
            "facts_ai": "facts_ai" in updated_features
        }

        saved = await store.upsert_profile(existing)
        response.headers["Cache-Control"] = "no-cache"
        return saved

    return router
