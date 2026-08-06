from datetime import datetime, timezone

from forecast_ai.models.evidence import Evidence
from forecast_ai.sources.cache import SourceCache


def test_source_cache_preserves_timestamp_and_provenance(tmp_path):
    cache = SourceCache(cache_dir=tmp_path)
    timestamp = datetime.now(timezone.utc)
    evidence = Evidence(
        source_name="Tavily Search",
        content="Current evidence",
        timestamp=timestamp,
        title="Source title",
        url="https://example.com/source",
        relevance_score=0.9,
        metadata={"provider": "Tavily", "source_type": "web"},
    )

    cache.set("tavily", "query", [evidence])
    restored = cache.get("tavily", "query")

    assert restored is not None
    assert restored[0].timestamp == timestamp
    assert restored[0].metadata == {
        "provider": "Tavily",
        "source_type": "web",
    }
