import asyncio
import socket
from datetime import datetime
from datetime import timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from aiogram import Bot
from aiogram.enums import ChatType
from aiogram.methods import SendMessage
from aiogram.types import Chat
from aiogram.types import Message as AiogramMessage
from aiogram.types import Update
from aiogram.types import User as AiogramUser
from pydantic import ValidationError
from pydantic_settings import SettingsError
from sqlalchemy import func
from sqlalchemy import select

from app.bot.authorization import PrivateOwnerFilter
from app.bot.handlers import ACK_TEXT
from app.bot.handlers import START_TEXT
from app.bot.runtime import TelegramPollingRuntime
from app.bot.runtime import build_dispatcher
from app.db.models import Artifact
from app.db.models import Message
from app.db.models import ProcessingTask
from app.db.models import User
from app.db.session import get_session_factory
from app.knowledge.markdown import render_text_note
from app.settings import Settings
from app.worker.dispatcher import find_dispatch_candidates
from app.worker.dispatcher import mark_task_queued
from app.worker.processing import run_processing_task


ALLOWED_USER_ID = 700_000_001
UNKNOWN_USER_ID = 700_000_002
PRIVATE_CHAT_ID = 700_000_010
GROUP_CHAT_ID = -700_000_020
BOT_TOKEN = "123456:abcdefghijklmnopqrstuvwxyzABCDEFGHI"


class RecordingBot(Bot):
    def __init__(self) -> None:
        super().__init__(BOT_TOKEN)
        self.requests: list[object] = []

    async def __call__(self, method, request_timeout=None):
        self.requests.append(method)
        return None


def make_update(
    *,
    update_id: int,
    message_id: int,
    text: str,
    user_id: int | None,
    chat_id: int,
    chat_type: ChatType = ChatType.PRIVATE,
    username: str | None = None,
    first_name: str = "Test",
    last_name: str | None = "User",
) -> Update:
    sender = None
    if user_id is not None:
        sender = AiogramUser(
            id=user_id,
            is_bot=False,
            first_name=first_name,
            last_name=last_name,
            username=username,
        )

    return Update(
        update_id=update_id,
        message=AiogramMessage(
            message_id=message_id,
            date=datetime(2026, 7, 3, 12, 0, tzinfo=timezone.utc),
            chat=Chat(id=chat_id, type=chat_type),
            from_user=sender,
            text=text,
        ),
    )


def settings_from_allowlist_json(
    monkeypatch: pytest.MonkeyPatch,
    raw_allowlist: str,
    *,
    enabled: bool = False,
    token: str | None = None,
) -> Settings:
    monkeypatch.setenv("TELEGRAM_ALLOWED_USER_IDS", raw_allowlist)
    return Settings(
        _env_file=None,
        telegram_bot_enabled=enabled,
        telegram_bot_token=token,
    )


def test_disabled_telegram_accepts_omitted_empty_and_nonempty_allowlists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("TELEGRAM_ALLOWED_USER_IDS", raising=False)
    omitted = Settings(
        _env_file=None,
        telegram_bot_enabled=False,
        telegram_bot_token=None,
    )
    empty = settings_from_allowlist_json(monkeypatch, "[]")
    configured = settings_from_allowlist_json(monkeypatch, "[700000001]")

    assert omitted.telegram_allowed_user_ids == frozenset()
    assert empty.telegram_allowed_user_ids == frozenset()
    assert configured.telegram_allowed_user_ids == frozenset({ALLOWED_USER_ID})


