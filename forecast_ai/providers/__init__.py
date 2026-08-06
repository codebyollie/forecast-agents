import logging
from pathlib import Path
from typing import Dict, List, Optional
from .base import BaseProvider, ProviderError
from .openai import OpenAIProvider
from .anthropic import AnthropicProvider
from .gemini import GeminiProvider
from .ollama import OllamaProvider
from .openrouter import OpenRouterProvider
from ..config import ForecastConfig

from ..services.spend_guard import SpendGuard, SpendCapExceededError

logger = logging.getLogger(__name__)

class ProviderManager:
    def __init__(self, config: ForecastConfig):
        self.config = config
        self.providers: Dict[str, BaseProvider] = {}
        self.spend_guard = None
        if config.server.spend_guard_enabled:
            spend_path = Path(config.memory.store_dir) / "llm_spend_log.json"
            self.spend_guard = SpendGuard(
                store_path=str(spend_path),
                daily_cap_usd=config.server.daily_llm_budget_usd,
                monthly_cap_usd=config.server.monthly_llm_budget_usd,
            )
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

    def _map_model_for_provider(self, provider_name: str, model_override: str) -> str:
        p_name = provider_name.lower()
        m_override = model_override.lower()

        # Preserve an override only when it is native to the provider handling
        # the request. Cross-provider fallbacks use that provider's configured
        # model instead of hard-coded model IDs that can become retired.
        native_override = (
            (p_name == "openai" and m_override.startswith(("gpt-", "o1", "o3", "o4")))
            or (p_name == "anthropic" and m_override.startswith("claude-"))
            or (p_name == "gemini" and m_override.startswith("gemini-"))
            or p_name == "ollama"
        )
        if native_override:
            return model_override

        if p_name == "openrouter":
            if "/" in model_override:
                return model_override
            if m_override.startswith(("gpt-", "o1", "o3", "o4")):
                return f"openai/{model_override}"
            if m_override.startswith("claude-"):
                return f"anthropic/{model_override}"
            if m_override.startswith("gemini-"):
                return f"google/{model_override}"

        provider_config = self.config.providers.get(provider_name)
        if provider_config and provider_config.model_id:
            return provider_config.model_id
        return model_override

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
        model_override: Optional[str] = None
    ) -> str:
        """
        Attempts generation with primary_name provider first.
        Upon ProviderError, falls through configured fallback providers in sequence.
        Deduplicates and excludes primary_name from fallback sequence.
        """
        # Determine candidate sequence
        agent_cfg = self.config.agents.get(agent_name) if agent_name else None
        configured_fallbacks = (
            agent_cfg.fallback_providers
            if agent_cfg and agent_cfg.fallback_providers
            else getattr(self.config, "fallback_providers", ["openai", "anthropic", "gemini", "openrouter"])
        )

        # Filter candidates: dedupe and exclude primary_name from fallbacks.
        # Only include primary if it's actually initialized
        candidates: List[str] = []
        if primary_name in self.providers:
            candidates.append(primary_name)
        for name in configured_fallbacks:
            if name == primary_name:
                continue
            if name not in candidates and name in self.providers:
                candidates.append(name)

        if not candidates:
            raise ProviderError("none", f"No configured providers available (requested primary: '{primary_name}')")

        errors: List[str] = []
        for idx, provider_name in enumerate(candidates):
            provider = self.providers[provider_name]
            try:
                # Map a requested model family to the active fallback provider.
                resolved_override = None
                if model_override is not None:
                    resolved_override = self._map_model_for_provider(provider_name, model_override)

                # Check SpendGuard circuit breaker before generation
                if hasattr(self, "spend_guard") and self.spend_guard:
                    model_name = resolved_override or getattr(provider, "model_id", "default_model")
                    self.spend_guard.check_and_record_call(
                        provider=provider_name,
                        model_id=model_name,
                        agent_name=agent_name
                    )

                if idx > 0:
                    logger.warning(
                        f"[ProviderManager] Falling back to provider '{provider_name}' "
                        f"for agent='{agent_name or 'global'}' after previous failures: {errors}"
                    )
                gen_kwargs = {
                    "system_prompt": system_prompt,
                    "user_prompt": user_prompt,
                    "temperature": temperature,
                    "max_tokens": max_tokens
                }
                if resolved_override is not None:
                    gen_kwargs["model_override"] = resolved_override

                res = await provider.generate(**gen_kwargs)
                if idx > 0:
                    logger.info(f"[ProviderManager] Fallback provider '{provider_name}' succeeded.")
                return res
            except SpendCapExceededError as sce:
                raise ProviderError("circuit_breaker", str(sce))
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
