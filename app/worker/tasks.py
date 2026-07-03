import asyncio
import logging
import uuid

import dramatiq

from app.db.session import dispose_engine
from app.worker.broker import broker as broker
from app.worker.processing import parse_processing_task_id
from app.worker.processing import run_processing_task


logger = logging.getLogger(__name__)


async def _run_actor_delivery(task_id: uuid.UUID) -> None:
    try:
        await run_processing_task(task_id)
    except BaseException as processing_error:
        try:
            await dispose_engine()
        except BaseException as disposal_error:
            logger.error(
                "Database engine disposal failed after processing error",
                exc_info=(
                    type(disposal_error),
                    disposal_error,
                    disposal_error.__traceback__,
                ),
            )
            processing_error.add_note(
                "database engine disposal also failed: "
                f"{type(disposal_error).__name__}"
            )
        raise

    await dispose_engine()


@dramatiq.actor(max_retries=0)
def process_processing_task(processing_task_id: str) -> None:
    task_id = parse_processing_task_id(processing_task_id)
    asyncio.run(_run_actor_delivery(task_id))
