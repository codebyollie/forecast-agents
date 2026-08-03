"""
Polymarket data models.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

@dataclass
class PolymarketMarket:
    id: str
    question: str
    condition_id: str
    slug: str
    resolution_source: str
    end_date_iso: str
    tokens: List[Dict[str, str]] = field(default_factory=list)  # token_id, outcome
    active: bool = True
    closed: bool = False
    volume: float = 0.0
    liquidity: float = 0.0
    category: str = ""
    event_id: str = ""
    image: Optional[str] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)

    @property
    def outcome_prices(self) -> List[float]:
        if self.raw_data and self.raw_data.get("outcomePrices"):
            try:
                op = self.raw_data["outcomePrices"]
                if isinstance(op, str):
                    import json
                    op = json.loads(op)
                if isinstance(op, list):
                    return [float(p) for p in op]
            except Exception:
                pass
        return []

@dataclass
class PolymarketEvent:
    id: str
    title: str
    slug: str
    description: str
    markets: List[PolymarketMarket] = field(default_factory=list)
    raw_data: Dict[str, Any] = field(default_factory=dict)

@dataclass
class BookLevel:
    price: float
    size: float

@dataclass
class OrderBookSummary:
    token_id: str
    bids: List[BookLevel] = field(default_factory=list)
    asks: List[BookLevel] = field(default_factory=list)
    last_trade_price: Optional[float] = None
    spread: float = 0.0
    raw_data: Dict[str, Any] = field(default_factory=dict)
