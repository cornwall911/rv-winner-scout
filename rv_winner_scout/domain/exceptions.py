"""Domain-specific exceptions for RV Winner Scout.

Enforces fail-closed semantics, provenance, and honest failure tracking.
"""


class ScoutException(Exception):
    """Base exception for all domain and operational failures."""


class AntiBotBlockedException(ScoutException):
    """Raised when an anti-bot check, CAPTCHA, or access denial is encountered.

    The system must fail closed, record exact reason, and trip the circuit breaker.
    Never attempt to bypass.
    """

    def __init__(self, source_url: str, failure_detail: str) -> None:
        self.source_url = source_url
        self.failure_detail = failure_detail
        super().__init__(f"SOURCE UNAVAILABLE — {failure_detail} at {source_url}")


class CircuitBreakerOpenException(ScoutException):
    """Raised when an operation is attempted against a provider whose circuit is open."""

    def __init__(self, provider_name: str, reset_eta_seconds: float) -> None:
        self.provider_name = provider_name
        self.reset_eta_seconds = reset_eta_seconds
        super().__init__(
            f"Circuit breaker for {provider_name} is OPEN. Cooldown remaining: {reset_eta_seconds:.1f}s"
        )


class RateLimitExceededException(ScoutException):
    """Raised when an external service responds with rate-limiting / HTTP 429."""


class VerificationFailedException(ScoutException):
    """Raised when a candidate product page fails verification criteria."""


class AIProviderError(ScoutException):
    """Base exception for AI provider communication or response issues."""


class AITokenBudgetExhaustedError(AIProviderError):
    """Raised when completion tokens are exhausted by reasoning tokens and content is null.

    Required for GLM/TokenRouter models to prevent treating incomplete reasoning as answer.
    """


class AISchemaValidationError(AIProviderError):
    """Raised when an AI provider returns output that violates the expected schema."""


class GoogleSheetsError(ScoutException):
    """Raised when Google Sheets API operations fail or transaction rollback is triggered."""


class RunLockActiveError(ScoutException):
    """Raised when another instance of the scout is currently holding the run lock."""


class DeadlineExceededError(ScoutException):
    """Raised when the global execution deadline is reached."""
