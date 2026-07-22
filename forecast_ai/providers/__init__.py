from typing import Dict, Optional
from .base import BaseProvider
from .openai import OpenAIProvider
from .anthropic import AnthropicProvider
from .gemini import GeminiProvider
from .ollama import OllamaProvider
from .openrouter import OpenRouterProvider
from ..config import ForecastConfig

class ProviderManager:
    def __init__(self, config: ForecastConfig):
        self.config = config
        self.providers: Dict[str, BaseProvider] = {}
        self._init_providers()

    def _init_providers(self):
        for name, p_cfg in self.config.providers.items():
            if p_cfg.provider == "openai":
                self.providers[name] = OpenAIProvider(
                    api_key=p_cfg.api_key,
                    api_base=p_cfg.api_base or "https://api.openai.com/v1",
                    model_id=p_cfg.model_id
                )
            elif p_cfg.provider == "anthropic":
                self.providers[name] = AnthropicProvider(
                    api_key=p_cfg.api_key,
                    api_base=p_cfg.api_base or "https://api.anthropic.com/v1",
                    model_id=p_cfg.model_id
                )
            elif p_cfg.provider == "gemini":
                self.providers[name] = GeminiProvider(
                    api_key=p_cfg.api_key,
                    model_id=p_cfg.model_id
                )
            elif p_cfg.provider == "ollama":
                self.providers[name] = OllamaProvider(
                    api_base=p_cfg.api_base or "http://localhost:11434",
                    model_id=p_cfg.model_id
                )
            elif p_cfg.provider == "openrouter":
                self.providers[name] = OpenRouterProvider(
                    api_key=p_cfg.api_key,
                    api_base=p_cfg.api_base or "https://openrouter.ai/api/v1",
                    model_id=p_cfg.model_id
                )

    def get_provider(self, name: str) -> BaseProvider:
        # Fallback if specific provider name not found
        if name not in self.providers:
            # Fallback to default provider
            default = self.config.default_provider
            if default in self.providers:
                return self.providers[default]
            # If all else fails, return a dummy provider
            raise ValueError(f"Provider '{name}' and default provider '{default}' not found/configured.")
        return self.providers[name]

__all__ = [
    "BaseProvider",
    "OpenAIProvider",
    "AnthropicProvider",
    "GeminiProvider",
    "OllamaProvider",
    "OpenRouterProvider",
    "ProviderManager",
]
