import pytest
from unittest.mock import AsyncMock
from rv_winner_scout.adapters.amazon.category_crawler import (
    AmazonCategoryCrawler,
    canonicalize_amazon_url,
    extract_asin,
)
from rv_winner_scout.adapters.amazon.product_verifier import AmazonProductVerifier
from rv_winner_scout.adapters.http.client import ResilientHttpClient
from rv_winner_scout.domain.enums import VerificationState


MOCK_NEW_RELEASES_HTML = """<!DOCTYPE html>
<html>
<head><title>Amazon Hot New Releases: RV Parts & Accessories</title></head>
<body>
  <h1>Hot New Releases in RV Parts & Accessories</h1>
  <div role="tree">
    <a href="/gp/new-releases/automotive/2258019011/sub1">Awnings & Screens</a>
    <a href="/gp/new-releases/automotive/2258019011/sub2">Plumbing & Water</a>
  </div>
  <div id="gridItemRoot">
    <div class="zg-grid-general-faceout" data-asin="B0ABC12345">
      <a class="a-link-normal" href="/dp/B0ABC12345/ref=zg_bsnr_automotive_1">
        <div class="_cDEzb_p13n-sc-css-line-clamp-1_1Fn1y">RV Tank Rinsing Wand 360 Degree Swivel</div>
      </a>
      <span class="p13n-sc-price">$29.99</span>
      <img src="https://m.media-amazon.com/images/I/wand.jpg" alt="RV Tank Rinsing Wand" />
    </div>
  </div>
  <div id="gridItemRoot">
    <div class="zg-grid-general-faceout" data-asin="B0XYZ98765">
      <a class="a-link-normal" href="/dp/B0XYZ98765">
        <div class="_cDEzb_p13n-sc-css-line-clamp-1_1Fn1y">Collapsible RV Stepping Stool With Storage</div>
      </a>
      <span class="p13n-sc-price">$45.50</span>
      <img src="https://m.media-amazon.com/images/I/stool.jpg" alt="Collapsible Stool" />
    </div>
  </div>
</body>
</html>
""" + ("<!-- padding -->\n" * 50)


MOCK_PRODUCT_PAGE_HTML = """<!DOCTYPE html>
<html>
<head><title>RV Tank Rinsing Wand 360 Degree Swivel - Amazon.com</title></head>
<body>
  <span id="productTitle">RV Tank Rinsing Wand 360 Degree Swivel Heavy Duty</span>
  <div id="corePriceDisplay_desktop_feature_div">
    <span class="a-price"><span class="a-offscreen">$29.99</span></span>
  </div>
  <div id="feature-bullets">
    <ul>
      <li><span class="a-list-item">Powerful 360-degree rotating spray removes stubborn black tank deposits</span></li>
      <li><span class="a-list-item">Connects directly to standard RV sewer cleanout fittings</span></li>
    </ul>
  </div>
  <div id="productDetails_db_sections">
    Date First Available: August 12, 2026
  </div>
  <button id="add-to-cart-button">Add to Cart</button>
</body>
</html>
""" + ("<!-- padding -->\n" * 50)


def test_asin_extraction_and_canonicalization() -> None:
    url = "https://www.amazon.com/Some-Fancy-Name/dp/B0ABC12345/ref=zg_bsnr_1?psc=1"
    assert extract_asin(url) == "B0ABC12345"
    assert canonicalize_amazon_url(url) == "https://www.amazon.com/dp/B0ABC12345"


@pytest.mark.asyncio
async def test_category_crawler_mock() -> None:
    mock_client = AsyncMock(spec=ResilientHttpClient)
    mock_client.get_html.return_value = MOCK_NEW_RELEASES_HTML

    crawler = AmazonCategoryCrawler(http_client=mock_client)

    # 1. Discover subcategories
    subcats = await crawler.discover_categories("https://www.amazon.com/gp/new-releases/automotive/2258019011/")
    assert len(subcats) >= 2

    # 2. Crawl products
    products = await crawler.crawl_category_products(
        "https://www.amazon.com/gp/new-releases/automotive/2258019011/"
    )
    assert len(products) == 2
    assert products[0].asin == "B0ABC12345"
    assert products[0].displayed_price == 29.99
    assert products[0].url == "https://www.amazon.com/dp/B0ABC12345"
    assert products[1].asin == "B0XYZ98765"
    assert products[1].displayed_price == 45.50


@pytest.mark.asyncio
async def test_product_verifier_mock() -> None:
    mock_client = AsyncMock(spec=ResilientHttpClient)
    mock_client.get_html.return_value = MOCK_PRODUCT_PAGE_HTML

    verifier = AmazonProductVerifier(http_client=mock_client)
    result = await verifier.verify_product("https://www.amazon.com/dp/B0ABC12345")

    assert result.verification_state == VerificationState.VERIFIED
    assert result.asin == "B0ABC12345"
    assert result.displayed_price == 29.99
    assert "Heavy Duty" in result.title
    assert len(result.bullet_points) == 2
    assert any("August 12, 2026" in e for e in result.newness_evidence)
    assert result.buy_box_available is True
