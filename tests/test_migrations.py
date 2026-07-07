import asyncio
import uuid

from alembic import command
from alembic.config import Config
from sqlalchemy import text

from app.db.models import AIEnrichment
from app.db.models import Artifact
from app.db.models import Message
from app.db.models import ProcessingTask
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


def test_processing_task_migration_preserves_sources_and_does_not_backfill() -> None:
    user_id = uuid.uuid4()
    message_id = uuid.uuid4()
    artifact_id = uuid.uuid4()

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
                    telegram_chat_id=2,
                    telegram_message_id=2,
                    input_type="text",
                    raw_text="processing migration source",
                    status="done",
                    idempotency_key=f"migration:{message_id}",
                )
            )
            session.add(
                Artifact(
                    id=artifact_id,
                    message_id=message_id,
                    artifact_type="note",
                    title="Migration",
                    slug="migration",
                    file_path=f"inbox/{message_id}.md",
                )
            )
            session.add(ProcessingTask(message_id=message_id))
            await session.commit()

    async def state() -> tuple[str | None, int, int, int, str]:
        async with get_engine().connect() as connection:
            task_table = await connection.scalar(
                text("SELECT to_regclass('public.processing_tasks')::text")
            )
            user_count = await connection.scalar(
                text("SELECT count(*) FROM users WHERE id = :id"), {"id": user_id}
            )
            message_count = await connection.scalar(
                text("SELECT count(*) FROM messages WHERE id = :id"),
                {"id": message_id},
            )
            artifact_count = await connection.scalar(
                text("SELECT count(*) FROM artifacts WHERE id = :id"),
                {"id": artifact_id},
            )
            status = await connection.scalar(
                text("SELECT status FROM messages WHERE id = :id"),
                {"id": message_id},
            )
        return task_table, user_count, message_count, artifact_count, status

    asyncio.run(seed())
    asyncio.run(dispose_engine())
    config = Config("alembic.ini")

    try:
        command.downgrade(config, "0002")
        asyncio.run(dispose_engine())
        assert asyncio.run(state()) == (None, 1, 1, 1, "done")

        asyncio.run(dispose_engine())
        command.upgrade(config, "head")
        asyncio.run(dispose_engine())
        assert asyncio.run(state()) == ("processing_tasks", 1, 1, 1, "done")

        async def task_count() -> int:
            async with get_engine().connect() as connection:
                return await connection.scalar(
                    text("SELECT count(*) FROM processing_tasks")
                )

        asyncio.run(dispose_engine())
        assert asyncio.run(task_count()) == 0
    finally:
        asyncio.run(dispose_engine())
        command.upgrade(config, "head")
        asyncio.run(dispose_engine())


def test_git_commit_sha_migration_downgrade_and_reupgrade_preserves_state() -> None:
    user_id = uuid.uuid4()
    message_id = uuid.uuid4()
    artifact_id = uuid.uuid4()
    task_id = uuid.uuid4()

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
                    telegram_chat_id=3,
                    telegram_message_id=3,
                    input_type="text",
                    raw_text="git migration source",
                    status="done",
                    idempotency_key=f"migration:{message_id}",
                )
            )
            session.add(
                Artifact(
                    id=artifact_id,
                    message_id=message_id,
                    artifact_type="note",
                    title="Git migration",
                    slug="git-migration",
                    file_path=f"inbox/{message_id}.md",
                )
            )
            session.add(
                ProcessingTask(
                    id=task_id,
                    message_id=message_id,
                    status="succeeded",
                )
            )
            await session.commit()

    async def state() -> tuple[bool, int, int, int, int, str]:
        async with get_engine().connect() as connection:
            sha_column = await connection.scalar(
                text(
                    "SELECT count(*) FROM information_schema.columns "
                    "WHERE table_schema = 'public' AND table_name = 'artifacts' "
                    "AND column_name = 'git_commit_sha'"
                )
            )
            counts = []
            for table, identifier in (
                ("users", user_id),
                ("messages", message_id),
                ("artifacts", artifact_id),
                ("processing_tasks", task_id),
            ):
                counts.append(
                    await connection.scalar(
                        text(f"SELECT count(*) FROM {table} WHERE id = :id"),
                        {"id": identifier},
                    )
                )
            status = await connection.scalar(
                text("SELECT status FROM messages WHERE id = :id"),
                {"id": message_id},
            )
        return bool(sha_column), *counts, status

    asyncio.run(seed())
    asyncio.run(dispose_engine())
    config = Config("alembic.ini")

    try:
        assert asyncio.run(state()) == (True, 1, 1, 1, 1, "done")
        command.downgrade(config, "0003")
        asyncio.run(dispose_engine())
        assert asyncio.run(state()) == (False, 1, 1, 1, 1, "done")

        command.upgrade(config, "0004")
        asyncio.run(dispose_engine())
        assert asyncio.run(state()) == (True, 1, 1, 1, 1, "done")

        async def sha_value() -> str | None:
            async with get_engine().connect() as connection:
                return await connection.scalar(
                    text("SELECT git_commit_sha FROM artifacts WHERE id = :id"),
                    {"id": artifact_id},
                )

        asyncio.run(dispose_engine())
        assert asyncio.run(sha_value()) is None
    finally:
        asyncio.run(dispose_engine())
        command.upgrade(config, "head")
        asyncio.run(dispose_engine())


