"""
Base Provider interface and provider exception definitions.
"""

from abc import ABC, abstractmethod
from typing import Optional

class ProviderError(Exception):
    """Raised when an LLM provider API call fails."""
    def __init__(self, provider_name: str, message: str, raw_exception: Optional[Exception] = None):
        super().__init__(f"[{provider_name}] {message}")
        self.provider_name = provider_name
        self.message = message
        self.raw_exception = raw_exception

class BaseProvider(ABC):
    @abstractmethod
    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Generate completion for a given system and user prompt.
        """
        pass
