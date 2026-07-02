import asyncio
import os
import uuid
from datetime import datetime
from datetime import timezone
from pathlib import Path

import pytest
from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

import app.knowledge.processing as processing
from app.db.models import Artifact
from app.db.models import Message
from app.db.models import User
from app.db.session import get_session_factory
from app.knowledge.errors import ArtifactConsistencyError
from app.knowledge.errors import FileConflictError
from app.knowledge.errors import KnowledgeBaseError
from app.knowledge.errors import ProcessingTransactionError
from app.knowledge.errors import SourceMessageError
from app.knowledge.markdown import render_text_note
from app.knowledge.processing import _validate_source_message
from app.knowledge.processing import process_text_message


CREATED_AT = datetime(2026, 7, 2, 12, 34, 56, 123456, tzinfo=timezone.utc)


async def create_message(
    *,
    status: str = "received",
    input_type: str = "text",
    raw_text: str | None = "First line\nSecond line",
    created_at: datetime = CREATED_AT,
) -> uuid.UUID:
    session_factory = get_session_factory()
    unique = uuid.uuid4().int % 9_000_000_000_000_000_000
    async with session_factory() as session:
        user = User(telegram_user_id=unique)
        session.add(user)
        await session.flush()
        message = Message(
            user_id=user.id,
            telegram_chat_id=-unique,
            telegram_message_id=42,
            input_type=input_type,
            raw_text=raw_text,
            status=status,
            idempotency_key=f"telegram:{-unique}:42",
            created_at=created_at,
        )
        session.add(message)
        await session.commit()
        return message.id


async def load_message(message_id: uuid.UUID) -> Message:
    session_factory = get_session_factory()
    async with session_factory() as session:
        message = await session.get(Message, message_id)
        assert message is not None
        return message


async def expected_note(message_id: uuid.UUID):
    message = await load_message(message_id)
    assert message.raw_text is not None
    return render_text_note(
        message_id=message.id,
        telegram_chat_id=message.telegram_chat_id,
        telegram_message_id=message.telegram_message_id,
        created_at=message.created_at,
        raw_text=message.raw_text,
    )


async def insert_artifact(
    message_id: uuid.UUID,
    *,
    title: str | None = None,
    slug: str | None = None,
    file_path: str | None = None,
    artifact_type: str = "note",
) -> uuid.UUID:
    note = await expected_note(message_id)
    session_factory = get_session_factory()
    async with session_factory() as session:
        artifact = Artifact(
            message_id=message_id,
            artifact_type=artifact_type,
            title=title if title is not None else note.title,
            slug=slug if slug is not None else note.slug,
            file_path=file_path if file_path is not None else note.file_path,
        )
        session.add(artifact)
        await session.commit()
        return artifact.id


async def counts_and_status(message_id: uuid.UUID) -> tuple[int, str]:
    session_factory = get_session_factory()
    async with session_factory() as session:
        count = await session.scalar(
            select(func.count()).select_from(Artifact).where(
                Artifact.message_id == message_id
            )
        )
        status = await session.scalar(
            select(Message.status).where(Message.id == message_id)
        )
    assert count is not None
    assert status is not None
    return count, status


def test_no_row_no_file_creates_artifact_file_and_done_status(tmp_path: Path) -> None:
    async def run() -> None:
        message_id = await create_message()
        session_factory = get_session_factory()
        async with session_factory() as session:
            artifact = await process_text_message(session, message_id, tmp_path)

        note = await expected_note(message_id)
        assert artifact.message_id == message_id
        assert artifact.file_path == note.file_path
        assert (tmp_path / note.file_path).read_bytes() == note.content
        assert await counts_and_status(message_id) == (1, "done")
        assert list((tmp_path / "inbox").glob(".*.tmp")) == []

    asyncio.run(run())


def test_no_row_exact_file_reconciles_without_rewrite(tmp_path: Path) -> None:
    async def run() -> None:
        message_id = await create_message()
        note = await expected_note(message_id)
        destination = tmp_path / note.file_path
        destination.parent.mkdir()
        destination.write_bytes(note.content)
        original_mtime = destination.stat().st_mtime_ns

        session_factory = get_session_factory()
        async with session_factory() as session:
            await process_text_message(session, message_id, tmp_path)

        assert destination.stat().st_mtime_ns == original_mtime
        assert await counts_and_status(message_id) == (1, "done")

    asyncio.run(run())


