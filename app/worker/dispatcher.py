import asyncio
import logging
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from datetime import timezone

from sqlalchemy import select
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.db.models import ProcessingTask
from app.db.session import get_session_factory
from app.settings import Settings
from app.worker.broker import close_broker
from app.worker.constants import BROKER_FAILURE_RETRY_SECONDS
from app.worker.constants import DISPATCH_BATCH_SIZE
from app.worker.constants import DISPATCH_POLL_INTERVAL_SECONDS
from app.worker.constants import DISPATCHABLE_STATUSES
from app.worker.constants import MAX_ATTEMPTS_LEASE_EXPIRED_ERROR
from app.worker.constants import PROCESSING_RETRY_BACKOFF
from app.worker.constants import QUEUED_LEASE_DURATION
from app.worker.constants import TASK_STATUS_FAILED
from app.worker.constants import TASK_STATUS_PENDING
from app.worker.constants import TASK_STATUS_QUEUED
from app.worker.constants import TASK_STATUS_RETRYING
from app.worker.constants import TASK_STATUS_RUNNING
from app.worker.constants import WORKER_LEASE_EXPIRED_ERROR
from app.worker.tasks import process_processing_task


logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class DispatchCandidate:
    id: uuid.UUID
    status: str
    attempts: int
    observed_at: datetime


async def recover_expired_leases(
    session: AsyncSession,
    now: datetime,
) -> tuple[int, int, int]:
    queued = await session.execute(
        update(ProcessingTask)
        .where(
            ProcessingTask.status == TASK_STATUS_QUEUED,
            ProcessingTask.lease_expires_at <= now,
        )
        .values(
            status=TASK_STATUS_PENDING,
            available_at=now,
            lease_expires_at=None,
            updated_at=now,
        )
    )
    retrying = await session.execute(
        update(ProcessingTask)
        .where(
            ProcessingTask.status == TASK_STATUS_RUNNING,
            ProcessingTask.lease_expires_at <= now,
            ProcessingTask.attempts < ProcessingTask.max_attempts,
        )
        .values(
            status=TASK_STATUS_RETRYING,
            available_at=now + PROCESSING_RETRY_BACKOFF,
            lease_expires_at=None,
            last_error=WORKER_LEASE_EXPIRED_ERROR,
            updated_at=now,
        )
    )
    failed = await session.execute(
        update(ProcessingTask)
        .where(
            ProcessingTask.status == TASK_STATUS_RUNNING,
            ProcessingTask.lease_expires_at <= now,
            ProcessingTask.attempts >= ProcessingTask.max_attempts,
        )
        .values(
            status=TASK_STATUS_FAILED,
            lease_expires_at=None,
            last_error=MAX_ATTEMPTS_LEASE_EXPIRED_ERROR,
            updated_at=now,
        )
    )
    return queued.rowcount, retrying.rowcount, failed.rowcount


async def find_dispatch_candidates(
    *,
    now: datetime | None = None,
    batch_size: int = DISPATCH_BATCH_SIZE,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
) -> list[DispatchCandidate]:
    observation_time = now or utc_now()
    factory = session_factory or get_session_factory()
    async with factory() as session:
        async with session.begin():
            recovered = await recover_expired_leases(session, observation_time)
            rows = (
                await session.execute(
                    select(
                        ProcessingTask.id,
                        ProcessingTask.status,
                        ProcessingTask.attempts,
                    )
                    .where(
                        ProcessingTask.status.in_(DISPATCHABLE_STATUSES),
                        ProcessingTask.available_at <= observation_time,
                        ProcessingTask.attempts < ProcessingTask.max_attempts,
                    )
                    .order_by(
                        ProcessingTask.available_at,
                        ProcessingTask.created_at,
                        ProcessingTask.id,
                    )
                    .limit(batch_size)
                )
            ).all()

    if any(recovered):
        logger.info(
            "Recovered expired processing leases: queued=%s retrying=%s failed=%s",
            *recovered,
        )
    return [
        DispatchCandidate(row.id, row.status, row.attempts, observation_time)
        for row in rows
    ]


async def mark_task_queued(
    candidate: DispatchCandidate,
    *,
    now: datetime | None = None,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
) -> bool:
    queued_at = now or utc_now()
    factory = session_factory or get_session_factory()
    async with factory() as session:
        async with session.begin():
            result = await session.execute(
                update(ProcessingTask)
                .where(
                    ProcessingTask.id == candidate.id,
                    ProcessingTask.status == candidate.status,
                    ProcessingTask.attempts == candidate.attempts,
                    ProcessingTask.available_at <= candidate.observed_at,
                )
                .values(
                    status=TASK_STATUS_QUEUED,
                    lease_expires_at=queued_at + QUEUED_LEASE_DURATION,
                    updated_at=queued_at,
                )
            )
            return result.rowcount == 1


class TaskDispatcherRuntime:
    def __init__(
        self,
        *,
        enabled: bool,
        publisher: Callable[[str], object] = process_processing_task.send,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
    ) -> None:
        self.enabled = enabled
        self.publisher = publisher
        self.session_factory = session_factory
        self.dispatch_task: asyncio.Task[None] | None = None

    @classmethod
    def from_settings(cls, settings: Settings) -> "TaskDispatcherRuntime":
        return cls(enabled=settings.task_dispatcher_enabled)

    async def start(self) -> None:
        if not self.enabled:
            logger.info("Processing task dispatcher disabled")
            return
        if self.dispatch_task is not None:
            return
        self.dispatch_task = asyncio.create_task(self._run())
        logger.info("Processing task dispatcher started")

    async def _dispatch_once(self) -> bool:
        candidates = await find_dispatch_candidates(
            session_factory=self.session_factory
        )
        for candidate in candidates:
            try:
                await asyncio.to_thread(self.publisher, str(candidate.id))
            except Exception as exc:
                logger.warning(
                    "Processing task publication failed: task_id=%s error=%s",
                    candidate.id,
                    type(exc).__name__,
                )
                return False
            await mark_task_queued(
                candidate,
                session_factory=self.session_factory,
            )
        return True

    async def _run(self) -> None:
        while True:
            delay = DISPATCH_POLL_INTERVAL_SECONDS
            try:
                published = await self._dispatch_once()
                if not published:
                    delay = BROKER_FAILURE_RETRY_SECONDS
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Processing task dispatcher iteration failed")
                delay = BROKER_FAILURE_RETRY_SECONDS
            await asyncio.sleep(delay)

    async def stop(self) -> None:
        if self.dispatch_task is not None:
            self.dispatch_task.cancel()
            try:
                await self.dispatch_task
            except asyncio.CancelledError:
                pass
            self.dispatch_task = None
        if self.enabled:
            await asyncio.to_thread(close_broker)
            logger.info("Processing task dispatcher stopped")
