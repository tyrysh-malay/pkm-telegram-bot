from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "PKM Telegram Bot"
    environment: str = "development"
    telegram_bot_enabled: bool = False
    telegram_bot_token: str | None = None
    openai_api_key: str | None = None
    database_url: str | None = None
    test_database_url: str | None = None
    redis_url: str | None = None
    knowledge_base_path: Path = Path("knowledge-base")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
