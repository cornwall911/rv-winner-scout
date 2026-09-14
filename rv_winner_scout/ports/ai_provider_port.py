"""Abstract interface for AI evaluation providers."""

from abc import ABC, abstractmethod
from typing import Optional, Type, TypeVar
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class AIProviderPort(ABC):
    """Port for AI providers returning schema-validated structured responses."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the provider (e.g. 'gemini', 'tokenrouter')."""
        pass

    @abstractmethod
    async def generate_structured(
        self,
        prompt: str,
        schema: Type[T],
        system_prompt: Optional[str] = None,
    ) -> T:
        """Generates a strictly structured response conforming to the provided Pydantic model.

        Raises:
            AITokenBudgetExhaustedError: If completion tokens were consumed by reasoning.
            AISchemaValidationError: If the response fails schema validation.
            AIProviderError: On API or network errors.
        """
        pass
