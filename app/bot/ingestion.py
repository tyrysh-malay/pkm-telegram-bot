import logging
import uuid

from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert

from app.db.models import Message
from app.db.models import ProcessingTask
from app.db.models import User
from app.db.session import get_session_factory


logger = logging.getLogger(__name__)


class TelegramTextInput(BaseModel):
    telegram_user_id: int
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    telegram_chat_id: int
    telegram_message_id: int
    text: str

    @property
    def idempotency_key(self) -> str:
        return f"telegram:{self.telegram_chat_id}:{self.telegram_message_id}"


class PersistedTelegramMessage(BaseModel):
    user_id: uuid.UUID
    message_id: uuid.UUID | None
    idempotency_key: str
    inserted: bool


async def persist_text_message(
    telegram_input: TelegramTextInput,
) -> PersistedTelegramMessage:
    session_factory = get_session_factory()

    async with session_factory() as session:
        async with session.begin():
            user_insert = insert(User).values(
                telegram_user_id=telegram_input.telegram_user_id,
                username=telegram_input.username,
                first_name=telegram_input.first_name,
                last_name=telegram_input.last_name,
            )
            user_result = await session.execute(
                user_insert.on_conflict_do_update(
                    constraint="uq_users_telegram_user_id",
                    set_={
                        "username": user_insert.excluded.username,
                        "first_name": user_insert.excluded.first_name,
                        "last_name": user_insert.excluded.last_name,
                        "updated_at": func.now(),
                    },
                ).returning(User.id)
            )
            user_id = user_result.scalar_one()

            message_insert = insert(Message).values(
                user_id=user_id,
                telegram_chat_id=telegram_input.telegram_chat_id,
                telegram_message_id=telegram_input.telegram_message_id,
                input_type="text",
                raw_text=telegram_input.text,
                status="received",
                idempotency_key=telegram_input.idempotency_key,
            )
            message_result = await session.execute(
                message_insert.on_conflict_do_nothing(
                    constraint="uq_messages_idempotency_key",
                ).returning(Message.id)
            )
            message_id = message_result.scalar_one_or_none()
            if message_id is not None:
                session.add(ProcessingTask(message_id=message_id))
                await session.flush()

    if message_id is None:
        logger.info(
            "Duplicate Telegram text message observed: telegram_user_id=%s "
            "telegram_chat_id=%s telegram_message_id=%s",
            telegram_input.telegram_user_id,
            telegram_input.telegram_chat_id,
            telegram_input.telegram_message_id,
        )
    else:
        logger.info(
            "Telegram text message persisted: telegram_user_id=%s "
            "telegram_chat_id=%s telegram_message_id=%s",
            telegram_input.telegram_user_id,
            telegram_input.telegram_chat_id,
            telegram_input.telegram_message_id,
        )

    return PersistedTelegramMessage(
        user_id=user_id,
        message_id=message_id,
        idempotency_key=telegram_input.idempotency_key,
        inserted=message_id is not None,
    )