def test_no_row_conflicting_file_fails_without_changes(tmp_path: Path) -> None:
    async def run() -> None:
        message_id = await create_message()
        note = await expected_note(message_id)
        destination = tmp_path / note.file_path
        destination.parent.mkdir()
        destination.write_bytes(b"keep me")

        session_factory = get_session_factory()
        async with session_factory() as session:
            with pytest.raises(FileConflictError):
                await process_text_message(session, message_id, tmp_path)

        assert destination.read_bytes() == b"keep me"
        assert await counts_and_status(message_id) == (0, "received")

    asyncio.run(run())


def test_valid_row_missing_file_is_recreated_with_same_identity(tmp_path: Path) -> None:
    async def run() -> None:
        message_id = await create_message()
        artifact_id = await insert_artifact(message_id)

        session_factory = get_session_factory()
        async with session_factory() as session:
            artifact = await process_text_message(session, message_id, tmp_path)

        note = await expected_note(message_id)
        assert artifact.id == artifact_id
        assert (tmp_path / note.file_path).read_bytes() == note.content
        assert await counts_and_status(message_id) == (1, "done")

    asyncio.run(run())


def test_valid_row_exact_file_is_semantic_no_op(tmp_path: Path) -> None:
    async def run() -> None:
        message_id = await create_message(status="done")
        artifact_id = await insert_artifact(message_id)
        note = await expected_note(message_id)
        destination = tmp_path / note.file_path
        destination.parent.mkdir()
        destination.write_bytes(note.content)

        session_factory = get_session_factory()
        async with session_factory() as session:
            before = await session.get(Artifact, artifact_id)
            assert before is not None
            timestamps = (before.created_at, before.updated_at)
        mtime = destination.stat().st_mtime_ns

        async with session_factory() as session:
            first = await process_text_message(session, message_id, tmp_path)
        async with session_factory() as session:
            second = await process_text_message(session, message_id, tmp_path)

        async with session_factory() as session:
            after = await session.get(Artifact, artifact_id)
            assert after is not None
            assert (after.created_at, after.updated_at) == timestamps
        assert first.id == second.id == artifact_id
        assert destination.stat().st_mtime_ns == mtime
        assert await counts_and_status(message_id) == (1, "done")

    asyncio.run(run())


def test_valid_row_conflicting_file_preserves_row_and_status(tmp_path: Path) -> None:
    async def run() -> None:
        message_id = await create_message(status="done")
        artifact_id = await insert_artifact(message_id)
        note = await expected_note(message_id)
        destination = tmp_path / note.file_path
        destination.parent.mkdir()
        destination.write_bytes(b"conflict")

        session_factory = get_session_factory()
        async with session_factory() as session:
            with pytest.raises(FileConflictError):
                await process_text_message(session, message_id, tmp_path)

        async with session_factory() as session:
            artifact = await session.get(Artifact, artifact_id)
            assert artifact is not None
        assert destination.read_bytes() == b"conflict"
        assert await counts_and_status(message_id) == (1, "done")

    asyncio.run(run())


@pytest.mark.parametrize(
    ("field", "value"),
    (("title", "wrong"), ("slug", "wrong"), ("file_path", "inbox/wrong.md")),
)
def test_inconsistent_artifact_metadata_fails_before_file_write(
    tmp_path: Path,
    field: str,
    value: str,
) -> None:
    async def run() -> None:
        message_id = await create_message()
        await insert_artifact(message_id, **{field: value})

        session_factory = get_session_factory()
        async with session_factory() as session:
            with pytest.raises(ArtifactConsistencyError, match=field):
                await process_text_message(session, message_id, tmp_path)

        assert not (tmp_path / "inbox").exists()
        assert await counts_and_status(message_id) == (1, "received")

    asyncio.run(run())


def test_expected_path_owned_by_another_artifact_fails_before_file_write(
    tmp_path: Path,
) -> None:
    async def run() -> None:
        source_id = await create_message()
        owner_id = await create_message(raw_text="owner")
        source_note = await expected_note(source_id)
        await insert_artifact(owner_id, file_path=source_note.file_path)

        session_factory = get_session_factory()
        async with session_factory() as session:
            with pytest.raises(ArtifactConsistencyError, match="owned"):
                await process_text_message(session, source_id, tmp_path)

        assert not (tmp_path / "inbox").exists()
        assert await counts_and_status(source_id) == (0, "received")

    asyncio.run(run())


