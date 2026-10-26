"""
Scrapling Crawler Adapter for RV Winner Scout.
Provides high-performance, undetected stealth HTTP & browser fetching using Scrapling
(curl_cffi TLS impersonation + Camoufox/Playwright stealth + auto-healing selectors).
"""

import logging
from typing import Optional, Dict, Any, Tuple

logger = logging.getLogger(__name__)

# Graceful optional import so pipeline never crashes if dependency is absent
try:
    import scrapling
    from scrapling import Fetcher, StealthyFetcher, Selector
    SCRAPLING_AVAILABLE = True
    SCRAPLING_VERSION = getattr(scrapling, "__version__", "0.5")
except ImportError:
    scrapling = None  # type: ignore
    Fetcher = None  # type: ignore
    StealthyFetcher = None  # type: ignore
    Selector = None  # type: ignore
    SCRAPLING_AVAILABLE = False
    SCRAPLING_VERSION = "none"


class ScraplingCrawlerAdapter:
    """
    Adapter integrating Scrapling into the RV Scout pipeline.
    
    Architecture:
    - Tier 1 (Fast & Stealthy): Fetcher (impersonating Chrome TLS fingerprints via curl_cffi).
      Low CPU/RAM usage, avoids standard requests/urllib fingerprint bans.
    - Tier 2 (Deep Anti-Bot Fallback): StealthyFetcher (for CAPTCHA / Akamai / Cloudflare challenge bypass).
    """

    def __init__(self, default_timeout: int = 15):
        self.default_timeout = default_timeout
        self.is_enabled = SCRAPLING_AVAILABLE

    @classmethod
    def is_available(cls) -> bool:
        return SCRAPLING_AVAILABLE

    @classmethod
    def get_version(cls) -> str:
        return SCRAPLING_VERSION

    def fetch(self, url: str, force_stealth: bool = False, headers: Optional[Dict[str, str]] = None) -> Tuple[int, str]:
        """
        Fetch HTML content from a target URL.
        Returns: (status_code, html_content)
        """
        if not self.is_enabled:
            raise RuntimeError("Scrapling is not installed in the current environment.")

        # If force_stealth is requested, skip straight to StealthyFetcher
        if force_stealth and StealthyFetcher is not None:
            logger.info("Using Scrapling StealthyFetcher for %s", url)
            try:
                fetcher = StealthyFetcher()
                response = fetcher.fetch(url)
                return getattr(response, "status", 200), getattr(response, "text", "")
            except Exception as e:
                logger.warning("StealthyFetcher failed on %s: %s", url, e)

        # Primary Fast Tier: Fetcher
        try:
            fetcher = Fetcher()
            kwargs: Dict[str, Any] = {"timeout": self.default_timeout}
            if headers:
                kwargs["headers"] = headers
            response = fetcher.get(url, **kwargs)
            status = getattr(response, "status_code", getattr(response, "status", 200))
            text = getattr(response, "text", "")

            # If fast tier hits a 403 or captcha page and StealthyFetcher is available, attempt fallback
            if (status in (403, 429, 503) or "Robot Check" in text) and StealthyFetcher is not None:
                logger.info("Fast tier blocked (%s). Escalating to Scrapling StealthyFetcher for %s", status, url)
                stealth_fetcher = StealthyFetcher()
                stealth_resp = stealth_fetcher.fetch(url)
                return getattr(stealth_resp, "status", 200), getattr(stealth_resp, "text", "")

            return status, text
        except Exception as e:
            logger.error("Scrapling Fetcher failed on %s: %s", url, e)
            raise

    def parse_dom(self, html_text: str) -> Optional[Any]:
        """Wrap HTML string in Scrapling Selector for auto-healing / CSS / XPath selection."""
        if not self.is_enabled or Selector is None:
            return None
        return Selector(html_text)
