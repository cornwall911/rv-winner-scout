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

        # 5. Extract Image Gallery (All Available Product Photos)
        images: List[str] = []
        seen_imgs = set()
        # Find high-res image URLs in raw HTML scripts
        hi_res_matches = re.findall(r'"hiRes"\s*:\s*"(https://[^"]+)"', html)
        large_matches = re.findall(r'"large"\s*:\s*"(https://[^"]+)"', html)
        dynamic_matches = re.findall(r'https://m\.media-amazon\.com/images/I/[A-Za-z0-9+_-]+\.(?:jpg|png)', html)

        for img in hi_res_matches + large_matches + dynamic_matches:
            if any(k in img for k in ["sprite", "icon", "transparent-pixel", "grey-pixel"]):
                continue
            clean_img = img.split("._")[0] + ".jpg" if "._" in img else img
            if clean_img not in seen_imgs:
                seen_imgs.add(clean_img)
                images.append(clean_img)

        # Fallback to DOM images
        if not images:
            for img_node in soup.select("#altImages img, #imageBlock img, #landingImage"):
                src = img_node.get("src") or img_node.get("data-old-hires")
                if src and src.startswith("http") and src not in seen_imgs:
                    seen_imgs.add(src)
                    images.append(src)

        # 6. Extract Best Sellers Rank (BSR)
        bsr_rank: Optional[str] = None
        bsr_match = re.search(r"Best Sellers Rank\s*[:\n]?\s*#?([0-9,]+)\s*in\s*([^(\n<]+)", html, re.IGNORECASE)
        if bsr_match:
            rank_num = bsr_match.group(1).strip()
            cat = bsr_match.group(2).strip().replace("&amp;", "&")
            bsr_rank = f"#{rank_num} in {cat[:32]}"
        else:
            sec_match = re.search(r"#([0-9,]+)\s*in\s*([A-Za-z0-9 &',-]{4,32})", html)
            if sec_match:
                bsr_rank = f"#{sec_match.group(1)} in {sec_match.group(2).strip()}"

        # 7. Buy Box Availability
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
            image_url=images[0] if images else None,
            images=images,
            bsr_rank=bsr_rank,
            bullet_points=bullets,
            buy_box_available=has_buy_box,
            newness_evidence=newness_evidence,
            verification_state=state,
            failure_reason=failure_reason,
        )
