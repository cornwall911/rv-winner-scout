import time
import pytest
from rv_winner_scout.adapters.http.circuit_breaker import CircuitBreaker, CircuitState
from rv_winner_scout.domain.exceptions import CircuitBreakerOpenException


def test_circuit_breaker_starts_closed() -> None:
    cb = CircuitBreaker(failure_threshold=3, reset_timeout_seconds=1.0)
    assert cb.get_state("amazon") == CircuitState.CLOSED
    cb.check_can_execute("amazon")  # Should not raise


def test_circuit_breaker_trips_to_open() -> None:
    cb = CircuitBreaker(failure_threshold=3, reset_timeout_seconds=0.2)
    cb.record_failure("amazon")
    assert cb.get_state("amazon") == CircuitState.CLOSED
    cb.record_failure("amazon")
    assert cb.get_state("amazon") == CircuitState.CLOSED
    cb.record_failure("amazon")
    assert cb.get_state("amazon") == CircuitState.OPEN

    with pytest.raises(CircuitBreakerOpenException) as exc_info:
        cb.check_can_execute("amazon")
    assert "Circuit breaker for amazon is OPEN" in str(exc_info.value)


def test_circuit_breaker_half_open_and_reset() -> None:
    cb = CircuitBreaker(failure_threshold=2, reset_timeout_seconds=0.1)
    cb.record_failure("test")
    cb.record_failure("test")
    assert cb.get_state("test") == CircuitState.OPEN

    time.sleep(0.15)
    # State transitions to HALF_OPEN after timeout
    assert cb.get_state("test") == CircuitState.HALF_OPEN

    # Success closes the circuit
    cb.record_success("test")
    assert cb.get_state("test") == CircuitState.CLOSED
    assert cb.failure_counts["test"] == 0
