from abc import ABC, abstractmethod
from typing import List, Optional, Tuple
from rv_winner_scout.domain.enums import ExposureLevel
from rv_winner_scout.domain.models import ExposureSignal


class ExposureResearcherPort(ABC):
    """Port for querying public web/forum/Reddit/Facebook signals."""

    @abstractmethod
    async def research_exposure(
        self,
        product_name: str,
        brand: Optional[str] = None,
        product_type: Optional[str] = None,
        key_function: Optional[str] = None,
    ) -> Tuple[ExposureLevel, List[ExposureSignal]]:
        """Executes public search across variants and returns classified exposure level and signals."""
        pass
