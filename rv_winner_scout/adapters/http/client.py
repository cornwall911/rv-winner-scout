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


# Modern realistic Desktop User-Agents
DESKTOP_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:134.0) Gecko/20100101 Firefox/134.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36 Edg/133.0.0.0",
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
        self.client = httpx.AsyncClient(
            timeout=self.settings.http_timeout_seconds,
            follow_redirects=True,
            headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
            },
        )

    def _get_headers(self) -> Dict[str, str]:
        return {
            "User-Agent": random.choice(DESKTOP_USER_AGENTS),
        }

    async def get_html(self, url: str, provider_key: str = "amazon") -> str:
        """Executes a polite GET request under circuit breaker supervision."""
        self.circuit_breaker.check_can_execute(provider_key)
        await self.rate_limiter.wait()

        try:
            response = await self.client.get(url, headers=self._get_headers())
            html = response.text

            # Save immutable raw snapshot if enabled
            if self.settings.enable_html_snapshots:
                self._save_snapshot(url, html)

            self.circuit_breaker.record_success(provider_key)
            return html
        except Exception as e:
            self.circuit_breaker.record_failure(provider_key)
            raise e

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
