"""Polite randomized rate limiter with jittered delays."""

import asyncio
import random
import time
from typing import Optional


class PoliteRateLimiter:
    """Enforces randomized politeness delays between sequential network requests."""

    def __init__(self, min_delay: float = 2.0, max_delay: float = 5.0) -> None:
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.last_request_time: float = 0.0

    async def wait(self) -> float:
        """Asynchronously sleeps for a jittered duration if needed since the last request."""
        now = time.time()
        elapsed = now - self.last_request_time
        jittered_delay = random.uniform(self.min_delay, self.max_delay)

        if elapsed < jittered_delay:
            to_sleep = jittered_delay - elapsed
            await asyncio.sleep(to_sleep)
            self.last_request_time = time.time()
            return to_sleep

        self.last_request_time = now
        return 0.0

    def wait_sync(self) -> float:
        """Synchronously sleeps for a jittered duration if needed."""
        now = time.time()
        elapsed = now - self.last_request_time
        jittered_delay = random.uniform(self.min_delay, self.max_delay)

        if elapsed < jittered_delay:
            to_sleep = jittered_delay - elapsed
            time.sleep(to_sleep)
            self.last_request_time = time.time()
            return to_sleep

        self.last_request_time = now
        return 0.0
