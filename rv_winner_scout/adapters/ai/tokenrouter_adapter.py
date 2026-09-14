"""TokenRouter AI adapter supporting OpenAI-compatible chat completions and GLM reasoning safety."""

import json
import re
from typing import Any, Dict, Optional, Type, TypeVar
import httpx
from pydantic import BaseModel, ValidationError

from rv_winner_scout.domain.exceptions import (
    AIProviderError,
    AISchemaValidationError,
    AITokenBudgetExhaustedError,
    RateLimitExceededException,
)
from rv_winner_scout.ports.ai_provider_port import AIProviderPort

T = TypeVar("T", bound=BaseModel)


def extract_json_block(text: str) -> str:
    """Extracts JSON substring if wrapped inside markdown code fences."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        # Match ```json ... ``` or ``` ... ```
        pattern = re.compile(r"^```(?:json)?\s*\n?(.*?)\n?```$", re.DOTALL | re.IGNORECASE)
        match = pattern.match(cleaned)
        if match:
            return match.group(1).strip()
    return cleaned


class TokenRouterAdapter(AIProviderPort):
    """Adapter for TokenRouter (OpenAI-compatible) API with GLM reasoning token protection."""

    def __init__(
        self,
        api_key: Optional[str],
        base_url: str = "https://api.tokenrouter.com/v1",
        model: str = "z-ai/glm-5.3-free",
        timeout_seconds: float = 60.0,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds

    @property
    def provider_name(self) -> str:
        return "tokenrouter"

    async def generate_structured(
        self,
        prompt: str,
        schema: Type[T],
        system_prompt: Optional[str] = None,
    ) -> T:
        if not self.api_key:
            raise AIProviderError("TokenRouter API key is not configured.")

        endpoint = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # Request JSON output
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        schema_json = json.dumps(schema.model_json_schema(), indent=2)
        augmented_prompt = (
            f"{prompt}\n\n"
            f"CRITICAL: Respond ONLY with a valid JSON object strictly matching this JSON Schema:\n"
            f"{schema_json}\n"
            f"Do not include any extra text, markdown formatting, or explanation."
        )
        messages.append({"role": "user", "content": augmented_prompt})

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.2,
        }

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            try:
                response = await client.post(endpoint, headers=headers, json=payload)
            except httpx.TimeoutException as exc:
                raise AIProviderError(f"TokenRouter timeout: {str(exc)}") from exc
            except httpx.RequestError as exc:
                raise AIProviderError(f"TokenRouter network error: {str(exc)}") from exc

        if response.status_code == 429:
            raise RateLimitExceededException("TokenRouter HTTP 429: Rate limit exceeded")
        if response.status_code in (401, 403):
            raise AIProviderError(f"TokenRouter Authentication/Permission Error ({response.status_code})")
        if response.status_code >= 500:
            raise AIProviderError(f"TokenRouter Server Error ({response.status_code})")
        if response.status_code != 200:
            raise AIProviderError(f"TokenRouter returned unexpected HTTP {response.status_code}: {response.text}")

        try:
            data = response.json()
        except Exception as exc:
            raise AIProviderError(f"TokenRouter response was not valid JSON: {response.text}") from exc

        choices = data.get("choices", [])
        if not choices:
            raise AIProviderError("TokenRouter returned empty choices array")

        first_choice = choices[0]
        finish_reason = first_choice.get("finish_reason")
        message = first_choice.get("message", {})
        content = message.get("content")
        reasoning_content = message.get("reasoning_content")

        # =========================================================================
        # GLM REASONING SAFETY GUARDRAIL:
        # reasoning_content is NEVER the answer.
        # If content is null and finish_reason == 'length' and reasoning_content exists,
        # fail closed with a clear error indicating truncation.
        # =========================================================================
        if (content is None or str(content).strip() == ""):
            if finish_reason == "length" and reasoning_content:
                raise AITokenBudgetExhaustedError(
                    "TokenRouter/GLM completion tokens were consumed entirely by reasoning. "
                    "Output was truncated before answer could be written to message.content."
                )
            raise AIProviderError(
                f"TokenRouter returned empty message.content with finish_reason='{finish_reason}'"
            )

        # Parse content as JSON
        cleaned_json = extract_json_block(str(content))
        try:
            parsed = schema.model_validate_json(cleaned_json)
            return parsed
        except ValidationError as exc:
            raise AISchemaValidationError(
                f"TokenRouter output failed schema validation: {str(exc)}\nRaw Content: {content}"
            ) from exc
