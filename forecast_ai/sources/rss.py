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

    async def fetch(self, query: str, limit: int = 5) -> List[Evidence]:
        results = []
        async with httpx.AsyncClient() as client:
            for url in self.feed_urls:
                try:
                    resp = await client.get(url, timeout=10.0)
                    if resp.status_code != 200:
                        continue
                    
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

                        # Filter by simple text search to match query
                        if query.lower() in title_text.lower() or query.lower() in desc_text.lower():
                            dt = datetime.utcnow()
                            if pub_date is not None and pub_date.text:
                                try:
                                    # Try to parse RFC 822 format (very basic parse)
                                    dt = datetime.strptime(pub_date.text[:25].strip(), "%a, %d %b %Y %H:%M:%S")
                                except Exception:
                                    pass

                            results.append(Evidence(
                                source_name="rss",
                                content=f"{title_text}: {desc_text}",
                                timestamp=dt,
                                title=title_text,
                                url=link_text,
                                relevance_score=0.7
                            ))
                            if len(results) >= limit:
                                return results
                except Exception:
                    pass
        return results
