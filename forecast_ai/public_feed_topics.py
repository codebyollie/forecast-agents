"""
Curated Topic Definitions for Public Read-Only Forecast Feed.
"""

from dataclasses import dataclass
from typing import List, Optional

@dataclass
class CuratedTopic:
    topic_id: str
    question: str
    category: str
    tier: str                      # "long" (6h) or "short" (2h)
    refresh_interval_hours: int
    source_venue: str              # "Kalshi / Robinhood Predict" or "Polymarket"
    market_ticker: str             # Ticker symbol or slug on exchange

CURATED_TOPICS: List[CuratedTopic] = [
    CuratedTopic(
        topic_id="fed-rate-q3-2026",
        question="Will the US Federal Reserve cut interest rates before 2027?",
        category="macro",
        tier="long",
        refresh_interval_hours=6,
        source_venue="Kalshi / Robinhood Predict",
        market_ticker="KXRATECUT-26DEC31"
    ),
    CuratedTopic(
        topic_id="us-cpi-inflation",
        question="Will US Used Cars & Trucks CPI for July 2026 be above 180.00?",
        category="macro",
        tier="long",
        refresh_interval_hours=6,
        source_venue="Kalshi / Robinhood Predict",
        market_ticker="KXUSEDCARCPI-26AUG12-T180.00"
    ),
    CuratedTopic(
        topic_id="btc-above-100k",
        question="Will Bitcoin (BTC) trade above $150,000 before end of 2026?",
        category="crypto",
        tier="short",
        refresh_interval_hours=2,
        source_venue="Kalshi / Robinhood Predict",
        market_ticker="KXBTCMAX150-25-26DEC31-149999.99"
    ),
    CuratedTopic(
        topic_id="eth-above-4k",
        question="Will Ethereum (ETH) trade above $2,700 at target date?",
        category="crypto",
        tier="short",
        refresh_interval_hours=2,
        source_venue="Kalshi / Robinhood Predict",
        market_ticker="KXETH-26JUL2805-T2694.99"
    ),
    CuratedTopic(
        topic_id="spacex-starship-orbital",
        question="Will SpaceX land anything successfully on Mars before 2030?",
        category="tech",
        tier="short",
        refresh_interval_hours=2,
        source_venue="Kalshi / Robinhood Predict",
        market_ticker="KXSPACEXMARS-30"
    ),
    CuratedTopic(
        topic_id="sol-market-cap-rank",
        question="Will the US government take control of any AI company or project before 2030?",
        category="tech",
        tier="short",
        refresh_interval_hours=2,
        source_venue="Kalshi / Robinhood Predict",
        market_ticker="KXUSTAKEOVER-30"
    ),
    CuratedTopic(
        topic_id="us-presidential-election-2028",
        question="Which party will win the 2028 US Presidential Election?",
        category="politics",
        tier="long",
        refresh_interval_hours=6,
        source_venue="Kalshi / Robinhood Predict",
        market_ticker="KXPRESPARTY-2028-D"
    ),
]

def get_topic_by_id(topic_id: str) -> Optional[CuratedTopic]:
    for topic in CURATED_TOPICS:
        if topic.topic_id == topic_id:
            return topic
    return None
