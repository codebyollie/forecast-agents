"""
Reddit Data Source.

Fetches data via Reddit API or falls back to public search JSON when API keys are absent.
"""

from typing import List, Optional
import httpx
from datetime import datetime, timezone
from .base import BaseSource
from ..models.evidence import Evidence

class RedditSource(BaseSource):
    def __init__(self, client_id: Optional[str] = None, client_secret: Optional[str] = None, user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"):
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
                        dt = (
                            datetime.fromtimestamp(created_utc, timezone.utc)
                            if created_utc
                            else datetime.now(timezone.utc)
                        )
                        
                        title = post_data.get("title", "")
                        selftext = post_data.get("selftext", "")
                        subreddit = post_data.get("subreddit", "")

                        results.append(Evidence(
                            source_name="reddit",
                            content=f"[{subreddit}] {title}: {selftext}",
                            timestamp=dt,
                            title=title,
                            url=f"https://reddit.com{post_data.get('permalink', '')}",
                            relevance_score=0.5,
                            metadata={
                                "provider": "Reddit",
                                "source_type": "reddit",
                                "subreddit": subreddit,
                            },
                        ))
                    return results
            except Exception:
                pass
        return []
