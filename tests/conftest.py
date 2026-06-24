import asyncio

import pytest
from alembic import command
from alembic.config import Config

from app.db.session import dispose_engine


@pytest.fixture(scope="session", autouse=True)
def migrated_database() -> None:
    command.upgrade(Config("alembic.ini"), "head")


@pytest.fixture(autouse=True)
def clean_database_engine() -> None:
    yield

    asyncio.run(dispose_engine())
