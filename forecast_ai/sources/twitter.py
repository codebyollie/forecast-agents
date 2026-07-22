"""
X (formerly Twitter) Data Source.
"""

from typing import List, Optional
import httpx
from datetime import datetime
from .base import BaseSource
from ..models.evidence import Evidence

class TwitterSource(BaseSource):
    def __init__(self, bearer_token: Optional[str] = None):
        self.bearer_token = bearer_token

    async def fetch(self, query: str, limit: int = 5) -> List[Evidence]:
        if not self.bearer_token:
            return []

        url = "https://api.twitter.com/2/tweets/search/recent"
        headers = {
            "Authorization": f"Bearer {self.bearer_token}"
        }
        params = {
            "query": query,
            "max_results": max(10, min(100, limit)),
            "tweet.fields": "created_at,author_id"
        }

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(url, headers=headers, params=params)
                if resp.status_code == 200:
                    tweets = resp.json().get("data", [])
                    results = []
                    for t in tweets[:limit]:
                        created_at = t.get("created_at", "")
                        try:
                            dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                        except Exception:
                            dt = datetime.utcnow()

                        results.append(Evidence(
                            source_name="twitter",
                            content=t.get("text", ""),
                            timestamp=dt,
                            relevance_score=0.6,
                            metadata={"author_id": t.get("author_id")}
                        ))
                    return results
            except Exception:
                pass
        return []
