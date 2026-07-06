import logging
import re
import uuid
from collections.abc import Awaitable
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from datetime import timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy import update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.db.models import Artifact
from app.db.models import ProcessingTask
from app.db.session import get_session_factory
from app.knowledge.errors import AtomicPublicationError
from app.knowledge.errors import ArtifactConsistencyError
from app.knowledge.errors import DuplicateArtifactRaceError
from app.knowledge.errors import FileConflictError
from app.knowledge.errors import GitPublicationBusyError
from app.knowledge.errors import GitPublicationInvariantError
from app.knowledge.errors import GitPublicationOperationalError
from app.knowledge.errors import GitPublicationTransactionError
from app.knowledge.errors import KnowledgeArtifactError
from app.knowledge.errors import KnowledgeBaseError
from app.knowledge.errors import KnowledgeBaseInvariantError
from app.knowledge.errors import KnowledgeBaseOperationalError
from app.knowledge.errors import ProcessingTransactionError
from app.knowledge.errors import SourceMessageError
from app.knowledge.errors import TemporaryFileCleanupError
from app.knowledge.errors import UnsupportedFileEntryError
from app.knowledge.git_publication import publish_artifact_to_git
from app.knowledge.markdown import ARTIFACT_TYPE
from app.knowledge.processing import process_text_message
from app.settings import get_settings
from app.worker.constants import MAX_ATTEMPTS_ERROR
from app.worker.constants import MAX_STORED_ERROR_LENGTH
from app.worker.constants import PROCESSING_RETRY_BACKOFF
from app.worker.constants import RUNNING_LEASE_DURATION
from app.worker.constants import TASK_STATUS_FAILED
from app.worker.constants import TASK_STATUS_PENDING
from app.worker.constants import TASK_STATUS_QUEUED
from app.worker.constants import TASK_STATUS_RETRYING
from app.worker.constants import TASK_STATUS_RUNNING
from app.worker.constants import TASK_STATUS_SUCCEEDED
from app.worker.constants import TASK_TYPE_GENERATE_NOTE
from app.worker.constants import TASK_TYPE_PUBLISH_ARTIFACT
from app.worker.constants import SUPPORTED_TASK_TYPES
from app.worker.constants import TERMINAL_STATUSES
from app.worker.constants import UNSUPPORTED_TASK_TYPE_ERROR


logger = logging.getLogger(__name__)

PERMANENT_PROCESSING_ERRORS = (
    SourceMessageError,
    ArtifactConsistencyError,
    FileConflictError,
    UnsupportedFileEntryError,
    ProcessingTransactionError,
)


@dataclass(frozen=True)
class ClaimedTask:
    id: uuid.UUID
    message_id: uuid.UUID
    task_type: str
    attempt: int
    max_attempts: int


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_processing_task_id(value: str) -> uuid.UUID:
    try:
        task_id = uuid.UUID(value)
    except (AttributeError, TypeError, ValueError) as exc:
        raise ValueError("processing task ID must be a canonical UUID") from exc
    if str(task_id) != value:
        raise ValueError("processing task ID must be a canonical UUID")
    return task_id


