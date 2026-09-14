"""AI Provider factory and transient failover coordinator."""

import logging
from typing import Optional, Type, TypeVar
from pydantic import BaseModel

from rv_winner_scout.adapters.ai.gemini_adapter import GeminiAdapter
from rv_winner_scout.adapters.ai.tokenrouter_adapter import TokenRouterAdapter
from rv_winner_scout.config.settings import Settings, get_settings
from rv_winner_scout.domain.exceptions import (
    AIProviderError,
    AISchemaValidationError,
    AITokenBudgetExhaustedError,
    RateLimitExceededException,
)
from rv_winner_scout.ports.ai_provider_port import AIProviderPort

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)


class AIFactory:
    """Manages primary and fallback AI providers with strict transient-only failover."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()
        self.primary_provider, self.fallback_provider = self._init_providers()

    def _init_providers(self) -> tuple[AIProviderPort, Optional[AIProviderPort]]:
        primary_name = self.settings.ai_provider.lower().strip()

        if primary_name == "gemini":
            primary = GeminiAdapter(
                api_key=self.settings.ai_api_key,
                model=self.settings.ai_model,
                timeout_seconds=self.settings.http_timeout_seconds * 2,
            )
            fallback = None
            if self.settings.tokenrouter_api_key:
                fallback = TokenRouterAdapter(
                    api_key=self.settings.tokenrouter_api_key,
                    base_url=self.settings.tokenrouter_base_url,
                    model=self.settings.tokenrouter_model,
                    timeout_seconds=self.settings.http_timeout_seconds * 2,
                )
            return primary, fallback

        elif primary_name == "tokenrouter":
            primary = TokenRouterAdapter(
                api_key=self.settings.tokenrouter_api_key,
                base_url=self.settings.tokenrouter_base_url,
                model=self.settings.tokenrouter_model,
                timeout_seconds=self.settings.http_timeout_seconds * 2,
            )
            fallback = None
            if self.settings.ai_api_key:
                fallback = GeminiAdapter(
                    api_key=self.settings.ai_api_key,
                    model=self.settings.ai_model,
                    timeout_seconds=self.settings.http_timeout_seconds * 2,
                )
            return primary, fallback

        else:
            raise AIProviderError(f"Unsupported AI_PROVIDER configuration: '{primary_name}'")

    async def generate_structured(
        self,
        prompt: str,
        schema: Type[T],
        system_prompt: Optional[str] = None,
    ) -> T:
        """Executes structured generation with transient-only failover."""
        try:
            return await self.primary_provider.generate_structured(
                prompt=prompt, schema=schema, system_prompt=system_prompt
            )
        except (RateLimitExceededException, AIProviderError) as exc:
            # NEVER failover on schema violation or reasoning token exhaustion
            if isinstance(exc, (AISchemaValidationError, AITokenBudgetExhaustedError)):
                logger.error("Non-transient AI error encountered; failover prohibited: %s", exc)
                raise exc

            # Check if this error is eligible for failover (timeout, rate limit, quota exhaustion, provider outage)
            err_str = str(exc).lower()
            is_quota_or_transient = (
                isinstance(exc, RateLimitExceededException)
                or "quota" in err_str
                or "credit" in err_str
                or "timeout" in err_str
                or "rate limit" in err_str
                or "empty message.content" in err_str
                or "429" in err_str
                or "403" in err_str
                or "500" in err_str
                or "503" in err_str
            )

            if is_quota_or_transient and self.fallback_provider:
                logger.warning(
                    "Primary AI provider %s encountered quota/transient failure (%s). Automatically failing over to %s.",
                    self.primary_provider.provider_name,
                    exc,
                    self.fallback_provider.provider_name,
                )
                return await self.fallback_provider.generate_structured(
                    prompt=prompt, schema=schema, system_prompt=system_prompt
                )

            # Otherwise re-raise
            raise exc
