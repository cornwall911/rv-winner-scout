"""Gemini AI adapter using structured JSON output and schema validation."""

import json
from typing import Any, Dict, Optional, Type, TypeVar
import httpx
from pydantic import BaseModel, ValidationError

from rv_winner_scout.adapters.ai.tokenrouter_adapter import extract_json_block
from rv_winner_scout.domain.exceptions import (
    AIProviderError,
    AISchemaValidationError,
    RateLimitExceededException,
)
from rv_winner_scout.ports.ai_provider_port import AIProviderPort

T = TypeVar("T", bound=BaseModel)


class GeminiAdapter(AIProviderPort):
    """Adapter for Google Gemini API with strict structured schema validation."""

    def __init__(
        self,
        api_key: Optional[str],
        model: str = "gemini-3.8-flash",
        timeout_seconds: float = 60.0,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds

    @property
    def provider_name(self) -> str:
        return "gemini"

    async def generate_structured(
        self,
        prompt: str,
        schema: Type[T],
        system_prompt: Optional[str] = None,
    ) -> T:
        if not self.api_key:
            raise AIProviderError("Gemini API key is not configured.")

        endpoint = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent?key={self.api_key}"
        )

        schema_json = json.dumps(schema.model_json_schema(), indent=2)
        augmented_prompt = (
            f"{prompt}\n\n"
            f"CRITICAL: Output ONLY a valid JSON object matching this schema:\n{schema_json}"
        )

        payload: Dict[str, Any] = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": augmented_prompt}],
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json",
            },
        }

        if system_prompt:
            payload["systemInstruction"] = {
                "parts": [{"text": system_prompt}]
            }

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            max_attempts = 3
            for attempt in range(1, max_attempts + 1):
                try:
                    response = await client.post(
                        endpoint,
                        json=payload,
                        headers={"Content-Type": "application/json"},
                    )
                except httpx.TimeoutException as exc:
                    if attempt == max_attempts:
                        raise AIProviderError(f"Gemini timeout: {str(exc)}") from exc
                    import asyncio
                    await asyncio.sleep(2.0 * attempt)
                    continue
                except httpx.RequestError as exc:
                    if attempt == max_attempts:
                        raise AIProviderError(f"Gemini network error: {str(exc)}") from exc
                    import asyncio
                    await asyncio.sleep(2.0 * attempt)
                    continue

                if response.status_code in (429, 503) and attempt < max_attempts:
                    import asyncio
                    await asyncio.sleep(2.5 * attempt)
                    continue
                break

        if response.status_code == 429:
            raise RateLimitExceededException("Gemini HTTP 429: Rate limit or quota exhausted")
        if response.status_code in (400, 401, 403):
            raise AIProviderError(f"Gemini Request/Auth Error ({response.status_code}): {response.text}")
        if response.status_code >= 500:
            raise AIProviderError(f"Gemini Server Error ({response.status_code})")
        if response.status_code != 200:
            raise AIProviderError(f"Gemini returned unexpected HTTP {response.status_code}: {response.text}")

        try:
            data = response.json()
        except Exception as exc:
            raise AIProviderError(f"Gemini response was not valid JSON: {response.text}") from exc

        candidates = data.get("candidates", [])
        if not candidates:
            raise AIProviderError("Gemini returned no candidates in response")

        content_parts = candidates[0].get("content", {}).get("parts", [])
        if not content_parts or "text" not in content_parts[0]:
            raise AIProviderError("Gemini response missing candidate text content")

        raw_text = content_parts[0]["text"]
        cleaned_json = extract_json_block(raw_text)

        try:
            parsed = schema.model_validate_json(cleaned_json)
            return parsed
        except ValidationError as exc:
            raise AISchemaValidationError(
                f"Gemini output failed schema validation: {str(exc)}\nRaw Text: {raw_text}"
            ) from exc
