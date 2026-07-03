import asyncio
import uuid
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from pathlib import Path

import pytest
from sqlalchemy import func
from sqlalchemy import select

import app.worker.processing as worker_processing
import app.worker.tasks as worker_tasks
from app.bot.ingestion import TelegramTextInput
from app.bot.ingestion import persist_text_message
from app.db.models import Artifact
from app.db.models import Message
from app.db.models import ProcessingTask
from app.db.session import dispose_engine
from app.db.session import get_session_factory
from app.knowledge.errors import SourceMessageError
from app.knowledge.markdown import render_text_note
from app.worker.processing import claim_processing_task
from app.worker.processing import finalize_processing_task
from app.worker.processing import parse_processing_task_id
from app.worker.processing import run_processing_task
from app.worker.processing import sanitize_processing_error
from app.worker.tasks import process_processing_task
from app.settings import get_settings
from app.worker.dispatcher import recover_expired_leases


async def create_task(**changes: object) -> ProcessingTask:
    unique = uuid.uuid4().int % 9_000_000_000_000_000_000
    persisted = await persist_text_message(
        TelegramTextInput(
            telegram_user_id=unique,
            telegram_chat_id=-unique,
            telegram_message_id=7,
            text="Worker title\nWorker body",
        )
    )
    session_factory = get_session_factory()
    async with session_factory() as session:
        task = await session.scalar(
            select(ProcessingTask).where(
                ProcessingTask.message_id == persisted.message_id
            )
        )
        assert task is not None
        for name, value in changes.items():
            setattr(task, name, value)
        await session.commit()
        return task


async def load_task(task_id: uuid.UUID) -> ProcessingTask:
    session_factory = get_session_factory()
    async with session_factory() as session:
        task = await session.get(ProcessingTask, task_id)
        assert task is not None
        return task


@pytest.mark.parametrize("status", ["queued", "pending", "retrying"])
def test_claimable_status_increments_attempt_once(status: str) -> None:
    async def run() -> None:
        now = datetime.now(timezone.utc)
        task = await create_task(
            status=status,
            available_at=now - timedelta(seconds=1),
            lease_expires_at=(
                now + timedelta(seconds=30) if status == "queued" else None
            ),
        )
        claimed = await claim_processing_task(task.id, now=now)
        assert claimed is not None
        assert claimed.attempt == 1

        current = await load_task(task.id)
        assert current.status == "running"
        assert current.attempts == 1
        assert current.lease_expires_at == now + timedelta(seconds=300)

        assert await claim_processing_task(task.id, now=now) is None
        assert (await load_task(task.id)).attempts == 1

    asyncio.run(run())


def test_future_retry_and_terminal_or_missing_deliveries_are_noops() -> None:
    async def run() -> None:
        now = datetime.now(timezone.utc)
        future = await create_task(
            status="retrying", available_at=now + timedelta(seconds=1)
        )
        succeeded = await create_task(status="succeeded")

        assert await claim_processing_task(future.id, now=now) is None
        assert await claim_processing_task(succeeded.id, now=now) is None
        assert await claim_processing_task(uuid.uuid4(), now=now) is None
        assert (await load_task(future.id)).status == "retrying"
        assert (await load_task(succeeded.id)).status == "succeeded"

    asyncio.run(run())


def test_duplicate_delivery_does_not_fail_active_final_attempt() -> None:
    async def run() -> None:
        now = datetime.now(timezone.utc)
        task = await create_task(
            status="running",
            attempts=3,
            lease_expires_at=now + timedelta(minutes=5),
        )
        assert await claim_processing_task(task.id, now=now) is None
        current = await load_task(task.id)
        assert current.status == "running"
        assert current.attempts == 3

    asyncio.run(run())


def test_success_uses_fresh_session_and_worker_does_not_set_message_done(
    tmp_path: Path,
) -> None:
    async def run() -> None:
        task = await create_task()
        seen: list[tuple[uuid.UUID, Path]] = []

        async def processor(session, message_id, root):
            assert session.in_transaction() is False
            seen.append((message_id, root))

        await run_processing_task(
            task.id,
            knowledge_base_root=tmp_path,
            processor=processor,
        )

        current = await load_task(task.id)
        session_factory = get_session_factory()
        async with session_factory() as session:
            message_status = await session.scalar(
                select(Message.status).where(Message.id == task.message_id)
            )
        assert seen == [(task.message_id, tmp_path)]
        assert current.status == "succeeded"
        assert current.attempts == 1
        assert current.lease_expires_at is None
        assert message_status == "received"

    asyncio.run(run())


