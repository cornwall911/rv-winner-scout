"""Amazon product detail page verifier for direct verification and evidence extraction."""

import re
from typing import List, Optional
from bs4 import BeautifulSoup

from rv_winner_scout.adapters.amazon.anti_bot_detector import AntiBotDetector
from rv_winner_scout.adapters.amazon.category_crawler import PRICE_REGEX, canonicalize_amazon_url, extract_asin
from rv_winner_scout.adapters.http.client import ResilientHttpClient
from rv_winner_scout.domain.enums import VerificationState
from rv_winner_scout.domain.exceptions import AntiBotBlockedException
from rv_winner_scout.domain.models import VerifiedAmazonProduct


class AmazonProductVerifier:
    """Directly opens Amazon product pages to verify facts, live price, and metadata."""

    def __init__(self, http_client: ResilientHttpClient) -> None:
        self.http_client = http_client

    async def verify_product(self, product_url: str) -> VerifiedAmazonProduct:
        """Opens product page, extracts live details, and validates verification state."""
        canonical_url = canonicalize_amazon_url(product_url)
        asin = extract_asin(canonical_url) or "UNKNOWN"

        try:
            html = await self.http_client.get_html(canonical_url, provider_key="amazon")
            AntiBotDetector.check_response(canonical_url, 200, html)
        except AntiBotBlockedException as e:
            return VerifiedAmazonProduct(
                title="Unknown",
                asin=asin,
                canonical_url=canonical_url,
                verification_state=VerificationState.FAILED,
                failure_reason=str(e),
            )
        except Exception as e:
            return VerifiedAmazonProduct(
                title="Unknown",
                asin=asin,
                canonical_url=canonical_url,
                verification_state=VerificationState.FAILED,
                failure_reason=f"Network/HTTP failure: {str(e)}",
            )

        soup = BeautifulSoup(html, "lxml")

        # 1. Product Title
        title_tag = soup.select_one("#productTitle, #title span")
        title = title_tag.get_text(strip=True) if title_tag else ""

        # 2. Live Price
        price_val: Optional[float] = None
        price_tag = soup.select_one(
            "#corePriceDisplay_desktop_feature_div .a-price .a-offscreen, "
            "#corePrice_desktop .a-price .a-offscreen, "
            "#priceblock_ourprice, "
            "#priceblock_dealprice, "
            "span.a-price span.a-offscreen"
        )
        if price_tag:
            price_text = price_tag.get_text(strip=True)
            m = PRICE_REGEX.search(price_text)
            if m:
                try:
                    price_val = float(m.group(1).replace(",", ""))
                except ValueError:
                    pass

        # 3. Bullet points
        bullets: List[str] = []
        for li in soup.select("#feature-bullets ul li span.a-list-item, #featurebullets_feature_div ul li"):
            txt = li.get_text(strip=True)
            if txt and not txt.startswith("Make sure this fits"):
                bullets.append(txt)

        # 4. Newness Evidence (Date First Available)
        newness_evidence: List[str] = []
        date_pattern = re.compile(r"Date First Available\s*[:\n]\s*([A-Za-z0-9, ]+)", re.IGNORECASE)
        match = date_pattern.search(soup.get_text())
        if match:
            newness_evidence.append(f"Date First Available: {match.group(1).strip()}")

        # 5. Buy Box Availability
        has_buy_box = bool(soup.select_one("#add-to-cart-button, #buy-now-button, #buyBoxAccordion"))

        # Determine Verification State
        if title and asin != "UNKNOWN" and has_buy_box:
            state = VerificationState.VERIFIED
            failure_reason = None
        elif title and asin != "UNKNOWN":
            state = VerificationState.PARTIAL
            failure_reason = "Missing buy-box or out-of-stock"
        else:
            state = VerificationState.FAILED
            failure_reason = "Could not extract mandatory product title or ASIN"

        return VerifiedAmazonProduct(
            title=title or f"Amazon Product {asin}",
            asin=asin,
            canonical_url=canonical_url,
            displayed_price=price_val,
            bullet_points=bullets,
            buy_box_available=has_buy_box,
            newness_evidence=newness_evidence,
            verification_state=state,
            failure_reason=failure_reason,
        )
