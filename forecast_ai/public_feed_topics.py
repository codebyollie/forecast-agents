"""
Curated Topic Definitions for Public Read-Only Forecast Feed.
"""

from dataclasses import dataclass
from typing import List, Optional

@dataclass
class MarketResolutionSpec:
    series_ticker: str                     # True base series code (e.g. "KXBTC", "KXCPI", "KXRATECUT", "KXSOLD26")
    target_strike: Optional[float] = None # Numeric threshold to match against floor_strike / cap_strike
    resolves_by: Optional[str] = None    # Target resolution cutoff date (ISO format, e.g. "2027-01-01")
    keyword_fallback: str = ""          # Keyword search query for Polymarket Gamma API
    expected_ticker_fallback: str = ""  # Last confirmed working ticker symbol fallback

@dataclass
class CuratedTopic:
    topic_id: str
    question: str
    category: str
    tier: str                      # "long" (6h) or "short" (2h)
    refresh_interval_hours: int
    source_venue: str              # "Kalshi / Robinhood Predict" or "Polymarket"
    spec: MarketResolutionSpec

    @property
    def market_ticker(self) -> str:
        """Backward compatibility property returning the expected resolved market ticker."""
        return self.spec.expected_ticker_fallback or self.spec.series_ticker

CURATED_TOPICS: List[CuratedTopic] = [
    CuratedTopic(
        topic_id="fed-rate-q3-2026",
        question="Will the US Federal Reserve cut interest rates before 2027?",
        category="macro",
        tier="long",
        refresh_interval_hours=6,
        source_venue="Kalshi / Robinhood Predict",
        spec=MarketResolutionSpec(
            series_ticker="KXRATECUT",
            resolves_by="2027-01-01",
            keyword_fallback="Federal Reserve rate cut",
            expected_ticker_fallback="KXRATECUT-26DEC31"
        )
    ),
    CuratedTopic(
        topic_id="us-cpi-inflation",
        question="Will US CPI YoY rise more than 1.0% in August 2026?",
        category="macro",
        tier="long",
        refresh_interval_hours=6,
        source_venue="Kalshi / Robinhood Predict",
        spec=MarketResolutionSpec(
            series_ticker="KXCPI",
            target_strike=1.0,
            resolves_by="2026-09-01",
            keyword_fallback="US CPI inflation August 2026",
            expected_ticker_fallback="KXCPI-26AUG-T1.0"
        )
    ),
    CuratedTopic(
        topic_id="btc-above-100k",
        question="Will Bitcoin (BTC) trade above $72,299.99 on target date?",
        category="crypto",
        tier="short",
        refresh_interval_hours=2,
        source_venue="Kalshi / Robinhood Predict",
        spec=MarketResolutionSpec(
            series_ticker="KXBTC",
            target_strike=72299.99,
            resolves_by="2026-08-01",
            keyword_fallback="Bitcoin BTC 72300",
            expected_ticker_fallback="KXBTC-26JUL3000-T72299.99"
        )
    ),
    CuratedTopic(
        topic_id="eth-above-4k",
        question="Will Ethereum (ETH) trade above $2,594.99 on target date?",
        category="crypto",
        tier="short",
        refresh_interval_hours=2,
        source_venue="Kalshi / Robinhood Predict",
        spec=MarketResolutionSpec(
            series_ticker="KXETH",
            target_strike=2594.99,
            resolves_by="2026-08-01",
            keyword_fallback="Ethereum ETH 2595",
            expected_ticker_fallback="KXETH-26JUL3000-T2594.99"
        )
    ),
    CuratedTopic(
        topic_id="spacex-starship-orbital",
        question="Will SpaceX land anything successfully on Mars before 2030?",
        category="tech",
        tier="short",
        refresh_interval_hours=2,
        source_venue="Kalshi / Robinhood Predict",
        spec=MarketResolutionSpec(
            series_ticker="KXSPACEXMARS",
            resolves_by="2030-01-01",
            keyword_fallback="SpaceX Mars landing 2030",
            expected_ticker_fallback="KXSPACEXMARS-30"
        )
    ),
    CuratedTopic(
        topic_id="sol-market-cap-rank",
        question="Will Solana (SOL) trade above $150 before end of 2026?",
        category="crypto",
        tier="short",
        refresh_interval_hours=2,
        source_venue="Kalshi / Robinhood Predict",
        spec=MarketResolutionSpec(
            series_ticker="KXSOLD26",
            target_strike=149.99,
            resolves_by="2027-01-01",
            keyword_fallback="Solana SOL 150 2026",
            expected_ticker_fallback="KXSOLD26-27JAN0100-T149.99"
        )
    ),
    CuratedTopic(
        topic_id="us-presidential-election-2028",
        question="Which party will win the 2028 US Presidential Election?",
        category="politics",
        tier="long",
        refresh_interval_hours=6,
        source_venue="Kalshi / Robinhood Predict",
        spec=MarketResolutionSpec(
            series_ticker="KXPRESPARTY",
            resolves_by="2028-12-31",
            keyword_fallback="US 2028 Presidential Election Democratic Republican",
            expected_ticker_fallback="KXPRESPARTY-2028-D"
        )
    ),
]

def get_topic_by_id(topic_id: str) -> Optional[CuratedTopic]:
    for topic in CURATED_TOPICS:
        if topic.topic_id == topic_id:
            return topic
    return None
