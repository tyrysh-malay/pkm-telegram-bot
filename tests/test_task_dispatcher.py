import asyncio
import uuid
from datetime import datetime
from datetime import timedelta
from datetime import timezone

from sqlalchemy import select

from app.bot.ingestion import TelegramTextInput
from app.bot.ingestion import persist_text_message
from app.db.models import ProcessingTask
from app.db.session import get_session_factory
from app.worker.constants import PROCESSING_RETRY_BACKOFF
from app.worker.dispatcher import TaskDispatcherRuntime
from app.worker.dispatcher import find_dispatch_candidates
from app.worker.dispatcher import mark_task_queued
from app.worker.dispatcher import recover_expired_leases


NOW = datetime(2026, 7, 3, 12, 0, tzinfo=timezone.utc)


async def create_task(**changes: object) -> ProcessingTask:
    unique = uuid.uuid4().int % 9_000_000_000_000_000_000
    persisted = await persist_text_message(
        TelegramTextInput(
            telegram_user_id=unique,
            telegram_chat_id=-unique,
            telegram_message_id=1,
            text="dispatcher source",
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


def test_due_task_publishes_uuid_and_becomes_queued() -> None:
    async def run() -> None:
        task = await create_task(available_at=NOW - timedelta(seconds=1))
        published: list[str] = []
        candidates = await find_dispatch_candidates(now=NOW)
        assert [candidate.id for candidate in candidates] == [task.id]
        published.append(str(candidates[0].id))
        assert await mark_task_queued(candidates[0], now=NOW) is True

        current = await load_task(task.id)
        assert published == [str(task.id)]
        assert current.status == "queued"
        assert current.attempts == 0
        assert current.lease_expires_at == NOW + timedelta(seconds=30)

    asyncio.run(run())


def test_dispatcher_selects_publication_task_without_task_type_branching() -> None:
    async def run() -> None:
        task = await create_task(
            task_type="publish_artifact",
            available_at=NOW - timedelta(seconds=1),
        )

        candidates = await find_dispatch_candidates(now=NOW)

        assert [candidate.id for candidate in candidates] == [task.id]
        assert await mark_task_queued(candidates[0], now=NOW) is True
        assert (await load_task(task.id)).status == "queued"

    asyncio.run(run())


def test_future_retry_is_not_dispatched_and_batch_order_is_deterministic() -> None:
    async def run() -> None:
        late = await create_task(
            status="retrying", available_at=NOW + timedelta(seconds=1)
        )
        second = await create_task(available_at=NOW - timedelta(seconds=1))
        first = await create_task(available_at=NOW - timedelta(seconds=2))

        candidates = await find_dispatch_candidates(now=NOW, batch_size=2)

        assert [candidate.id for candidate in candidates] == [first.id, second.id]
        assert late.id not in {candidate.id for candidate in candidates}

    asyncio.run(run())


def test_publication_failure_leaves_task_unchanged() -> None:
    async def run() -> None:
        task = await create_task(available_at=datetime.now(timezone.utc))

        def fail(_task_id: str) -> None:
            raise ConnectionError("redis unavailable")

        runtime = TaskDispatcherRuntime(enabled=True, publisher=fail)
        assert await runtime._dispatch_once() is False

        current = await load_task(task.id)
        assert current.status == "pending"
        assert current.attempts == 0
        assert current.lease_expires_at is None
        assert current.last_error is None

    asyncio.run(run())


def test_fast_worker_race_does_not_overwrite_running_state() -> None:
    async def run() -> None:
        task = await create_task(available_at=NOW - timedelta(seconds=1))
        candidate = (await find_dispatch_candidates(now=NOW))[0]

        session_factory = get_session_factory()
        async with session_factory() as session:
            current = await session.get(ProcessingTask, task.id)
            assert current is not None
            current.status = "running"
            current.attempts = 1
            current.lease_expires_at = NOW + timedelta(minutes=5)
            await session.commit()

        assert await mark_task_queued(candidate, now=NOW) is False
        current = await load_task(task.id)
        assert current.status == "running"
        assert current.attempts == 1

    asyncio.run(run())


def test_expired_leases_recover_to_required_states() -> None:
    async def run() -> None:
        queued = await create_task(
            status="queued",
            attempts=0,
            lease_expires_at=NOW - timedelta(seconds=1),
        )
        running = await create_task(
            status="running",
            attempts=1,
            lease_expires_at=NOW - timedelta(seconds=1),
        )
        exhausted = await create_task(
            status="running",
            attempts=3,
            lease_expires_at=NOW - timedelta(seconds=1),
        )
        active = await create_task(
            status="running",
            attempts=1,
            lease_expires_at=NOW + timedelta(seconds=1),
        )

        session_factory = get_session_factory()
        async with session_factory() as session:
            async with session.begin():
                assert await recover_expired_leases(session, NOW) == (1, 1, 1)

        queued_current = await load_task(queued.id)
        running_current = await load_task(running.id)
        exhausted_current = await load_task(exhausted.id)
        active_current = await load_task(active.id)
        assert (queued_current.status, queued_current.attempts) == ("pending", 0)
        assert queued_current.available_at == NOW
        assert queued_current.lease_expires_at is None
        assert running_current.status == "retrying"
        assert running_current.available_at == NOW + PROCESSING_RETRY_BACKOFF
        assert running_current.lease_expires_at is None
        assert exhausted_current.status == "failed"
        assert exhausted_current.lease_expires_at is None
        assert active_current.status == "running"

    asyncio.run(run())


def test_disabled_runtime_starts_no_task_or_publication() -> None:
    async def run() -> None:
        published: list[str] = []
        runtime = TaskDispatcherRuntime(enabled=False, publisher=published.append)
        await runtime.start()
        await runtime.stop()
        assert runtime.dispatch_task is None
        assert published == []

    asyncio.run(run())


def test_dispatcher_setting_is_independent_of_telegram_setting() -> None:
    from app.settings import Settings

    settings = Settings(
        telegram_bot_enabled=False,
        task_dispatcher_enabled=True,
    )
    runtime = TaskDispatcherRuntime.from_settings(settings)
    assert runtime.enabled is True


def test_enabled_runtime_start_is_nonblocking_when_publication_fails(
    monkeypatch,
) -> None:
    async def run() -> None:
        await create_task(available_at=datetime.now(timezone.utc))

        def fail(_task_id: str) -> None:
            raise ConnectionError("redis unavailable")

        monkeypatch.setattr("app.worker.dispatcher.close_broker", lambda: None)
        runtime = TaskDispatcherRuntime(enabled=True, publisher=fail)
        await runtime.start()
        assert runtime.dispatch_task is not None
        await asyncio.sleep(0.05)
        assert runtime.dispatch_task.done() is False
        await runtime.stop()

    asyncio.run(run())


def test_compose_worker_and_redis_boundary() -> None:
    from pathlib import Path

    import yaml

    compose = yaml.safe_load(Path("docker-compose.yml").read_text())
    services = compose["services"]
    assert set(services) == {"app", "worker", "redis", "postgres"}
    assert services["worker"]["command"] == [
        "dramatiq",
        "app.worker.tasks",
        "--processes",
        "1",
        "--threads",
        "1",
    ]
    assert services["worker"]["volumes"] == services["app"]["volumes"]
    assert services["worker"]["image"] == services["app"]["image"]
    assert "redis" not in services["app"]["depends_on"]
    assert "REDIS_URL" in services["worker"]["environment"]
    assert "DATABASE_URL" in services["worker"]["environment"]
    assert "KNOWLEDGE_BASE_PATH" in services["worker"]["environment"]


def test_broker_has_no_result_backend_middleware() -> None:
    from dramatiq.results import Results

    from app.worker.broker import broker

    assert not any(isinstance(middleware, Results) for middleware in broker.middleware)
