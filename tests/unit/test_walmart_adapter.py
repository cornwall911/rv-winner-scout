import pytest
from unittest.mock import AsyncMock
from rv_winner_scout.adapters.http.client import ResilientHttpClient
from rv_winner_scout.adapters.walmart.search_adapter import WalmartSearchAdapter
from rv_winner_scout.domain.enums import WalmartStatus


MOCK_WALMART_FOUND_HTML = """
<html><body>
  <div data-testid="list-view">
    <div data-item-id="12345">
      <a href="/ip/Camco-RV-Tank-Rinse-Wand/123456789">
        <span data-automation-id="product-title">Camco RV Swivel Stik Tank Rinsing Wand</span>
      </a>
      <div data-automation-id="product-price">
        <span class="w_iUH7">$24.88</span>
      </div>
    </div>
  </div>
</body></html>
""" + ("<!-- pad -->\n" * 50)


MOCK_WALMART_BLOCKED_HTML = """
<html><head><title>Access to this page has been denied</title></head>
<body>Please verify you are a human. PerimeterX blocked.</body></html>
"""


@pytest.mark.asyncio
async def test_walmart_found_alternative() -> None:
    mock_client = AsyncMock(spec=ResilientHttpClient)
    mock_client.get_html.return_value = MOCK_WALMART_FOUND_HTML

    adapter = WalmartSearchAdapter(http_client=mock_client)
    result = await adapter.search_and_verify(
        query="rv tank rinsing wand",
        expected_title="RV Tank Rinsing Wand 360 Swivel",
    )

    assert result.status == WalmartStatus.FOUND
    assert result.displayed_price == 24.88
    assert result.url == "https://www.walmart.com/ip/Camco-RV-Tank-Rinse-Wand/123456789"
    assert result.is_direct_alternative is True


@pytest.mark.asyncio
async def test_walmart_anti_bot_blocked_honest_failure() -> None:
    mock_client = AsyncMock(spec=ResilientHttpClient)
    mock_client.get_html.return_value = MOCK_WALMART_BLOCKED_HTML

    adapter = WalmartSearchAdapter(http_client=mock_client)
    result = await adapter.search_and_verify(
        query="rv step stool",
        expected_title="RV Step Stool",
    )

    assert result.status == WalmartStatus.NOT_VERIFIED
    assert "SOURCE UNAVAILABLE" in (result.notes or "")
    assert result.url is None
    assert result.displayed_price is None
