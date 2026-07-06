import asyncio
import fcntl
import os
import subprocess
import uuid
from pathlib import Path

import pytest
from sqlalchemy import select

import app.knowledge.git_publication as git_publication
from app.db.models import Artifact
from app.db.models import Message
from app.db.models import User
from app.db.session import get_session_factory
from app.knowledge.errors import GitPublicationError
from app.knowledge.errors import GitPublicationTransactionError
from app.knowledge.errors import KnowledgeBaseError
from app.knowledge.errors import UnsupportedFileEntryError
from app.knowledge.git_publication import LOCK_NAME
from app.knowledge.git_publication import _GitRepository
from app.knowledge.git_publication import publish_artifact_to_git
from app.knowledge.processing import process_text_message


def git(root: Path, *arguments: str, input_text: str | None = None):
    return subprocess.run(
        ["git", "-C", str(root), *arguments],
        input=input_text,
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )


def initialize_repository(root: Path, *, author: bool = True) -> None:
    root.mkdir(parents=True, exist_ok=True)
    result = git(root, "init")
    assert result.returncode == 0, result.stderr
    if author:
        assert git(root, "config", "--local", "user.name", "PKM Test").returncode == 0
        assert (
            git(
                root,
                "config",
                "--local",
                "user.email",
                "pkm-test@example.invalid",
            ).returncode
            == 0
        )


async def establish_artifact(root: Path, text: str = "Publish me") -> uuid.UUID:
    unique = uuid.uuid4().int % 9_000_000_000_000_000_000
    session_factory = get_session_factory()
    async with session_factory() as session:
        user = User(telegram_user_id=unique)
        session.add(user)
        await session.flush()
        message = Message(
            user_id=user.id,
            telegram_chat_id=-unique,
            telegram_message_id=77,
            input_type="text",
            raw_text=text,
            status="received",
            idempotency_key=f"telegram:{-unique}:77",
        )
        session.add(message)
        await session.commit()

    async with session_factory() as session:
        artifact = await process_text_message(session, message.id, root)
        return artifact.id


async def publish(root: Path, artifact_id: uuid.UUID):
    session_factory = get_session_factory()
    async with session_factory() as session:
        return await publish_artifact_to_git(session, artifact_id, root)


async def load_artifact(artifact_id: uuid.UUID) -> Artifact:
    session_factory = get_session_factory()
    async with session_factory() as session:
        artifact = await session.get(Artifact, artifact_id)
        assert artifact is not None
        return artifact


def test_unborn_repository_creates_exact_selected_path_commit(tmp_path: Path) -> None:
    async def run() -> None:
        initialize_repository(tmp_path)
        artifact_id = await establish_artifact(tmp_path)
        artifact = await load_artifact(artifact_id)
        unrelated = tmp_path / "unrelated.txt"
        unrelated.write_text("leave me\n")

        result = await publish(tmp_path, artifact_id)

        assert result.outcome == "created"
        assert result.git_commit_sha == git(tmp_path, "rev-parse", "HEAD").stdout.strip()
        assert (await load_artifact(artifact_id)).git_commit_sha == result.git_commit_sha
        changed = git(
            tmp_path,
            "diff-tree",
            "--root",
            "--no-commit-id",
            "--name-only",
            "-r",
            "HEAD",
        ).stdout.splitlines()
        assert changed == [artifact.file_path]
        assert git(tmp_path, "show", f"HEAD:{artifact.file_path}").stdout.encode() == (
            tmp_path / artifact.file_path
        ).read_bytes()
        message = git(tmp_path, "show", "--no-patch", "--format=%B", "HEAD").stdout
        assert message.splitlines().count(f"PKM-Artifact-ID: {artifact_id}") == 1
        assert message.splitlines().count(
            f"PKM-Artifact-Path: {artifact.file_path}"
        ) == 1
        assert unrelated.read_text() == "leave me\n"
        assert git(tmp_path, "status", "--porcelain=v1").stdout.splitlines() == [
            "?? unrelated.txt"
        ]

    asyncio.run(run())


def test_valid_stored_sha_is_idempotent(tmp_path: Path) -> None:
    async def run() -> None:
        initialize_repository(tmp_path)
        artifact_id = await establish_artifact(tmp_path)
        first = await publish(tmp_path, artifact_id)
        second = await publish(tmp_path, artifact_id)

        assert second.outcome == "existing"
        assert second.git_commit_sha == first.git_commit_sha
        assert git(tmp_path, "rev-list", "--count", "HEAD").stdout.strip() == "1"

    asyncio.run(run())


