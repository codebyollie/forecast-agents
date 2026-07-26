"""
User Badge Evaluator.

Derives user badges based on holder tier, balance, and account creation cutoff date.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Dict, Any

BADGE_CATALOG: Dict[str, Dict[str, str]] = {
    "early_adopter": {
        "id": "early_adopter",
        "title": "Early Adopter",
        "description": "Registered during Forecast AI V1.0 launch.",
        "iconType": "sparkles"
    },
    "holder": {
        "id": "holder",
        "title": "Verified Holder",
        "description": "Holds 200,000+ $FORAI tokens on Robinhood Chain.",
        "iconType": "shield"
    },
    "pro_holder": {
        "id": "pro_holder",
        "title": "Pro Holder",
        "description": "Holds 1,000,000+ $FORAI tokens on Robinhood Chain.",
        "iconType": "crown"
    },
    "mcp_trader": {
        "id": "mcp_trader",
        "title": "Agentic MCP Ready",
        "description": "Robinhood Agentic Trading MCP connected.",
        "iconType": "zap"
    }
}

class BadgeEvaluator:
    def __init__(self, early_adopter_cutoff: str = "2026-09-01T00:00:00Z"):
        self.cutoff_str = early_adopter_cutoff
        try:
            self.cutoff_dt = datetime.fromisoformat(early_adopter_cutoff.replace("Z", "+00:00"))
        except Exception:
            self.cutoff_dt = datetime(2026, 9, 1, 0, 0, 0, tzinfo=timezone.utc)

    def evaluate_badges(
        self,
        holder_tier: str,
        created_at_iso: str,
        existing_badges: Any = None
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
        mcp_connected: bool = True
    ) -> List[Dict[str, Any]]:
        earned_ids = set(self.evaluate_badges(holder_tier, created_at_iso, existing_badges))
        if mcp_connected:
            earned_ids.add("mcp_trader")

        structured = []
        for b_id, meta in BADGE_CATALOG.items():
            structured.append({
                "id": meta["id"],
                "title": meta["title"],
                "description": meta["description"],
                "iconType": meta["iconType"],
                "earned": b_id in earned_ids
            })
        return structured
