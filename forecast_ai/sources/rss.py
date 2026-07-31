"""
RSS Feed Data Source.
"""

from typing import List, Optional
import xml.etree.ElementTree as ET
import httpx
from datetime import datetime
from .base import BaseSource
from ..models.evidence import Evidence

class RssSource(BaseSource):
    def __init__(self, feed_urls: Optional[List[str]] = None):
        # Default list of finance/news RSS feeds
        self.feed_urls = feed_urls or [
            "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",
            "https://www.ft.com/?format=rss"
        ]

    async def _fetch_feed(self, client: httpx.AsyncClient, url: str, query: str, limit: int) -> List[Evidence]:
        items_evidence = []
        try:
            resp = await client.get(url, timeout=5.0)
            if resp.status_code != 200:
                return []
            
            root = ET.fromstring(resp.content)
            items = root.findall(".//item")
            for item in items:
                title = item.find("title")
                desc = item.find("description")
                link = item.find("link")
                pub_date = item.find("pubDate")

                title_text = title.text if title is not None else ""
                desc_text = desc.text if desc is not None else ""
                link_text = link.text if link is not None else ""

                if any(kw in title_text.lower() or kw in desc_text.lower() for kw in query.lower().split()):
                    dt = datetime.now(timezone.utc)
                    if pub_date is not None and pub_date.text:
                        try:
                            dt = datetime.strptime(pub_date.text[:25].strip(), "%a, %d %b %Y %H:%M:%S").replace(tzinfo=timezone.utc)
                        except Exception:
                            pass

                    items_evidence.append(Evidence(
                        source_name="rss",
                        content=f"{title_text}: {desc_text}",
                        timestamp=dt,
                        title=title_text,
                        url=link_text,
                        relevance_score=0.7
                    ))
                    if len(items_evidence) >= limit:
                        break
        except Exception:
            pass
        return items_evidence

    async def fetch(self, query: str, limit: int = 5) -> List[Evidence]:
        results = []
        async with httpx.AsyncClient() as client:
            tasks = [
                asyncio.create_task(self._fetch_feed(client, url, query, limit))
                for url in self.feed_urls
            ]
            feed_results = await asyncio.gather(*tasks, return_exceptions=True)
            for item_list in feed_results:
                if isinstance(item_list, list):
                    results.extend(item_list)
                    if len(results) >= limit:
                        return results[:limit]
        return results[:limit]
