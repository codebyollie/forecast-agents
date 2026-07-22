"""
Evidence model definition.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional

@dataclass
class Evidence:
    source_name: str           # e.g., "polymarket", "reddit", "news", "rss"
    content: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    title: Optional[str] = None
    url: Optional[str] = None
    relevance_score: float = 0.5
    metadata: Dict[str, Any] = field(default_factory=dict)