def test_exact_path_already_in_head_creates_identity_commit(tmp_path: Path) -> None:
    async def run() -> None:
        initialize_repository(tmp_path)
        artifact_id = await establish_artifact(tmp_path)
        artifact = await load_artifact(artifact_id)
        assert git(tmp_path, "add", "--", artifact.file_path).returncode == 0
        assert git(tmp_path, "commit", "-m", "Baseline note").returncode == 0

        result = await publish(tmp_path, artifact_id)

        assert result.outcome == "created"
        assert git(tmp_path, "rev-list", "--count", "HEAD").stdout.strip() == "2"
        assert git(tmp_path, "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD").stdout == ""

    asyncio.run(run())


def test_application_repository_is_rejected_without_state_changes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def run() -> None:
        application_root = tmp_path / "application"
        initialize_repository(application_root)
        artifact_id = await establish_artifact(application_root)
        monkeypatch.setattr(
            git_publication,
            "APPLICATION_ROOT",
            application_root.resolve(),
        )
        before_head = git(application_root, "rev-parse", "--verify", "HEAD")
        before_index = git(application_root, "ls-files", "--stage").stdout
        before_status = git(
            application_root,
            "status",
            "--porcelain=v1",
            "--untracked-files=all",
        ).stdout

        with pytest.raises(GitPublicationError, match="application repository"):
            await publish(application_root, artifact_id)

        after_head = git(application_root, "rev-parse", "--verify", "HEAD")
        assert (after_head.returncode, after_head.stdout, after_head.stderr) == (
            before_head.returncode,
            before_head.stdout,
            before_head.stderr,
        )
        assert git(application_root, "ls-files", "--stage").stdout == before_index
        assert (
            git(
                application_root,
                "status",
                "--porcelain=v1",
                "--untracked-files=all",
            ).stdout
            == before_status
        )
        assert (await load_artifact(artifact_id)).git_commit_sha is None

    asyncio.run(run())


def test_distinct_nested_knowledge_base_repository_succeeds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def run() -> None:
        application_root = tmp_path / "application"
        knowledge_base_root = application_root / "knowledge-base"
        initialize_repository(application_root)
        initialize_repository(knowledge_base_root)
        monkeypatch.setattr(
            git_publication,
            "APPLICATION_ROOT",
            application_root.resolve(),
        )
        artifact_id = await establish_artifact(knowledge_base_root)

        result = await publish(knowledge_base_root, artifact_id)

        assert result.outcome == "created"
        assert (await load_artifact(artifact_id)).git_commit_sha == result.git_commit_sha
        assert git(knowledge_base_root, "rev-parse", "HEAD").stdout.strip() == (
            result.git_commit_sha
        )

    asyncio.run(run())


@pytest.mark.parametrize("case", ("missing", "parent", "bare", "detached"))
def test_invalid_repository_boundaries_fail_before_database_change(
    tmp_path: Path, case: str
) -> None:
    async def run() -> None:
        root = tmp_path / "knowledge"
        if case == "missing":
            root.mkdir()
        elif case == "parent":
            initialize_repository(tmp_path)
            root.mkdir()
        elif case == "bare":
            root.mkdir()
            assert git(root, "init", "--bare").returncode == 0
        else:
            initialize_repository(root)
            assert git(root, "commit", "--allow-empty", "-m", "initial").returncode == 0
            assert git(root, "checkout", "--detach").returncode == 0

        artifact_id = await establish_artifact(root)
        with pytest.raises(GitPublicationError):
            await publish(root, artifact_id)
        assert (await load_artifact(artifact_id)).git_commit_sha is None

    asyncio.run(run())


@pytest.mark.parametrize("missing_key", ("user.name", "user.email"))
def test_repository_local_author_identity_is_required(
    tmp_path: Path, missing_key: str
) -> None:
    async def run() -> None:
        initialize_repository(tmp_path)
        assert git(tmp_path, "config", "--local", "--unset", missing_key).returncode == 0
        artifact_id = await establish_artifact(tmp_path)

        with pytest.raises(GitPublicationError, match=missing_key):
            await publish(tmp_path, artifact_id)

    asyncio.run(run())


