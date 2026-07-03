import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi import HTTPException

from app.bot.runtime import TelegramPollingRuntime
from app.db.session import check_database_ready
from app.settings import get_settings
from app.worker.dispatcher import TaskDispatcherRuntime


logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    telegram_runtime = TelegramPollingRuntime.from_settings(settings)
    task_dispatcher_runtime = TaskDispatcherRuntime.from_settings(settings)
    app.state.telegram_runtime = telegram_runtime
    app.state.task_dispatcher_runtime = task_dispatcher_runtime

    await telegram_runtime.start()
    await task_dispatcher_runtime.start()
    try:
        yield
    finally:
        await task_dispatcher_runtime.stop()
        await telegram_runtime.stop()


app = FastAPI(title=settings.app_name, lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "ok",
        "app": settings.app_name,
        "environment": settings.environment,
    }


@app.get("/ready")
async def ready() -> dict[str, str]:
    try:
        await check_database_ready()
    except Exception as exc:
        logger.exception("Database readiness check failed")
        raise HTTPException(status_code=503, detail="database unavailable") from exc

    return {"status": "ready", "database": "ok"}
