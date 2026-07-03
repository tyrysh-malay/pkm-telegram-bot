import asyncio
import logging
from collections.abc import Collection
from contextlib import suppress

from aiogram import Bot
from aiogram import Dispatcher

from app.bot.authorization import PrivateOwnerFilter
from app.bot.handlers import build_handlers_router
from app.settings import Settings


logger = logging.getLogger(__name__)


def build_dispatcher(allowed_user_ids: Collection[int]) -> Dispatcher:
    dispatcher = Dispatcher()
    dispatcher.message.filter(PrivateOwnerFilter(allowed_user_ids))
    dispatcher.include_router(build_handlers_router())
    return dispatcher


class TelegramPollingRuntime:
    def __init__(
        self,
        enabled: bool,
        token: str | None,
        allowed_user_ids: Collection[int] = frozenset(),
    ) -> None:
        self.enabled = enabled
        self.token = token
        self.allowed_user_ids = frozenset(allowed_user_ids)
        self.bot: Bot | None = None
        self.dispatcher: Dispatcher | None = None
        self.polling_task: asyncio.Task[None] | None = None
        self._stopping = False

    @classmethod
    def from_settings(cls, settings: Settings) -> "TelegramPollingRuntime":
        return cls(
            enabled=settings.telegram_bot_enabled,
            token=settings.telegram_bot_token,
            allowed_user_ids=settings.telegram_allowed_user_ids,
        )

    async def start(self) -> None:
        if not self.enabled:
            logger.info("Telegram polling disabled")
            return

        if not self.token or not self.token.strip():
            raise RuntimeError(
                "TELEGRAM_BOT_TOKEN is required when TELEGRAM_BOT_ENABLED=true"
            )
        if not self.allowed_user_ids:
            raise RuntimeError(
                "TELEGRAM_ALLOWED_USER_IDS is required when "
                "TELEGRAM_BOT_ENABLED=true"
            )

        self.bot = Bot(self.token)
        self.dispatcher = build_dispatcher(self.allowed_user_ids)
        self.polling_task = asyncio.create_task(self.dispatcher.start_polling(self.bot))
        self.polling_task.add_done_callback(self._handle_polling_done)
        logger.info("Telegram polling started")

    def _handle_polling_done(self, task: asyncio.Task[None]) -> None:
        if self._stopping or task.cancelled():
            return

        exception = task.exception()
        if exception is None:
            logger.warning("Telegram polling task stopped unexpectedly")
            return

        logger.error(
            "Telegram polling task stopped with an error",
            exc_info=(type(exception), exception, exception.__traceback__),
        )

    async def stop(self) -> None:
        self._stopping = True

        if self.dispatcher is not None:
            with suppress(RuntimeError):
                await self.dispatcher.stop_polling()

        if self.polling_task is not None:
            task_error_logged = False
            if not self.polling_task.done():
                try:
                    await asyncio.wait_for(asyncio.shield(self.polling_task), timeout=5)
                except TimeoutError:
                    self.polling_task.cancel()
                except Exception:
                    logger.exception("Telegram polling task stopped with an error")
                    task_error_logged = True

            try:
                await self.polling_task
            except asyncio.CancelledError:
                pass
            except Exception:
                if not task_error_logged:
                    logger.exception("Telegram polling task stopped with an error")

        if self.bot is not None:
            await self.bot.session.close()

        if self.enabled:
            logger.info("Telegram polling stopped")
