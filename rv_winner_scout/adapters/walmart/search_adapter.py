"""Walmart product search and price verification adapter.

Adheres strictly to honest verification and high-confidence matching. Never fabricates prices or URLs.
"""

import re
from typing import List, Optional
from urllib.parse import quote_plus, urljoin
from bs4 import BeautifulSoup

from rv_winner_scout.adapters.amazon.category_crawler import PRICE_REGEX
from rv_winner_scout.adapters.http.client import ResilientHttpClient
from rv_winner_scout.domain.enums import WalmartStatus
from rv_winner_scout.domain.models import WalmartResearchResult
from rv_winner_scout.domain.walmart_matcher import evaluate_match
from rv_winner_scout.ports.walmart_port import WalmartResearchPort


class WalmartSearchAdapter(WalmartResearchPort):
    """Searches Walmart to verify alternative products, URLs, and prices."""

    def __init__(self, http_client: ResilientHttpClient) -> None:
        self.http_client = http_client

    async def search_and_verify(
        self, query: str, expected_title: str, expected_price: Optional[float] = None
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

        # Inspect candidate cards
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

            # High-confidence matching check
            decision = evaluate_match(
                amazon_title=expected_title,
                amazon_price=expected_price,
                walmart_title=found_title,
                walmart_price=price_val,
                walmart_url=full_url,
            )

            if decision.is_match and decision.confidence == "high":
                return WalmartResearchResult(
                    status=WalmartStatus.FOUND,
                    product_name=found_title,
                    url=decision.clean_walmart_url,
                    displayed_price=price_val,
                    is_direct_alternative=True,
                    search_query_used=clean_query,
                    notes=f"High-confidence match: {decision.reason}",
                )

        return WalmartResearchResult(
            status=WalmartStatus.NOT_FOUND,
            search_query_used=clean_query,
            notes="Search completed; no direct equivalent products identified",
        )
