from functools import lru_cache
from pathlib import Path
from typing import Annotated
from typing import Self

from pydantic import Field
from pydantic import Strict
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


TelegramUserId = Annotated[int, Strict(), Field(gt=0, le=2**63 - 1)]


class Settings(BaseSettings):
    app_name: str = "PKM Telegram Bot"
    environment: str = "development"
    telegram_bot_enabled: bool = False
    telegram_bot_token: str | None = None
    telegram_allowed_user_ids: frozenset[TelegramUserId] = frozenset()
    openai_api_key: str | None = None
    database_url: str | None = None
    test_database_url: str | None = None
    redis_url: str = "redis://redis:6379/0"
    task_dispatcher_enabled: bool = False
    knowledge_base_path: Path = Path("knowledge-base")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @model_validator(mode="after")
    def validate_enabled_telegram_configuration(self) -> Self:
        if not self.telegram_bot_enabled:
            return self

        missing: list[str] = []
        if not self.telegram_bot_token or not self.telegram_bot_token.strip():
            missing.append("TELEGRAM_BOT_TOKEN must be non-blank")
        if not self.telegram_allowed_user_ids:
            missing.append("TELEGRAM_ALLOWED_USER_IDS must contain at least one user ID")
        if missing:
            raise ValueError(
                "invalid enabled Telegram configuration: " + "; ".join(missing)
            )

        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
