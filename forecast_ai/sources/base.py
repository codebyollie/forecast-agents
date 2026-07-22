"""
Base Source interface.
"""

from abc import ABC, abstractmethod
from typing import List
from ..models.evidence import Evidence

class BaseSource(ABC):
    @abstractmethod
    async def fetch(self, query: str, limit: int = 5) -> List[Evidence]:
        """
        Fetch evidence from this data source related to the given query.
        """
        pass
