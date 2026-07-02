import asyncio
import os
import subprocess
import sys
import uuid
from pathlib import Path

from app.db.models import Message
from app.db.models import User
from app.db.session import get_session_factory


REPOSITORY_ROOT = Path(__file__).parents[1]


async def create_cli_message() -> uuid.UUID:
    session_factory = get_session_factory()
    unique = uuid.uuid4().int % 9_000_000_000_000_000_000
    async with session_factory() as session:
        user = User(telegram_user_id=unique)
        session.add(user)
        await session.flush()
        message = Message(
            user_id=user.id,
            telegram_chat_id=-123456,
            telegram_message_id=987,
            input_type="text",
            raw_text="CLI note",
            status="received",
            idempotency_key=f"telegram:cli:{unique}",
        )
        session.add(message)
        await session.commit()
        return message.id


def invoke(*arguments: str, environment: dict[str, str] | None = None):
    return subprocess.run(
        [sys.executable, "-m", "app.knowledge.cli", *arguments],
        cwd=REPOSITORY_ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def test_message_id_is_required_and_must_be_uuid() -> None:
    missing = invoke()
    malformed = invoke("--message-id", "not-a-uuid")

    assert missing.returncode != 0
    assert "--message-id" in missing.stderr
    assert missing.stdout == ""
    assert malformed.returncode != 0
    assert "valid UUID" in malformed.stderr
    assert malformed.stdout == ""


def test_cli_processes_one_message_with_configured_root_and_is_idempotent(
    tmp_path: Path,
) -> None:
    message_id = asyncio.run(create_cli_message())
    environment = os.environ.copy()
    environment["KNOWLEDGE_BASE_PATH"] = str(tmp_path)

    first = invoke("--message-id", str(message_id), environment=environment)
    second = invoke("--message-id", str(message_id), environment=environment)

    assert first.returncode == 0, first.stderr
    assert second.returncode == 0, second.stderr
    assert first.stderr == second.stderr == ""
    assert first.stdout == second.stdout
    lines = first.stdout.splitlines()
    assert len(lines) == 2
    assert lines[0].startswith("artifact_id: ")
    assert uuid.UUID(lines[0].removeprefix("artifact_id: "))
    expected_path = f"inbox/{lines[1].split('/', 1)[1]}"
    assert lines[1] == f"file_path: {expected_path}"
    assert (tmp_path / expected_path).is_file()


def test_cli_expected_processing_error_is_concise(tmp_path: Path) -> None:
    environment = os.environ.copy()
    environment["KNOWLEDGE_BASE_PATH"] = str(tmp_path)

    result = invoke("--message-id", str(uuid.uuid4()), environment=environment)

    assert result.returncode == 1
    assert result.stdout == ""
    assert "was not found" in result.stderr
    assert "Traceback" not in result.stderr