def test_received_message_with_valid_row_and_file_becomes_done(tmp_path: Path) -> None:
    async def run() -> None:
        message_id = await create_message(status="received")
        await insert_artifact(message_id)
        note = await expected_note(message_id)
        destination = tmp_path / note.file_path
        destination.parent.mkdir()
        destination.write_bytes(note.content)

        session_factory = get_session_factory()
        async with session_factory() as session:
            await process_text_message(session, message_id, tmp_path)

        assert await counts_and_status(message_id) == (1, "done")

    asyncio.run(run())


def test_same_message_concurrency_creates_one_row_and_file(tmp_path: Path) -> None:
    async def run() -> None:
        message_id = await create_message()
        session_factory = get_session_factory()

        async def process() -> uuid.UUID:
            async with session_factory() as session:
                artifact = await process_text_message(session, message_id, tmp_path)
                return artifact.id

        artifact_ids = await asyncio.gather(process(), process(), process())

        note = await expected_note(message_id)
        assert len(set(artifact_ids)) == 1
        assert await counts_and_status(message_id) == (1, "done")
        assert (tmp_path / note.file_path).read_bytes() == note.content
        assert list((tmp_path / "inbox").glob(".*.tmp")) == []

    asyncio.run(run())


def test_expected_uniqueness_race_retries_once_and_returns_existing_artifact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def run() -> None:
        message_id = await create_message(status="done")
        artifact_id = await insert_artifact(message_id)
        note = await expected_note(message_id)
        destination = tmp_path / note.file_path
        destination.parent.mkdir()
        destination.write_bytes(note.content)
        real_attempt = processing._process_attempt
        calls = 0

        class DuplicateViolation(Exception):
            constraint_name = "uq_artifacts_message_id_artifact_type"

        async def racing_attempt(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 1:
                raise IntegrityError("insert", {}, DuplicateViolation())
            return await real_attempt(*args, **kwargs)

        monkeypatch.setattr(processing, "_process_attempt", racing_attempt)
        session_factory = get_session_factory()
        async with session_factory() as session:
            artifact = await process_text_message(session, message_id, tmp_path)

        assert calls == 2
        assert artifact.id == artifact_id
        assert await counts_and_status(message_id) == (1, "done")

    asyncio.run(run())


def test_unrelated_integrity_error_is_not_retried(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def run() -> None:
        message_id = await create_message()
        calls = 0

        class OtherViolation(Exception):
            constraint_name = "uq_unrelated"

        async def failing_attempt(*_args, **_kwargs):
            nonlocal calls
            calls += 1
            raise IntegrityError("insert", {}, OtherViolation())

        monkeypatch.setattr(processing, "_process_attempt", failing_attempt)
        session_factory = get_session_factory()
        async with session_factory() as session:
            with pytest.raises(IntegrityError):
                await process_text_message(session, message_id, tmp_path)

        assert calls == 1
        assert await counts_and_status(message_id) == (0, "received")

    asyncio.run(run())


def test_database_commit_failure_preserves_orphan_file_for_reconciliation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def run() -> None:
        message_id = await create_message()
        note = await expected_note(message_id)
        session_factory = get_session_factory()

        async with session_factory() as failing_session:
            async def fail_commit() -> None:
                raise RuntimeError("simulated commit failure")

            monkeypatch.setattr(failing_session, "commit", fail_commit)
            with pytest.raises(RuntimeError, match="commit failure"):
                await process_text_message(failing_session, message_id, tmp_path)

        assert (tmp_path / note.file_path).read_bytes() == note.content
        assert await counts_and_status(message_id) == (0, "received")

        async with session_factory() as recovery_session:
            artifact = await process_text_message(
                recovery_session, message_id, tmp_path
            )
        assert artifact.message_id == message_id
        assert await counts_and_status(message_id) == (1, "done")

    asyncio.run(run())


def test_flush_failure_preserves_orphan_file_without_artifact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def run() -> None:
        message_id = await create_message()
        note = await expected_note(message_id)
        session_factory = get_session_factory()

        async with session_factory() as session:
            async def fail_flush(*_args, **_kwargs) -> None:
                raise RuntimeError("simulated flush failure")

            monkeypatch.setattr(session, "flush", fail_flush)
            with pytest.raises(RuntimeError, match="flush failure"):
                await process_text_message(session, message_id, tmp_path)

        assert (tmp_path / note.file_path).read_bytes() == note.content
        assert await counts_and_status(message_id) == (0, "received")

    asyncio.run(run())


def test_existing_artifact_status_commit_failure_preserves_received_status(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def run() -> None:
        message_id = await create_message(status="received")
        await insert_artifact(message_id)
        note = await expected_note(message_id)
        destination = tmp_path / note.file_path
        destination.parent.mkdir()
        destination.write_bytes(note.content)
        session_factory = get_session_factory()

        async with session_factory() as session:
            async def fail_commit() -> None:
                raise RuntimeError("simulated status commit failure")

            monkeypatch.setattr(session, "commit", fail_commit)
            with pytest.raises(RuntimeError, match="status commit failure"):
                await process_text_message(session, message_id, tmp_path)

        assert destination.read_bytes() == note.content
        assert await counts_and_status(message_id) == (1, "received")

    asyncio.run(run())


@pytest.mark.parametrize(
    ("input_type", "raw_text", "error"),
    (
        ("voice", "text", "unsupported input_type"),
        ("text", None, "null raw_text"),
    ),
)
def test_invalid_sources_preserve_status_and_create_nothing(
    tmp_path: Path,
    input_type: str,
    raw_text: str | None,
    error: str,
) -> None:
    async def run() -> None:
        message_id = await create_message(input_type=input_type, raw_text=raw_text)
        session_factory = get_session_factory()
        async with session_factory() as session:
            with pytest.raises(SourceMessageError, match=error):
                await process_text_message(session, message_id, tmp_path)

        assert not (tmp_path / "inbox").exists()
        assert await counts_and_status(message_id) == (0, "received")

    asyncio.run(run())


def test_unsupported_source_status_is_preserved(tmp_path: Path) -> None:
    async def run() -> None:
        message_id = await create_message(status="processing")
        session_factory = get_session_factory()
        async with session_factory() as session:
            with pytest.raises(SourceMessageError, match="unsupported status"):
                await process_text_message(session, message_id, tmp_path)

        assert not (tmp_path / "inbox").exists()
        assert await counts_and_status(message_id) == (0, "processing")

    asyncio.run(run())


def test_missing_message_and_active_caller_transaction_fail_clearly(
    tmp_path: Path,
) -> None:
    async def run() -> None:
        session_factory = get_session_factory()
        missing_id = uuid.uuid4()
        async with session_factory() as session:
            with pytest.raises(SourceMessageError, match="not found"):
                await process_text_message(session, missing_id, tmp_path)

        message_id = await create_message()
        async with session_factory() as session:
            async with session.begin():
                with pytest.raises(ProcessingTransactionError, match="active"):
                    await process_text_message(session, message_id, tmp_path)

    asyncio.run(run())


def test_naive_timestamp_and_malformed_telegram_ids_are_rejected() -> None:
    message_id = uuid.uuid4()
    message = Message(
        id=message_id,
        user_id=uuid.uuid4(),
        telegram_chat_id=1,
        telegram_message_id=2,
        input_type="text",
        raw_text="note",
        status="received",
        idempotency_key="test",
        created_at=datetime(2026, 7, 2),
    )

    with pytest.raises(SourceMessageError, match="naive"):
        _validate_source_message(message, message_id)

    message.created_at = CREATED_AT
    message.telegram_chat_id = None  # type: ignore[assignment]
    with pytest.raises(SourceMessageError, match="identifiers"):
        _validate_source_message(message, message_id)

    message.telegram_chat_id = 1
    message.raw_text = "bad\0text"
    with pytest.raises(SourceMessageError, match="contains NUL"):
        _validate_source_message(message, message_id)


def test_permission_failure_leaves_no_database_or_temporary_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def run() -> None:
        message_id = await create_message()

        def fail_open(*_args, **_kwargs):
            raise PermissionError("simulated permission failure")

        monkeypatch.setattr("app.knowledge.storage.os.open", fail_open)
        session_factory = get_session_factory()
        async with session_factory() as session:
            with pytest.raises(KnowledgeBaseError):
                await process_text_message(session, message_id, tmp_path)

        assert await counts_and_status(message_id) == (0, "received")
        assert list((tmp_path / "inbox").iterdir()) == []

    asyncio.run(run())
