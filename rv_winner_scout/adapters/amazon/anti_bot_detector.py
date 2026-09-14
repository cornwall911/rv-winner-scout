"""Anti-bot and CAPTCHA detection engine.

Fails closed immediately upon identifying access barriers or challenge pages.
Never attempts to bypass or fabricate content.
"""

from typing import Optional
from bs4 import BeautifulSoup
from rv_winner_scout.domain.exceptions import AntiBotBlockedException


class AntiBotDetector:
    """Detects Amazon CAPTCHA, robot checks, access restrictions, and DOM anomalies."""

    CAPTCHA_INDICATORS = [
        "type the characters you see in this image",
        "robot check",
        "enter the characters you see below",
        "/errors/validatecaptcha",
        "images-amazon.com/captcha/",
        "to discuss automated access to amazon data please contact",
        "sorry, we just need to make sure you're not a robot",
    ]

    ANOMALY_MIN_HTML_LENGTH = 800

    @classmethod
    def check_response(cls, url: str, status_code: int, html: str) -> None:
        """Inspects HTTP status code and DOM content for anti-bot barriers.

        Raises:
            AntiBotBlockedException: If CAPTCHA, block, or anomaly is confirmed.
        """
        # 1. HTTP Status Code barriers
        if status_code in (403, 503):
            raise AntiBotBlockedException(
                source_url=url,
                failure_detail=f"HTTP {status_code} Access Denied / Service Unavailable",
            )
        if status_code == 429:
            raise AntiBotBlockedException(
                source_url=url,
                failure_detail="HTTP 429 Too Many Requests (Rate Limited)",
            )

        # 2. Content-based checks
        html_lower = html.lower()

        # Check for Amazon's explicit captcha title / header
        if "<title>robot check</title>" in html_lower or "<title>503 - " in html_lower:
            raise AntiBotBlockedException(
                source_url=url,
                failure_detail="Amazon Robot Check page encountered",
            )

        for indicator in cls.CAPTCHA_INDICATORS:
            if indicator in html_lower:
                raise AntiBotBlockedException(
                    source_url=url,
                    failure_detail=f"CAPTCHA / Bot detection pattern: '{indicator}'",
                )

        # 3. DOM Anomaly / Incomplete truncated page check
        if len(html.strip()) < cls.ANOMALY_MIN_HTML_LENGTH:
            raise AntiBotBlockedException(
                source_url=url,
                failure_detail=f"DOM Anomaly: Incomplete or empty response ({len(html.strip())} bytes)",
            )
