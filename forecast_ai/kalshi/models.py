"""
Data models for Kalshi Market Data API (Robinhood Predict Proxy).
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

@dataclass
class KalshiBookLevel:
    price: float  # Implied probability ($0.01 to $0.99)
    size: float   # Quantity / volume

@dataclass
class KalshiOrderbook:
    ticker: str
    yes_bids: List[KalshiBookLevel] = field(default_factory=list)
    yes_asks: List[KalshiBookLevel] = field(default_factory=list)
    no_bids: List[KalshiBookLevel] = field(default_factory=list)
    no_asks: List[KalshiBookLevel] = field(default_factory=list)
    spread: float = 0.0
    midpoint: float = 0.5
    raw_data: Dict[str, Any] = field(default_factory=dict)

@dataclass
class KalshiMarket:
    ticker: str
    title: str
    subtitle: str = ""
    category: str = ""
    event_ticker: str = ""
    status: str = "active"
    yes_bid: float = 0.0
    yes_ask: float = 0.0
    no_bid: float = 0.0
    no_ask: float = 0.0
    last_price: float = 0.5
    volume: float = 0.0
    open_interest: float = 0.0
    expiration_time: str = ""
    result: Optional[str] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)

    @property
    def midpoint_price(self) -> float:
        if self.yes_bid > 0 and self.yes_ask > 0:
            return round((self.yes_bid + self.yes_ask) / 2.0, 4)
        if self.last_price > 0:
            return self.last_price
        return 0.5

@dataclass
class KalshiSeries:
    ticker: str
    title: str
    category: str = ""
    markets: List[KalshiMarket] = field(default_factory=list)
