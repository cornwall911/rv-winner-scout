import pytest
from rv_winner_scout.adapters.amazon.anti_bot_detector import AntiBotDetector
from rv_winner_scout.domain.exceptions import AntiBotBlockedException


def test_anti_bot_detects_http_403() -> None:
    with pytest.raises(AntiBotBlockedException) as exc_info:
        AntiBotDetector.check_response(
            "https://amazon.com", 403, "<html><body>Forbidden</body></html>"
        )
    assert "HTTP 403 Access Denied" in str(exc_info.value)


def test_anti_bot_detects_captcha_title() -> None:
    html = "<html><head><title>Robot Check</title></head><body>" + ("x" * 1000) + "</body></html>"
    with pytest.raises(AntiBotBlockedException) as exc_info:
        AntiBotDetector.check_response("https://amazon.com", 200, html)
    assert "Amazon Robot Check" in str(exc_info.value)


def test_anti_bot_detects_captcha_phrase() -> None:
    html = "<html><body>Type the characters you see in this image" + ("x" * 1000) + "</body></html>"
    with pytest.raises(AntiBotBlockedException) as exc_info:
        AntiBotDetector.check_response("https://amazon.com", 200, html)
    assert "CAPTCHA / Bot detection pattern" in str(exc_info.value)


def test_anti_bot_detects_dom_anomaly() -> None:
    # Truncated / empty response < 800 bytes
    html = "<html><body>Blocked</body></html>"
    with pytest.raises(AntiBotBlockedException) as exc_info:
        AntiBotDetector.check_response("https://amazon.com", 200, html)
    assert "DOM Anomaly: Incomplete or empty response" in str(exc_info.value)


def test_anti_bot_passes_valid_dom() -> None:
    # Large valid HTML response with no triggers
    html = "<html><head><title>Amazon RV New Releases</title></head><body>" + ("<p>Product Item</p>" * 100) + "</body></html>"
    # Should not raise
    AntiBotDetector.check_response("https://amazon.com", 200, html)
