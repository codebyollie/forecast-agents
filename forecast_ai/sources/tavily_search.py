"""
Tavily Search Source.

Uses Tavily API to perform fast fact-checking and deep research.
"""

from __future__ import annotations

import logging
from typing import List, Dict, Any
import httpx
from .base import BaseSource
from ..models.evidence import Evidence

logger = logging.getLogger(__name__)


class TavilySearchSource(BaseSource):
    """
    Uses Tavily Search API.
    """

    def __init__(
        self,
        api_key: str = "",
        enabled: bool = False
    ):
        self.api_key = api_key
        self.enabled = enabled
        self.api_base_url = "https://api.tavily.com"

    async def fetch(self, query: str, limit: int = 5) -> List[Evidence]:
        """BaseSource interface: returns list of Evidence objects."""
        if not self.enabled or not self.api_key:
            logger.debug("[TavilySearchSource] Source is disabled or API key is missing.")
            return []
            
        headers = {
            "Content-Type": "application/json"
        }
        
        payload = {
            "api_key": self.api_key,
            "query": query,
            "search_depth": "advanced",
            "include_answer": True,
            "include_raw_content": False,
            "max_results": limit
        }
        
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self.api_base_url}/search",
                    headers=headers,
                    json=payload,
                    timeout=30.0
                )
                
                if resp.status_code != 200:
                    logger.error(f"[TavilySearchSource] HTTP {resp.status_code}: {resp.text}")
                    return []
                    
                data = resp.json()
                results = data.get("results", [])
                answer = data.get("answer", "")
                
                evidence_list = []
                
                # Add the synthesized answer first if available
                if answer:
                    evidence_list.append(
                        Evidence(
                            source_name="Tavily Answer",
                            content=answer,
                            relevance_score=0.95,
                            title=f"Tavily Summary: {query[:50]}",
                            url=""
                        )
                    )
                
                # Add individual source results
                for res in results:
                    text_content = res.get("content", "")
                    if text_content:
                        evidence_list.append(
                            Evidence(
                                source_name="Tavily Search",
                                content=text_content,
                                relevance_score=res.get("score", 0.85),
                                title=res.get("title", "Web Result"),
                                url=res.get("url", "")
                            )
                        )
                        
                logger.info(f"[TavilySearchSource] Found {len(evidence_list)} evidence pieces for query: {query}")
                return evidence_list
                
        except Exception as e:
            logger.warning(f"[TavilySearchSource] Search failed: {e}")
            return []