def test_real_processing_reaches_succeeded_with_exact_artifact(tmp_path: Path) -> None:
    async def run() -> None:
        task = await create_task()
        await run_processing_task(task.id, knowledge_base_root=tmp_path)

        current = await load_task(task.id)
        session_factory = get_session_factory()
        async with session_factory() as session:
            message = await session.get(Message, task.message_id)
            artifact = await session.scalar(
                select(Artifact).where(Artifact.message_id == task.message_id)
            )
        assert message is not None
        assert artifact is not None
        assert message.raw_text is not None
        expected = render_text_note(
            message_id=message.id,
            telegram_chat_id=message.telegram_chat_id,
            telegram_message_id=message.telegram_message_id,
            created_at=message.created_at,
            raw_text=message.raw_text,
        )
        assert current.status == "succeeded"
        assert message.status == "done"
        assert artifact.file_path == expected.file_path
        assert (tmp_path / expected.file_path).read_bytes() == expected.content

        await run_processing_task(task.id, knowledge_base_root=tmp_path)
        async with session_factory() as session:
            artifact_count = await session.scalar(
                select(func.count())
                .select_from(Artifact)
                .where(Artifact.message_id == task.message_id)
            )
        assert artifact_count == 1
        assert (await load_task(task.id)).attempts == 1

    asyncio.run(run())


def test_actor_processes_two_tasks_sequentially_in_one_process(
    monkeypatch,
    tmp_path: Path,
) -> None:
    async def create_tasks() -> list[uuid.UUID]:
        first = await create_task()
        second = await create_task()
        return [first.id, second.id]

    task_ids = asyncio.run(create_tasks())
    asyncio.run(dispose_engine())
    monkeypatch.setattr(get_settings(), "knowledge_base_path", tmp_path)

    for task_id in task_ids:
        process_processing_task(str(task_id))

    async def verify() -> None:
        session_factory = get_session_factory()
        async with session_factory() as session:
            tasks = list(
                await session.scalars(
                    select(ProcessingTask)
                    .where(ProcessingTask.id.in_(task_ids))
                    .order_by(ProcessingTask.id)
                )
            )
            messages = {
                message.id: message
                for message in await session.scalars(
                    select(Message).where(
                        Message.id.in_(task.message_id for task in tasks)
                    )
                )
            }
            artifacts = list(
                await session.scalars(
                    select(Artifact).where(
                        Artifact.message_id.in_(messages)
                    )
                )
            )

        assert len(tasks) == 2
        assert len(messages) == 2
        assert len(artifacts) == 2
        assert all(task.status == "succeeded" for task in tasks)
        assert all(task.attempts == 1 for task in tasks)
        assert all(message.status == "done" for message in messages.values())

        artifacts_by_message = {
            artifact.message_id: artifact for artifact in artifacts
        }
        assert len(artifacts_by_message) == 2
        for message_id, message in messages.items():
            assert message.raw_text is not None
            artifact = artifacts_by_message[message_id]
            expected = render_text_note(
                message_id=message.id,
                telegram_chat_id=message.telegram_chat_id,
                telegram_message_id=message.telegram_message_id,
                created_at=message.created_at,
                raw_text=message.raw_text,
            )
            assert artifact.file_path == expected.file_path
            assert (tmp_path / artifact.file_path).read_bytes() == expected.content

    asyncio.run(verify())


def test_permanent_failure_fails_immediately(tmp_path: Path) -> None:
    async def run() -> None:
        task = await create_task()

        async def fail(_session, _message_id, _root):
            raise SourceMessageError("invalid persisted source")

        await run_processing_task(
            task.id,
            knowledge_base_root=tmp_path,
            processor=fail,
        )
        current = await load_task(task.id)
        assert current.status == "failed"
        assert current.attempts == 1
        assert current.last_error == (
            "SourceMessageError: source message contract violation"
        )

    asyncio.run(run())


@pytest.mark.parametrize(
    ("starting_attempts", "expected_status"),
    [(0, "retrying"), (2, "failed")],
)
def test_operational_failure_uses_postgres_retry_state(
    tmp_path: Path,
    starting_attempts: int,
    expected_status: str,
) -> None:
    async def run() -> None:
        task = await create_task(attempts=starting_attempts)

        async def fail(_session, _message_id, _root):
            raise OSError("/secret/path token=do-not-store")

        before = datetime.now(timezone.utc)
        await run_processing_task(
            task.id,
            knowledge_base_root=tmp_path,
            processor=fail,
        )
        current = await load_task(task.id)
        assert current.status == expected_status
        assert current.attempts == starting_attempts + 1
        assert current.last_error == "OSError: knowledge-base operation failed"
        assert current.lease_expires_at is None
        if expected_status == "retrying":
            assert current.available_at >= before + timedelta(seconds=5)

    asyncio.run(run())


def test_error_summary_is_one_line_bounded_and_secret_free() -> None:
    error = SourceMessageError(
        "raw secret\npostgresql://user:password@host/db " + "x" * 600
    )
    summary = sanitize_processing_error(error)
    assert summary == "SourceMessageError: source message contract violation"
    assert "\n" not in summary
    assert "password" not in summary
    assert len(summary) <= 500


