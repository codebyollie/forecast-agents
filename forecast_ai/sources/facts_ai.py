"""
FactsAI Deep Research API Source Connector.

Queries FactsAI's serverless Cloudflare Edge API (`/answer`) for synthesized research
and cited sources. Handles HTTP error codes explicitly (401, 402, 429, 500).
"""

from __future__ import annotations

import logging
from typing import List, Dict, Any, Optional
import httpx
from .base import BaseSource
from ..models.evidence import Evidence

logger = logging.getLogger(__name__)

class FactsAIError(Exception):
    """Exception raised when FactsAI API returns an error."""
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"FactsAI Error {status_code}: {message}")

class FactsAISource(BaseSource):
    def __init__(
        self,
        api_key: str = "",
        api_url: str = "https://deep-research-api.degodmode3-33.workers.dev/answer",
        query_max_length: int = 1000
    ):
        self.api_key = api_key
        self.api_url = api_url
        self.query_max_length = query_max_length

    async def fetch_deep_research(self, query: str) -> Dict[str, Any]:
        """
        Queries FactsAI API for synthesized deep research answer and citations.
        Raises FactsAIError explicitly on 401, 402, 429, or 500 errors.
        """
        if not self.api_key:
            raise FactsAIError(401, "FactsAI API key not configured.")

        # Respect query length limit (1000 chars)
        clean_query = query.strip()[:self.query_max_length]

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {"query": clean_query}

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(self.api_url, headers=headers, json=payload, timeout=30.0)
                
                if resp.status_code == 200:
                    res_data = resp.json()
                    # Support both data.answer / data.citations and top-level response format
                    data_obj = res_data.get("data") if isinstance(res_data.get("data"), dict) else res_data
                    
                    answer = data_obj.get("answer") or data_obj.get("result") or ""
                    raw_citations = data_obj.get("citations") or data_obj.get("sources") or []
                    
                    clean_citations = []
                    for c in raw_citations:
                        if isinstance(c, dict):
                            clean_citations.append({
                                "url": c.get("url", ""),
                                "title": c.get("title") or c.get("name") or "Source",
                                "author": c.get("author", ""),
                                "publishedDate": c.get("publishedDate") or c.get("date", "")
                            })
                        elif isinstance(c, str):
                            clean_citations.append({"url": c, "title": "Source", "author": "", "publishedDate": ""})

                    return {
                        "answer": answer,
                        "citations": clean_citations
                    }
                elif resp.status_code == 401:
                    raise FactsAIError(401, "Invalid FactsAI API key (Unauthorized).")
                elif resp.status_code == 402:
                    raise FactsAIError(402, "Insufficient FactsAI credits (Payment Required).")
                elif resp.status_code == 429:
                    raise FactsAIError(429, "FactsAI rate limit exceeded (Too Many Requests).")
                elif resp.status_code >= 500:
                    raise FactsAIError(resp.status_code, f"FactsAI server error: {resp.text[:200]}")
                else:
                    raise FactsAIError(resp.status_code, f"FactsAI request failed: {resp.text[:200]}")

            except FactsAIError:
                raise
            except Exception as e:
                raise FactsAIError(500, f"Network or execution error calling FactsAI: {e}")

    async def fetch(self, query: str, limit: int = 5) -> List[Evidence]:
        """
        Implementation of BaseSource interface. Converts FactsAI citations & answer into Evidence objects.
        """
        try:
            res = await self.fetch_deep_research(query)
            evidence_list = []
            
            # Synthesized Answer Evidence
            if res.get("answer"):
                evidence_list.append(Evidence(
                    source_name="FactsAI Deep Research",
                    content=res["answer"],
                    relevance_score=0.95,
                    title=f"FactsAI Research: {query[:60]}",
                    url="https://factsai.org"
                ))

            # Citations Evidence
            for c in res.get("citations", [])[:limit]:
                evidence_list.append(Evidence(
                    source_name="FactsAI Citation",
                    content=f"Citation for '{query[:60]}': {c.get('title')}",
                    relevance_score=0.90,
                    title=c.get("title"),
                    url=c.get("url")
                ))

            return evidence_list
        except Exception as e:
            logger.warning(f"[FactsAISource] Fetch failed: {e}")
            return []
