"""Polite randomized rate limiter with jittered delays."""

import asyncio
import random
import time
from typing import Optional


class PoliteRateLimiter:
    """Enforces randomized politeness delays between sequential network requests per provider."""

    def __init__(self, min_delay: float = 2.0, max_delay: float = 5.0) -> None:
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.last_request_time: float = 0.0
        self._provider_last_times: dict[str, float] = {}

    async def wait(self, provider_key: str = "amazon") -> float:
        """Asynchronously sleeps for a jittered duration if needed for the given provider."""
        now = time.time()
        last_time = self._provider_last_times.get(provider_key, 0.0)
        elapsed = now - last_time

        # For Amazon, enforce standard polite jitter to avoid anti-bot/CAPTCHA triggers.
        # For other search providers (DuckDuckGo, Walmart), use lower jittered polite delays.
        if provider_key.lower() == "amazon":
            target_min = self.min_delay
            target_max = self.max_delay
        else:
            target_min = 0.4
            target_max = 1.2

        jittered_delay = random.uniform(target_min, target_max)

        if elapsed < jittered_delay:
            to_sleep = jittered_delay - elapsed
            await asyncio.sleep(to_sleep)
            cur_now = time.time()
            self._provider_last_times[provider_key] = cur_now
            self.last_request_time = cur_now
            return to_sleep

        self._provider_last_times[provider_key] = now
        self.last_request_time = now
        return 0.0

    def wait_sync(self, provider_key: str = "amazon") -> float:
        """Synchronously sleeps for a jittered duration if needed."""
        now = time.time()
        last_time = self._provider_last_times.get(provider_key, 0.0)
        elapsed = now - last_time

        if provider_key.lower() == "amazon":
            target_min = self.min_delay
            target_max = self.max_delay
        else:
            target_min = 0.4
            target_max = 1.2

        jittered_delay = random.uniform(target_min, target_max)

        if elapsed < jittered_delay:
            to_sleep = jittered_delay - elapsed
            time.sleep(to_sleep)
            cur_now = time.time()
            self._provider_last_times[provider_key] = cur_now
            self.last_request_time = cur_now
            return to_sleep

        self._provider_last_times[provider_key] = now
        self.last_request_time = now
        return 0.0
