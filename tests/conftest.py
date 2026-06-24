import asyncio

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import delete

from app.db.models import Message
from app.db.models import User
from app.db.session import dispose_engine
from app.db.session import get_session_factory


@pytest.fixture(scope="session", autouse=True)
def migrated_database() -> None:
    command.upgrade(Config("alembic.ini"), "head")


async def cleanup_database_rows() -> None:
    session_factory = get_session_factory()

    async with session_factory() as session:
        async with session.begin():
            await session.execute(delete(Message))
            await session.execute(delete(User))


@pytest.fixture(autouse=True)
def clean_database() -> None:
    yield

    asyncio.run(dispose_engine())
    asyncio.run(cleanup_database_rows())
    asyncio.run(dispose_engine())
