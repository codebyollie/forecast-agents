"""
News API Data Source.
"""

from typing import List, Optional
import httpx
from datetime import datetime
from .base import BaseSource
from ..models.evidence import Evidence

class NewsSource(BaseSource):
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key

    async def fetch(self, query: str, limit: int = 5) -> List[Evidence]:
        if not self.api_key:
            # Gracefully returns empty list if not configured (no fake data)
            return []

        url = "https://newsapi.org/v2/everything"
        params = {
            "q": query,
            "pageSize": limit,
            "sortBy": "relevancy",
            "apiKey": self.api_key
        }

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(url, params=params)
                if resp.status_code == 200:
                    articles = resp.json().get("articles", [])
                    results = []
                    for art in articles:
                        published = art.get("publishedAt", "")
                        try:
                            dt = datetime.fromisoformat(published.replace("Z", "+00:00"))
                        except Exception:
                            dt = datetime.utcnow()

                        results.append(Evidence(
                            source_name="news",
                            content=f"{art.get('description', '')} {art.get('content', '')}",
                            timestamp=dt,
                            title=art.get('title'),
                            url=art.get('url'),
                            relevance_score=0.8
                        ))
                    return results
            except Exception:
                pass
        return []
