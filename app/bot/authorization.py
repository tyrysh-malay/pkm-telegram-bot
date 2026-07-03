from collections.abc import Collection

from aiogram.enums import ChatType
from aiogram.filters import BaseFilter
from aiogram.types import Message


class PrivateOwnerFilter(BaseFilter):
    def __init__(self, allowed_user_ids: Collection[int]) -> None:
        self.allowed_user_ids = frozenset(allowed_user_ids)

    async def __call__(self, message: Message) -> bool:
        sender = getattr(message, "from_user", None)
        sender_id = getattr(sender, "id", None)
        chat_type = getattr(getattr(message, "chat", None), "type", None)

        return (
            chat_type == ChatType.PRIVATE
            and type(sender_id) is int
            and sender_id in self.allowed_user_ids
        )
