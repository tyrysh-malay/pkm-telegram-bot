import asyncio
import subprocess
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
from app.knowledge.errors import AtomicPublicationError
from app.knowledge.errors import FileConflictError
from app.knowledge.errors import GitPublicationBusyError
from app.knowledge.errors import GitPublicationInvariantError
from app.knowledge.errors import GitPublicationOperationalError
from app.knowledge.errors import KnowledgeBaseError
from app.knowledge.errors import KnowledgeBaseInvariantError
from app.knowledge.errors import KnowledgeBaseOperationalError
from app.knowledge.errors import SourceMessageError
from app.knowledge.errors import TemporaryFileCleanupError
from app.knowledge.errors import UnsupportedFileEntryError
from app.knowledge.git_publication import publish_artifact_to_git
from app.knowledge.markdown import render_text_note
from app.knowledge.storage import classify_file
from app.knowledge.storage import resolve_destination
from app.worker.processing import claim_processing_task
from app.worker.processing import finalize_processing_task
from app.worker.processing import parse_processing_task_id
from app.worker.processing import resolve_note_artifact_id
from app.worker.processing import run_processing_task
from app.worker.processing import sanitize_processing_error
from app.worker.tasks import process_processing_task
from app.settings import get_settings
from app.worker.dispatcher import recover_expired_leases
from app.worker.constants import TASK_TYPE_PUBLISH_ARTIFACT


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


async def create_publication_task(
    message_id: uuid.UUID,
    **changes: object,
) -> ProcessingTask:
    session_factory = get_session_factory()
    async with session_factory() as session:
        task = ProcessingTask(
            message_id=message_id,
            task_type=TASK_TYPE_PUBLISH_ARTIFACT,
        )
        for name, value in changes.items():
            setattr(task, name, value)
        session.add(task)
        await session.commit()
        return task


def git(root: Path, *arguments: str):
    return subprocess.run(
        ["git", "-C", str(root), *arguments],
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )


