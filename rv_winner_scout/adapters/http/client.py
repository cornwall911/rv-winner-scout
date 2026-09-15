"""Resilient HTTP client with circuit breaking, rate limiting, and realistic headers."""

import hashlib
import os
import random
from typing import Dict, List, Optional
import httpx

from rv_winner_scout.adapters.http.circuit_breaker import CircuitBreaker
from rv_winner_scout.adapters.http.rate_limiter import PoliteRateLimiter
from rv_winner_scout.config.settings import Settings, get_settings
from rv_winner_scout.domain.exceptions import ScoutException


# Modern realistic Desktop User-Agents and consistent Client Hints
DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"

DESKTOP_USER_AGENTS = [
    DEFAULT_USER_AGENT,
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
]


class ResilientHttpClient:
    """Provides resilient HTTP communications respecting anti-bot limits and circuit breaking."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        circuit_breaker: Optional[CircuitBreaker] = None,
        rate_limiter: Optional[PoliteRateLimiter] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.circuit_breaker = circuit_breaker or CircuitBreaker(
            failure_threshold=self.settings.circuit_breaker_failures,
            reset_timeout_seconds=self.settings.circuit_breaker_reset_seconds,
        )
        self.rate_limiter = rate_limiter or PoliteRateLimiter(
            min_delay=self.settings.polite_delay_min_seconds,
            max_delay=self.settings.polite_delay_max_seconds,
        )
        # Consistent session-level User-Agent to prevent WAF fingerprinting
        self.session_user_agent = random.choice(DESKTOP_USER_AGENTS)

        # Support proxy if configured via environment (e.g. residential/datacenter proxy)
        proxy_url = (
            os.environ.get("AMAZON_PROXY_URL")
            or os.environ.get("HTTPS_PROXY")
            or os.environ.get("HTTP_PROXY")
        )

        client_kwargs = {
            "timeout": self.settings.http_timeout_seconds,
            "follow_redirects": True,
            "limits": httpx.Limits(max_keepalive_connections=20, max_connections=50, keepalive_expiry=30.0),
            "headers": {
                "User-Agent": self.session_user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "cross-site",
                "Sec-Fetch-User": "?1",
                "sec-ch-ua": '"Chromium";v="133", "Not(A:Brand";v="99", "Google Chrome";v="133"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Windows"',
            },
            "cookies": {
                "i18n-prefs": "USD",
                "lc-main": "en_US",
            },
        }
        if proxy_url:
            client_kwargs["proxy"] = proxy_url

        self.client = httpx.AsyncClient(**client_kwargs)

    def _get_headers(self, url: str) -> Dict[str, str]:
        is_amazon = "amazon.com" in url
        headers = {
            "User-Agent": self.session_user_agent,
            "Referer": "https://www.amazon.com/gp/new-releases/automotive/2258019011" if is_amazon else "https://www.google.com/",
            "Sec-Fetch-Site": "same-origin" if is_amazon else "cross-site",
        }
        return headers

    async def get_html(self, url: str, provider_key: str = "amazon") -> str:
        """Executes a polite GET request under circuit breaker supervision with smart cooling-off retry."""
        import asyncio

        self.circuit_breaker.check_can_execute(provider_key)
        await self.rate_limiter.wait(provider_key=provider_key)

        max_attempts = 2
        last_exception = None

        for attempt in range(1, max_attempts + 1):
            try:
                response = await self.client.get(url, headers=self._get_headers(url))
                html = response.text

                # If Amazon returns 503 or bot challenge on first attempt, cool down and retry politely once
                if attempt < max_attempts and (
                    response.status_code in (503, 429)
                    or "to discuss automated access" in html.lower()
                    or "robot check" in html.lower()
                ):
                    await asyncio.sleep(random.uniform(2.5, 4.5))
                    continue

                # Save immutable raw snapshot if enabled
                if self.settings.enable_html_snapshots:
                    self._save_snapshot(url, html)

                self.circuit_breaker.record_success(provider_key)
                return html
            except Exception as e:
                last_exception = e
                if attempt < max_attempts:
                    await asyncio.sleep(random.uniform(2.0, 3.5))
                    continue
                self.circuit_breaker.record_failure(provider_key)
                raise last_exception

    def _save_snapshot(self, url: str, html: str) -> None:
        try:
            snapshot_dir = os.path.join(self.settings.data_dir, "snapshots")
            os.makedirs(snapshot_dir, exist_ok=True)
            url_hash = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
            file_path = os.path.join(snapshot_dir, f"{url_hash}.html")
            with open(file_path, "w", encoding="utf-8", errors="replace") as f:
                f.write(html)
        except Exception:
            pass  # Snapshot failures must never crash the pipeline

    async def close(self) -> None:
        await self.client.aclose()
