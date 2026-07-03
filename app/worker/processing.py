import logging
import re
import uuid
from collections.abc import Awaitable
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from datetime import timezone
from pathlib import Path

from sqlalchemy import update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.db.models import ProcessingTask
from app.db.session import get_session_factory
from app.knowledge.errors import ArtifactConsistencyError
from app.knowledge.errors import DuplicateArtifactRaceError
from app.knowledge.errors import FileConflictError
from app.knowledge.errors import KnowledgeArtifactError
from app.knowledge.errors import KnowledgeBaseError
from app.knowledge.errors import ProcessingTransactionError
from app.knowledge.errors import SourceMessageError
from app.knowledge.errors import UnsupportedFileEntryError
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


def sanitize_processing_error(error: Exception) -> str:
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
            if task.task_type != TASK_TYPE_GENERATE_NOTE:
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
                attempt=task.attempts,
                max_attempts=task.max_attempts,
            )


async def finalize_processing_task(
    claimed: ClaimedTask,
    *,
    error: Exception | None,
    permanent: bool = False,
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
        values["last_error"] = sanitize_processing_error(error)
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
                )
                .values(**values)
            )
            updated = result.rowcount == 1

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
) -> None:
    factory = session_factory or get_session_factory()
    claimed = await claim_processing_task(task_id, session_factory=factory)
    if claimed is None:
        return

    root = knowledge_base_root or get_settings().knowledge_base_path
    processing_error: Exception | None = None
    permanent = False
    try:
        async with factory() as session:
            await processor(session, claimed.message_id, root)
    except Exception as exc:
        processing_error = exc
        permanent = isinstance(exc, PERMANENT_PROCESSING_ERRORS)

    try:
        await finalize_processing_task(
            claimed,
            error=processing_error,
            permanent=permanent,
            session_factory=factory,
        )
    except Exception:
        logger.exception(
            "Processing task finalization failed: task_id=%s attempt=%s",
            claimed.id,
            claimed.attempt,
        )
        raise