def test_history_operation_is_rejected(tmp_path: Path) -> None:
    async def run() -> None:
        initialize_repository(tmp_path)
        artifact_id = await establish_artifact(tmp_path)
        git_path = Path(git(tmp_path, "rev-parse", "--git-path", "MERGE_HEAD").stdout.strip())
        if not git_path.is_absolute():
            git_path = tmp_path / git_path
        git_path.write_text("0" * 40)

        with pytest.raises(GitPublicationError, match="history operation"):
            await publish(tmp_path, artifact_id)

    asyncio.run(run())


def test_dirty_index_fails_without_modifying_staged_or_working_state(
    tmp_path: Path,
) -> None:
    async def run() -> None:
        initialize_repository(tmp_path)
        artifact_id = await establish_artifact(tmp_path)
        staged = tmp_path / "staged.txt"
        staged.write_text("staged\n")
        assert git(tmp_path, "add", "--", "staged.txt").returncode == 0

        with pytest.raises(GitPublicationError, match="index must be empty"):
            await publish(tmp_path, artifact_id)

        assert git(tmp_path, "diff", "--cached", "--name-only").stdout.strip() == "staged.txt"
        assert staged.read_text() == "staged\n"
        assert (await load_artifact(artifact_id)).git_commit_sha is None

    asyncio.run(run())


@pytest.mark.parametrize("target", ("unrelated", "selected"))
def test_intent_to_add_index_state_is_rejected_and_preserved(
    tmp_path: Path, target: str
) -> None:
    async def run() -> None:
        initialize_repository(tmp_path)
        artifact_id = await establish_artifact(tmp_path)
        artifact = await load_artifact(artifact_id)
        intent_path = artifact.file_path if target == "selected" else "intent.txt"
        if target == "unrelated":
            (tmp_path / intent_path).write_text("leave intent state unchanged\n")
        assert git(tmp_path, "add", "--intent-to-add", "--", intent_path).returncode == 0
        before_status = git(
            tmp_path,
            "status",
            "--porcelain=v1",
            "--untracked-files=all",
        ).stdout
        before_index = git(tmp_path, "ls-files", "--debug", "--", intent_path).stdout

        with pytest.raises(GitPublicationError, match="index must be empty"):
            await publish(tmp_path, artifact_id)

        assert (
            git(
                tmp_path,
                "status",
                "--porcelain=v1",
                "--untracked-files=all",
            ).stdout
            == before_status
        )
        assert git(tmp_path, "ls-files", "--debug", "--", intent_path).stdout == (
            before_index
        )
        assert git(tmp_path, "rev-parse", "--verify", "HEAD").returncode != 0
        assert (await load_artifact(artifact_id)).git_commit_sha is None

    asyncio.run(run())


def test_deleted_intent_to_add_path_is_rejected_and_preserved(tmp_path: Path) -> None:
    async def run() -> None:
        initialize_repository(tmp_path)
        artifact_id = await establish_artifact(tmp_path)
        intent_path = "deleted-intent.txt"
        destination = tmp_path / intent_path
        destination.write_text("leave intent state unchanged\n")
        assert git(tmp_path, "add", "--intent-to-add", "--", intent_path).returncode == 0
        destination.unlink()
        before_status = git(
            tmp_path,
            "status",
            "--porcelain=v1",
            "--untracked-files=all",
        ).stdout
        before_index = git(tmp_path, "ls-files", "--debug", "--", intent_path).stdout

        with pytest.raises(GitPublicationError, match="index must be empty"):
            await publish(tmp_path, artifact_id)

        assert (
            git(
                tmp_path,
                "status",
                "--porcelain=v1",
                "--untracked-files=all",
            ).stdout
            == before_status
        )
        assert git(tmp_path, "ls-files", "--debug", "--", intent_path).stdout == (
            before_index
        )
        assert not destination.exists()
        assert git(tmp_path, "rev-parse", "--verify", "HEAD").returncode != 0
        assert (await load_artifact(artifact_id)).git_commit_sha is None

    asyncio.run(run())


