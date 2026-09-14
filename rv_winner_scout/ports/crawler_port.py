"""Abstract interface for Amazon catalog crawlers and verifiers."""

from abc import ABC, abstractmethod
from typing import List, Optional
from rv_winner_scout.domain.models import RawAmazonProduct, VerifiedAmazonProduct


class AmazonCrawlerPort(ABC):
    """Port for Amazon New Releases traversal and product-level verification."""

    @abstractmethod
    async def discover_categories(self, root_url: str) -> List[str]:
        """Discovers accessible subcategory URLs under the RV Parts tree."""
        pass

    @abstractmethod
    async def crawl_category_products(
        self, category_url: str, max_items: Optional[int] = None
    ) -> List[RawAmazonProduct]:
        """Crawls all accessible product cards on a category New Releases page."""
        pass

    @abstractmethod
    async def verify_product_page(self, product_url: str) -> VerifiedAmazonProduct:
        """Opens a product detail page, extracting live price, ASIN, and bullet points."""
        pass