def sanitize_processing_error(
    error: Exception,
    *,
    task_type: str | None = None,
) -> str:
    if isinstance(error, SourceMessageError):
        summary = "SourceMessageError: source message contract violation"
    elif isinstance(error, ArtifactConsistencyError):
        summary = "ArtifactConsistencyError: artifact metadata conflict"
    elif isinstance(error, FileConflictError):
        summary = "FileConflictError: deterministic artifact file conflict"
    elif isinstance(error, UnsupportedFileEntryError):
        summary = "UnsupportedFileEntryError: unsupported artifact filesystem entry"
    elif isinstance(error, ProcessingTransactionError):
        summary = "ProcessingTransactionError: processing transaction contract violation"
    elif task_type == TASK_TYPE_GENERATE_NOTE and isinstance(
        error,
        (
            KnowledgeBaseInvariantError,
            KnowledgeBaseOperationalError,
        ),
    ):
        if isinstance(error, (AtomicPublicationError, TemporaryFileCleanupError)):
            summary = f"{type(error).__name__}: knowledge-base operation failed"
        else:
            summary = "KnowledgeBaseError: knowledge-base operation failed"
    elif isinstance(error, GitPublicationBusyError):
        summary = "GitPublicationBusyError: Git publication already in progress"
    elif isinstance(error, GitPublicationInvariantError):
        summary = "GitPublicationInvariantError: Git publication contract violation"
    elif isinstance(error, GitPublicationOperationalError):
        summary = "GitPublicationOperationalError: Git publication operation failed"
    elif isinstance(error, KnowledgeBaseInvariantError):
        summary = "KnowledgeBaseInvariantError: knowledge-base contract violation"
    elif isinstance(error, KnowledgeBaseOperationalError):
        summary = "KnowledgeBaseOperationalError: knowledge-base operation failed"
    elif isinstance(error, SQLAlchemyError):
        summary = f"{type(error).__name__}: database operation failed"
    elif isinstance(error, (KnowledgeBaseError, OSError)):
        summary = f"{type(error).__name__}: knowledge-base operation failed"
    elif isinstance(error, DuplicateArtifactRaceError):
        summary = f"{type(error).__name__}: artifact reconciliation race"
    elif isinstance(error, KnowledgeArtifactError):
        summary = f"{type(error).__name__}: artifact processing failed"
    else:
        summary = f"{type(error).__name__}: unexpected processing failure"

    return re.sub(r"\s+", " ", summary).strip()[:MAX_STORED_ERROR_LENGTH]


async def claim_processing_task(
    task_id: uuid.UUID,
    *,
    now: datetime | None = None,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
) -> ClaimedTask | None:
    claim_time = now or utc_now()
    factory = session_factory or get_session_factory()

    async with factory() as session:
        async with session.begin():
            task = await session.get(ProcessingTask, task_id, with_for_update=True)
            if task is None:
                logger.info("Ignoring stale processing delivery: task_id=%s", task_id)
                return None
            if task.status in TERMINAL_STATUSES:
                return None
            if task.task_type not in SUPPORTED_TASK_TYPES:
                task.status = TASK_STATUS_FAILED
                task.lease_expires_at = None
                task.last_error = UNSUPPORTED_TASK_TYPE_ERROR
                task.updated_at = claim_time
                return None
            if task.status == TASK_STATUS_RUNNING:
                return None
            if task.attempts >= task.max_attempts:
                task.status = TASK_STATUS_FAILED
                task.lease_expires_at = None
                task.last_error = MAX_ATTEMPTS_ERROR
                task.updated_at = claim_time
                return None

            claimable = task.status == TASK_STATUS_QUEUED or (
                task.status in (TASK_STATUS_PENDING, TASK_STATUS_RETRYING)
                and task.available_at <= claim_time
            )
            if not claimable:
                return None

            task.attempts += 1
            task.status = TASK_STATUS_RUNNING
            task.lease_expires_at = claim_time + RUNNING_LEASE_DURATION
            task.last_error = None
            task.updated_at = claim_time
            await session.flush()
            return ClaimedTask(
                id=task.id,
                message_id=task.message_id,
                task_type=task.task_type,
                attempt=task.attempts,
                max_attempts=task.max_attempts,
            )


async def resolve_note_artifact_id(
    session: AsyncSession,
    message_id: uuid.UUID,
) -> uuid.UUID:
    if session.in_transaction():
        raise GitPublicationTransactionError(
            "resolve_note_artifact_id requires a session without an active transaction"
        )

    try:
        artifact_ids = list(
            await session.scalars(
                select(Artifact.id)
                .where(
                    Artifact.message_id == message_id,
                    Artifact.artifact_type == ARTIFACT_TYPE,
                )
                .limit(2)
            )
        )
    finally:
        await session.rollback()

    if not artifact_ids:
        raise GitPublicationInvariantError(
            "deterministic note Artifact is missing for the publication task"
        )
    if len(artifact_ids) != 1:
        raise GitPublicationInvariantError(
            "multiple deterministic note Artifacts exist for the publication task"
        )
    return artifact_ids[0]