def test_ignored_selected_path_fails_without_forced_staging(tmp_path: Path) -> None:
    async def run() -> None:
        initialize_repository(tmp_path)
        artifact_id = await establish_artifact(tmp_path)
        artifact = await load_artifact(artifact_id)
        (tmp_path / ".gitignore").write_text(f"/{artifact.file_path}\n")

        with pytest.raises(GitPublicationError, match="ignored"):
            await publish(tmp_path, artifact_id)

        assert git(tmp_path, "diff", "--cached", "--name-only").stdout == ""

    asyncio.run(run())


def test_commit_hooks_are_disabled(tmp_path: Path) -> None:
    async def run() -> None:
        initialize_repository(tmp_path)
        artifact_id = await establish_artifact(tmp_path)
        hook = tmp_path / ".git" / "hooks" / "pre-commit"
        sentinel = tmp_path / "hook-ran"
        hook.parent.mkdir(exist_ok=True)
        hook.write_text(f"#!/bin/sh\ntouch '{sentinel}'\nexit 1\n")
        hook.chmod(0o755)

        result = await publish(tmp_path, artifact_id)

        assert result.outcome == "created"
        assert not sentinel.exists()

    asyncio.run(run())


def test_database_failure_retains_commit_then_reconciles(tmp_path: Path) -> None:
    async def run() -> None:
        initialize_repository(tmp_path)
        artifact_id = await establish_artifact(tmp_path)
        session_factory = get_session_factory()

        async with session_factory() as session:
            async def fail_commit() -> None:
                raise RuntimeError("simulated database commit failure")

            session.commit = fail_commit  # type: ignore[method-assign]
            with pytest.raises(RuntimeError, match="database commit failure"):
                await publish_artifact_to_git(session, artifact_id, tmp_path)

        retained = git(tmp_path, "rev-parse", "HEAD").stdout.strip()
        assert retained
        assert (await load_artifact(artifact_id)).git_commit_sha is None

        recovered = await publish(tmp_path, artifact_id)
        assert recovered.outcome == "reconciled"
        assert recovered.git_commit_sha == retained
        assert git(tmp_path, "rev-list", "--count", "HEAD").stdout.strip() == "1"

    asyncio.run(run())


