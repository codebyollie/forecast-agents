"""
Gemini LLM provider integration.
"""

from typing import Optional
import httpx
from .base import BaseProvider, ProviderError

class GeminiProvider(BaseProvider):
    def __init__(self, api_key: str, model_id: str = "gemini-2.5-flash"):
        self.api_key = api_key
        self.model_id = model_id

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        if not self.api_key:
            raise ProviderError("gemini", "Gemini API Key not configured.")

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_id}:generateContent?key={self.api_key}"
        
        payload = {
            "contents": [
                {
                    "parts": [{"text": user_prompt}]
                }
            ],
            "systemInstruction": {
                "parts": [{"text": system_prompt}]
            },
            "generationConfig": {
                "temperature": temperature if temperature is not None else 0.2,
            }
        }
        if max_tokens:
            payload["generationConfig"]["maxOutputTokens"] = max_tokens

        headers = {
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(url, headers=headers, json=payload, timeout=60.0)
                if resp.status_code == 200:
                    data = resp.json()
                    try:
                        return data["candidates"][0]["content"]["parts"][0]["text"]
                    except (KeyError, IndexError) as parse_err:
                        raise ProviderError("gemini", f"Error parsing response payload: {data}", parse_err)
                else:
                    raise ProviderError("gemini", f"HTTP {resp.status_code}: {resp.text}")
            except ProviderError:
                raise
            except Exception as e:
                raise ProviderError("gemini", f"Network or execution error: {e}", e)
