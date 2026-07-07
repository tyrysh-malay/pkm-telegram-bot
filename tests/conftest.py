import asyncio
import os

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import delete
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine

from app.settings import Settings
from app.settings import get_settings


def _database_name(database_url: str, setting_name: str) -> str:
    database_name = make_url(database_url).database
    if not database_name:
        raise RuntimeError(f"{setting_name} must include a database name")

    return database_name


def _configure_test_database_url() -> str:
    settings = Settings()
    database_url = settings.database_url
    test_database_url = settings.test_database_url

    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured")
    if not test_database_url:
        raise RuntimeError("TEST_DATABASE_URL is not configured")

    database_name = _database_name(database_url, "DATABASE_URL")
    test_database_name = _database_name(test_database_url, "TEST_DATABASE_URL")

    if database_url == test_database_url or database_name == test_database_name:
        raise RuntimeError(
            "TEST_DATABASE_URL must target a different database than DATABASE_URL"
        )

    os.environ["DATABASE_URL"] = test_database_url
    get_settings.cache_clear()

    return test_database_url


TEST_DATABASE_URL = _configure_test_database_url()

from app.db.models import AIEnrichment
from app.db.models import Artifact
from app.db.models import Message
from app.db.models import ProcessingTask
from app.db.models import User
from app.db.session import dispose_engine
from app.db.session import get_session_factory


def _quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


async def _ensure_test_database_exists(database_url: str) -> None:
    test_url = make_url(database_url)
    test_database_name = _database_name(database_url, "TEST_DATABASE_URL")
    maintenance_url = test_url.set(database="postgres")
    maintenance_engine = create_async_engine(
        maintenance_url,
        isolation_level="AUTOCOMMIT",
    )

    try:
        async with maintenance_engine.connect() as connection:
            exists = await connection.scalar(
                text("SELECT 1 FROM pg_database WHERE datname = :database_name"),
                {"database_name": test_database_name},
            )

            if exists is None:
                await connection.execute(
                    text(f"CREATE DATABASE {_quote_identifier(test_database_name)}")
                )
    finally:
        await maintenance_engine.dispose()


@pytest.fixture(scope="session", autouse=True)
def migrated_database() -> None:
    asyncio.run(_ensure_test_database_exists(TEST_DATABASE_URL))
    asyncio.run(dispose_engine())
    command.upgrade(Config("alembic.ini"), "head")


async def cleanup_database_rows() -> None:
    session_factory = get_session_factory()

    async with session_factory() as session:
        async with session.begin():
            await session.execute(delete(ProcessingTask))
            await session.execute(delete(AIEnrichment))
            await session.execute(delete(Artifact))
            await session.execute(delete(Message))
            await session.execute(delete(User))


@pytest.fixture(autouse=True)
def clean_database() -> None:
    asyncio.run(dispose_engine())
    asyncio.run(cleanup_database_rows())
    asyncio.run(dispose_engine())

    try:
        yield
    finally:
        asyncio.run(dispose_engine())
        asyncio.run(cleanup_database_rows())
        asyncio.run(dispose_engine())