def test_ai_enrichment_migration_downgrade_and_reupgrade_preserves_other_state() -> None:
    user_id = uuid.uuid4()
    message_id = uuid.uuid4()
    artifact_id = uuid.uuid4()
    task_id = uuid.uuid4()

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
                    telegram_chat_id=4,
                    telegram_message_id=4,
                    input_type="text",
                    raw_text="ai migration source",
                    status="done",
                    idempotency_key=f"migration:{message_id}",
                )
            )
            session.add(
                Artifact(
                    id=artifact_id,
                    message_id=message_id,
                    artifact_type="note",
                    title="AI migration",
                    slug="ai-migration",
                    file_path=f"inbox/{message_id}.md",
                )
            )
            session.add(
                ProcessingTask(
                    id=task_id,
                    message_id=message_id,
                    status="succeeded",
                )
            )
            await session.flush()
            session.add(
                AIEnrichment(
                    message_id=message_id,
                    source_artifact_id=artifact_id,
                    source_content_sha256="a" * 64,
                    provider="openai",
                    model="gpt-test",
                    prompt_version=1,
                    schema_version=1,
                    result_json={
                        "title": "Title",
                        "summary": "Summary",
                        "key_points": [],
                        "tags": [],
                        "action_items": [],
                    },
                )
            )
            await session.commit()

    async def state() -> tuple[str | None, int, int, int, int, str]:
        async with get_engine().connect() as connection:
            ai_table = await connection.scalar(
                text("SELECT to_regclass('public.ai_enrichments')::text")
            )
            counts = []
            for table, identifier in (
                ("users", user_id),
                ("messages", message_id),
                ("artifacts", artifact_id),
                ("processing_tasks", task_id),
            ):
                counts.append(
                    await connection.scalar(
                        text(f"SELECT count(*) FROM {table} WHERE id = :id"),
                        {"id": identifier},
                    )
                )
            status = await connection.scalar(
                text("SELECT status FROM messages WHERE id = :id"),
                {"id": message_id},
            )
        return ai_table, *counts, status

    asyncio.run(seed())
    asyncio.run(dispose_engine())
    config = Config("alembic.ini")

    try:
        assert asyncio.run(state()) == ("ai_enrichments", 1, 1, 1, 1, "done")
        command.downgrade(config, "0004")
        asyncio.run(dispose_engine())
        assert asyncio.run(state()) == (None, 1, 1, 1, 1, "done")

        command.upgrade(config, "0005")
        asyncio.run(dispose_engine())
        assert asyncio.run(state()) == ("ai_enrichments", 1, 1, 1, 1, "done")

        async def ai_count() -> int:
            async with get_engine().connect() as connection:
                return await connection.scalar(
                    text("SELECT count(*) FROM ai_enrichments")
                )

        asyncio.run(dispose_engine())
        assert asyncio.run(ai_count()) == 0
    finally:
        asyncio.run(dispose_engine())
        command.upgrade(config, "head")
        asyncio.run(dispose_engine())
