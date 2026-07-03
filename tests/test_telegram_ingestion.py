import asyncio
import uuid

import pytest
from sqlalchemy import func
from sqlalchemy import select

from app.bot.ingestion import TelegramTextInput
from app.bot.ingestion import persist_text_message
from app.db.models import Message
from app.db.models import ProcessingTask
from app.db.models import User
from app.db.session import get_session_factory


def random_telegram_id() -> int:
    return uuid.uuid4().int % 9_000_000_000_000_000_000


def test_text_message_creates_user_and_message() -> None:
    async def run() -> None:
        telegram_user_id = random_telegram_id()
        telegram_chat_id = random_telegram_id()
        telegram_input = TelegramTextInput(
            telegram_user_id=telegram_user_id,
            username="original_user",
            first_name="Original",
            last_name="User",
            telegram_chat_id=telegram_chat_id,
            telegram_message_id=10,
            text="remember this",
        )

        result = await persist_text_message(telegram_input)

        session_factory = get_session_factory()
        async with session_factory() as session:
            user = await session.scalar(
                select(User).where(User.telegram_user_id == telegram_user_id)
            )
            message = await session.scalar(
                select(Message).where(
                    Message.idempotency_key == telegram_input.idempotency_key
                )
            )

        assert result.inserted is True
        assert user is not None
        assert user.username == "original_user"
        assert message is not None
        assert message.user_id == user.id
        assert message.telegram_chat_id == telegram_chat_id
        assert message.telegram_message_id == 10
        assert message.raw_text == "remember this"
        assert message.input_type == "text"
        assert message.status == "received"
        assert message.idempotency_key == f"telegram:{telegram_chat_id}:10"

        async with session_factory() as session:
            task = await session.scalar(
                select(ProcessingTask).where(
                    ProcessingTask.message_id == message.id
                )
            )
        assert task is not None

    asyncio.run(run())


def test_existing_user_profile_fields_are_updated() -> None:
    async def run() -> None:
        telegram_user_id = random_telegram_id()
        telegram_chat_id = random_telegram_id()

        await persist_text_message(
            TelegramTextInput(
                telegram_user_id=telegram_user_id,
                username="old_username",
                first_name="Old",
                last_name="Name",
                telegram_chat_id=telegram_chat_id,
                telegram_message_id=11,
                text="first note",
            )
        )
        await persist_text_message(
            TelegramTextInput(
                telegram_user_id=telegram_user_id,
                username="new_username",
                first_name="New",
                last_name="Profile",
                telegram_chat_id=telegram_chat_id,
                telegram_message_id=12,
                text="second note",
            )
        )

        session_factory = get_session_factory()
        async with session_factory() as session:
            user = await session.scalar(
                select(User).where(User.telegram_user_id == telegram_user_id)
            )

        assert user is not None
        assert user.username == "new_username"
        assert user.first_name == "New"
        assert user.last_name == "Profile"

    asyncio.run(run())


def test_duplicate_telegram_delivery_creates_one_message() -> None:
    async def run() -> None:
        telegram_user_id = random_telegram_id()
        telegram_chat_id = random_telegram_id()
        telegram_input = TelegramTextInput(
            telegram_user_id=telegram_user_id,
            username="duplicate_user",
            telegram_chat_id=telegram_chat_id,
            telegram_message_id=13,
            text="same note",
        )

        first_result = await persist_text_message(telegram_input)
        second_result = await persist_text_message(telegram_input)

        session_factory = get_session_factory()
        async with session_factory() as session:
            count = await session.scalar(
                select(func.count())
                .select_from(Message)
                .where(Message.idempotency_key == telegram_input.idempotency_key)
            )
            task_count = await session.scalar(
                select(func.count())
                .select_from(ProcessingTask)
                .join(Message)
                .where(Message.idempotency_key == telegram_input.idempotency_key)
            )

        assert first_result.inserted is True
        assert second_result.inserted is False
        assert count == 1
        assert task_count == 1

    asyncio.run(run())


def test_concurrent_duplicate_delivery_creates_one_message_and_task() -> None:
    async def run() -> None:
        telegram_user_id = random_telegram_id()
        telegram_chat_id = random_telegram_id()
        telegram_input = TelegramTextInput(
            telegram_user_id=telegram_user_id,
            telegram_chat_id=telegram_chat_id,
            telegram_message_id=14,
            text="concurrent duplicate",
        )

        results = await asyncio.gather(
            persist_text_message(telegram_input),
            persist_text_message(telegram_input),
        )

        session_factory = get_session_factory()
        async with session_factory() as session:
            message_count = await session.scalar(
                select(func.count())
                .select_from(Message)
                .where(Message.idempotency_key == telegram_input.idempotency_key)
            )
            task_count = await session.scalar(
                select(func.count()).select_from(ProcessingTask)
            )

        assert sorted(result.inserted for result in results) == [False, True]
        assert message_count == 1
        assert task_count == 1

    asyncio.run(run())


def test_duplicate_pre_task_message_does_not_backfill_task() -> None:
    async def run() -> None:
        telegram_user_id = random_telegram_id()
        telegram_chat_id = random_telegram_id()
        telegram_input = TelegramTextInput(
            telegram_user_id=telegram_user_id,
            telegram_chat_id=telegram_chat_id,
            telegram_message_id=15,
            text="legacy source",
        )
        session_factory = get_session_factory()
        async with session_factory() as session:
            user = User(telegram_user_id=telegram_user_id)
            session.add(user)
            await session.flush()
            session.add(
                Message(
                    user_id=user.id,
                    telegram_chat_id=telegram_chat_id,
                    telegram_message_id=15,
                    input_type="text",
                    raw_text="legacy source",
                    status="received",
                    idempotency_key=telegram_input.idempotency_key,
                )
            )
            await session.commit()

        result = await persist_text_message(telegram_input)
        async with session_factory() as session:
            task_count = await session.scalar(
                select(func.count()).select_from(ProcessingTask)
            )

        assert result.inserted is False
        assert task_count == 0

    asyncio.run(run())


def test_task_creation_failure_rolls_back_message(monkeypatch) -> None:
    async def run() -> None:
        telegram_input = TelegramTextInput(
            telegram_user_id=random_telegram_id(),
            telegram_chat_id=random_telegram_id(),
            telegram_message_id=16,
            text="must roll back",
        )

        class FailingProcessingTask:
            def __init__(self, **_values) -> None:
                raise RuntimeError("task creation failed")

        monkeypatch.setattr(
            "app.bot.ingestion.ProcessingTask", FailingProcessingTask
        )
        with pytest.raises(RuntimeError, match="task creation failed"):
            await persist_text_message(telegram_input)

        session_factory = get_session_factory()
        async with session_factory() as session:
            message_count = await session.scalar(
                select(func.count())
                .select_from(Message)
                .where(Message.idempotency_key == telegram_input.idempotency_key)
            )
        assert message_count == 0

    asyncio.run(run())
