"""
Anthropic LLM provider integration.
"""

from typing import Optional
import httpx
from .base import BaseProvider, ProviderError

class AnthropicProvider(BaseProvider):
    def __init__(self, api_key: str, api_base: str = "https://api.anthropic.com/v1", model_id: str = "claude-3-5-sonnet-latest"):
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
            raise ProviderError("anthropic", "Anthropic API Key not configured.")

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        payload = {
            "model": self.model_id,
            "system": system_prompt,
            "messages": [
                {"role": "user", "content": user_prompt}
            ],
            "max_tokens": max_tokens if max_tokens is not None else 2000,
            "temperature": temperature if temperature is not None else 0.2
        }

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(f"{self.api_base}/messages", headers=headers, json=payload, timeout=60.0)
                if resp.status_code == 200:
                    data = resp.json()
                    try:
                        return data["content"][0]["text"]
                    except (KeyError, IndexError) as parse_err:
                        raise ProviderError("anthropic", f"Error parsing response payload: {data}", parse_err)
                else:
                    raise ProviderError("anthropic", f"HTTP {resp.status_code}: {resp.text}")
            except ProviderError:
                raise
            except Exception as e:
                raise ProviderError("anthropic", f"Network or execution error: {e}", e)
