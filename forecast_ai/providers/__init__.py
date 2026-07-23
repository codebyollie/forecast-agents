import logging
from typing import Dict, List, Optional
from .base import BaseProvider, ProviderError
from .openai import OpenAIProvider
from .anthropic import AnthropicProvider
from .gemini import GeminiProvider
from .ollama import OllamaProvider
from .openrouter import OpenRouterProvider
from ..config import ForecastConfig

logger = logging.getLogger(__name__)

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
        if name not in self.providers:
            default = self.config.default_provider
            if default in self.providers:
                return self.providers[default]
            raise ValueError(f"Provider '{name}' and default provider '{default}' not found/configured.")
        return self.providers[name]

    async def generate_with_fallback(
        self,
        primary_name: str,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        agent_name: Optional[str] = None,
        is_public_feed: bool = False
    ) -> str:
        """
        Attempts generation with primary_name provider first.
        Upon ProviderError, falls through configured fallback providers in sequence.
        Deduplicates and excludes primary_name from fallback sequence.
        Excludes 'ollama' if is_public_feed is True.
        """
        # Determine candidate sequence
        agent_cfg = self.config.agents.get(agent_name) if agent_name else None
        configured_fallbacks = (
            agent_cfg.fallback_providers
            if agent_cfg and agent_cfg.fallback_providers
            else getattr(self.config, "fallback_providers", ["openai", "anthropic", "gemini", "openrouter"])
        )

        # Filter candidates: dedupe, exclude primary_name, exclude 'ollama' if public feed
        candidates: List[str] = [primary_name]
        for name in configured_fallbacks:
            if name == primary_name:
                continue
            if is_public_feed and name == "ollama":
                continue
            if name not in candidates and name in self.providers:
                candidates.append(name)

        errors: List[str] = []
        for idx, provider_name in enumerate(candidates):
            provider = self.providers[provider_name]
            try:
                if idx > 0:
                    logger.warning(
                        f"[ProviderManager] Falling back to provider '{provider_name}' "
                        f"for agent='{agent_name or 'global'}' after previous failures: {errors}"
                    )
                res = await provider.generate(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                if idx > 0:
                    logger.info(f"[ProviderManager] Fallback provider '{provider_name}' succeeded.")
                return res
            except ProviderError as pe:
                err_msg = f"Provider '{provider_name}' failed: {pe.message}"
                logger.warning(f"[ProviderManager] {err_msg}")
                errors.append(err_msg)
            except Exception as e:
                err_msg = f"Provider '{provider_name}' encountered error: {e}"
                logger.warning(f"[ProviderManager] {err_msg}")
                errors.append(err_msg)

        # All providers failed
        full_err_msg = f"All LLM providers in fallback chain failed for agent '{agent_name or 'global'}': {'; '.join(errors)}"
        logger.error(f"[ProviderManager] {full_err_msg}")
        raise ProviderError("chain", full_err_msg)

__all__ = [
    "BaseProvider",
    "ProviderError",
    "OpenAIProvider",
    "AnthropicProvider",
    "GeminiProvider",
    "OllamaProvider",
    "OpenRouterProvider",
    "ProviderManager",
]
