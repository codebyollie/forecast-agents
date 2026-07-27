"""
User Badge Evaluator.

Derives user badges based on holder tier, balance, tier_since duration, partner integrations, and account creation cutoff date.
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
        "locked_reason": "Requires 200,000+ $FORAI held on-chain."
    },
    "mcp_trader": {
        "id": "mcp_trader",
        "title": "Agentic MCP Ready",
        "description": "Robinhood Agentic Trading MCP connected.",
        "iconType": "zap",
        "locked_reason": "Requires connecting Robinhood Agentic Trading MCP."
    },
    "swarm_master": {
        "id": "swarm_master",
        "title": "Swarm Analyst",
        "description": "Ran 50+ multi-agent consensus queries.",
        "iconType": "star",
        "locked_reason": "Available once analysis history exists."
    },
    "pro_tier": {
        "id": "pro_tier",
        "title": "Pro Elite",
        "description": "Reached Pro Holder tier status (1,000,000+ $FORAI).",
        "iconType": "shield",
        "locked_reason": "Requires Pro Holder tier status (1M $FORAI)."
    },
    "polyfactual_citation": {
        "id": "polyfactual_citation",
        "title": "FactsAI Scholar",
        "description": "Used FactsAI primary source citations in predictions.",
        "iconType": "sparkles",
        "locked_reason": "Enable FactsAI partner integration to unlock."
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
        tier_since_iso: Optional[str] = None,
        facts_ai_enabled: bool = False
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
            badges.add("pro_tier")

        # FactsAI Scholar badge
        if facts_ai_enabled:
            badges.add("polyfactual_citation")

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
        mcp_connected: bool = True,
        facts_ai_enabled: bool = False
    ) -> List[Dict[str, Any]]:
        earned_ids = set(self.evaluate_badges(
            holder_tier=holder_tier,
            created_at_iso=created_at_iso,
            existing_badges=existing_badges,
            tier_since_iso=tier_since_iso,
            facts_ai_enabled=facts_ai_enabled
        ))
        if mcp_connected:
            earned_ids.add("mcp_trader")

        structured = []
        for b_id, meta in BADGE_CATALOG.items():
            is_earned = b_id in earned_ids
            badge_obj: Dict[str, Any] = {
                "id": meta["id"],
                "title": meta["title"],
                "description": meta["description"],
                "iconType": meta["iconType"],
                "earned": is_earned
            }
            if not is_earned and meta.get("locked_reason"):
                badge_obj["locked_reason"] = meta["locked_reason"]
            structured.append(badge_obj)

        return structured
