import asyncio

from sqlalchemy import text

from app.db.session import get_engine


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
