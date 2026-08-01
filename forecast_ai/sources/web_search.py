"""
OpenAI Web Search Source.

Uses gpt-4o-mini-search-preview to perform real-time web searches
and return cited answers with URL references.
No additional API keys needed — uses the existing OPENAI_API_KEY.
"""

from __future__ import annotations

import logging
from typing import List, Dict, Any, Optional
import httpx
from .base import BaseSource
from ..models.evidence import Evidence

logger = logging.getLogger(__name__)


class WebSearchSource(BaseSource):
    """
    Uses OpenAI's gpt-4o-mini-search-preview model to search the web
    and return synthesized answers with URL citations.
    Falls back gracefully when the API key is unavailable.
    """

    def __init__(
        self,
        api_key: str = "",
        model: str = "gpt-4o-mini-search-preview",
        api_base: str = "https://api.openai.com/v1",
    ):
        self.api_key = api_key
        self.model = model
        self.api_base = api_base.rstrip("/")

    async def search(self, query: str) -> Dict[str, Any]:
        """
        Performs a live web search and returns:
          {"answer": str, "citations": [{"url", "title", "author", "publishedDate"}]}
        Raises ValueError on API failure.
        """
        if not self.api_key:
            raise ValueError("OpenAI API key not configured for WebSearchSource.")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # gpt-4o-mini-search-preview does NOT support temperature parameter
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": (
                        f"Search for the most current and relevant information about: {query}\n\n"
                        "Provide a comprehensive, factual summary with specific data points, "
                        "expert opinions, and recent developments. Cite all sources."
                    ),
                }
            ],
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.api_base}/chat/completions",
                headers=headers,
                json=payload,
                timeout=45.0,
            )

            if resp.status_code != 200:
                raise ValueError(
                    f"OpenAI Web Search HTTP {resp.status_code}: {resp.text[:300]}"
                )

            data = resp.json()
            choice = data.get("choices", [{}])[0]
            message = choice.get("message", {})
            answer = message.get("content", "")

            # Extract URL citations from annotations
            annotations = message.get("annotations", [])
            citations: List[Dict[str, str]] = []
            seen_urls: set = set()

            for ann in annotations:
                if ann.get("type") == "url_citation":
                    url_data = ann.get("url_citation", {})
                    url = url_data.get("url", "")
                    title = url_data.get("title", "Web Source")
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        citations.append(
                            {
                                "url": url,
                                "title": title,
                                "author": "",
                                "publishedDate": "",
                            }
                        )

            logger.info(
                f"[WebSearchSource] Search complete. Answer length: {len(answer)}, "
                f"Citations: {len(citations)}"
            )
            return {"answer": answer, "citations": citations}

    async def fetch(self, query: str, limit: int = 5) -> List[Evidence]:
        """BaseSource interface: returns list of Evidence objects."""
        try:
            result = await self.search(query)
            evidence_list: List[Evidence] = []

            if result.get("answer"):
                evidence_list.append(
                    Evidence(
                        source_name="Web Search",
                        content=result["answer"],
                        relevance_score=0.93,
                        title=f"Web Research: {query[:60]}",
                        url="https://openai.com",
                    )
                )

            for c in result.get("citations", [])[:limit]:
                evidence_list.append(
                    Evidence(
                        source_name="Web Citation",
                        content=f"Cited source: {c.get('title')}",
                        relevance_score=0.88,
                        title=c.get("title"),
                        url=c.get("url"),
                    )
                )

            return evidence_list
        except Exception as e:
            logger.warning(f"[WebSearchSource] Search failed: {e}")
            return []