async def finalize_processing_task(
    claimed: ClaimedTask,
    *,
    error: Exception | None,
    permanent: bool = False,
    create_publication_task: bool = False,
    now: datetime | None = None,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
) -> bool:
    finalization_time = now or utc_now()
    factory = session_factory or get_session_factory()

    values: dict[str, object] = {
        "lease_expires_at": None,
        "updated_at": finalization_time,
    }
    if error is None:
        values.update(status=TASK_STATUS_SUCCEEDED, last_error=None)
    else:
        values["last_error"] = sanitize_processing_error(
            error,
            task_type=claimed.task_type,
        )
        if permanent or claimed.attempt >= claimed.max_attempts:
            values["status"] = TASK_STATUS_FAILED
        else:
            values.update(
                status=TASK_STATUS_RETRYING,
                available_at=finalization_time + PROCESSING_RETRY_BACKOFF,
            )

    async with factory() as session:
        async with session.begin():
            result = await session.execute(
                update(ProcessingTask)
                .where(
                    ProcessingTask.id == claimed.id,
                    ProcessingTask.status == TASK_STATUS_RUNNING,
                    ProcessingTask.attempts == claimed.attempt,
                    ProcessingTask.task_type == claimed.task_type,
                )
                .values(**values)
            )
            updated = result.rowcount == 1
            if (
                updated
                and error is None
                and create_publication_task
                and claimed.task_type == TASK_TYPE_GENERATE_NOTE
            ):
                await session.execute(
                    insert(ProcessingTask)
                    .values(
                        message_id=claimed.message_id,
                        task_type=TASK_TYPE_PUBLISH_ARTIFACT,
                    )
                    .on_conflict_do_nothing(
                        constraint="uq_processing_tasks_message_id_task_type"
                    )
                )

    if not updated:
        logger.info(
            "Ignoring stale processing finalizer: task_id=%s attempt=%s",
            claimed.id,
            claimed.attempt,
        )
    return updated


async def run_processing_task(
    task_id: uuid.UUID,
    *,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
    knowledge_base_root: Path | None = None,
    processor: Callable[[AsyncSession, uuid.UUID, Path], Awaitable[object]] = (
        process_text_message
    ),
    publication_processor: Callable[
        [AsyncSession, uuid.UUID, Path], Awaitable[object]
    ] = publish_artifact_to_git,
    artifact_resolver: Callable[
        [AsyncSession, uuid.UUID], Awaitable[uuid.UUID]
    ] = resolve_note_artifact_id,
    git_publication_enabled: bool | None = None,
) -> None:
    factory = session_factory or get_session_factory()
    claimed = await claim_processing_task(task_id, session_factory=factory)
    if claimed is None:
        return

    settings = get_settings()
    root = knowledge_base_root or settings.knowledge_base_path
    publication_enabled = (
        settings.git_publication_enabled
        if git_publication_enabled is None
        else git_publication_enabled
    )
    processing_error: Exception | None = None
    permanent = False
    try:
        if claimed.task_type == TASK_TYPE_GENERATE_NOTE:
            async with factory() as session:
                await processor(session, claimed.message_id, root)
        else:
            async with factory() as session:
                artifact_id = await artifact_resolver(session, claimed.message_id)
            async with factory() as session:
                await publication_processor(session, artifact_id, root)
    except Exception as exc:
        processing_error = exc
        if claimed.task_type == TASK_TYPE_PUBLISH_ARTIFACT:
            permanent = isinstance(
                exc,
                (
                    GitPublicationInvariantError,
                    SourceMessageError,
                    ArtifactConsistencyError,
                    KnowledgeBaseInvariantError,
                ),
            )
        else:
            permanent = isinstance(exc, PERMANENT_PROCESSING_ERRORS)

    try:
        await finalize_processing_task(
            claimed,
            error=processing_error,
            permanent=permanent,
            create_publication_task=publication_enabled,
            session_factory=factory,
        )
    except Exception:
        logger.exception(
            "Processing task finalization failed: task_id=%s attempt=%s",
            claimed.id,
            claimed.attempt,
        )
        raise