def initialize_repository(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    assert git(root, "init").returncode == 0
    assert git(root, "config", "--local", "user.name", "PKM Test").returncode == 0
    assert (
        git(
            root,
            "config",
            "--local",
            "user.email",
            "pkm-test@example.invalid",
        ).returncode
        == 0
    )


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
        assert claimed.task_type == task.task_type

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


def test_generation_success_creates_publication_task_only_when_enabled(
    tmp_path: Path,
) -> None:
    async def run() -> None:
        disabled = await create_task()
        enabled = await create_task()

        async def processor(_session, _message_id, _root):
            return None

        await run_processing_task(
            disabled.id,
            knowledge_base_root=tmp_path,
            processor=processor,
            git_publication_enabled=False,
        )
        await run_processing_task(
            enabled.id,
            knowledge_base_root=tmp_path,
            processor=processor,
            git_publication_enabled=True,
        )

        session_factory = get_session_factory()
        async with session_factory() as session:
            disabled_publications = list(
                await session.scalars(
                    select(ProcessingTask).where(
                        ProcessingTask.message_id == disabled.message_id,
                        ProcessingTask.task_type == TASK_TYPE_PUBLISH_ARTIFACT,
                    )
                )
            )
            publication = await session.scalar(
                select(ProcessingTask).where(
                    ProcessingTask.message_id == enabled.message_id,
                    ProcessingTask.task_type == TASK_TYPE_PUBLISH_ARTIFACT,
                )
            )

        assert (await load_task(disabled.id)).status == "succeeded"
        assert disabled_publications == []
        assert (await load_task(enabled.id)).status == "succeeded"
        assert publication is not None
        assert publication.status == "pending"
        assert publication.attempts == 0
        assert publication.max_attempts == 3
        assert publication.lease_expires_at is None
        assert publication.last_error is None

    asyncio.run(run())


@pytest.mark.parametrize(
    "status",
    ["pending", "queued", "running", "retrying", "succeeded", "failed"],
)
def test_generation_finalization_preserves_existing_publication_task(
    tmp_path: Path,
    status: str,
) -> None:
    async def run() -> None:
        generate = await create_task()
        now = datetime.now(timezone.utc)
        publication = await create_publication_task(
            generate.message_id,
            status=status,
            attempts=2,
            max_attempts=7,
            available_at=now + timedelta(hours=1),
            lease_expires_at=(
                now + timedelta(minutes=1)
                if status in {"queued", "running"}
                else None
            ),
            last_error="preserve me",
        )
        before = await load_task(publication.id)

        async def processor(_session, _message_id, _root):
            return None

        await run_processing_task(
            generate.id,
            knowledge_base_root=tmp_path,
            processor=processor,
            git_publication_enabled=True,
        )

        current = await load_task(publication.id)
        assert (await load_task(generate.id)).status == "succeeded"
        assert current.status == before.status
        assert current.attempts == before.attempts
        assert current.max_attempts == before.max_attempts
        assert current.available_at == before.available_at
        assert current.lease_expires_at == before.lease_expires_at
        assert current.last_error == before.last_error
        assert current.updated_at == before.updated_at

    asyncio.run(run())


def test_publication_resolves_artifact_in_closed_read_transaction_and_dispatches(
    tmp_path: Path,
) -> None:
    async def run() -> None:
        task = await create_task(task_type=TASK_TYPE_PUBLISH_ARTIFACT)
        session_factory = get_session_factory()
        async with session_factory() as session:
            artifact = await worker_processing.process_text_message(
                session,
                task.message_id,
                tmp_path,
            )

        seen: list[tuple[uuid.UUID, Path]] = []

        async def fail_generation(*_args):
            raise AssertionError("publication must not invoke Task 006")

        async def publish(session, artifact_id, root):
            assert session.in_transaction() is False
            seen.append((artifact_id, root))

        await run_processing_task(
            task.id,
            knowledge_base_root=tmp_path,
            processor=fail_generation,
            publication_processor=publish,
            git_publication_enabled=False,
        )

        assert seen == [(artifact.id, tmp_path)]
        assert (await load_task(task.id)).status == "succeeded"

    asyncio.run(run())


def test_missing_publication_artifact_fails_permanently(tmp_path: Path) -> None:
    async def run() -> None:
        task = await create_task(task_type=TASK_TYPE_PUBLISH_ARTIFACT)
        await run_processing_task(
            task.id,
            knowledge_base_root=tmp_path,
            git_publication_enabled=False,
        )

        current = await load_task(task.id)
        assert current.status == "failed"
        assert current.attempts == 1
        assert current.last_error == (
            "GitPublicationInvariantError: Git publication contract violation"
        )

    asyncio.run(run())


def test_missing_deterministic_publication_file_fails_permanently(
    tmp_path: Path,
) -> None:
    async def run() -> None:
        initialize_repository(tmp_path)
        generate = await create_task()
        session_factory = get_session_factory()
        async with session_factory() as session:
            artifact = await worker_processing.process_text_message(
                session,
                generate.message_id,
                tmp_path,
            )
        path = tmp_path / artifact.file_path
        path.unlink()
        path.parent.rmdir()

        publication = await create_publication_task(generate.message_id)
        await run_processing_task(
            publication.id,
            knowledge_base_root=tmp_path,
            git_publication_enabled=False,
        )

        current = await load_task(publication.id)
        assert current.status == "failed"
        assert current.attempts == 1
        assert current.last_error == (
            "KnowledgeBaseInvariantError: knowledge-base contract violation"
        )

    asyncio.run(run())


@pytest.mark.parametrize(
    ("entry_kind", "expected_error"),
    [
        ("conflicting", "FileConflictError: deterministic artifact file conflict"),
        (
            "unsupported",
            "UnsupportedFileEntryError: unsupported artifact filesystem entry",
        ),
    ],
)
def test_conflicting_and_unsupported_publication_files_fail_permanently(
    tmp_path: Path,
    entry_kind: str,
    expected_error: str,
) -> None:
    async def run() -> None:
        initialize_repository(tmp_path)
        generate = await create_task()
        session_factory = get_session_factory()
        async with session_factory() as session:
            artifact = await worker_processing.process_text_message(
                session,
                generate.message_id,
                tmp_path,
            )
        path = tmp_path / artifact.file_path
        path.unlink()
        if entry_kind == "conflicting":
            path.write_text("different deterministic bytes\n")
        else:
            path.mkdir()

        publication = await create_publication_task(generate.message_id)
        await run_processing_task(
            publication.id,
            knowledge_base_root=tmp_path,
            git_publication_enabled=False,
        )

        current = await load_task(publication.id)
        assert current.status == "failed"
        assert current.attempts == 1
        assert current.last_error == expected_error

    asyncio.run(run())


@pytest.mark.parametrize("inspection_target", ["root", "directory", "file"])
def test_transient_artifact_filesystem_inspection_retries(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    inspection_target: str,
) -> None:
    async def run() -> None:
        generate = await create_task()
        session_factory = get_session_factory()
        async with session_factory() as session:
            artifact = await worker_processing.process_text_message(
                session,
                generate.message_id,
                tmp_path,
            )
        inspected_path = {
            "root": tmp_path,
            "directory": (tmp_path / artifact.file_path).parent,
            "file": tmp_path / artifact.file_path,
        }[inspection_target]
        original_lstat = Path.lstat

        def fail_selected_lstat(path: Path):
            if path == inspected_path:
                raise OSError(
                    "transient filesystem outage at /secret/root stderr=token"
                )
            return original_lstat(path)

        monkeypatch.setattr(Path, "lstat", fail_selected_lstat)

        publication = await create_publication_task(generate.message_id)

        async def resolve(_session, _message_id):
            return artifact.id

        async def inspect_artifact_filesystem(_session, _artifact_id, root):
            if inspection_target == "file":
                _, destination = resolve_destination(
                    root,
                    artifact.file_path,
                    create_missing=False,
                )
                classify_file(destination, b"expected bytes")
            else:
                resolve_destination(
                    root,
                    artifact.file_path,
                    create_missing=False,
                )

        await run_processing_task(
            publication.id,
            knowledge_base_root=tmp_path,
            artifact_resolver=resolve,
            publication_processor=inspect_artifact_filesystem,
            git_publication_enabled=False,
        )

        current = await load_task(publication.id)
        assert current.status == "retrying"
        assert current.attempts == 1
        assert current.last_error == (
            "KnowledgeBaseOperationalError: knowledge-base operation failed"
        )
        assert "/secret" not in current.last_error
        assert "stderr" not in current.last_error
        assert "token" not in current.last_error

    asyncio.run(run())


@pytest.mark.parametrize("resolution_target", ["root", "top_level"])
def test_transient_git_root_resolution_retries(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    resolution_target: str,
) -> None:
    async def run() -> None:
        initialize_repository(tmp_path)
        generate = await create_task()
        session_factory = get_session_factory()
        async with session_factory() as session:
            artifact = await worker_processing.process_text_message(
                session,
                generate.message_id,
                tmp_path,
            )
        publication = await create_publication_task(generate.message_id)
        original_resolve = Path.resolve
        root_resolve_calls = 0

        def fail_selected_resolve(path: Path, *args, **kwargs):
            nonlocal root_resolve_calls
            if path == tmp_path:
                root_resolve_calls += 1
                should_fail = (
                    resolution_target == "root"
                    or (
                        resolution_target == "top_level"
                        and root_resolve_calls == 2
                    )
                )
                if should_fail:
                    raise OSError(
                        "transient Git root I/O at /secret/root stderr=token"
                    )
            return original_resolve(path, *args, **kwargs)

        monkeypatch.setattr(Path, "resolve", fail_selected_resolve)

        await run_processing_task(
            publication.id,
            knowledge_base_root=tmp_path,
            git_publication_enabled=False,
        )

        current = await load_task(publication.id)
        assert current.status == "retrying"
        assert current.attempts == 1
        assert current.last_error == (
            "GitPublicationOperationalError: Git publication operation failed"
        )

    asyncio.run(run())


@pytest.mark.parametrize("root_case", ["missing", "not_git"])
def test_missing_or_wrong_git_root_fails_permanently(
    tmp_path: Path,
    root_case: str,
) -> None:
    async def run() -> None:
        root = tmp_path / root_case
        if root_case == "not_git":
            root.mkdir()
        task = await create_task(task_type=TASK_TYPE_PUBLISH_ARTIFACT)

        async def resolve(_session, _message_id):
            return uuid.uuid4()

        await run_processing_task(
            task.id,
            knowledge_base_root=root,
            artifact_resolver=resolve,
            git_publication_enabled=False,
        )

        current = await load_task(task.id)
        assert current.status == "failed"
        assert current.attempts == 1
        assert current.last_error == (
            "GitPublicationInvariantError: Git publication contract violation"
        )

    asyncio.run(run())


@pytest.mark.parametrize(
    ("error", "expected_status", "expected_summary"),
    [
        (
            GitPublicationBusyError("/secret/repository is locked"),
            "retrying",
            "GitPublicationBusyError: Git publication already in progress",
        ),
        (
            GitPublicationInvariantError("/secret/repository is invalid"),
            "failed",
            "GitPublicationInvariantError: Git publication contract violation",
        ),
        (
            GitPublicationOperationalError(
                "git failed at /secret/root stderr=ghp_token password=hunter2"
            ),
            "retrying",
            "GitPublicationOperationalError: Git publication operation failed",
        ),
        (
            KnowledgeBaseOperationalError(
                "filesystem failed at /secret/root stderr=ghp_token"
            ),
            "retrying",
            "KnowledgeBaseOperationalError: knowledge-base operation failed",
        ),
        (
            KnowledgeBaseInvariantError(
                "filesystem invariant failed at /secret/root stderr=ghp_token"
            ),
            "failed",
            "KnowledgeBaseInvariantError: knowledge-base contract violation",
        ),
    ],
)
def test_publication_error_types_control_retry_and_sanitization(
    tmp_path: Path,
    error: Exception,
    expected_status: str,
    expected_summary: str,
) -> None:
    async def run() -> None:
        task = await create_task(task_type=TASK_TYPE_PUBLISH_ARTIFACT)

        async def resolve(_session, _message_id):
            return uuid.uuid4()

        async def fail(_session, _artifact_id, _root):
            raise error

        await run_processing_task(
            task.id,
            knowledge_base_root=tmp_path,
            artifact_resolver=resolve,
            publication_processor=fail,
            git_publication_enabled=False,
        )
        current = await load_task(task.id)
        assert current.status == expected_status
        assert current.last_error == expected_summary
        assert "/secret" not in current.last_error
        assert "stderr" not in current.last_error
        assert "ghp_" not in current.last_error
        assert "password" not in current.last_error

    asyncio.run(run())


def test_enabled_generation_to_git_publication_is_end_to_end_idempotent(
    tmp_path: Path,
) -> None:
    async def run() -> None:
        initialize_repository(tmp_path)
        generate = await create_task()
        await run_processing_task(
            generate.id,
            knowledge_base_root=tmp_path,
            git_publication_enabled=True,
        )

        session_factory = get_session_factory()
        async with session_factory() as session:
            publication = await session.scalar(
                select(ProcessingTask).where(
                    ProcessingTask.message_id == generate.message_id,
                    ProcessingTask.task_type == TASK_TYPE_PUBLISH_ARTIFACT,
                )
            )
        assert publication is not None

        await run_processing_task(
            publication.id,
            knowledge_base_root=tmp_path,
            git_publication_enabled=False,
        )
        async with session_factory() as session:
            message = await session.get(Message, generate.message_id)
            artifact = await session.scalar(
                select(Artifact).where(Artifact.message_id == generate.message_id)
            )
        assert message is not None and message.status == "done"
        assert artifact is not None and artifact.git_commit_sha is not None
        assert (await load_task(generate.id)).status == "succeeded"
        assert (await load_task(publication.id)).status == "succeeded"
        assert git(tmp_path, "rev-list", "--count", "HEAD").stdout.strip() == "1"
        assert git(
            tmp_path,
            "show",
            f"{artifact.git_commit_sha}:{artifact.file_path}",
        ).stdout.encode() == (tmp_path / artifact.file_path).read_bytes()

        await run_processing_task(
            publication.id,
            knowledge_base_root=tmp_path,
            git_publication_enabled=False,
        )
        assert git(tmp_path, "rev-list", "--count", "HEAD").stdout.strip() == "1"
        assert (await load_task(publication.id)).attempts == 1

    asyncio.run(run())


def test_manual_publication_before_automatic_task_creates_no_duplicate(
    tmp_path: Path,
) -> None:
    async def run() -> None:
        initialize_repository(tmp_path)
        generate = await create_task()
        await run_processing_task(
            generate.id,
            knowledge_base_root=tmp_path,
            git_publication_enabled=False,
        )
        session_factory = get_session_factory()
        async with session_factory() as session:
            artifact = await session.scalar(
                select(Artifact).where(Artifact.message_id == generate.message_id)
            )
        assert artifact is not None
        async with session_factory() as session:
            manual = await publish_artifact_to_git(session, artifact.id, tmp_path)
        assert manual.outcome == "created"

        publication = await create_publication_task(generate.message_id)
        await run_processing_task(
            publication.id,
            knowledge_base_root=tmp_path,
            git_publication_enabled=False,
        )

        assert (await load_task(publication.id)).status == "succeeded"
        assert git(tmp_path, "rev-list", "--count", "HEAD").stdout.strip() == "1"
        async with session_factory() as session:
            stored = await session.get(Artifact, artifact.id)
        assert stored is not None
        assert stored.git_commit_sha == manual.git_commit_sha

    asyncio.run(run())


def test_publication_database_failure_retries_and_reconciles_retained_commit(
    tmp_path: Path,
) -> None:
    async def run() -> None:
        initialize_repository(tmp_path)
        generate = await create_task()
        await run_processing_task(
            generate.id,
            knowledge_base_root=tmp_path,
            git_publication_enabled=True,
        )
        session_factory = get_session_factory()
        async with session_factory() as session:
            publication = await session.scalar(
                select(ProcessingTask).where(
                    ProcessingTask.message_id == generate.message_id,
                    ProcessingTask.task_type == TASK_TYPE_PUBLISH_ARTIFACT,
                )
            )
        assert publication is not None

        async def fail_database_commit(session, artifact_id, root):
            async def fail_commit() -> None:
                raise RuntimeError("simulated publication database failure")

            session.commit = fail_commit
            return await publish_artifact_to_git(session, artifact_id, root)

        await run_processing_task(
            publication.id,
            knowledge_base_root=tmp_path,
            publication_processor=fail_database_commit,
            git_publication_enabled=False,
        )
        failed_attempt = await load_task(publication.id)
        assert failed_attempt.status == "retrying"
        assert failed_attempt.attempts == 1
        assert git(tmp_path, "rev-list", "--count", "HEAD").stdout.strip() == "1"
        async with session_factory() as session:
            artifact = await session.scalar(
                select(Artifact).where(Artifact.message_id == generate.message_id)
            )
            assert artifact is not None and artifact.git_commit_sha is None
            current = await session.get(ProcessingTask, publication.id)
            assert current is not None
            current.available_at = datetime.now(timezone.utc) - timedelta(seconds=1)
            await session.commit()

        await run_processing_task(
            publication.id,
            knowledge_base_root=tmp_path,
            git_publication_enabled=False,
        )
        recovered = await load_task(publication.id)
        async with session_factory() as session:
            artifact = await session.scalar(
                select(Artifact).where(Artifact.message_id == generate.message_id)
            )
        assert recovered.status == "succeeded"
        assert recovered.attempts == 2
        assert artifact is not None and artifact.git_commit_sha is not None
        assert git(tmp_path, "rev-list", "--count", "HEAD").stdout.strip() == "1"

    asyncio.run(run())


def test_crash_after_publication_commit_recovers_without_duplicate(
    monkeypatch,
    tmp_path: Path,
) -> None:
    async def run() -> None:
        initialize_repository(tmp_path)
        generate = await create_task()
        await run_processing_task(
            generate.id,
            knowledge_base_root=tmp_path,
            git_publication_enabled=True,
        )
        session_factory = get_session_factory()
        async with session_factory() as session:
            publication = await session.scalar(
                select(ProcessingTask).where(
                    ProcessingTask.message_id == generate.message_id,
                    ProcessingTask.task_type == TASK_TYPE_PUBLISH_ARTIFACT,
                )
            )
        assert publication is not None

        original_finalize = worker_processing.finalize_processing_task

        async def crash_finalizer(*_args, **_kwargs):
            raise RuntimeError("simulated post-publication crash")

        monkeypatch.setattr(
            worker_processing,
            "finalize_processing_task",
            crash_finalizer,
        )
        with pytest.raises(RuntimeError, match="post-publication crash"):
            await run_processing_task(
                publication.id,
                knowledge_base_root=tmp_path,
                git_publication_enabled=False,
            )

        running = await load_task(publication.id)
        assert running.status == "running"
        assert running.attempts == 1
        assert git(tmp_path, "rev-list", "--count", "HEAD").stdout.strip() == "1"

        recovery_time = datetime.now(timezone.utc) + timedelta(minutes=6)
        async with session_factory() as session:
            current = await session.get(ProcessingTask, publication.id)
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
            current = await session.get(ProcessingTask, publication.id)
            assert current is not None
            current.available_at = datetime.now(timezone.utc) - timedelta(seconds=1)
            await session.commit()

        monkeypatch.setattr(
            worker_processing,
            "finalize_processing_task",
            original_finalize,
        )
        await run_processing_task(
            publication.id,
            knowledge_base_root=tmp_path,
            git_publication_enabled=False,
        )

        recovered = await load_task(publication.id)
        assert recovered.status == "succeeded"
        assert recovered.attempts == 2
        assert git(tmp_path, "rev-list", "--count", "HEAD").stdout.strip() == "1"

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


@pytest.mark.parametrize(
    ("error", "expected_status", "expected_summary"),
    [
        (
            KnowledgeBaseOperationalError(
                "transient I/O at /secret/root stderr=ghp_token password=hunter2"
            ),
            "retrying",
            "KnowledgeBaseError: knowledge-base operation failed",
        ),
        (
            KnowledgeBaseInvariantError(
                "unsafe deterministic path at /secret/root stderr=ghp_token"
            ),
            "retrying",
            "KnowledgeBaseError: knowledge-base operation failed",
        ),
        (
            KnowledgeBaseError(
                "legacy knowledge-base failure at /secret/root stderr=ghp_token"
            ),
            "retrying",
            "KnowledgeBaseError: knowledge-base operation failed",
        ),
        (
            AtomicPublicationError(
                "atomic publication failed at /secret/root stderr=ghp_token"
            ),
            "retrying",
            "AtomicPublicationError: knowledge-base operation failed",
        ),
        (
            TemporaryFileCleanupError(
                "cleanup failed at /secret/root stderr=ghp_token"
            ),
            "retrying",
            "TemporaryFileCleanupError: knowledge-base operation failed",
        ),
        (
            FileConflictError(
                "conflict at /secret/root stderr=ghp_token password=hunter2"
            ),
            "failed",
            "FileConflictError: deterministic artifact file conflict",
        ),
        (
            UnsupportedFileEntryError(
                "unsupported entry at /secret/root stderr=ghp_token"
            ),
            "failed",
            "UnsupportedFileEntryError: unsupported artifact filesystem entry",
        ),
    ],
)
def test_generate_note_knowledge_base_summaries_preserve_task006_contract(
    tmp_path: Path,
    error: Exception,
    expected_status: str,
    expected_summary: str,
) -> None:
    async def run() -> None:
        task = await create_task()

        async def fail(_session, _message_id, _root):
            raise error

        await run_processing_task(
            task.id,
            knowledge_base_root=tmp_path,
            processor=fail,
        )

        current = await load_task(task.id)
        assert current.status == expected_status
        assert current.attempts == 1
        assert current.last_error == expected_summary
        assert current.lease_expires_at is None
        assert "/secret" not in current.last_error
        assert "stderr" not in current.last_error
        assert "ghp_" not in current.last_error
        assert "password" not in current.last_error

    asyncio.run(run())


def test_task006_filesystem_operational_failure_still_retries(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def run() -> None:
        task = await create_task()

        def fail_open(*_args, **_kwargs):
            raise PermissionError(
                "temporary generation I/O failure at /secret/root token=do-not-store"
            )

        monkeypatch.setattr("app.knowledge.storage.os.open", fail_open)

        await run_processing_task(task.id, knowledge_base_root=tmp_path)

        current = await load_task(task.id)
        assert current.status == "retrying"
        assert current.attempts == 1
        assert current.last_error == (
            "KnowledgeBaseError: knowledge-base operation failed"
        )
        session_factory = get_session_factory()
        async with session_factory() as session:
            artifact_count = await session.scalar(
                select(func.count())
                .select_from(Artifact)
                .where(Artifact.message_id == task.message_id)
            )
            message_status = await session.scalar(
                select(Message.status).where(Message.id == task.message_id)
            )
        assert artifact_count == 0
        assert message_status == "received"
        assert "/secret" not in current.last_error
        assert "token" not in current.last_error

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

        assert await finalize_processing_task(
            claimed,
            error=None,
            create_publication_task=True,
        ) is False
        current = await load_task(task.id)
        assert current.status == "running"
        assert current.attempts == 2
        session_factory = get_session_factory()
        async with session_factory() as session:
            publication_count = await session.scalar(
                select(func.count())
                .select_from(ProcessingTask)
                .where(
                    ProcessingTask.message_id == task.message_id,
                    ProcessingTask.task_type == TASK_TYPE_PUBLISH_ARTIFACT,
                )
            )
        assert publication_count == 0

    asyncio.run(run())


def test_downstream_insert_failure_rolls_back_generation_success(
    monkeypatch,
) -> None:
    async def run() -> None:
        task = await create_task()
        claimed = await claim_processing_task(task.id)
        assert claimed is not None

        def fail_insert(_model):
            raise RuntimeError("simulated downstream insertion failure")

        monkeypatch.setattr(worker_processing, "insert", fail_insert)
        with pytest.raises(RuntimeError, match="downstream insertion failure"):
            await finalize_processing_task(
                claimed,
                error=None,
                create_publication_task=True,
            )

        current = await load_task(task.id)
        assert current.status == "running"
        assert current.attempts == 1
        session_factory = get_session_factory()
        async with session_factory() as session:
            publication_count = await session.scalar(
                select(func.count())
                .select_from(ProcessingTask)
                .where(
                    ProcessingTask.message_id == task.message_id,
                    ProcessingTask.task_type == TASK_TYPE_PUBLISH_ARTIFACT,
                )
            )
        assert publication_count == 0

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
