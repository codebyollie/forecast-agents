"""
User Badge Evaluator.

Derives user badges based on holder tier, balance, tier_since duration, and account creation cutoff date.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

BADGE_CATALOG: Dict[str, Dict[str, Any]] = {
    "early_adopter": {
        "id": "early_adopter",
        "title": "Early Adopter",
        "description": "Registered during Forecast AI V1.0 launch.",
        "iconType": "sparkles",
        "locked_reason": "Only available to users registered prior to cutoff date."
    },
    "holder": {
        "id": "holder",
        "title": "Verified Holder",
        "description": "Holds 200,000+ $FORAI tokens on Robinhood Chain.",
        "iconType": "shield",
        "locked_reason": "Requires holding 200,000+ $FORAI tokens on Robinhood Chain."
    },
    "pro_holder": {
        "id": "pro_holder",
        "title": "Pro Holder",
        "description": "Holds 1,000,000+ $FORAI tokens on Robinhood Chain.",
        "iconType": "crown",
        "locked_reason": "Requires holding 1,000,000+ $FORAI tokens on Robinhood Chain."
    },
    "long_term_holder": {
        "id": "long_term_holder",
        "title": "Long-Term Holder",
        "description": "Maintained $FORAI Holder tier continuously for 30+ days.",
        "iconType": "award",
        "locked_reason": "Requires holding 200,000+ $FORAI for 30+ consecutive days."
    },
    "mcp_trader": {
        "id": "mcp_trader",
        "title": "Agentic MCP Ready",
        "description": "Robinhood Agentic Trading MCP connected.",
        "iconType": "zap",
        "locked_reason": "Requires connecting Robinhood Agentic Trading MCP."
    },
    "power_user": {
        "id": "power_user",
        "title": "Power User",
        "description": "Run 10+ custom agent market analyses.",
        "iconType": "flame",
        "locked_reason": "Available once custom analysis history is active."
    },
    "top_forecaster": {
        "id": "top_forecaster",
        "title": "Top Forecaster",
        "description": "Achieve top 10% forecast accuracy across prediction markets.",
        "iconType": "trophy",
        "locked_reason": "Available once forecast accuracy tracking is live."
    }
}

class BadgeEvaluator:
    def __init__(
        self,
        early_adopter_cutoff: str = "2026-09-01T00:00:00Z",
        long_term_holder_days: int = 30
    ):
        self.cutoff_str = early_adopter_cutoff
        self.long_term_holder_days = long_term_holder_days
        try:
            self.cutoff_dt = datetime.fromisoformat(early_adopter_cutoff.replace("Z", "+00:00"))
        except Exception:
            self.cutoff_dt = datetime(2026, 9, 1, 0, 0, 0, tzinfo=timezone.utc)

    def evaluate_badges(
        self,
        holder_tier: str,
        created_at_iso: str,
        existing_badges: Any = None,
        tier_since_iso: Optional[str] = None
    ) -> List[str]:
        raw_list = existing_badges or []
        extracted_ids = []
        for item in raw_list:
            if isinstance(item, str):
                extracted_ids.append(item)
            elif isinstance(item, dict) and "id" in item:
                extracted_ids.append(str(item["id"]))

        badges = set(extracted_ids)

        # Holder tier badges
        if holder_tier in ("Holder", "Pro Holder"):
            badges.add("holder")
        if holder_tier == "Pro Holder":
            badges.add("pro_holder")

        # Long term holder badge evaluation
        if holder_tier in ("Holder", "Pro Holder") and tier_since_iso:
            try:
                dt_tier = datetime.fromisoformat(tier_since_iso.replace("Z", "+00:00"))
                days_held = (datetime.now(timezone.utc) - dt_tier).total_seconds() / 86400.0
                if days_held >= self.long_term_holder_days:
                    badges.add("long_term_holder")
            except Exception:
                pass

        # Early adopter badge
        if created_at_iso:
            try:
                dt = datetime.fromisoformat(created_at_iso.replace("Z", "+00:00"))
                if dt < self.cutoff_dt:
                    badges.add("early_adopter")
            except Exception:
                pass

        return sorted(list(badges))

    def evaluate_structured_badges(
        self,
        holder_tier: str,
        created_at_iso: str,
        existing_badges: Any = None,
        tier_since_iso: Optional[str] = None,
        mcp_connected: bool = True
    ) -> List[Dict[str, Any]]:
        earned_ids = set(self.evaluate_badges(holder_tier, created_at_iso, existing_badges, tier_since_iso))
        if mcp_connected:
            earned_ids.add("mcp_trader")

        structured = []
        for b_id, meta in BADGE_CATALOG.items():
            is_earned = b_id in earned_ids
            structured.append({
                "id": meta["id"],
                "title": meta["title"],
                "description": meta["description"],
                "iconType": meta["iconType"],
                "earned": is_earned,
                "locked_reason": None if is_earned else meta.get("locked_reason")
            })
        return structured
