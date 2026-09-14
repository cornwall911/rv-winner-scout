"""Resilient 3-state Circuit Breaker (CLOSED, OPEN, HALF_OPEN) with cooldown timers."""

import time
from enum import Enum
from typing import Dict, Optional

from rv_winner_scout.domain.exceptions import CircuitBreakerOpenException


class CircuitState(str, Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreaker:
    """Manages circuit state per provider or host to prevent cascading failures."""

    def __init__(self, failure_threshold: int = 3, reset_timeout_seconds: float = 600.0) -> None:
        self.failure_threshold = failure_threshold
        self.reset_timeout_seconds = reset_timeout_seconds
        self.failure_counts: Dict[str, int] = {}
        self.state_map: Dict[str, CircuitState] = {}
        self.last_failure_times: Dict[str, float] = {}

    def get_state(self, key: str) -> CircuitState:
        current_state = self.state_map.get(key, CircuitState.CLOSED)
        if current_state == CircuitState.OPEN:
            last_fail = self.last_failure_times.get(key, 0.0)
            elapsed = time.time() - last_fail
            if elapsed >= self.reset_timeout_seconds:
                self.state_map[key] = CircuitState.HALF_OPEN
                return CircuitState.HALF_OPEN
        return current_state

    def check_can_execute(self, key: str) -> None:
        """Throws CircuitBreakerOpenException if the circuit for this key is OPEN."""
        state = self.get_state(key)
        if state == CircuitState.OPEN:
            last_fail = self.last_failure_times.get(key, 0.0)
            elapsed = time.time() - last_fail
            remaining = max(0.0, self.reset_timeout_seconds - elapsed)
            raise CircuitBreakerOpenException(provider_name=key, reset_eta_seconds=remaining)

    def record_success(self, key: str) -> None:
        """Records a successful operation, resetting failure counter and closing circuit."""
        self.failure_counts[key] = 0
        self.state_map[key] = CircuitState.CLOSED

    def record_failure(self, key: str) -> None:
        """Records an operational failure; trips circuit to OPEN once threshold is met."""
        now = time.time()
        self.last_failure_times[key] = now
        count = self.failure_counts.get(key, 0) + 1
        self.failure_counts[key] = count

        if count >= self.failure_threshold or self.get_state(key) == CircuitState.HALF_OPEN:
            self.state_map[key] = CircuitState.OPEN
