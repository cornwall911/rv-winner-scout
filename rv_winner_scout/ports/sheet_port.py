"""Abstract interface for Google Sheets synchronization."""

from abc import ABC, abstractmethod
from typing import List
from rv_winner_scout.domain.models import ProductCandidate


class GoogleSheetsPort(ABC):
    """Port for transactional Google Sheets append operations."""

    @abstractmethod
    async def create_backup(self) -> str:
        """Takes a backup snapshot prior to executing mutations."""
        pass

    @abstractmethod
    async def append_winners(
        self,
        run_date: str,
        winners: List[ProductCandidate],
        run_id: str = "",
        reviewed_count: int = 0,
    ) -> int:
        """Appends full-width date separator and product rows atomically below historical data."""
        pass
