import asyncio
import uuid

from alembic import command
from alembic.config import Config
from sqlalchemy import text

from app.db.models import Message
from app.db.models import User
from app.db.session import dispose_engine
from app.db.session import get_engine
from app.db.session import get_session_factory


def test_artifact_migration_downgrade_preserves_sources_and_reupgrade() -> None:
    user_id = uuid.uuid4()
    message_id = uuid.uuid4()

    async def seed() -> None:
        session_factory = get_session_factory()
        async with session_factory() as session:
            session.add(
                User(
                    id=user_id,
                    telegram_user_id=uuid.uuid4().int
                    % 9_000_000_000_000_000_000,
                )
            )
            session.add(
                Message(
                    id=message_id,
                    user_id=user_id,
                    telegram_chat_id=1,
                    telegram_message_id=1,
                    input_type="text",
                    raw_text="migration source",
                    status="received",
                    idempotency_key=f"migration:{message_id}",
                )
            )
            await session.commit()

    async def schema_state() -> tuple[str | None, int, int]:
        async with get_engine().connect() as connection:
            artifact_table = await connection.scalar(
                text("SELECT to_regclass('public.artifacts')::text")
            )
            user_count = await connection.scalar(
                text("SELECT count(*) FROM users WHERE id = :id"),
                {"id": user_id},
            )
            message_count = await connection.scalar(
                text("SELECT count(*) FROM messages WHERE id = :id"),
                {"id": message_id},
            )
        return artifact_table, user_count, message_count

    asyncio.run(seed())
    asyncio.run(dispose_engine())
    config = Config("alembic.ini")

    try:
        command.downgrade(config, "0001")
        asyncio.run(dispose_engine())
        assert asyncio.run(schema_state()) == (None, 1, 1)

        asyncio.run(dispose_engine())
        command.upgrade(config, "head")
        asyncio.run(dispose_engine())
        assert asyncio.run(schema_state()) == ("artifacts", 1, 1)
    finally:
        asyncio.run(dispose_engine())
        command.upgrade(config, "head")
        asyncio.run(dispose_engine())
