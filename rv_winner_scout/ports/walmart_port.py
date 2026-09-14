"""Abstract interface for Walmart cross-market verification."""

from abc import ABC, abstractmethod
from rv_winner_scout.domain.models import WalmartResearchResult


class WalmartResearchPort(ABC):
    """Port for searching and verifying Walmart product availability and pricing."""

    @abstractmethod
    async def search_and_verify(
        self, query: str, expected_title: str
    ) -> WalmartResearchResult:
        """Executes actual Walmart search, verifying whether a direct alternative exists."""
        pass
