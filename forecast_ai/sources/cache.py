"""
Source Cache.

Lightweight file-based cache for data source queries to save API costs
and speed up repeated agent requests.
"""

import os
import json
import time
import hashlib
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from ..models.evidence import Evidence

logger = logging.getLogger(__name__)

CACHE_DIR = Path.home() / ".forecast_ai" / "cache"


class SourceCache:
    """
    JSON-based TTL cache for storing Evidence results per source and query.
    """

    def __init__(self, cache_dir: Path = CACHE_DIR):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_path(self, source_name: str, query: str) -> Path:
        """Generate a deterministic file path for a given source and query."""
        query_hash = hashlib.md5(query.encode("utf-8")).hexdigest()
        safe_source_name = "".join(c if c.isalnum() else "_" for c in source_name)
        return self.cache_dir / f"{safe_source_name}_{query_hash}.json"

    def get(self, source_name: str, query: str, ttl_seconds: int = 3600) -> Optional[List[Evidence]]:
        """
        Retrieve cached evidence if it exists and is not expired.
        """
        cache_path = self._get_cache_path(source_name, query)
        
        if not cache_path.exists():
            return None
            
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            timestamp = data.get("timestamp", 0)
            if time.time() - timestamp > ttl_seconds:
                # Expired
                return None
                
            evidence_data = data.get("evidence", [])
            evidence_list = []
            for item in evidence_data:
                # Reconstruct Evidence object (ignoring metadata that might not map perfectly)
                evidence_list.append(
                    Evidence(
                        source_name=item.get("source_name", source_name),
                        content=item.get("content", ""),
                        relevance_score=item.get("relevance_score", 1.0),
                        title=item.get("title", ""),
                        url=item.get("url", ""),
                        timestamp=item.get("timestamp")
                    )
                )
            
            logger.debug(f"[SourceCache] HIT for {source_name} on '{query}'")
            return evidence_list
            
        except Exception as e:
            logger.warning(f"[SourceCache] Failed to read cache file {cache_path}: {e}")
            return None

    def set(self, source_name: str, query: str, evidence: List[Evidence]) -> None:
        """
        Store evidence in the cache.
        """
        cache_path = self._get_cache_path(source_name, query)
        
        try:
            evidence_dicts = [
                {
                    "source_name": e.source_name,
                    "content": e.content,
                    "relevance_score": e.relevance_score,
                    "title": e.title,
                    "url": e.url,
                    "timestamp": e.timestamp
                }
                for e in evidence
            ]
            
            data = {
                "timestamp": time.time(),
                "query": query,
                "evidence": evidence_dicts
            }
            
            # Write to temporary file first then rename for atomicity
            temp_path = cache_path.with_suffix(".tmp")
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
            temp_path.replace(cache_path)
            
        except Exception as e:
            logger.warning(f"[SourceCache] Failed to write cache file {cache_path}: {e}")

    def clear(self) -> None:
        """Clear all cached files."""
        try:
            for f in self.cache_dir.glob("*.json"):
                f.unlink(missing_ok=True)
            logger.info("[SourceCache] Cleared all cache files.")
        except Exception as e:
            logger.error(f"[SourceCache] Error clearing cache: {e}")
