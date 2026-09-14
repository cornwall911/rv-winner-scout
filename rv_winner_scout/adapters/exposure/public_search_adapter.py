"""Public RV social and community exposure researcher.

Researches ONLY publicly accessible, indexed sources.
Private Facebook groups are not visible and never simulated.
"""

from typing import List, Optional, Tuple
from urllib.parse import quote_plus
from bs4 import BeautifulSoup

from rv_winner_scout.adapters.http.client import ResilientHttpClient
from rv_winner_scout.config.constants import (
    EXPOSURE_SEARCH_VARIANTS,
    PUBLIC_SIGNAL_DISCLAIMER,
)
from rv_winner_scout.domain.enums import ExposureLevel
from rv_winner_scout.domain.models import ExposureSignal
from rv_winner_scout.ports.exposure_port import ExposureResearcherPort


class PublicExposureResearcher(ExposureResearcherPort):
    """Conducts public web and forum queries to gauge community exposure."""

    def __init__(self, http_client: ResilientHttpClient) -> None:
        self.http_client = http_client

    def build_query_variants(
        self,
        product_name: str,
        brand: Optional[str] = None,
        product_type: Optional[str] = None,
        key_function: Optional[str] = None,
    ) -> List[str]:
        """Builds the 9 required search variants based on product parameters."""
        b = brand or "RV"
        pt = product_type or product_name
        kf = key_function or product_name

        variants = [
            product_name,
            f"{b} {pt}",
            pt,
            kf,
            f"{pt} RV",
            f"{pt} motorhome",
            f"{pt} camper",
            f"{pt} travel trailer",
            f"{pt} fifth wheel",
        ]
        # Remove duplicates preserving order
        unique_variants: List[str] = []
        for v in variants:
            clean = " ".join(v.strip().split())
            if clean and clean not in unique_variants:
                unique_variants.append(clean)
        return unique_variants

    async def research_exposure(
        self,
        product_name: str,
        brand: Optional[str] = None,
        product_type: Optional[str] = None,
        key_function: Optional[str] = None,
    ) -> Tuple[ExposureLevel, List[ExposureSignal]]:
        """Executes targeted searches across RV forums, Reddit, and public Facebook."""
        variants = self.build_query_variants(
            product_name=product_name,
            brand=brand,
            product_type=product_type,
            key_function=key_function,
        )

        signals: List[ExposureSignal] = []
        provider_failed = False

        # Query top 3 distinctive variants to prevent IP burning
        selected_queries = variants[:3]

        for query in selected_queries:
            # Query targeted communities
            scoped_query = f'"{query}" (site:reddit.com/r/GoRVing OR site:reddit.com/r/RVLiving OR site:irv2.com OR site:facebook.com)'
            url = f"https://html.duckduckgo.com/html/?q={quote_plus(scoped_query)}"

            try:
                html = await self.http_client.get_html(url, provider_key="duckduckgo")
                soup = BeautifulSoup(html, "lxml")

                results = soup.select("div.result, div.results_links")
                for r in results[:4]:  # Top 4 per query
                    title_elem = r.select_one("a.result__url, a.result__snippet, a")
                    snippet_elem = r.select_one("a.result__snippet, div.result__snippet")
                    href = title_elem.get("href") if title_elem else None
                    snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""

                    if href and ("reddit.com" in href or "irv2.com" in href or "facebook.com" in href):
                        signals.append(
                            ExposureSignal(
                                query_used=query,
                                source_url=href,
                                snippet=f"{snippet} {PUBLIC_SIGNAL_DISCLAIMER}",
                                source_type="public_community",
                            )
                        )
            except Exception:
                # If search provider fails or rate limits, note degraded state
                provider_failed = True

        # If search failed completely, return UNKNOWN
        if provider_failed and not signals:
            return ExposureLevel.UNKNOWN, []

        # Classify exposure level based on verified public signals
        count = len(signals)
        if count == 0:
            return ExposureLevel.VERY_LOW, []
        elif 1 <= count <= 3:
            return ExposureLevel.LOW, signals
        elif 4 <= count <= 8:
            return ExposureLevel.MEDIUM, signals
        elif 9 <= count <= 15:
            return ExposureLevel.HIGH, signals
        else:
            return ExposureLevel.SATURATED, signals
