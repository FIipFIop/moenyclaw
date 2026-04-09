from typing import Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # AI
    openrouter_api_key: str = ""

    # Polymarket
    polymarket_api_key: str = ""
    polymarket_private_key: str = ""
    polymarket_proxy_address: str = ""

    # Hyperliquid
    hyperliquid_private_key: str = ""
    hyperliquid_address: str = ""
    hyperliquid_network: str = "mainnet"

    # Telegram (all optional — bot simply won't start without a token)
    telegram_bot_token: str = ""
    telegram_allowed_user_id: Optional[int] = None  # None = bot accepts no users

    # App
    database_url: str = "sqlite+aiosqlite:///./moneyclaw.sqlite"
    backend_url: str = "http://localhost:8000"
    dashboard_url: str = "http://localhost:3000"
    secret_key: str = ""
    trading_enabled: bool = False
    log_level: str = "INFO"

    # OpenRouter model assignments
    model_master: str = "nvidia/llama-3.1-nemotron-ultra-253b-v1:free"
    model_research: str = "minimax/minimax-m2.5:free"
    model_analysis: str = "google/gemma-4-31b:free"
    model_risk: str = "nvidia/llama-3.1-nemotron-ultra-253b-v1:free"
    model_debate: str = "google/gemma-4-26b-a4b:free"
    model_execution: str = "google/gemma-4-26b-a4b:free"

    @field_validator("telegram_allowed_user_id", mode="before")
    @classmethod
    def parse_user_id(cls, v):
        """Accept empty string or None as 'not set'."""
        if v is None or str(v).strip() == "":
            return None
        try:
            return int(v)
        except (ValueError, TypeError):
            return None


settings = Settings()
