"""Amazon New Releases category crawler and subcategory tree explorer."""

import re
from typing import List, Optional, Set
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

from rv_winner_scout.adapters.amazon.anti_bot_detector import AntiBotDetector
from rv_winner_scout.adapters.http.client import ResilientHttpClient
from rv_winner_scout.config.constants import MAIN_AMAZON_SOURCE, RV_PARTS_CATEGORY_ID
from rv_winner_scout.domain.models import RawAmazonProduct
from rv_winner_scout.ports.crawler_port import AmazonCrawlerPort


ASIN_REGEX = re.compile(r"/(?:dp|gp/product)/([A-Z0-9]{10})", re.IGNORECASE)
PRICE_REGEX = re.compile(r"\$([\d,]+\.?\d*)")


def extract_asin(url: str) -> Optional[str]:
    """Extracts a 10-character Amazon ASIN from any standard Amazon URL."""
    match = ASIN_REGEX.search(url)
    if match:
        return match.group(1).upper()
    return None


def canonicalize_amazon_url(url: str) -> str:
    """Builds a canonical, tracking-tag-free product URL."""
    asin = extract_asin(url)
    if asin:
        return f"https://www.amazon.com/dp/{asin}"
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"


class AmazonCategoryCrawler:
    """Discovers categories and crawls product faceouts from Amazon New Releases."""

    def __init__(self, http_client: ResilientHttpClient) -> None:
        self.http_client = http_client

    async def discover_categories(
        self, root_url: str = MAIN_AMAZON_SOURCE, max_depth: int = 2
    ) -> List[str]:
        """Systematically crawls top-level categories and recursively enters all nested subcategories."""
        discovered: Set[str] = {root_url}
        to_explore: List[str] = [root_url]
        visited: Set[str] = set()

        depth = 0
        while to_explore and depth < max_depth:
            current_batch = list(to_explore)
            to_explore = []
            depth += 1

            for cat_url in current_batch:
                if cat_url in visited:
                    continue
                visited.add(cat_url)

                try:
                    html = await self.http_client.get_html(cat_url, provider_key="amazon")
                    AntiBotDetector.check_response(cat_url, 200, html)
                    soup = BeautifulSoup(html, "lxml")

                    for a_tag in soup.select("div[role='tree'] a, ul[class*='zg-browse-group'] a, div.zg-browse-group a, a[href*='/new-releases/automotive/']"):
                        href = a_tag.get("href")
                        if not href:
                            continue
                        clean_href = href.split("?")[0].split("#")[0]
                        full_url = urljoin(cat_url, clean_href)
                        if "/new-releases/automotive/" in full_url and full_url not in discovered:
                            discovered.add(full_url)
                            if depth < max_depth:
                                to_explore.append(full_url)
                except Exception:
                    pass

        return sorted(list(discovered))

    async def crawl_category_products(
        self, category_url: str, max_items: Optional[int] = None, max_pages: int = 2
    ) -> List[RawAmazonProduct]:
        """Crawl products with pagination support across page 1, 2, etc."""
        products: List[RawAmazonProduct] = []
        seen_asins: Set[str] = set()

        for page_num in range(1, max_pages + 1):
            if max_items and len(products) >= max_items:
                break

            page_url = category_url
            if page_num > 1:
                delimiter = "&" if "?" in category_url else "?"
                page_url = f"{category_url}{delimiter}pg={page_num}"

            try:
                html = await self.http_client.get_html(page_url, provider_key="amazon")
                AntiBotDetector.check_response(page_url, 200, html)
            except Exception:
                break

            soup = BeautifulSoup(html, "lxml")
            category_name = self._extract_category_title(soup)

            grid_items = soup.select(
                "div#gridItemRoot, div[id^='gridItemRoot'], div.zg-grid-general-faceout, div[data-asin]"
            )

            if not grid_items:
                break

            items_on_page = 0
            for item in grid_items:
                link_tag = item.select_one("a[href*='/dp/'], a[href*='/gp/product/']")
                if not link_tag:
                    continue
                raw_url = urljoin("https://www.amazon.com", link_tag.get("href", ""))
                asin = item.get("data-asin") or extract_asin(raw_url)
                if not asin or asin in seen_asins:
                    continue

                canonical_url = f"https://www.amazon.com/dp/{asin}"
                seen_asins.add(asin)

                title = ""
                title_node = item.select_one("div[class*='_cDEzb_p13n-sc-css-line-clamp-'], span.a-size-small, img[alt]")
                if title_node:
                    if title_node.name == "img":
                        title = title_node.get("alt", "").strip()
                    else:
                        title = title_node.get_text(strip=True)

                if not title:
                    title = link_tag.get_text(strip=True)

                price_val: Optional[float] = None
                price_node = item.select_one("span[class*='p13n-sc-price'], span.a-price span.a-offscreen")
                if price_node:
                    price_text = price_node.get_text(strip=True)
                    m = PRICE_REGEX.search(price_text)
                    if m:
                        try:
                            price_val = float(m.group(1).replace(",", ""))
                        except ValueError:
                            pass

                img_url: Optional[str] = None
                img_tag = item.select_one("img[src]")
                if img_tag:
                    img_url = img_tag.get("src")

                products.append(
                    RawAmazonProduct(
                        title=title or f"Amazon Product {asin}",
                        url=canonical_url,
                        asin=asin,
                        displayed_price=price_val,
                        image_url=img_url,
                        category="RV Parts & Accessories",
                        subcategory=category_name,
                        source_page_url=page_url,
                    )
                )
                items_on_page += 1

                if max_items and len(products) >= max_items:
                    break

            if items_on_page == 0:
                break

        return products

    def _extract_category_title(self, soup: BeautifulSoup) -> str:
        h1 = soup.select_one("h1, span[class*='zg-selected-']", )
        if h1:
            return h1.get_text(strip=True)
        return "RV Parts & Accessories"
