"""
User Badge Evaluator.

Derives user badges based on holder tier, balance, and account creation cutoff date.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Dict, Any

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
        existing_badges: List[str] = None
    ) -> List[str]:
        badges = set(existing_badges or [])

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
