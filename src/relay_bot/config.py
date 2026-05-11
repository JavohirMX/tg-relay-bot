from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    bot_token: str = Field(alias="BOT_TOKEN")
    admin_telegram_id: int = Field(alias="ADMIN_TELEGRAM_ID")
    database_path: Path = Field(default=Path("data/relay_bot.sqlite3"), alias="DATABASE_PATH")
    rate_limit_window_seconds: int = Field(default=60, alias="RATE_LIMIT_WINDOW_SECONDS")
    rate_limit_max_messages: int = Field(default=20, alias="RATE_LIMIT_MAX_MESSAGES")
    rate_limit_cooldown_seconds: int = Field(default=300, alias="RATE_LIMIT_COOLDOWN_SECONDS")
    welcome_text: str = Field(
        default=(
            "Hi. You can message me here without seeing my personal Telegram account. "
            "Be respectful and avoid spam; abusive messages may be blocked."
        ),
        alias="WELCOME_TEXT",
    )

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @field_validator("bot_token")
    @classmethod
    def bot_token_must_not_be_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("BOT_TOKEN must not be empty")
        return value

    @field_validator(
        "rate_limit_window_seconds",
        "rate_limit_max_messages",
        "rate_limit_cooldown_seconds",
    )
    @classmethod
    def positive_int(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("rate limit values must be positive")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
