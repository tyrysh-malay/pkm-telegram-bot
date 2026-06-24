import asyncio
from types import SimpleNamespace

from app.bot.handlers import ACK_TEXT
from app.bot.handlers import START_TEXT
from app.bot.handlers import handle_start
from app.bot.handlers import handle_text_message


class FakeMessage:
    def __init__(self) -> None:
        self.from_user = SimpleNamespace(
            id=123,
            username="tester",
            first_name="Test",
            last_name="User",
        )
        self.chat = SimpleNamespace(id=456)
        self.message_id = 789
        self.text = "hello from telegram"
        self.answers: list[str] = []

    async def answer(self, text: str) -> None:
        self.answers.append(text)


def test_start_handler_returns_expected_text() -> None:
    async def run() -> None:
        message = FakeMessage()

        await handle_start(message)

        assert message.answers == [START_TEXT]

    asyncio.run(run())


def test_text_handler_sends_ack_after_successful_persistence(monkeypatch) -> None:
    async def run() -> None:
        seen_inputs = []

        async def fake_persist(telegram_input):
            seen_inputs.append(telegram_input)

        monkeypatch.setattr("app.bot.handlers.persist_text_message", fake_persist)
        message = FakeMessage()

        await handle_text_message(message)

        assert message.answers == [ACK_TEXT]
        assert seen_inputs[0].telegram_user_id == 123
        assert seen_inputs[0].telegram_chat_id == 456
        assert seen_inputs[0].telegram_message_id == 789
        assert seen_inputs[0].text == "hello from telegram"
        assert seen_inputs[0].idempotency_key == "telegram:456:789"

    asyncio.run(run())


def test_text_handler_does_not_acknowledge_database_failure(monkeypatch) -> None:
    async def run() -> None:
        async def failing_persist(_telegram_input):
            raise RuntimeError("database unavailable")

        monkeypatch.setattr("app.bot.handlers.persist_text_message", failing_persist)
        message = FakeMessage()

        await handle_text_message(message)

        assert message.answers == []

    asyncio.run(run())
