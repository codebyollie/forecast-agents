"""
OpenAI LLM provider integration.
"""

from typing import Optional
import httpx
from .base import BaseProvider

class OpenAIProvider(BaseProvider):
    def __init__(self, api_key: str, api_base: str = "https://api.openai.com/v1", model_id: str = "gpt-4o"):
        self.api_key = api_key
        self.api_base = api_base.rstrip('/')
        self.model_id = model_id

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        if not self.api_key:
            return "Error: OpenAI API Key not configured."

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model_id,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": temperature if temperature is not None else 0.2,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(f"{self.api_base}/chat/completions", headers=headers, json=payload, timeout=60.0)
                if resp.status_code == 200:
                    data = resp.json()
                    return data["choices"][0]["message"]["content"]
                else:
                    return f"Error from OpenAI API: {resp.status_code} - {resp.text}"
            except Exception as e:
                return f"Error calling OpenAI Provider: {e}"
