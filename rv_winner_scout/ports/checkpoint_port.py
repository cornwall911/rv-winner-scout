"""Abstract interface for checkpoint persistence."""

from abc import ABC, abstractmethod
from typing import List, Optional
from rv_winner_scout.domain.models import ProductCandidate


class CheckpointPort(ABC):
    """Port for persisting product lifecycle checkpoints and resuming runs."""

    @abstractmethod
    def save_candidate(self, run_id: str, candidate: ProductCandidate) -> None:
        """Saves or updates a product candidate state."""
        pass

    @abstractmethod
    def get_candidate(self, asin: str) -> Optional[ProductCandidate]:
        """Retrieves a candidate by ASIN."""
        pass

    @abstractmethod
    def get_run_candidates(self, run_id: str) -> List[ProductCandidate]:
        """Retrieves all candidates processed under a given run ID."""
        pass

    @abstractmethod
    def quarantine_candidate(self, asin: str, stage: str, error_detail: str) -> None:
        """Pushes a failing or malformed candidate into the dead-letter quarantine."""
        pass
