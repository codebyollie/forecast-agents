"""
Blockchain On-chain Data Source.
"""

from typing import List, Optional
import httpx
from datetime import datetime
from .base import BaseSource
from ..models.evidence import Evidence

class BlockchainSource(BaseSource):
    def __init__(self, polygonscan_key: Optional[str] = None):
        self.polygonscan_key = polygonscan_key
        # Polymarket CTF contract address on Polygon
        self.ctf_address = "0x4b78619e0750a6E869D6EcC5C3EEb254a6C31C5d" 

    async def fetch(self, query: str, limit: int = 5) -> List[Evidence]:
        if not self.polygonscan_key:
            return []

        url = "https://api.polygonscan.com/api"
        params = {
            "module": "account",
            "action": "tokentx",
            "address": self.ctf_address,
            "startblock": 0,
            "endblock": 99999999,
            "sort": "desc",
            "apikey": self.polygonscan_key
        }

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(url, params=params)
                if resp.status_code == 200:
                    txs = resp.json().get("result", [])
                    if not isinstance(txs, list):
                        return []
                    
                    results = []
                    for tx in txs[:limit]:
                        timestamp = int(tx.get("timeStamp", 0))
                        dt = datetime.fromtimestamp(timestamp) if timestamp else datetime.utcnow()
                        
                        results.append(Evidence(
                            source_name="blockchain",
                            content=f"Token Tx from {tx.get('from')} to {tx.get('to')}. Value: {tx.get('value')} Token: {tx.get('tokenSymbol')}",
                            timestamp=dt,
                            relevance_score=0.9,
                            metadata=tx
                        ))
                    return results
            except Exception:
                pass
        return []