def test_enabled_telegram_accepts_one_or_multiple_valid_ids(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    one = settings_from_allowlist_json(
        monkeypatch,
        "[700000001]",
        enabled=True,
        token=BOT_TOKEN,
    )
    multiple = settings_from_allowlist_json(
        monkeypatch,
        " [700000001, 700000002] ",
        enabled=True,
        token=BOT_TOKEN,
    )

    assert one.telegram_allowed_user_ids == frozenset({ALLOWED_USER_ID})
    assert multiple.telegram_allowed_user_ids == frozenset(
        {ALLOWED_USER_ID, UNKNOWN_USER_ID}
    )


@pytest.mark.parametrize("raw_allowlist", ["[]", None])
def test_enabled_telegram_rejects_empty_or_omitted_allowlist(
    monkeypatch: pytest.MonkeyPatch,
    raw_allowlist: str | None,
) -> None:
    if raw_allowlist is None:
        monkeypatch.delenv("TELEGRAM_ALLOWED_USER_IDS", raising=False)
    else:
        monkeypatch.setenv("TELEGRAM_ALLOWED_USER_IDS", raw_allowlist)

    with pytest.raises(ValidationError, match="TELEGRAM_ALLOWED_USER_IDS"):
        Settings(
            _env_file=None,
            telegram_bot_enabled=True,
            telegram_bot_token=BOT_TOKEN,
        )


@pytest.mark.parametrize("token", [None, "", "   "])
def test_enabled_telegram_rejects_missing_or_blank_token(
    monkeypatch: pytest.MonkeyPatch,
    token: str | None,
) -> None:
    with pytest.raises(ValidationError, match="TELEGRAM_BOT_TOKEN"):
        settings_from_allowlist_json(
            monkeypatch,
            "[700000001]",
            enabled=True,
            token=token,
        )


@pytest.mark.parametrize(
    "raw_allowlist",
    [
        "not-json",
        "123456789",
        "123,456",
        '["700000001"]',
        "[true]",
        "[null]",
        "[12.5]",
        "[0]",
        "[-1]",
        f"[{2**63}]",
    ],
)
def test_allowlist_rejects_malformed_or_non_strict_ids(
    monkeypatch: pytest.MonkeyPatch,
    raw_allowlist: str,
) -> None:
    monkeypatch.setenv("TELEGRAM_ALLOWED_USER_IDS", raw_allowlist)

    with pytest.raises((SettingsError, ValidationError)):
        Settings(_env_file=None, telegram_bot_enabled=False)


def test_duplicate_allowlist_ids_normalize_to_one_member(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = settings_from_allowlist_json(
        monkeypatch,
        "[700000001, 700000001]",
        enabled=True,
        token=BOT_TOKEN,
    )

    assert settings.telegram_allowed_user_ids == frozenset({ALLOWED_USER_ID})


def test_settings_validation_performs_no_network_connection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_connection(*_args, **_kwargs):
        raise AssertionError("settings validation attempted a network connection")

    monkeypatch.setattr(socket, "create_connection", fail_connection)
    settings = settings_from_allowlist_json(
        monkeypatch,
        "[700000001]",
        enabled=True,
        token=BOT_TOKEN,
    )

    assert settings.telegram_bot_enabled is True


@pytest.mark.parametrize(
    ("sender_id", "chat_id", "chat_type", "expected"),
    [
        (ALLOWED_USER_ID, PRIVATE_CHAT_ID, ChatType.PRIVATE, True),
        (UNKNOWN_USER_ID, PRIVATE_CHAT_ID, ChatType.PRIVATE, False),
        (ALLOWED_USER_ID, GROUP_CHAT_ID, ChatType.GROUP, False),
        (UNKNOWN_USER_ID, GROUP_CHAT_ID, ChatType.GROUP, False),
        (ALLOWED_USER_ID, GROUP_CHAT_ID, ChatType.SUPERGROUP, False),
        (ALLOWED_USER_ID, GROUP_CHAT_ID, ChatType.CHANNEL, False),
        (UNKNOWN_USER_ID, ALLOWED_USER_ID, ChatType.PRIVATE, False),
    ],
)
def test_private_owner_filter_uses_sender_id_and_private_chat(
    sender_id: int,
    chat_id: int,
    chat_type: ChatType,
    expected: bool,
) -> None:
    message = SimpleNamespace(
        from_user=SimpleNamespace(
            id=sender_id,
            username="owner",
            first_name="Same",
            last_name="Profile",
        ),
        chat=SimpleNamespace(id=chat_id, type=chat_type),
    )
    owner_filter = PrivateOwnerFilter({ALLOWED_USER_ID})

    assert asyncio.run(owner_filter(message)) is expected


@pytest.mark.parametrize("sender_id", [None, "700000001", 700000001.0, True])
def test_private_owner_filter_rejects_missing_or_unusable_sender_id(
    sender_id: object,
) -> None:
    sender = None if sender_id is None else SimpleNamespace(id=sender_id)
    message = SimpleNamespace(
        from_user=sender,
        chat=SimpleNamespace(id=PRIVATE_CHAT_ID, type=ChatType.PRIVATE),
    )

    assert asyncio.run(PrivateOwnerFilter({ALLOWED_USER_ID})(message)) is False


@pytest.mark.parametrize("chat_type", [None, "unknown"])
def test_private_owner_filter_rejects_missing_or_unknown_chat_type(
    chat_type: object,
) -> None:
    message = SimpleNamespace(
        from_user=SimpleNamespace(id=ALLOWED_USER_ID),
        chat=SimpleNamespace(id=PRIVATE_CHAT_ID, type=chat_type),
    )

    assert asyncio.run(PrivateOwnerFilter({ALLOWED_USER_ID})(message)) is False


def test_profile_fields_neither_grant_nor_revoke_authorization() -> None:
    owner_filter = PrivateOwnerFilter({ALLOWED_USER_ID})
    changed_owner = SimpleNamespace(
        from_user=SimpleNamespace(
            id=ALLOWED_USER_ID,
            username="changed",
            first_name="Changed",
            last_name="Owner",
        ),
        chat=SimpleNamespace(type=ChatType.PRIVATE),
    )
    copied_profile = SimpleNamespace(
        from_user=SimpleNamespace(
            id=UNKNOWN_USER_ID,
            username="changed",
            first_name="Changed",
            last_name="Owner",
        ),
        chat=SimpleNamespace(type=ChatType.PRIVATE),
    )

    assert asyncio.run(owner_filter(changed_owner)) is True
    assert asyncio.run(owner_filter(copied_profile)) is False


def test_actual_dispatcher_protects_start_and_text_handlers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def run() -> None:
        persisted = []

        async def record_persistence(telegram_input):
            persisted.append(telegram_input)

        monkeypatch.setattr(
            "app.bot.handlers.persist_text_message",
            record_persistence,
        )
        dispatcher = build_dispatcher(frozenset({ALLOWED_USER_ID}))
        bot = RecordingBot()
        updates = [
            make_update(
                update_id=1,
                message_id=1,
                text="/start",
                user_id=ALLOWED_USER_ID,
                chat_id=PRIVATE_CHAT_ID,
            ),
            make_update(
                update_id=2,
                message_id=2,
                text="/start",
                user_id=UNKNOWN_USER_ID,
                chat_id=PRIVATE_CHAT_ID,
            ),
            make_update(
                update_id=3,
                message_id=3,
                text="/start",
                user_id=ALLOWED_USER_ID,
                chat_id=GROUP_CHAT_ID,
                chat_type=ChatType.GROUP,
            ),
            make_update(
                update_id=4,
                message_id=4,
                text="/start",
                user_id=None,
                chat_id=PRIVATE_CHAT_ID,
            ),
            make_update(
                update_id=5,
                message_id=5,
                text="allowed note",
                user_id=ALLOWED_USER_ID,
                chat_id=PRIVATE_CHAT_ID,
            ),
            make_update(
                update_id=6,
                message_id=6,
                text="unknown note",
                user_id=UNKNOWN_USER_ID,
                chat_id=PRIVATE_CHAT_ID,
            ),
            make_update(
                update_id=7,
                message_id=7,
                text="owner in group",
                user_id=ALLOWED_USER_ID,
                chat_id=GROUP_CHAT_ID,
                chat_type=ChatType.GROUP,
            ),
            make_update(
                update_id=8,
                message_id=8,
                text="unknown in same group",
                user_id=UNKNOWN_USER_ID,
                chat_id=GROUP_CHAT_ID,
                chat_type=ChatType.GROUP,
            ),
            make_update(
                update_id=9,
                message_id=9,
                text="missing sender",
                user_id=None,
                chat_id=PRIVATE_CHAT_ID,
            ),
        ]
        for update in updates:
            await dispatcher.feed_update(bot, update)

        sent_texts = [
            request.text for request in bot.requests if isinstance(request, SendMessage)
        ]
        assert sent_texts == [START_TEXT, ACK_TEXT]
        assert len(persisted) == 1
        assert persisted[0].telegram_user_id == ALLOWED_USER_ID
        assert persisted[0].text == "allowed note"
        await bot.session.close()

    asyncio.run(run())


def test_rejected_text_updates_create_no_state_response_or_artifact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def run() -> None:
        actor_deliveries: list[str] = []
        monkeypatch.setattr(
            "app.worker.tasks.process_processing_task.send",
            actor_deliveries.append,
        )
        dispatcher = build_dispatcher(frozenset({ALLOWED_USER_ID}))
        bot = RecordingBot()
        rejected = [
            make_update(
                update_id=20,
                message_id=20,
                text="same rejected text",
                user_id=UNKNOWN_USER_ID,
                chat_id=PRIVATE_CHAT_ID,
                username="owner_profile",
                first_name="Owner",
                last_name="Name",
            ),
            make_update(
                update_id=21,
                message_id=21,
                text="same rejected text",
                user_id=ALLOWED_USER_ID,
                chat_id=GROUP_CHAT_ID,
                chat_type=ChatType.GROUP,
            ),
            make_update(
                update_id=22,
                message_id=22,
                text="same rejected text",
                user_id=UNKNOWN_USER_ID,
                chat_id=GROUP_CHAT_ID,
                chat_type=ChatType.GROUP,
            ),
            make_update(
                update_id=23,
                message_id=23,
                text="same rejected text",
                user_id=None,
                chat_id=PRIVATE_CHAT_ID,
            ),
        ]
        for update in rejected:
            await dispatcher.feed_update(bot, update)

        session_factory = get_session_factory()
        async with session_factory() as session:
            counts = [
                await session.scalar(select(func.count()).select_from(model))
                for model in (User, Message, ProcessingTask, Artifact)
            ]

        assert counts == [0, 0, 0, 0]
        assert bot.requests == []
        assert actor_deliveries == []
        assert list(tmp_path.rglob("*")) == []
        await bot.session.close()

    asyncio.run(run())


def test_allowed_profile_updates_duplicates_and_unknown_profile_copy() -> None:
    async def run() -> None:
        dispatcher = build_dispatcher(frozenset({ALLOWED_USER_ID}))
        bot = RecordingBot()
        original = make_update(
            update_id=30,
            message_id=30,
            text="identical note text",
            user_id=ALLOWED_USER_ID,
            chat_id=PRIVATE_CHAT_ID,
            username="original_owner",
            first_name="Original",
            last_name="Owner",
        )
        changed = make_update(
            update_id=31,
            message_id=31,
            text="identical note text",
            user_id=ALLOWED_USER_ID,
            chat_id=PRIVATE_CHAT_ID,
            username="changed_owner",
            first_name="Changed",
            last_name="Profile",
        )
        copied = make_update(
            update_id=32,
            message_id=32,
            text="identical note text",
            user_id=UNKNOWN_USER_ID,
            chat_id=PRIVATE_CHAT_ID,
            username="changed_owner",
            first_name="Changed",
            last_name="Profile",
        )

        await dispatcher.feed_update(bot, original)
        await dispatcher.feed_update(bot, original)
        await dispatcher.feed_update(bot, changed)
        await dispatcher.feed_update(bot, copied)

        session_factory = get_session_factory()
        async with session_factory() as session:
            users = list(await session.scalars(select(User)))
            message_count = await session.scalar(
                select(func.count()).select_from(Message)
            )
            task_count = await session.scalar(
                select(func.count()).select_from(ProcessingTask)
            )

        assert len(users) == 1
        assert users[0].telegram_user_id == ALLOWED_USER_ID
        assert users[0].username == "changed_owner"
        assert users[0].first_name == "Changed"
        assert users[0].last_name == "Profile"
        assert message_count == 2
        assert task_count == 2
        assert [request.text for request in bot.requests] == [
            ACK_TEXT,
            ACK_TEXT,
            ACK_TEXT,
        ]
        await bot.session.close()

    asyncio.run(run())


def test_authorized_update_reaches_exact_end_to_end_artifact(tmp_path: Path) -> None:
    async def run() -> None:
        dispatcher = build_dispatcher(frozenset({ALLOWED_USER_ID}))
        bot = RecordingBot()
        update = make_update(
            update_id=40,
            message_id=40,
            text="Authorized title\nAuthorized body",
            user_id=ALLOWED_USER_ID,
            chat_id=PRIVATE_CHAT_ID,
        )
        await dispatcher.feed_update(bot, update)

        candidates = await find_dispatch_candidates()
        assert len(candidates) == 1
        published = str(candidates[0].id)
        assert await mark_task_queued(candidates[0]) is True
        await run_processing_task(candidates[0].id, knowledge_base_root=tmp_path)

        session_factory = get_session_factory()
        async with session_factory() as session:
            task = await session.get(ProcessingTask, candidates[0].id)
            assert task is not None
            message = await session.get(Message, task.message_id)
            artifact = await session.scalar(
                select(Artifact).where(
                    Artifact.message_id == task.message_id
                )
            )

        assert task.status == "succeeded"
        assert task.attempts == 1
        assert message is not None and message.status == "done"
        assert message.raw_text is not None
        assert artifact is not None
        expected = render_text_note(
            message_id=message.id,
            telegram_chat_id=message.telegram_chat_id,
            telegram_message_id=message.telegram_message_id,
            created_at=message.created_at,
            raw_text=message.raw_text,
        )
        assert published == str(task.id)
        assert artifact.file_path == expected.file_path
        assert (tmp_path / artifact.file_path).read_bytes() == expected.content
        assert [request.text for request in bot.requests] == [ACK_TEXT]
        await bot.session.close()

    asyncio.run(run())


def test_runtime_receives_immutable_allowlist_and_defends_direct_construction() -> None:
    settings = Settings(
        _env_file=None,
        telegram_bot_enabled=True,
        telegram_bot_token=BOT_TOKEN,
        telegram_allowed_user_ids=frozenset({ALLOWED_USER_ID}),
    )
    runtime = TelegramPollingRuntime.from_settings(settings)

    assert runtime.allowed_user_ids == frozenset({ALLOWED_USER_ID})
    assert isinstance(runtime.allowed_user_ids, frozenset)

    async def reject_empty_allowlist() -> None:
        invalid_runtime = TelegramPollingRuntime(enabled=True, token=BOT_TOKEN)
        with pytest.raises(RuntimeError, match="TELEGRAM_ALLOWED_USER_IDS"):
            await invalid_runtime.start()

    asyncio.run(reject_empty_allowlist())
