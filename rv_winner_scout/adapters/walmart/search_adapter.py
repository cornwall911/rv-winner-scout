"""Walmart product search and price verification adapter.

Adheres strictly to honest verification. Never fabricates prices or URLs.
"""

import re
from typing import List, Optional
from urllib.parse import quote_plus, urljoin
from bs4 import BeautifulSoup

from rv_winner_scout.adapters.amazon.category_crawler import PRICE_REGEX
from rv_winner_scout.adapters.http.client import ResilientHttpClient
from rv_winner_scout.domain.enums import WalmartStatus
from rv_winner_scout.domain.models import WalmartResearchResult
from rv_winner_scout.ports.walmart_port import WalmartResearchPort


class WalmartSearchAdapter(WalmartResearchPort):
    """Searches Walmart to verify alternative products, URLs, and prices."""

    def __init__(self, http_client: ResilientHttpClient) -> None:
        self.http_client = http_client

    async def search_and_verify(
        self, query: str, expected_title: str
    ) -> WalmartResearchResult:
        """Searches Walmart for the given query and inspects top result for direct equivalence."""
        clean_query = " ".join(query.strip().split()[:5])  # Use 3-5 word query
        search_url = f"https://www.walmart.com/search?q={quote_plus(clean_query)}"

        try:
            html = await self.http_client.get_html(search_url, provider_key="walmart")
        except Exception as e:
            return WalmartResearchResult(
                status=WalmartStatus.NOT_VERIFIED,
                search_query_used=clean_query,
                notes=f"SOURCE UNAVAILABLE — Walmart request failed: {str(e)}",
            )

        html_lower = html.lower()
        # Detect PerimeterX / Blocked response
        if "blocked" in html_lower or "robot or human" in html_lower or "perimeterx" in html_lower or len(html.strip()) < 500:
            return WalmartResearchResult(
                status=WalmartStatus.NOT_VERIFIED,
                search_query_used=clean_query,
                notes="SOURCE UNAVAILABLE — Blocked by Walmart anti-bot barrier",
            )

        soup = BeautifulSoup(html, "lxml")

        # Parse product grid cards
        cards = soup.select(
            "div[data-item-id], div[data-testid='list-view'] > div, div.search-result-gridview-item"
        )
        if not cards:
            # Check if there are no search results
            if "no results for" in html_lower or "0 results" in html_lower:
                return WalmartResearchResult(
                    status=WalmartStatus.NOT_FOUND,
                    search_query_used=clean_query,
                    notes="No matching products found on Walmart",
                )
            return WalmartResearchResult(
                status=WalmartStatus.NOT_VERIFIED,
                search_query_used=clean_query,
                notes="Could not locate Walmart product grid items in DOM",
            )

        # Inspect first candidate card
        for card in cards[:3]:
            link_tag = card.select_one("a[href*='/ip/']")
            if not link_tag:
                continue

            href = link_tag.get("href", "")
            full_url = urljoin("https://www.walmart.com", href.split("?")[0])

            # Extract title
            title_node = card.select_one(
                "span[data-automation-id='product-title'], span.w_iUH7, a span"
            )
            found_title = title_node.get_text(strip=True) if title_node else link_tag.get_text(strip=True)

            # Extract price
            price_val: Optional[float] = None
            price_node = card.select_one(
                "div[data-automation-id='product-price'], span.w_iUH7"
            )
            if price_node:
                m = PRICE_REGEX.search(price_node.get_text())
                if m:
                    try:
                        price_val = float(m.group(1).replace(",", ""))
                    except ValueError:
                        pass

            # Determine whether it is a direct/real alternative
            is_alternative = self._is_direct_alternative(expected_title, found_title)

            if full_url and is_alternative:
                return WalmartResearchResult(
                    status=WalmartStatus.FOUND,
                    product_name=found_title,
                    url=full_url,
                    displayed_price=price_val,
                    is_direct_alternative=True,
                    search_query_used=clean_query,
                    notes="Verified direct alternative found",
                )

        return WalmartResearchResult(
            status=WalmartStatus.NOT_FOUND,
            search_query_used=clean_query,
            notes="Search completed; no direct equivalent products identified",
        )

    def _is_direct_alternative(self, original_title: str, candidate_title: str) -> bool:
        """Determines if the candidate product is a genuine direct alternative."""
        orig_tokens = set(re.findall(r"\w+", original_title.lower()))
        cand_tokens = set(re.findall(r"\w+", candidate_title.lower()))

        # Strip common stopwords
        stopwords = {"for", "the", "and", "with", "a", "an", "in", "on", "of", "to", "by"}
        orig_meaningful = orig_tokens - stopwords
        cand_meaningful = cand_tokens - stopwords

        if not orig_meaningful:
            return False

        overlap = orig_meaningful.intersection(cand_meaningful)
        # Require at least 2 key overlapping tokens or >= 30% Jaccard
        return len(overlap) >= 2 or (len(overlap) / len(orig_meaningful)) >= 0.3