def test_commit_failure_restores_untracked_selected_index(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def run() -> None:
        initialize_repository(tmp_path)
        artifact_id = await establish_artifact(tmp_path)

        def fail_commit(*_args, **_kwargs):
            raise GitPublicationError("simulated commit failure")

        monkeypatch.setattr(_GitRepository, "create_commit", fail_commit)
        with pytest.raises(GitPublicationError, match="simulated"):
            await publish(tmp_path, artifact_id)

        assert git(tmp_path, "diff", "--cached", "--name-only").stdout == ""
        artifact = await load_artifact(artifact_id)
        assert (tmp_path / artifact.file_path).is_file()
        assert artifact.git_commit_sha is None

    asyncio.run(run())


def test_filter_changed_staged_bytes_fail_and_are_cleaned(tmp_path: Path) -> None:
    async def run() -> None:
        initialize_repository(tmp_path)
        (tmp_path / ".gitattributes").write_text("*.md filter=mutate\n")
        assert (
            git(
                tmp_path,
                "config",
                "--local",
                "filter.mutate.clean",
                "sed s/Publish/Changed/g",
            ).returncode
            == 0
        )
        artifact_id = await establish_artifact(tmp_path)

        with pytest.raises(GitPublicationError, match="filters changed"):
            await publish(tmp_path, artifact_id)

        assert git(tmp_path, "diff", "--cached", "--name-only").stdout == ""

    asyncio.run(run())


def test_repository_lock_busy_fails_without_git_or_database_change(
    tmp_path: Path,
) -> None:
    async def run() -> None:
        initialize_repository(tmp_path)
        artifact_id = await establish_artifact(tmp_path)
        other_artifact_id = await establish_artifact(tmp_path, "Publish another")
        lock_path = Path(
            git(tmp_path, "rev-parse", "--git-path", LOCK_NAME).stdout.strip()
        )
        if not lock_path.is_absolute():
            lock_path = tmp_path / lock_path
        descriptor = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            with pytest.raises(GitPublicationError, match="already in progress"):
                await publish(tmp_path, artifact_id)
            with pytest.raises(GitPublicationError, match="already in progress"):
                await publish(tmp_path, other_artifact_id)
        finally:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
            os.close(descriptor)

        assert git(tmp_path, "rev-parse", "--verify", "HEAD").returncode != 0
        assert (await load_artifact(artifact_id)).git_commit_sha is None
        assert (await load_artifact(other_artifact_id)).git_commit_sha is None

    asyncio.run(run())


def test_missing_file_is_not_recreated_or_state_changed(tmp_path: Path) -> None:
    async def run() -> None:
        initialize_repository(tmp_path)
        artifact_id = await establish_artifact(tmp_path)
        artifact = await load_artifact(artifact_id)
        path = tmp_path / artifact.file_path
        path.unlink()
        path.parent.rmdir()

        with pytest.raises(KnowledgeBaseError, match="absent"):
            await publish(tmp_path, artifact_id)

        assert not path.exists()
        assert not path.parent.exists()
        assert (await load_artifact(artifact_id)).git_commit_sha is None

    asyncio.run(run())


def test_validation_rejects_symlink_and_preserves_message_status(tmp_path: Path) -> None:
    async def run() -> None:
        initialize_repository(tmp_path)
        artifact_id = await establish_artifact(tmp_path)
        artifact = await load_artifact(artifact_id)
        path = tmp_path / artifact.file_path
        path.unlink()
        target = tmp_path / "target.md"
        target.write_text("unrelated\n")
        path.symlink_to(target)

        session_factory = get_session_factory()
        async with session_factory() as session:
            stored = await session.get(Artifact, artifact_id)
            assert stored is not None
            message = await session.get(Message, stored.message_id)
            assert message is not None
            message.status = "received"
            await session.commit()

        with pytest.raises(
            UnsupportedFileEntryError, match="unsupported filesystem entry"
        ):
            await publish(tmp_path, artifact_id)

        assert path.is_symlink()
        assert target.read_text() == "unrelated\n"
        async with session_factory() as session:
            status = await session.scalar(
                select(Message.status).where(Message.id == artifact.message_id)
            )
        assert status == "received"

    asyncio.run(run())


def test_active_caller_transaction_is_rejected(tmp_path: Path) -> None:
    async def run() -> None:
        initialize_repository(tmp_path)
        artifact_id = await establish_artifact(tmp_path)
        session_factory = get_session_factory()
        async with session_factory() as session:
            async with session.begin():
                with pytest.raises(GitPublicationTransactionError):
                    await publish_artifact_to_git(session, artifact_id, tmp_path)

    asyncio.run(run())


def test_inconsistent_stored_sha_fails_closed(tmp_path: Path) -> None:
    async def run() -> None:
        initialize_repository(tmp_path)
        artifact_id = await establish_artifact(tmp_path)
        session_factory = get_session_factory()
        async with session_factory() as session:
            artifact = await session.get(Artifact, artifact_id)
            assert artifact is not None
            artifact.git_commit_sha = "abc"
            await session.commit()

        with pytest.raises(GitPublicationError, match="does not exist|canonical"):
            await publish(tmp_path, artifact_id)
        assert git(tmp_path, "rev-list", "--count", "--all").stdout.strip() == "0"

    asyncio.run(run())


def test_multiple_matching_publication_commits_fail_closed(tmp_path: Path) -> None:
    async def run() -> None:
        initialize_repository(tmp_path)
        artifact_id = await establish_artifact(tmp_path)
        first = await publish(tmp_path, artifact_id)
        artifact = await load_artifact(artifact_id)
        session_factory = get_session_factory()
        async with session_factory() as session:
            stored = await session.get(Artifact, artifact_id)
            assert stored is not None
            stored.git_commit_sha = None
            await session.commit()

        message = (
            f"Publish artifact {artifact_id}\n\n"
            f"PKM-Artifact-ID: {artifact_id}\n"
            f"PKM-Artifact-Path: {artifact.file_path}\n"
        )
        duplicate = git(tmp_path, "commit", "--allow-empty", "--file=-", input_text=message)
        assert duplicate.returncode == 0, duplicate.stderr

        with pytest.raises(GitPublicationError, match="multiple publication"):
            await publish(tmp_path, artifact_id)
        assert (await load_artifact(artifact_id)).git_commit_sha is None
        assert git(tmp_path, "rev-parse", "HEAD~1").stdout.strip() == first.git_commit_sha

    asyncio.run(run())


def test_candidate_with_mismatching_path_trailer_fails_closed(tmp_path: Path) -> None:
    async def run() -> None:
        initialize_repository(tmp_path)
        artifact_id = await establish_artifact(tmp_path)
        artifact = await load_artifact(artifact_id)
        assert git(tmp_path, "add", "--", artifact.file_path).returncode == 0
        message = (
            f"Publish artifact {artifact_id}\n\n"
            f"PKM-Artifact-ID: {artifact_id}\n"
            "PKM-Artifact-Path: inbox/wrong.md\n"
        )
        assert git(tmp_path, "commit", "--file=-", input_text=message).returncode == 0

        with pytest.raises(GitPublicationError, match="trailers"):
            await publish(tmp_path, artifact_id)
        assert (await load_artifact(artifact_id)).git_commit_sha is None

    asyncio.run(run())


@pytest.mark.parametrize("case", ("non_commit", "missing_path", "wrong_bytes", "wrong_trailers"))
def test_stored_commit_inconsistencies_fail_closed(tmp_path: Path, case: str) -> None:
    async def run() -> None:
        initialize_repository(tmp_path)
        artifact_id = await establish_artifact(tmp_path)
        artifact = await load_artifact(artifact_id)
        expected_bytes = (tmp_path / artifact.file_path).read_bytes()

        if case == "non_commit":
            object_id = git(
                tmp_path,
                "hash-object",
                "-w",
                "--stdin",
                input_text="not a commit",
            ).stdout.strip()
        else:
            if case == "wrong_bytes":
                (tmp_path / artifact.file_path).write_text("wrong bytes\n")
                assert git(tmp_path, "add", "--", artifact.file_path).returncode == 0
            elif case == "missing_path":
                pass
            else:
                assert git(tmp_path, "add", "--", artifact.file_path).returncode == 0
            message = (
                "Wrong publication\n\n"
                if case == "wrong_trailers"
                else (
                    f"Publish artifact {artifact_id}\n\n"
                    f"PKM-Artifact-ID: {artifact_id}\n"
                    f"PKM-Artifact-Path: {artifact.file_path}\n"
                )
            )
            assert (
                git(tmp_path, "commit", "--allow-empty", "--file=-", input_text=message).returncode
                == 0
            )
            object_id = git(tmp_path, "rev-parse", "HEAD").stdout.strip()
            if case == "wrong_bytes":
                (tmp_path / artifact.file_path).write_bytes(expected_bytes)

        session_factory = get_session_factory()
        async with session_factory() as session:
            stored = await session.get(Artifact, artifact_id)
            assert stored is not None
            stored.git_commit_sha = object_id
            await session.commit()

        with pytest.raises(GitPublicationError):
            await publish(tmp_path, artifact_id)

    asyncio.run(run())


def test_tracked_path_cleanup_preserves_expected_working_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def run() -> None:
        initialize_repository(tmp_path)
        artifact_id = await establish_artifact(tmp_path)
        artifact = await load_artifact(artifact_id)
        path = tmp_path / artifact.file_path
        expected_bytes = path.read_bytes()
        path.write_bytes(b"old committed bytes\n")
        assert git(tmp_path, "add", "--", artifact.file_path).returncode == 0
        assert git(tmp_path, "commit", "-m", "Old note").returncode == 0
        path.write_bytes(expected_bytes)

        def fail_commit(*_args, **_kwargs):
            raise GitPublicationError("simulated tracked commit failure")

        monkeypatch.setattr(_GitRepository, "create_commit", fail_commit)
        with pytest.raises(GitPublicationError, match="tracked commit failure"):
            await publish(tmp_path, artifact_id)

        assert git(tmp_path, "diff", "--cached", "--name-only").stdout == ""
        assert path.read_bytes() == expected_bytes

    asyncio.run(run())


def test_cleanup_failure_reports_primary_and_manual_recovery(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def run() -> None:
        initialize_repository(tmp_path)
        artifact_id = await establish_artifact(tmp_path)

        def fail_commit(*_args, **_kwargs):
            raise GitPublicationError("primary commit failure")

        def fail_cleanup(*_args, **_kwargs):
            raise GitPublicationError("cleanup failure")

        monkeypatch.setattr(_GitRepository, "create_commit", fail_commit)
        monkeypatch.setattr(_GitRepository, "restore_selected_index", fail_cleanup)
        with pytest.raises(
            GitPublicationError,
            match="primary commit failure.*cleanup failure.*manual index inspection",
        ):
            await publish(tmp_path, artifact_id)

    asyncio.run(run())
