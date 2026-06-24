import logging

from fastapi import FastAPI
from fastapi import HTTPException

from app.db.session import check_database_ready
from app.settings import get_settings


logger = logging.getLogger(__name__)
settings = get_settings()

app = FastAPI(title=settings.app_name)


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
