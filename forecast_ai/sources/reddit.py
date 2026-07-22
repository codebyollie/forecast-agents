"""
Reddit Data Source.

Fetches data via Reddit API or falls back to public search JSON when API keys are absent.
"""

from typing import List, Optional
import httpx
from datetime import datetime
from .base import BaseSource
from ..models.evidence import Evidence

class RedditSource(BaseSource):
    def __init__(self, client_id: Optional[str] = None, client_secret: Optional[str] = None, user_agent: str = "ForecastAI/0.1"):
        self.client_id = client_id
        self.client_secret = client_secret
        self.user_agent = user_agent

    async def fetch(self, query: str, limit: int = 5) -> List[Evidence]:
        # If API keys are missing, we fetch via Reddit's public .json endpoint (graceful access fallback)
        url = "https://www.reddit.com/search.json"
        params = {
            "q": query,
            "limit": limit,
            "sort": "relevance"
        }
        headers = {
            "User-Agent": self.user_agent
        }

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(url, params=params, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    children = data.get("data", {}).get("children", [])
                    results = []
                    for child in children:
                        post_data = child.get("data", {})
                        created_utc = post_data.get("created_utc", 0.0)
                        dt = datetime.fromtimestamp(created_utc) if created_utc else datetime.utcnow()
                        
                        title = post_data.get("title", "")
                        selftext = post_data.get("selftext", "")
                        subreddit = post_data.get("subreddit", "")

                        results.append(Evidence(
                            source_name="reddit",
                            content=f"[{subreddit}] {title}: {selftext}",
                            timestamp=dt,
                            title=title,
                            url=f"https://reddit.com{post_data.get('permalink', '')}",
                            relevance_score=0.5
                        ))
                    return results
            except Exception:
                pass
        return []
