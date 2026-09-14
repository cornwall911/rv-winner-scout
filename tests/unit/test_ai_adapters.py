import json
import pytest
from unittest.mock import AsyncMock, patch
from pydantic import BaseModel, Field

from rv_winner_scout.adapters.ai.factory import AIFactory
from rv_winner_scout.adapters.ai.tokenrouter_adapter import TokenRouterAdapter
from rv_winner_scout.config.settings import Settings
from rv_winner_scout.domain.exceptions import (
    AISchemaValidationError,
    AITokenBudgetExhaustedError,
    RateLimitExceededException,
)


class MockResultSchema(BaseModel):
    summary: str
    score: float = Field(ge=0.0, le=10.0)


@pytest.mark.asyncio
async def test_tokenrouter_glm_reasoning_truncation_fails_closed() -> None:
    adapter = TokenRouterAdapter(api_key="mock_key")

    mock_response_data = {
        "choices": [
            {
                "finish_reason": "length",
                "message": {
                    "role": "assistant",
                    "content": None,  # null content
                    "reasoning_content": "I am thinking about the RV product and its benefits...",
                },
            }
        ]
    }

    mock_resp = AsyncMock()
    mock_resp.status_code = 200
    mock_resp.json = lambda: mock_response_data

    with patch("httpx.AsyncClient.post", return_value=mock_resp):
        with pytest.raises(AITokenBudgetExhaustedError) as exc_info:
            await adapter.generate_structured("prompt", MockResultSchema)

        assert "consumed entirely by reasoning" in str(exc_info.value)


@pytest.mark.asyncio
async def test_tokenrouter_valid_json_success() -> None:
    adapter = TokenRouterAdapter(api_key="mock_key")

    mock_response_data = {
        "choices": [
            {
                "finish_reason": "stop",
                "message": {
                    "role": "assistant",
                    "content": '{"summary": "Compact RV step stool", "score": 9.2}',
                    "reasoning_content": "Some internal thought",
                },
            }
        ]
    }

    mock_resp = AsyncMock()
    mock_resp.status_code = 200
    mock_resp.json = lambda: mock_response_data

    with patch("httpx.AsyncClient.post", return_value=mock_resp):
        result = await adapter.generate_structured("prompt", MockResultSchema)
        assert result.summary == "Compact RV step stool"
        assert result.score == 9.2


@pytest.mark.asyncio
async def test_schema_validation_error_raised() -> None:
    adapter = TokenRouterAdapter(api_key="mock_key")

    # Invalid score (> 10.0) violates Field(ge=0, le=10)
    mock_response_data = {
        "choices": [
            {
                "finish_reason": "stop",
                "message": {
                    "role": "assistant",
                    "content": '{"summary": "Invalid score item", "score": 99.0}',
                },
            }
        ]
    }

    mock_resp = AsyncMock()
    mock_resp.status_code = 200
    mock_resp.json = lambda: mock_response_data

    with patch("httpx.AsyncClient.post", return_value=mock_resp):
        with pytest.raises(AISchemaValidationError):
            await adapter.generate_structured("prompt", MockResultSchema)


@pytest.mark.asyncio
async def test_factory_transient_failover_and_non_failover() -> None:
    settings = Settings(
        AI_PROVIDER="gemini",
        AI_API_KEY="mock_gemini",
        TOKENROUTER_API_KEY="mock_tokenrouter",
    )
    factory = AIFactory(settings=settings)

    # 1. Transient error triggers failover to TokenRouter
    factory.primary_provider.generate_structured = AsyncMock(
        side_effect=RateLimitExceededException("Gemini quota 429")
    )
    factory.fallback_provider.generate_structured = AsyncMock(
        return_value=MockResultSchema(summary="Fallback worked", score=8.0)
    )

    result = await factory.generate_structured("test", MockResultSchema)
    assert result.summary == "Fallback worked"
    assert factory.fallback_provider.generate_structured.called

    # 2. Schema violation does NOT failover
    factory.primary_provider.generate_structured = AsyncMock(
        side_effect=AISchemaValidationError("Malformed schema")
    )
    factory.fallback_provider.generate_structured.reset_mock()

    with pytest.raises(AISchemaValidationError):
        await factory.generate_structured("test", MockResultSchema)

    assert not factory.fallback_provider.generate_structured.called
