import asyncio
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.db.models import Message
from app.db.models import User
from app.db.session import get_session_factory


def random_telegram_id() -> int:
    return uuid.uuid4().int % 9_000_000_000_000_000_000


def test_telegram_user_id_is_unique() -> None:
    async def run() -> None:
        session_factory = get_session_factory()
        telegram_user_id = random_telegram_id()

        async with session_factory() as session:
            session.add_all(
                [
                    User(telegram_user_id=telegram_user_id),
                    User(telegram_user_id=telegram_user_id),
                ]
            )

            with pytest.raises(IntegrityError):
                await session.commit()

            await session.rollback()

    asyncio.run(run())


def test_message_idempotency_key_is_unique() -> None:
    async def run() -> None:
        session_factory = get_session_factory()
        telegram_user_id = random_telegram_id()
        idempotency_key = f"telegram:{telegram_user_id}:1"

        async with session_factory() as session:
            user = User(telegram_user_id=telegram_user_id)
            session.add(user)
            await session.flush()

            session.add_all(
                [
                    Message(
                        user_id=user.id,
                        telegram_chat_id=telegram_user_id,
                        telegram_message_id=1,
                        input_type="text",
                        raw_text="hello",
                        status="received",
                        idempotency_key=idempotency_key,
                    ),
                    Message(
                        user_id=user.id,
                        telegram_chat_id=telegram_user_id,
                        telegram_message_id=1,
                        input_type="text",
                        raw_text="hello again",
                        status="received",
                        idempotency_key=idempotency_key,
                    ),
                ]
            )

            with pytest.raises(IntegrityError):
                await session.commit()

            await session.rollback()

    asyncio.run(run())


def test_message_can_reference_user() -> None:
    async def run() -> None:
        session_factory = get_session_factory()
        telegram_user_id = random_telegram_id()

        async with session_factory() as session:
            user = User(
                telegram_user_id=telegram_user_id,
                username="pkm_user",
                first_name="PKM",
            )
            session.add(user)
            await session.flush()

            message = Message(
                user_id=user.id,
                telegram_chat_id=telegram_user_id,
                telegram_message_id=2,
                input_type="text",
                raw_text="save this",
                status="received",
                idempotency_key=f"telegram:{telegram_user_id}:2",
            )
            session.add(message)
            await session.commit()

            result = await session.execute(
                select(Message.user_id).where(Message.id == message.id)
            )

        assert result.scalar_one() == user.id

    asyncio.run(run())
