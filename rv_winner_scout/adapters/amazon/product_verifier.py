"""Amazon product detail page verifier for direct verification and evidence extraction."""

import json
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

        def add_clean_img(url_str: str) -> None:
            if not url_str or not url_str.startswith("http"):
                return
            if any(k in url_str.lower() for k in ["sprite", "icon", "transparent-pixel", "grey-pixel", "amazon-logo"]):
                return
            # Remove Amazon dynamic resizing/crop modifiers to obtain the original high-res photo
            # e.g., https://m.media-amazon.com/images/I/71xyz._AC_SL1500_.jpg -> .../71xyz.jpg
            clean_url = re.sub(r"\._[A-Za-z0-9_,-]+_\.", ".", url_str)
            if clean_url not in seen_imgs and clean_url.startswith("http"):
                seen_imgs.add(clean_url)
                images.append(clean_url)

        # A. Extract from 'colorImages' or 'imageGalleryData' JSON structures
        color_imgs_match = re.search(r"'(?:colorImages|imageGalleryData)'\s*:\s*(\{\s*['\"]initial['\"].*?\}),\s*\n", html)
        if not color_imgs_match:
            color_imgs_match = re.search(r'"(?:colorImages|imageGalleryData)"\s*:\s*(\{\s*"initial".*?\}),', html)
        if color_imgs_match:
            try:
                raw_json = color_imgs_match.group(1).replace("'", '"')
                data = json.loads(raw_json)
                for item in data.get("initial", []):
                    for k in ["hiRes", "large", "mainUrl"]:
                        if item.get(k):
                            add_clean_img(item[k])
            except Exception:
                pass

        # B. Find high-res image URLs in raw HTML scripts
        for match_url in re.findall(r'"(?:hiRes|large|mainUrl)"\s*:\s*"(https://[^"]+)"', html):
            add_clean_img(match_url)

        # C. Comprehensive Amazon CDN regex matching
        cdn_matches = re.findall(
            r'https://(?:m\.media-amazon\.com|images-na\.ssl-images-amazon\.com)/images/I/[A-Za-z0-9+_.%-]+?\.(?:jpg|jpeg|png)',
            html,
        )
        for cdn_url in cdn_matches:
            add_clean_img(cdn_url)

        # D. DOM Elements: data-a-dynamic-image & imageBlock
        for img_node in soup.select("#landingImage, #imgBlkFront, #altImages img, #imageBlock img"):
            dyn_data = img_node.get("data-a-dynamic-image")
            if dyn_data:
                try:
                    dyn_dict = json.loads(dyn_data)
                    for dyn_url in dyn_dict.keys():
                        add_clean_img(dyn_url)
                except Exception:
                    pass

            src = img_node.get("data-old-hires") or img_node.get("src")
            if src:
                add_clean_img(src)

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

        # 7. Buy Box Availability & In-Stock Status
        buybox_selectors = [
            "#add-to-cart-button",
            "#buy-now-button",
            "#buyBoxAccordion",
            "#desktop_buybox",
            "#buybox",
            "#qualifiedBuybox",
            "#exports_desktop_qualifiedBuybox",
            "#tabular-buybox",
            "#all-offers-display",
            "input[name='submit.add-to-cart']",
            ".a-button-stack",
            "#merchant-info",
        ]
        has_buy_box = bool(soup.select_one(", ".join(buybox_selectors)))
        page_text_lower = soup.get_text().lower()
        is_explicitly_out_of_stock = any(
            phrase in page_text_lower
            for phrase in [
                "currently unavailable",
                "we don't know when or if this item will be back in stock",
            ]
        ) and bool(soup.select_one("#outOfStock, #availability .a-color-price"))

        # Determine Verification State
        if title and asin != "UNKNOWN" and not is_explicitly_out_of_stock:
            state = VerificationState.VERIFIED
            failure_reason = None
        elif title and asin != "UNKNOWN":
            state = VerificationState.PARTIAL
            failure_reason = "Explicitly out of stock on Amazon"
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
