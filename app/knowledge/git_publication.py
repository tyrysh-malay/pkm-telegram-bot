import fcntl
import os
import re
import subprocess
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.knowledge.errors import GitPublicationBusyError
from app.knowledge.errors import GitPublicationInvariantError
from app.knowledge.errors import GitPublicationOperationalError
from app.knowledge.errors import GitPublicationTransactionError
from app.knowledge.processing import validate_existing_artifact


GIT_TIMEOUT_SECONDS = 15
LOCK_NAME = "pkm-artifact-publication.lock"
ARTIFACT_ID_TRAILER = "PKM-Artifact-ID"
ARTIFACT_PATH_TRAILER = "PKM-Artifact-Path"
FULL_OBJECT_ID = re.compile(r"[0-9a-f]+\Z")
APPLICATION_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class GitPublicationResult:
    artifact_id: uuid.UUID
    file_path: str
    git_commit_sha: str
    outcome: Literal["created", "reconciled", "existing"]


@dataclass(frozen=True)
class _GitResult:
    stdout: bytes
    stderr: bytes
    returncode: int


class _GitRepository:
    def __init__(self, root: Path) -> None:
        try:
            self.root = root.resolve(strict=True)
        except OSError as exc:
            raise GitPublicationInvariantError(
                "knowledge-base root does not exist or is unreadable"
            ) from exc
        if not self.root.is_dir():
            raise GitPublicationInvariantError("knowledge-base root is not a directory")

    def run(
        self,
        *arguments: str,
        input_bytes: bytes | None = None,
        check: bool = True,
        extra_config: tuple[str, ...] = (),
    ) -> _GitResult:
        environment = {
            "GIT_TERMINAL_PROMPT": "0",
            "LC_ALL": "C",
            "PATH": os.defpath,
        }
        command = [
            "git",
            "-c",
            f"safe.directory={self.root}",
        ]
        for config in extra_config:
            command.extend(("-c", config))
        command.extend(("-C", str(self.root), *arguments))
        try:
            completed = subprocess.run(
                command,
                input=input_bytes,
                capture_output=True,
                check=False,
                env=environment,
                timeout=GIT_TIMEOUT_SECONDS,
            )
        except FileNotFoundError as exc:
            raise GitPublicationOperationalError(
                "Git executable is unavailable"
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise GitPublicationOperationalError("Git command timed out") from exc
        except OSError as exc:
            raise GitPublicationOperationalError(
                "Git command could not be executed"
            ) from exc

        result = _GitResult(
            stdout=completed.stdout,
            stderr=completed.stderr,
            returncode=completed.returncode,
        )
        if check and result.returncode != 0:
            detail = _sanitized_detail(result.stderr, self.root)
            suffix = f": {detail}" if detail else ""
            raise GitPublicationOperationalError(f"Git command failed{suffix}")
        return result

    def text(self, *arguments: str) -> str:
        return self.run(*arguments).stdout.decode("utf-8", errors="strict").strip()

    def validate(self) -> Path:
        self.run("--version")
        repository_state = self.run(
            "rev-parse",
            "--is-inside-work-tree",
            "--is-bare-repository",
            check=False,
        )
        if repository_state.returncode != 0:
            raise GitPublicationInvariantError(
                "knowledge-base root is not an initialized Git repository; initialize it manually"
            )
        state_lines = repository_state.stdout.decode("ascii").splitlines()
        if state_lines == ["false", "true"]:
            raise GitPublicationInvariantError("knowledge-base Git repository is bare")
        if state_lines != ["true", "false"]:
            raise GitPublicationInvariantError(
                "knowledge-base root is not an initialized Git working tree"
            )

        top_level_text = self.text("rev-parse", "--show-toplevel")
        try:
            top_level = Path(top_level_text).resolve(strict=True)
        except OSError as exc:
            raise GitPublicationInvariantError(
                "Git repository top-level is unreadable"
            ) from exc
        if top_level != self.root:
            raise GitPublicationInvariantError(
                "configured knowledge-base root must be the exact Git top-level"
            )
        if top_level == APPLICATION_ROOT:
            raise GitPublicationInvariantError(
                "knowledge-base Git repository must be distinct from the application repository"
            )

        branch = self.run(
            "symbolic-ref", "--quiet", "--short", "HEAD", check=False
        )
        if branch.returncode != 0 or not branch.stdout.strip():
            raise GitPublicationInvariantError("knowledge-base Git HEAD is detached")

        for marker in (
            "MERGE_HEAD",
            "CHERRY_PICK_HEAD",
            "REVERT_HEAD",
            "rebase-merge",
            "rebase-apply",
        ):
            marker_path = Path(self.text("rev-parse", "--git-path", marker))
            if not marker_path.is_absolute():
                marker_path = self.root / marker_path
            if marker_path.exists():
                raise GitPublicationInvariantError(
                    "knowledge-base Git repository has a history operation in progress"
                )

        for key in ("user.name", "user.email"):
            value = self.run("config", "--local", "--get", key, check=False)
            if value.returncode != 0 or not value.stdout.decode().strip():
                raise GitPublicationInvariantError(
                    f"knowledge-base repository-local {key} is not configured"
                )

        lock_path = Path(self.text("rev-parse", "--git-path", LOCK_NAME))
        if not lock_path.is_absolute():
            lock_path = self.root / lock_path
        return lock_path.resolve(strict=False)

    def require_clean_index(self) -> None:
        unmerged = self.run("ls-files", "--unmerged", "-z").stdout
        staged_or_intent_to_add = self.run(
            "diff",
            "--cached",
            "--name-only",
            "-z",
            "--ita-visible-in-index",
        ).stdout
        if unmerged or staged_or_intent_to_add:
            raise GitPublicationInvariantError(
                "knowledge-base Git index must be empty; resolve staged, unmerged, or intent-to-add state manually"
            )

    def head_exists(self) -> bool:
        return (
            self.run("rev-parse", "--verify", "HEAD^{commit}", check=False).returncode
            == 0
        )

    def commit_message(self, commit_sha: str) -> str:
        return self.run(
            "show", "--no-patch", "--format=%B", commit_sha
        ).stdout.decode("utf-8", errors="strict")

    def commit_blob(self, commit_sha: str, file_path: str) -> bytes:
        entry = self.run(
            "ls-tree", "-z", commit_sha, "--", file_path
        ).stdout.rstrip(b"\0")
        if not entry or b"\0" in entry:
            raise GitPublicationInvariantError(
                f"publication commit does not contain exact artifact path {file_path}"
            )
        try:
            metadata, returned_path = entry.split(b"\t", 1)
            mode, object_type, object_id = metadata.split(b" ", 2)
        except ValueError as exc:
            raise GitPublicationInvariantError(
                "publication commit tree is malformed"
            ) from exc
        if (
            returned_path.decode("utf-8", errors="strict") != file_path
            or object_type != b"blob"
            or mode not in {b"100644", b"100755"}
        ):
            raise GitPublicationInvariantError(
                f"publication commit does not contain exact artifact path {file_path}"
            )
        return self.run("cat-file", "blob", object_id.decode("ascii")).stdout

    def validate_commit(
        self,
        commit_sha: str,
        artifact_id: uuid.UUID,
        file_path: str,
        expected_bytes: bytes,
    ) -> str:
        if not FULL_OBJECT_ID.fullmatch(commit_sha):
            raise GitPublicationInvariantError(
                "stored Git commit SHA is not canonical hexadecimal"
            )
        resolved = self.run(
            "rev-parse", "--verify", f"{commit_sha}^{{commit}}", check=False
        )
        if resolved.returncode != 0:
            raise GitPublicationInvariantError(
                "stored Git commit does not exist as a local commit"
            )
        canonical = resolved.stdout.decode("ascii", errors="strict").strip()
        if canonical != commit_sha:
            raise GitPublicationInvariantError(
                "stored Git commit SHA is not a full canonical object ID"
            )

        message = self.commit_message(canonical)
        ids = _trailer_values(message, ARTIFACT_ID_TRAILER)
        paths = _trailer_values(message, ARTIFACT_PATH_TRAILER)
        if ids != [str(artifact_id)] or paths != [file_path]:
            raise GitPublicationInvariantError(
                "publication commit has invalid artifact trailers"
            )
        if self.commit_blob(canonical, file_path) != expected_bytes:
            raise GitPublicationInvariantError(
                "publication commit artifact bytes do not match"
            )
        return canonical

    def find_publication(
        self,
        artifact_id: uuid.UUID,
        file_path: str,
        expected_bytes: bytes,
    ) -> str | None:
        refs = self.run(
            "for-each-ref", "--format=%(refname)", "refs/heads", "refs/tags"
        ).stdout.decode("utf-8", errors="strict").splitlines()
        revisions = list(refs)
        if self.head_exists():
            revisions.append("HEAD")
        if not revisions:
            return None

        commits = self.run("rev-list", *revisions).stdout.decode("ascii").splitlines()
        matches: list[str] = []
        wanted = str(artifact_id)
        for commit_sha in dict.fromkeys(commits):
            message = self.commit_message(commit_sha)
            if wanted in _trailer_values(message, ARTIFACT_ID_TRAILER):
                matches.append(commit_sha)

        if not matches:
            return None
        if len(matches) != 1:
            raise GitPublicationInvariantError(
                "multiple publication commits match this Artifact ID"
            )
        return self.validate_commit(
            matches[0], artifact_id, file_path, expected_bytes
        )

    def selected_path_is_ignored(self, file_path: str) -> bool:
        result = self.run("check-ignore", "--quiet", "--", file_path, check=False)
        if result.returncode not in {0, 1}:
            raise GitPublicationOperationalError("Git could not inspect ignore rules")
        return result.returncode == 0

    def stage_and_verify(self, file_path: str, expected_bytes: bytes) -> bool:
        if self.selected_path_is_ignored(file_path):
            raise GitPublicationInvariantError(
                f"artifact path is ignored by Git: {file_path}"
            )
        self.run("add", "--", file_path)

        staged_paths = self.run(
            "diff", "--cached", "--name-only", "-z"
        ).stdout.rstrip(b"\0")
        paths = [] if not staged_paths else staged_paths.split(b"\0")
        encoded_path = file_path.encode("utf-8")
        if paths not in ([], [encoded_path]):
            raise GitPublicationInvariantError(
                "Git staged paths outside the selected Artifact"
            )

        if paths:
            entry = self.run(
                "ls-files", "--stage", "-z", "--", file_path
            ).stdout.rstrip(b"\0")
            try:
                metadata, returned_path = entry.split(b"\t", 1)
                _mode, object_id, stage = metadata.split(b" ", 2)
            except ValueError as exc:
                raise GitPublicationInvariantError(
                    "selected Artifact index entry is malformed"
                ) from exc
            if returned_path != encoded_path or stage != b"0":
                raise GitPublicationInvariantError(
                    "selected Artifact index entry is unmerged"
                )
            staged_bytes = self.run(
                "cat-file", "blob", object_id.decode("ascii")
            ).stdout
            if staged_bytes != expected_bytes:
                raise GitPublicationInvariantError(
                    "Git attributes or filters changed the staged Artifact bytes"
                )
            return True

        if (
            not self.head_exists()
            or self.commit_blob("HEAD", file_path) != expected_bytes
        ):
            raise GitPublicationInvariantError(
                "Git did not stage the exact Artifact bytes"
            )
        return False

    def create_commit(
        self,
        artifact_id: uuid.UUID,
        file_path: str,
        expected_bytes: bytes,
    ) -> str:
        message = (
            f"Publish artifact {artifact_id}\n\n"
            f"{ARTIFACT_ID_TRAILER}: {artifact_id}\n"
            f"{ARTIFACT_PATH_TRAILER}: {file_path}\n"
        ).encode("utf-8")
        with tempfile.TemporaryDirectory(prefix="pkm-empty-hooks-") as hooks_path:
            self.run(
                "commit",
                "--allow-empty",
                "--no-gpg-sign",
                "--file=-",
                input_bytes=message,
                extra_config=(
                    f"core.hooksPath={hooks_path}",
                    "commit.gpgSign=false",
                ),
            )
        commit_sha = self.text("rev-parse", "HEAD^{commit}")
        return self.validate_commit(
            commit_sha, artifact_id, file_path, expected_bytes
        )

    def restore_selected_index(self, file_path: str) -> None:
        if not self.run("ls-files", "--stage", "--", file_path).stdout:
            return
        if self.head_exists():
            self.run("restore", "--staged", "--source=HEAD", "--", file_path)
        else:
            self.run("rm", "--cached", "--", file_path)


def _sanitized_detail(stderr: bytes, root: Path) -> str:
    detail = stderr.decode("utf-8", errors="replace").replace(
        str(root),
        "<knowledge-base>",
    )
    return " ".join(detail.split())[:300]


def _trailer_values(message: str, key: str) -> list[str]:
    prefix = f"{key}:"
    return [
        line[len(prefix) :].strip()
        for line in message.splitlines()
        if line.startswith(prefix)
    ]


def _acquire_lock(lock_path: Path):
    try:
        descriptor = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
    except OSError as exc:
        raise GitPublicationOperationalError(
            "cannot open the Git publication lock"
        ) from exc
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as exc:
        os.close(descriptor)
        raise GitPublicationBusyError(
            "knowledge-base Git publication is already in progress"
        ) from exc
    except OSError:
        os.close(descriptor)
        raise
    return descriptor


async def publish_artifact_to_git(
    session: AsyncSession,
    artifact_id: uuid.UUID,
    knowledge_base_root: Path,
) -> GitPublicationResult:
    if session.in_transaction():
        raise GitPublicationTransactionError(
            "publish_artifact_to_git requires a session without an active transaction"
        )

    repository = _GitRepository(knowledge_base_root)
    lock_path = repository.validate()
    lock_descriptor = _acquire_lock(lock_path)
    staged_by_invocation = False
    commit_created = False
    try:
        repository.validate()
        repository.require_clean_index()
        artifact, expected_bytes = await validate_existing_artifact(
            session,
            artifact_id,
            repository.root,
            for_update=True,
        )

        if artifact.git_commit_sha is not None:
            commit_sha = repository.validate_commit(
                artifact.git_commit_sha,
                artifact.id,
                artifact.file_path,
                expected_bytes,
            )
            await session.commit()
            return GitPublicationResult(
                artifact_id=artifact.id,
                file_path=artifact.file_path,
                git_commit_sha=commit_sha,
                outcome="existing",
            )

        commit_sha = repository.find_publication(
            artifact.id,
            artifact.file_path,
            expected_bytes,
        )
        outcome: Literal["created", "reconciled", "existing"]
        if commit_sha is None:
            staged_by_invocation = True
            path_was_staged = repository.stage_and_verify(
                artifact.file_path, expected_bytes
            )
            staged_by_invocation = path_was_staged
            commit_sha = repository.create_commit(
                artifact.id,
                artifact.file_path,
                expected_bytes,
            )
            commit_created = True
            staged_by_invocation = False
            outcome = "created"
        else:
            outcome = "reconciled"

        artifact.git_commit_sha = commit_sha
        await session.commit()
        return GitPublicationResult(
            artifact_id=artifact.id,
            file_path=artifact.file_path,
            git_commit_sha=commit_sha,
            outcome=outcome,
        )
    except Exception as primary_error:
        cleanup_error: Exception | None = None
        if staged_by_invocation and not commit_created:
            try:
                repository.restore_selected_index(
                    artifact.file_path  # type: ignore[possibly-undefined]
                )
            except Exception as exc:
                cleanup_error = exc
        await session.rollback()
        if cleanup_error is not None:
            raise GitPublicationOperationalError(
                f"{primary_error}; selected-path index cleanup also failed: "
                f"{cleanup_error}; manual index inspection is required"
            ) from primary_error
        raise
    finally:
        fcntl.flock(lock_descriptor, fcntl.LOCK_UN)
        os.close(lock_descriptor)
