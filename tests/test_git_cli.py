import asyncio
import os
import subprocess
import sys
import uuid
from pathlib import Path

from app.db.models import Message
from app.db.models import User
from app.db.session import get_session_factory
from app.knowledge.processing import process_text_message


REPOSITORY_ROOT = Path(__file__).parents[1]


def git(root: Path, *arguments: str) -> None:
    completed = subprocess.run(
        ["git", "-C", str(root), *arguments],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert completed.returncode == 0, completed.stderr


def initialize_repository(root: Path) -> None:
    git(root, "init")
    git(root, "config", "--local", "user.name", "PKM Test")
    git(
        root,
        "config",
        "--local",
        "user.email",
        "pkm-test@example.invalid",
    )


async def create_artifact(root: Path) -> uuid.UUID:
    session_factory = get_session_factory()
    unique = uuid.uuid4().int % 9_000_000_000_000_000_000
    async with session_factory() as session:
        user = User(telegram_user_id=unique)
        session.add(user)
        await session.flush()
        message = Message(
            user_id=user.id,
            telegram_chat_id=-123456,
            telegram_message_id=988,
            input_type="text",
            raw_text="Git CLI note",
            status="received",
            idempotency_key=f"telegram:git-cli:{unique}",
        )
        session.add(message)
        await session.commit()

    async with session_factory() as session:
        artifact = await process_text_message(session, message.id, root)
        return artifact.id


def invoke(*arguments: str, environment: dict[str, str] | None = None):
    return subprocess.run(
        [sys.executable, "-m", "app.knowledge.git_cli", *arguments],
        cwd=REPOSITORY_ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def test_artifact_id_is_required_and_must_be_uuid() -> None:
    missing = invoke()
    malformed = invoke("--artifact-id", "not-a-uuid")

    assert missing.returncode == 2
    assert "--artifact-id" in missing.stderr
    assert missing.stdout == ""
    assert malformed.returncode == 2
    assert "valid UUID" in malformed.stderr
    assert malformed.stdout == ""


def test_cli_prints_created_and_existing_results(tmp_path: Path) -> None:
    initialize_repository(tmp_path)
    artifact_id = asyncio.run(create_artifact(tmp_path))
    environment = os.environ.copy()
    environment["KNOWLEDGE_BASE_PATH"] = str(tmp_path)

    created = invoke("--artifact-id", str(artifact_id), environment=environment)
    existing = invoke("--artifact-id", str(artifact_id), environment=environment)

    assert created.returncode == existing.returncode == 0
    assert created.stderr == existing.stderr == ""
    created_lines = created.stdout.splitlines()
    existing_lines = existing.stdout.splitlines()
    assert created_lines[0] == existing_lines[0] == f"artifact_id: {artifact_id}"
    assert created_lines[1] == existing_lines[1]
    assert created_lines[1].startswith("file_path: inbox/")
    assert created_lines[2] == existing_lines[2]
    commit_sha = created_lines[2].removeprefix("git_commit_sha: ")
    assert len(commit_sha) in {40, 64}
    assert created_lines[3] == "outcome: created"
    assert existing_lines[3] == "outcome: existing"


def test_cli_expected_publication_error_is_concise(tmp_path: Path) -> None:
    initialize_repository(tmp_path)
    environment = os.environ.copy()
    environment["KNOWLEDGE_BASE_PATH"] = str(tmp_path)

    result = invoke(
        "--artifact-id",
        str(uuid.uuid4()),
        environment=environment,
    )

    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr.startswith("artifact Git publication failed: artifact ")
    assert "was not found" in result.stderr
    assert "Traceback" not in result.stderr
