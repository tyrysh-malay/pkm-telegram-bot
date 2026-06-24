import logging

from aiogram import F
from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message as AiogramMessage

from app.bot.ingestion import TelegramTextInput
from app.bot.ingestion import persist_text_message


START_TEXT = "Send me a text note and I will save it for processing."
ACK_TEXT = "Saved for processing."

logger = logging.getLogger(__name__)
router = Router()


def build_text_input(message: AiogramMessage) -> TelegramTextInput:
    if message.from_user is None:
        raise ValueError("Telegram message has no user metadata")
    if message.text is None:
        raise ValueError("Telegram message has no text")

    return TelegramTextInput(
        telegram_user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
        telegram_chat_id=message.chat.id,
        telegram_message_id=message.message_id,
        text=message.text,
    )


@router.message(CommandStart())
async def handle_start(message: AiogramMessage) -> None:
    await message.answer(START_TEXT)


@router.message(F.text, ~F.text.startswith("/"))
async def handle_text_message(message: AiogramMessage) -> None:
    try:
        telegram_input = build_text_input(message)
        await persist_text_message(telegram_input)
    except Exception:
        logger.exception(
            "Failed to persist Telegram text message: telegram_chat_id=%s "
            "telegram_message_id=%s",
            getattr(getattr(message, "chat", None), "id", None),
            getattr(message, "message_id", None),
        )
        return

    try:
        await message.answer(ACK_TEXT)
    except Exception:
        logger.exception(
            "Failed to send Telegram acknowledgement: telegram_chat_id=%s "
            "telegram_message_id=%s",
            message.chat.id,
            message.message_id,
        )
