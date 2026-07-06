import asyncio
import uuid

import pytest
from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.db.models import Artifact
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


def test_artifact_constraints_and_message_relation() -> None:
    async def run() -> None:
        session_factory = get_session_factory()
        telegram_user_id = random_telegram_id()

        async with session_factory() as session:
            user = User(telegram_user_id=telegram_user_id)
            session.add(user)
            await session.flush()
            message = Message(
                user_id=user.id,
                telegram_chat_id=telegram_user_id,
                telegram_message_id=3,
                input_type="text",
                raw_text="artifact source",
                status="received",
                idempotency_key=f"telegram:{telegram_user_id}:3",
            )
            session.add(message)
            await session.flush()
            artifact = Artifact(
                message_id=message.id,
                artifact_type="note",
                title="Artifact",
                slug="artifact",
                file_path=f"inbox/{message.id}.md",
            )
            session.add(artifact)
            await session.commit()

            result = await session.scalar(
                select(Artifact).where(Artifact.id == artifact.id)
            )

        assert result is not None
        assert result.message_id == message.id
        assert result.git_commit_sha is None

    asyncio.run(run())


def test_artifact_git_commit_sha_can_store_full_object_id() -> None:
    async def run() -> None:
        session_factory = get_session_factory()
        telegram_user_id = random_telegram_id()
        commit_sha = "a" * 64

        async with session_factory() as session:
            user = User(telegram_user_id=telegram_user_id)
            session.add(user)
            await session.flush()
            message = Message(
                user_id=user.id,
                telegram_chat_id=telegram_user_id,
                telegram_message_id=30,
                input_type="text",
                raw_text="published artifact",
                status="done",
                idempotency_key=f"telegram:{telegram_user_id}:30",
            )
            session.add(message)
            await session.flush()
            artifact = Artifact(
                message_id=message.id,
                artifact_type="note",
                title="Published",
                slug="published",
                file_path="inbox/published.md",
                git_commit_sha=commit_sha,
            )
            session.add(artifact)
            await session.commit()

            stored = await session.scalar(
                select(Artifact.git_commit_sha).where(Artifact.id == artifact.id)
            )

        assert stored == commit_sha

    asyncio.run(run())


@pytest.mark.parametrize("duplicate", ("message_type", "file_path"))
def test_artifact_uniqueness_constraints(duplicate: str) -> None:
    async def run() -> None:
        session_factory = get_session_factory()
        telegram_user_id = random_telegram_id()

        async with session_factory() as session:
            user = User(telegram_user_id=telegram_user_id)
            session.add(user)
            await session.flush()
            messages = [
                Message(
                    user_id=user.id,
                    telegram_chat_id=telegram_user_id,
                    telegram_message_id=index,
                    input_type="text",
                    raw_text="source",
                    status="received",
                    idempotency_key=f"telegram:{telegram_user_id}:{index}",
                )
                for index in (4, 5)
            ]
            session.add_all(messages)
            await session.flush()
            first = Artifact(
                message_id=messages[0].id,
                artifact_type="note",
                title="First",
                slug="first",
                file_path="inbox/first.md",
            )
            second = Artifact(
                message_id=(
                    messages[0].id if duplicate == "message_type" else messages[1].id
                ),
                artifact_type="note",
                title="Second",
                slug="second",
                file_path=(
                    "inbox/second.md"
                    if duplicate == "message_type"
                    else "inbox/first.md"
                ),
            )
            session.add_all([first, second])

            with pytest.raises(IntegrityError):
                await session.commit()
            await session.rollback()

    asyncio.run(run())


def test_different_artifact_types_for_one_message_are_schema_valid() -> None:
    async def run() -> None:
        session_factory = get_session_factory()
        telegram_user_id = random_telegram_id()

        async with session_factory() as session:
            user = User(telegram_user_id=telegram_user_id)
            session.add(user)
            await session.flush()
            message = Message(
                user_id=user.id,
                telegram_chat_id=telegram_user_id,
                telegram_message_id=6,
                input_type="text",
                raw_text="source",
                status="received",
                idempotency_key=f"telegram:{telegram_user_id}:6",
            )
            session.add(message)
            await session.flush()
            session.add_all(
                [
                    Artifact(
                        message_id=message.id,
                        artifact_type="note",
                        title="Note",
                        slug="note",
                        file_path="inbox/note.md",
                    ),
                    Artifact(
                        message_id=message.id,
                        artifact_type="future_type",
                        title="Future",
                        slug="future",
                        file_path="inbox/future.md",
                    ),
                ]
            )
            await session.commit()
            count = await session.scalar(
                select(func.count()).select_from(Artifact).where(
                    Artifact.message_id == message.id
                )
            )

        assert count == 2

    asyncio.run(run())
