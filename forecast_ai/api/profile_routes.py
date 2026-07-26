"""
Authenticated Profile API Routes (`/profile/me`).

Provides user profile data, $FORAI token balance holder tier, badges,
and track-record placeholder status.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel

class PartnerFeatureToggleRequest(BaseModel):
    feature: Optional[str] = None
    enabled: Optional[bool] = None
    facts_ai: Optional[bool] = None

class WaitlistRequest(BaseModel):
    wants_analysis_access: Optional[bool] = True

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
    badge_evaluator = BadgeEvaluator(config.profile.early_adopter_cutoff, config.profile.tier.long_term_holder_days)

    @router.get("/me")
    async def get_my_profile(
        response: Response,
        user: Dict[str, Any] = Depends(get_current_privy_user)
    ) -> Dict[str, Any]:
        """
        Returns authenticated user profile & My Dashboard metadata.
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
        old_tier = existing.get("holder_tier") or "Free"

        # Maintain tier_since timestamp
        now_iso = datetime.now(timezone.utc).isoformat()
        tier_since = existing.get("tier_since") or now_iso
        if old_tier != holder_tier:
            tier_since = now_iso
            await store.add_activity_event(
                privy_user_id=privy_user_id,
                event_type="tier_upgraded",
                event_detail=f"Tier updated to {holder_tier}"
            )

        # 4. Evaluate badges and partner features map
        created_at_iso = existing.get("created_at") or now_iso
        existing_badges = existing.get("badges") or []
        badge_ids = badge_evaluator.evaluate_badges(holder_tier, created_at_iso, existing_badges, tier_since)
        structured_badges = badge_evaluator.evaluate_structured_badges(
            holder_tier=holder_tier,
            created_at_iso=created_at_iso,
            existing_badges=existing_badges,
            tier_since_iso=tier_since,
            mcp_connected=bool(config.robinhood_agentic.enabled)
        )

        enabled_features = existing.get("enabled_partner_features") or []
        partner_features_map = {
            "facts_ai": "facts_ai" in enabled_features
        }

        # 5. Assemble updated profile dict
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
            "tier_since": tier_since,
            "wants_analysis_access": bool(existing.get("wants_analysis_access", False)),
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

    @router.get("/activity")
    async def get_my_activity_log(
        limit: int = 10,
        user: Dict[str, Any] = Depends(get_current_privy_user)
    ) -> List[Dict[str, Any]]:
        """
        GET /profile/activity?limit=10
        Returns recent activity feed events for the authenticated user, newest first.
        """
        privy_user_id = user["privy_user_id"]
        check_user_rate_limit(privy_user_id)
        return await store.get_activity_log(privy_user_id, limit=min(limit, 50))

    @router.patch("/partner-features")
    async def toggle_partner_feature(
        req: PartnerFeatureToggleRequest,
        response: Response,
        user: Dict[str, Any] = Depends(get_current_privy_user)
    ) -> Dict[str, Any]:
        """
        Toggles partner feature preferences (e.g. 'facts_ai') for the authenticated user.
        Supports both JSON payloads:
        1. {"facts_ai": true}
        2. {"feature": "facts_ai", "enabled": true}
        """
        privy_user_id = user["privy_user_id"]
        check_user_rate_limit(privy_user_id)

        existing = await store.get_profile(privy_user_id) or {}
        features_set = set(existing.get("enabled_partner_features") or [])

        feature_name = req.feature or ("facts_ai" if req.facts_ai is not None else "unknown")
        is_enabled = req.facts_ai if req.facts_ai is not None else (req.enabled if req.enabled is not None else True)

        if is_enabled:
            features_set.add(feature_name)
        else:
            features_set.discard(feature_name)

        updated_features = sorted(list(features_set))
        existing["enabled_partner_features"] = updated_features
        existing["privy_user_id"] = privy_user_id

        # Log activity event
        status_text = "Enabled" if is_enabled else "Disabled"
        await store.add_activity_event(
            privy_user_id=privy_user_id,
            event_type="partner_feature_toggled",
            event_detail=f"{feature_name} ({status_text})"
        )

        # Re-fetch profile data to return complete profile object
        email = user.get("email") or existing.get("email") or ""
        wallet_address = user.get("wallet_address") or existing.get("wallet_address") or ""
        forai_balance = 0.0
        if wallet_address:
            forai_balance = await balance_checker.fetch_onchain_balance(wallet_address)
        elif existing.get("forai_balance"):
            forai_balance = float(existing["forai_balance"])

        holder_tier = balance_checker.evaluate_holder_tier(forai_balance)
        now_iso = datetime.now(timezone.utc).isoformat()
        created_at_iso = existing.get("created_at") or now_iso
        tier_since = existing.get("tier_since") or now_iso
        existing_badges = existing.get("badges") or []
        badge_ids = badge_evaluator.evaluate_badges(holder_tier, created_at_iso, existing_badges, tier_since)
        structured_badges = badge_evaluator.evaluate_structured_badges(
            holder_tier=holder_tier,
            created_at_iso=created_at_iso,
            existing_badges=existing_badges,
            tier_since_iso=tier_since,
            mcp_connected=bool(config.robinhood_agentic.enabled)
        )

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
            "tier_since": tier_since,
            "wants_analysis_access": bool(existing.get("wants_analysis_access", False)),
            "partner_features": {
                "facts_ai": "facts_ai" in updated_features
            },
            "enabled_partner_features": updated_features,
            "badges": structured_badges,
            "badge_ids": badge_ids,
            "track_record_status": existing.get("track_record_status", "placeholder_active"),
            "created_at": created_at_iso,
            "updated_at": now_iso
        }

        saved = await store.upsert_profile(profile_data)
        response.headers["Cache-Control"] = "no-cache"
        return saved

    @router.patch("/waitlist")
    async def join_analysis_waitlist(
        req: Optional[WaitlistRequest] = None,
        response: Response = None,
        user: Dict[str, Any] = Depends(get_current_privy_user)
    ) -> Dict[str, Any]:
        """
        PATCH /profile/waitlist
        Registers the logged-in user's interest for custom agent market analysis access.
        """
        privy_user_id = user["privy_user_id"]
        check_user_rate_limit(privy_user_id)

        wants = req.wants_analysis_access if req and req.wants_analysis_access is not None else True
        existing = await store.get_profile(privy_user_id) or {}
        existing["wants_analysis_access"] = wants
        existing["privy_user_id"] = privy_user_id

        if wants:
            await store.add_activity_event(
                privy_user_id=privy_user_id,
                event_type="waitlist_joined",
                event_detail="Registered interest for custom agent analysis access"
            )

        now_iso = datetime.now(timezone.utc).isoformat()
        email = user.get("email") or existing.get("email") or ""
        wallet_address = user.get("wallet_address") or existing.get("wallet_address") or ""
        forai_balance = float(existing.get("forai_balance", 0.0))
        holder_tier = balance_checker.evaluate_holder_tier(forai_balance)
        created_at_iso = existing.get("created_at") or now_iso
        tier_since = existing.get("tier_since") or now_iso
        existing_badges = existing.get("badges") or []
        badge_ids = badge_evaluator.evaluate_badges(holder_tier, created_at_iso, existing_badges, tier_since)
        structured_badges = badge_evaluator.evaluate_structured_badges(
            holder_tier=holder_tier,
            created_at_iso=created_at_iso,
            existing_badges=existing_badges,
            tier_since_iso=tier_since,
            mcp_connected=bool(config.robinhood_agentic.enabled)
        )
        enabled_features = existing.get("enabled_partner_features") or []

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
            "tier_since": tier_since,
            "wants_analysis_access": wants,
            "partner_features": {
                "facts_ai": "facts_ai" in enabled_features
            },
            "enabled_partner_features": enabled_features,
            "badges": structured_badges,
            "badge_ids": badge_ids,
            "track_record_status": existing.get("track_record_status", "placeholder_active"),
            "created_at": created_at_iso,
            "updated_at": now_iso
        }

        saved = await store.upsert_profile(profile_data)
        if response:
            response.headers["Cache-Control"] = "no-cache"
        return saved

    return router
