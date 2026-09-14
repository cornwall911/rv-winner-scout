"""Application settings loaded from environment variables."""

from functools import lru_cache
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # AI Provider configuration
    # Options: gemini | tokenrouter
    ai_provider: str = Field(default="gemini", alias="AI_PROVIDER")
    ai_model: str = Field(default="gemini-3.8-flash", alias="AI_MODEL")
    ai_api_key: Optional[str] = Field(default=None, alias="AI_API_KEY")

    # TokenRouter (OpenAI-compatible) configuration
    tokenrouter_api_key: Optional[str] = Field(default=None, alias="TOKENROUTER_API_KEY")
    tokenrouter_base_url: str = Field(
        default="https://api.tokenrouter.com/v1", alias="TOKENROUTER_BASE_URL"
    )
    tokenrouter_model: str = Field(
        default="z-ai/glm-5.3-free", alias="TOKENROUTER_MODEL"
    )

    # Google Sheets configuration
    spreadsheet_id: Optional[str] = Field(default=None, alias="SPREADSHEET_ID")
    sheet_name: str = Field(default="RV Research", alias="SHEET_NAME")
    google_sheets_credentials_json: Optional[str] = Field(
        default=None, alias="GOOGLE_SHEETS_CREDENTIALS_JSON"
    )

    # Execution and Mode Controls
    # Options: smoke | small | full
    run_mode: str = Field(default="full", alias="RUN_MODE")
    max_products_per_run: int = Field(default=250, alias="MAX_PRODUCTS_PER_RUN")
    global_deadline_minutes: int = Field(default=45, alias="GLOBAL_DEADLINE_MINUTES")

    # Network, Timing, and Circuit Breaker
    http_timeout_seconds: float = Field(default=20.0, alias="HTTP_TIMEOUT_SECONDS")
    max_retries: int = Field(default=3, alias="MAX_RETRIES")
    polite_delay_min_seconds: float = Field(default=2.0, alias="POLITE_DELAY_MIN_SECONDS")
    polite_delay_max_seconds: float = Field(default=5.0, alias="POLITE_DELAY_MAX_SECONDS")
    circuit_breaker_failures: int = Field(default=3, alias="CIRCUIT_BREAKER_FAILURES")
    circuit_breaker_reset_seconds: float = Field(
        default=600.0, alias="CIRCUIT_BREAKER_RESET_SECONDS"
    )

    # Storage and Logging
    data_dir: str = Field(default="data", alias="DATA_DIR")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    enable_html_snapshots: bool = Field(default=True, alias="ENABLE_HTML_SNAPSHOTS")

    # Reference Winner Benchmark URL
    reference_winner_url: str = Field(
        default="https://www.amazon.com/dp/B0EXAMPLE", alias="REFERENCE_WINNER_URL"
    )

    # Telegram Notifications (Optional)
    telegram_bot_token: Optional[str] = Field(default=None, alias="TELEGRAM_BOT_TOKEN")
    telegram_chat_id: Optional[str] = Field(default=None, alias="TELEGRAM_CHAT_ID")


@lru_cache
def get_settings() -> Settings:
    """Singleton getter for application settings."""
    return Settings()
