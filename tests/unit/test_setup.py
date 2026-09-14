import pytest
import rv_winner_scout
from rv_winner_scout.domain.exceptions import (
    AntiBotBlockedException,
    AITokenBudgetExhaustedError,
    ScoutException,
)


def test_package_version() -> None:
    assert rv_winner_scout.__version__ == "0.1.0"


def test_anti_bot_exception_formatting() -> None:
    exc = AntiBotBlockedException("https://amazon.com/dp/B000", "Amazon CAPTCHA Challenge")
    assert "SOURCE UNAVAILABLE — Amazon CAPTCHA Challenge at https://amazon.com/dp/B000" in str(exc)
    assert isinstance(exc, ScoutException)


def test_token_budget_exhausted_exception() -> None:
    exc = AITokenBudgetExhaustedError("Reasoning consumed tokens without answer")
    assert isinstance(exc, ScoutException)
