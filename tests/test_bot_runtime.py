import asyncio

import pytest

from app.bot.runtime import TelegramPollingRuntime


def test_telegram_polling_disabled_does_not_create_bot_or_task() -> None:
    async def run() -> None:
        runtime = TelegramPollingRuntime(enabled=False, token=None)

        await runtime.start()
        await runtime.stop()

        assert runtime.bot is None
        assert runtime.dispatcher is None
        assert runtime.polling_task is None

    asyncio.run(run())


def test_telegram_enabled_without_token_fails_clearly() -> None:
    async def run() -> None:
        runtime = TelegramPollingRuntime(enabled=True, token="")

        with pytest.raises(RuntimeError, match="TELEGRAM_BOT_TOKEN is required"):
            await runtime.start()

    asyncio.run(run())
