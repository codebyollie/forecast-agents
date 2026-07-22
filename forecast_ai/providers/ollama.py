"""
Ollama local LLM provider integration.
"""

from typing import Optional
import httpx
from .base import BaseProvider

class OllamaProvider(BaseProvider):
    def __init__(self, api_base: str = "http://localhost:11434", model_id: str = "llama3"):
        self.api_base = api_base.rstrip('/')
        self.model_id = model_id

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        url = f"{self.api_base}/api/chat"
        
        payload = {
            "model": self.model_id,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "options": {
                "temperature": temperature if temperature is not None else 0.2
            },
            "stream": False
        }
        if max_tokens:
            payload["options"]["num_predict"] = max_tokens

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(url, json=payload, timeout=90.0)
                if resp.status_code == 200:
                    data = resp.json()
                    return data["message"]["content"]
                else:
                    return f"Error from Ollama API: {resp.status_code} - {resp.text}"
            except Exception as e:
                return f"Error calling Ollama Provider: {e}"
