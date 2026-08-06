from unittest.mock import AsyncMock, patch

import pytest

from forecast_ai.agents.reddit import RedditAgent
from forecast_ai.agents.research import ResearchAgent
from forecast_ai.config import ForecastConfig
from forecast_ai.models.evidence import Evidence
from forecast_ai.providers.base import BaseProvider


class DummyProvider(BaseProvider):
    async def generate(self, system_prompt: str, user_prompt: str, temperature: float = 0.3) -> str:
        return '{"probability": 0.4, "confidence": 0.8, "reasoning": "Evidence reviewed.", "warnings": []}'


@pytest.mark.asyncio
async def test_research_citations_are_deduplicated_and_provider_labelled():
    config = ForecastConfig()
    config.facts_ai.enabled = True
    config.facts_ai.api_key = "facts-key"
    agent = ResearchAgent(name="research", provider=DummyProvider(), config=config)

    facts_response = {
        "answer": "Verified research summary.",
        "citations": [
            {"title": "Official report", "url": "https://example.gov/report?ref=one"},
            {"title": "Official report duplicate", "url": "https://example.gov/report?ref=two"},
        ],
    }
    tavily_evidence = Evidence(
        source_name="Tavily Search",
        content="Current source",
        title="Current source",
        url="https://news.example/current",
        metadata={"provider": "Tavily", "source_type": "web"},
    )

    with patch(
        "forecast_ai.sources.facts_ai.FactsAISource.fetch_deep_research",
        new=AsyncMock(return_value=facts_response),
    ) as facts_fetch:
        prediction = await agent.forecast("Will the event happen?", [tavily_evidence])

    assert "Primary documents" in facts_fetch.await_args.args[0]
    assert prediction.research_providers == ["FactsAI", "Tavily"]
    assert len(prediction.citations) == 2
    assert {citation["provider"] for citation in prediction.citations} == {"FactsAI", "Tavily"}


@pytest.mark.asyncio
async def test_reddit_agent_uses_domain_filtered_tavily_sources():
    config = ForecastConfig()
    config.tavily.enabled = True
    config.tavily.api_key = "tavily-key"
    agent = RedditAgent(name="reddit", provider=DummyProvider(), config=config)

    reddit_evidence = [
        Evidence(
            source_name="Tavily Search",
            content="Reddit discussion",
            title="Reddit thread",
            url="https://www.reddit.com/r/predictionmarkets/comments/example/thread/",
        )
    ]

    with patch(
        "forecast_ai.sources.tavily_search.TavilySearchSource.fetch",
        new=AsyncMock(return_value=reddit_evidence),
    ) as tavily_fetch:
        prediction = await agent.forecast("Will the event happen?", [])

    assert tavily_fetch.await_args.kwargs["include_domains"] == ["reddit.com"]
    assert prediction.research_providers == ["Tavily"]
    assert prediction.citations == [
        {
            "title": "Reddit thread",
            "url": "https://www.reddit.com/r/predictionmarkets/comments/example/thread/",
            "provider": "Tavily",
            "sourceType": "reddit",
        }
    ]
