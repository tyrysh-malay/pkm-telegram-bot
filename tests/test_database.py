import asyncio
import os

from sqlalchemy import text
from sqlalchemy.engine import make_url

from app.db.session import get_engine


def test_pytest_uses_configured_test_database() -> None:
    async def run() -> str:
        async with get_engine().connect() as connection:
            result = await connection.execute(text("SELECT current_database()"))

        return result.scalar_one()

    expected_database = make_url(os.environ["TEST_DATABASE_URL"]).database

    assert asyncio.run(run()) == expected_database


def test_database_connectivity() -> None:
    async def run() -> None:
        async with get_engine().connect() as connection:
            result = await connection.execute(text("SELECT 1"))

        assert result.scalar_one() == 1

    asyncio.run(run())


def test_migration_created_users_and_messages_tables() -> None:
    async def run() -> None:
        async with get_engine().connect() as connection:
            result = await connection.execute(
                text(
                    "SELECT to_regclass('public.users')::text, "
                    "to_regclass('public.messages')::text"
                )
            )

        assert result.one() == ("users", "messages")

    asyncio.run(run())
