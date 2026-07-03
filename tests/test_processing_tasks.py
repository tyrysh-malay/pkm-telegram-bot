import asyncio
import uuid
from datetime import datetime
from datetime import timezone

import pytest
from sqlalchemy import DateTime
from sqlalchemy import Integer
from sqlalchemy import Text
from sqlalchemy import Uuid
from sqlalchemy import func
from sqlalchemy import inspect
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.bot.ingestion import TelegramTextInput
from app.bot.ingestion import persist_text_message
from app.db.models import ProcessingTask
from app.db.session import get_engine
from app.db.session import get_session_factory


def telegram_input() -> TelegramTextInput:
    unique = uuid.uuid4().int % 9_000_000_000_000_000_000
    return TelegramTextInput(
        telegram_user_id=unique,
        telegram_chat_id=-unique,
        telegram_message_id=1,
        text="processing task source",
    )


def test_processing_task_schema_matches_contract() -> None:
    async def run() -> dict[str, object]:
        async with get_engine().connect() as connection:
            return await connection.run_sync(
                lambda sync_connection: {
                    "columns": inspect(sync_connection).get_columns(
                        "processing_tasks"
                    ),
                    "foreign_keys": inspect(sync_connection).get_foreign_keys(
                        "processing_tasks"
                    ),
                    "unique_constraints": inspect(
                        sync_connection
                    ).get_unique_constraints("processing_tasks"),
                    "indexes": inspect(sync_connection).get_indexes(
                        "processing_tasks"
                    ),
                }
            )

    schema = asyncio.run(run())
    columns = {column["name"]: column for column in schema["columns"]}
    assert list(columns) == [
        "id",
        "message_id",
        "task_type",
        "status",
        "attempts",
        "max_attempts",
        "available_at",
        "lease_expires_at",
        "last_error",
        "created_at",
        "updated_at",
    ]
    assert columns["lease_expires_at"]["nullable"] is True
    assert columns["last_error"]["nullable"] is True
    assert all(
        not column["nullable"]
        for name, column in columns.items()
        if name not in {"lease_expires_at", "last_error"}
    )
    assert isinstance(columns["id"]["type"], Uuid)
    assert isinstance(columns["message_id"]["type"], Uuid)
    assert all(
        isinstance(columns[name]["type"], Text)
        for name in ("task_type", "status", "last_error")
    )
    assert all(
        isinstance(columns[name]["type"], Integer)
        for name in ("attempts", "max_attempts")
    )
    assert all(
        isinstance(columns[name]["type"], DateTime)
        and columns[name]["type"].timezone
        for name in (
            "available_at",
            "lease_expires_at",
            "created_at",
            "updated_at",
        )
    )
    assert schema["foreign_keys"][0]["referred_table"] == "messages"
    assert schema["foreign_keys"][0]["options"] == {}
    assert {
        constraint["name"] for constraint in schema["unique_constraints"]
    } == {"uq_processing_tasks_message_id_task_type"}
    assert {
        index["name"] for index in schema["indexes"] if not index["unique"]
    } == {
        "ix_processing_tasks_status_available_at",
        "ix_processing_tasks_status_lease_expires_at",
    }


def test_ingestion_creates_processing_task_with_initial_values() -> None:
    async def run() -> None:
        before = datetime.now(timezone.utc)
        result = await persist_text_message(telegram_input())
        after = datetime.now(timezone.utc)

        session_factory = get_session_factory()
        async with session_factory() as session:
            task = await session.scalar(
                select(ProcessingTask).where(
                    ProcessingTask.message_id == result.message_id
                )
            )

        assert task is not None
        assert task.task_type == "generate_note"
        assert task.status == "pending"
        assert task.attempts == 0
        assert task.max_attempts == 3
        assert before <= task.available_at <= after
        assert task.lease_expires_at is None
        assert task.last_error is None

    asyncio.run(run())


def test_processing_task_message_type_is_unique() -> None:
    async def run() -> None:
        persisted = await persist_text_message(telegram_input())
        assert persisted.message_id is not None
        session_factory = get_session_factory()
        async with session_factory() as session:
            session.add(ProcessingTask(message_id=persisted.message_id))
            with pytest.raises(IntegrityError):
                await session.commit()
            await session.rollback()
            count = await session.scalar(
                select(func.count())
                .select_from(ProcessingTask)
                .where(ProcessingTask.message_id == persisted.message_id)
            )
        assert count == 1

    asyncio.run(run())