def test_late_finalizer_cannot_overwrite_newer_attempt() -> None:
    async def run() -> None:
        task = await create_task()
        claimed = await claim_processing_task(task.id)
        assert claimed is not None

        session_factory = get_session_factory()
        async with session_factory() as session:
            current = await session.get(ProcessingTask, task.id)
            assert current is not None
            current.attempts = 2
            await session.commit()

        assert await finalize_processing_task(claimed, error=None) is False
        current = await load_task(task.id)
        assert current.status == "running"
        assert current.attempts == 2

    asyncio.run(run())


def test_unknown_task_type_fails_without_consuming_attempt() -> None:
    async def run() -> None:
        task = await create_task(task_type="unknown")
        assert await claim_processing_task(task.id) is None
        current = await load_task(task.id)
        assert current.status == "failed"
        assert current.attempts == 0
        assert current.last_error == "unsupported processing task type"

    asyncio.run(run())


def test_finalization_database_failure_leaves_running_for_recovery(
    monkeypatch,
    tmp_path: Path,
) -> None:
    async def run() -> None:
        task = await create_task()

        async def processor(_session, _message_id, _root):
            return None

        async def fail_finalization(*_args, **_kwargs):
            raise RuntimeError("database unavailable")

        monkeypatch.setattr(
            worker_processing,
            "finalize_processing_task",
            fail_finalization,
        )
        with pytest.raises(RuntimeError, match="database unavailable"):
            await run_processing_task(
                task.id,
                knowledge_base_root=tmp_path,
                processor=processor,
            )
        current = await load_task(task.id)
        assert current.status == "running"
        assert current.attempts == 1

    asyncio.run(run())


def test_crash_after_task006_commit_recovers_idempotently(
    monkeypatch,
    tmp_path: Path,
) -> None:
    async def run() -> None:
        task = await create_task()
        original_finalize = worker_processing.finalize_processing_task

        async def fail_finalization(*_args, **_kwargs):
            raise RuntimeError("simulated finalization crash")

        monkeypatch.setattr(
            worker_processing,
            "finalize_processing_task",
            fail_finalization,
        )
        with pytest.raises(RuntimeError, match="simulated finalization crash"):
            await run_processing_task(task.id, knowledge_base_root=tmp_path)

        session_factory = get_session_factory()
        async with session_factory() as session:
            message = await session.get(Message, task.message_id)
            first_artifact = await session.scalar(
                select(Artifact).where(Artifact.message_id == task.message_id)
            )
        assert message is not None and message.status == "done"
        assert first_artifact is not None
        first_bytes = (tmp_path / first_artifact.file_path).read_bytes()

        recovery_time = datetime.now(timezone.utc) + timedelta(minutes=6)
        async with session_factory() as session:
            current = await session.get(ProcessingTask, task.id)
            assert current is not None
            current.lease_expires_at = recovery_time - timedelta(seconds=1)
            await session.commit()
        async with session_factory() as session:
            async with session.begin():
                assert await recover_expired_leases(session, recovery_time) == (
                    0,
                    1,
                    0,
                )
        async with session_factory() as session:
            current = await session.get(ProcessingTask, task.id)
            assert current is not None
            current.available_at = datetime.now(timezone.utc) - timedelta(seconds=1)
            await session.commit()

        monkeypatch.setattr(
            worker_processing,
            "finalize_processing_task",
            original_finalize,
        )
        await run_processing_task(task.id, knowledge_base_root=tmp_path)

        current = await load_task(task.id)
        async with session_factory() as session:
            artifacts = (
                await session.scalars(
                    select(Artifact).where(Artifact.message_id == task.message_id)
                )
            ).all()
        assert current.status == "succeeded"
        assert current.attempts == 2
        assert [artifact.id for artifact in artifacts] == [first_artifact.id]
        assert (tmp_path / first_artifact.file_path).read_bytes() == first_bytes

    asyncio.run(run())


def test_actor_payload_validation_and_retry_configuration() -> None:
    task_id = uuid.uuid4()
    assert parse_processing_task_id(str(task_id)) == task_id
    with pytest.raises(ValueError, match="canonical UUID"):
        parse_processing_task_id("not-a-uuid")
    with pytest.raises(ValueError, match="canonical UUID"):
        parse_processing_task_id(str(task_id).upper())
    assert process_processing_task.options["max_retries"] == 0


def test_actor_wrapper_preserves_processing_error_when_disposal_also_fails(
    monkeypatch,
) -> None:
    processing_error = RuntimeError("processing failed")

    async def fail_processing(_task_id):
        raise processing_error

    async def fail_disposal():
        raise OSError("disposal failed")

    monkeypatch.setattr(worker_tasks, "run_processing_task", fail_processing)
    monkeypatch.setattr(worker_tasks, "dispose_engine", fail_disposal)

    with pytest.raises(RuntimeError) as raised:
        asyncio.run(worker_tasks._run_actor_delivery(uuid.uuid4()))

    assert raised.value is processing_error
    assert processing_error.__notes__ == [
        "database engine disposal also failed: OSError"
    ]
