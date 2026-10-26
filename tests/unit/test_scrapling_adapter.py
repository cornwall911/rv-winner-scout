import pytest
from unittest.mock import MagicMock, patch
from rv_winner_scout.adapters.scrapling_adapter import ScraplingCrawlerAdapter, SCRAPLING_AVAILABLE


def test_scrapling_adapter_status():
    adapter = ScraplingCrawlerAdapter()
    assert adapter.is_available() is True
    assert adapter.get_version() != "none"


def test_scrapling_parse_dom():
    adapter = ScraplingCrawlerAdapter()
    sample_html = '<html><body><span class="a-price-whole">49</span><span class="a-price-fraction">99</span></body></html>'
    selector = adapter.parse_dom(sample_html)
    assert selector is not None
    # Verify CSS selector support
    el = selector.css(".a-price-whole")
    assert el is not None


def test_scrapling_fetch_fast_tier_mock():
    adapter = ScraplingCrawlerAdapter()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = "<html><body>Amazon Mock Page</body></html>"

    with patch("rv_winner_scout.adapters.scrapling_adapter.Fetcher") as mock_fetcher_cls:
        mock_instance = MagicMock()
        mock_instance.get.return_value = mock_response
        mock_fetcher_cls.return_value = mock_instance

        status, text = adapter.fetch("https://www.amazon.com/dp/B0TEST001")
        assert status == 200
        assert "Amazon Mock Page" in text
        mock_instance.get.assert_called_once()
