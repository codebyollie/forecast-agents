"""
Curated Topic Definitions for Public Read-Only Forecast Feed.
"""

from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass
class CuratedTopic:
    topic_id: str
    question: str
    category: str
    tier: str                      # "long" (6h) or "short" (2h)
    refresh_interval_hours: int
    source_venue: str              # "Kalshi / Robinhood Predict" or "Polymarket"
    market_ticker: str

CURATED_TOPICS: List[CuratedTopic] = [
    CuratedTopic(
        topic_id="fed-rate-q3-2026",
        question="Will the US Federal Reserve reduce benchmark interest rates in Q3 2026?",
        category="macro",
        tier="long",
        refresh_interval_hours=6,
        source_venue="Kalshi / Robinhood Predict",
        market_ticker="KXFED"
    ),
    CuratedTopic(
        topic_id="us-cpi-inflation",
        question="Will US CPI Inflation YoY be under 2.8% at Q3 end?",
        category="macro",
        tier="long",
        refresh_interval_hours=6,
        source_venue="Kalshi / Robinhood Predict",
        market_ticker="KXCPI"
    ),
    CuratedTopic(
        topic_id="btc-above-100k",
        question="Will Bitcoin (BTC) trade above $100,000 before end of month?",
        category="crypto",
        tier="short",
        refresh_interval_hours=2,
        source_venue="Kalshi / Robinhood Predict",
        market_ticker="KXBTC"
    ),
    CuratedTopic(
        topic_id="eth-above-4k",
        question="Will Ethereum (ETH) trade above $4,000 before end of month?",
        category="crypto",
        tier="short",
        refresh_interval_hours=2,
        source_venue="Polymarket",
        market_ticker="ETH-4K"
    ),
    CuratedTopic(
        topic_id="spacex-starship-orbital",
        question="Will SpaceX complete a successful Starship orbital test launch this month?",
        category="tech",
        tier="short",
        refresh_interval_hours=2,
        source_venue="Kalshi / Robinhood Predict",
        market_ticker="KXSTARSHIP"
    ),
    CuratedTopic(
        topic_id="sol-market-cap-rank",
        question="Will Solana (SOL) maintain a top 4 market cap ranking this month?",
        category="crypto",
        tier="short",
        refresh_interval_hours=2,
        source_venue="Polymarket",
        market_ticker="SOL-TOP4"
    ),
]

def get_topic_by_id(topic_id: str) -> CuratedTopic | None:
    for topic in CURATED_TOPICS:
        if topic.topic_id == topic_id:
            return topic
    return None
