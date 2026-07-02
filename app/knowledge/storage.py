import errno
import os
import stat
import sys
import uuid
from enum import Enum
from pathlib import Path

from app.knowledge.errors import AtomicPublicationError
from app.knowledge.errors import FileConflictError
from app.knowledge.errors import KnowledgeBaseError
from app.knowledge.errors import TemporaryFileCleanupError
from app.knowledge.errors import UnsupportedFileEntryError


class FileState(Enum):
    ABSENT = "absent"
    EXACT = "exact"
    CONFLICTING = "conflicting"
    UNSUPPORTED = "unsupported"


def resolve_destination(
    knowledge_base_root: Path,
    relative_path: str,
) -> tuple[Path, Path]:
    raw_parts = relative_path.split("/")
    if (
        relative_path.startswith("/")
        or "\\" in relative_path
        or any(part in {"", ".", ".."} for part in raw_parts)
    ):
        raise KnowledgeBaseError(
            f"unsafe relative artifact path: {relative_path!r}"
        )

    try:
        root = knowledge_base_root.resolve(strict=False)
        root.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise KnowledgeBaseError(
            f"cannot create knowledge-base root {knowledge_base_root}"
        ) from exc

    try:
        root_stat = root.lstat()
    except OSError as exc:
        raise KnowledgeBaseError(
            f"cannot inspect knowledge-base root {knowledge_base_root}"
        ) from exc
    if not stat.S_ISDIR(root_stat.st_mode):
        raise KnowledgeBaseError(
            f"knowledge-base root is not a directory: {knowledge_base_root}"
        )

    destination = root.joinpath(*raw_parts)
    parent = destination.parent
    try:
        parent_stat = parent.lstat()
    except FileNotFoundError:
        try:
            parent.mkdir()
            parent_stat = parent.lstat()
        except FileExistsError:
            parent_stat = parent.lstat()
        except OSError as exc:
            raise KnowledgeBaseError(
                f"cannot create artifact directory for {relative_path}"
            ) from exc
    except OSError as exc:
        raise KnowledgeBaseError(
            f"cannot inspect artifact directory for {relative_path}"
        ) from exc

    if stat.S_ISLNK(parent_stat.st_mode) or not stat.S_ISDIR(parent_stat.st_mode):
        raise KnowledgeBaseError(
            f"artifact parent is not a safe directory for {relative_path}"
        )

    try:
        parent.resolve(strict=True).relative_to(root)
    except (OSError, ValueError) as exc:
        raise KnowledgeBaseError(
            f"artifact destination escapes the knowledge-base root: {relative_path}"
        ) from exc

    return root, destination


def _read_regular_file(path: Path) -> bytes:
    flags = os.O_RDONLY
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW

    descriptor = os.open(path, flags)
    try:
        file_stat = os.fstat(descriptor)
        if not stat.S_ISREG(file_stat.st_mode):
            raise UnsupportedFileEntryError(
                f"unsupported filesystem entry at {path.name}"
            )
        with os.fdopen(descriptor, "rb", closefd=False) as file:
            return file.read()
    finally:
        os.close(descriptor)


def classify_file(path: Path, expected_bytes: bytes) -> FileState:
    try:
        entry_stat = path.lstat()
    except FileNotFoundError:
        return FileState.ABSENT
    except OSError as exc:
        raise KnowledgeBaseError(f"cannot inspect artifact path {path.name}") from exc

    if not stat.S_ISREG(entry_stat.st_mode):
        return FileState.UNSUPPORTED

    try:
        actual_bytes = _read_regular_file(path)
    except FileNotFoundError:
        return FileState.ABSENT
    except OSError as exc:
        if exc.errno == errno.ELOOP:
            return FileState.UNSUPPORTED
        raise KnowledgeBaseError(f"cannot read artifact path {path.name}") from exc

    if actual_bytes == expected_bytes:
        return FileState.EXACT
    return FileState.CONFLICTING


def _raise_for_existing_state(state: FileState, relative_path: str) -> None:
    if state is FileState.CONFLICTING:
        raise FileConflictError(
            f"conflicting file exists at artifact path {relative_path}"
        )
    if state is FileState.UNSUPPORTED:
        raise UnsupportedFileEntryError(
            f"unsupported filesystem entry exists at artifact path {relative_path}"
        )


def _flush_directory(directory: Path) -> None:
    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    descriptor = os.open(directory, flags)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def publish_no_replace(
    destination: Path,
    relative_path: str,
    content: bytes,
) -> None:
    temporary_path = destination.parent / (
        f".{destination.name}.{uuid.uuid4().hex}.tmp"
    )
    descriptor: int | None = None

    try:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_CLOEXEC"):
            flags |= os.O_CLOEXEC
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(temporary_path, flags, 0o600)

        view = memoryview(content)
        while view:
            written = os.write(descriptor, view)
            if written == 0:
                raise OSError("temporary artifact write made no progress")
            view = view[written:]
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = None

        try:
            os.link(
                temporary_path,
                destination,
                src_dir_fd=None,
                dst_dir_fd=None,
                follow_symlinks=False,
            )
        except FileExistsError:
            state = classify_file(destination, content)
            if state is not FileState.EXACT:
                _raise_for_existing_state(state, relative_path)
                raise KnowledgeBaseError(
                    f"artifact path disappeared during publication: {relative_path}"
                )
        except OSError as exc:
            unsupported_errors = {
                errno.EXDEV,
                errno.ENOSYS,
                errno.EOPNOTSUPP,
            }
            if exc.errno in unsupported_errors:
                raise AtomicPublicationError(
                    f"atomic no-replace publication is unsupported for {relative_path}"
                ) from exc
            raise
        else:
            _flush_directory(destination.parent)
    finally:
        active_error = sys.exc_info()[1]
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError as exc:
                if active_error is None:
                    raise KnowledgeBaseError(
                        f"cannot close temporary artifact for {relative_path}"
                    ) from exc
        try:
            temporary_path.unlink(missing_ok=True)
        except OSError as exc:
            if active_error is not None:
                active_error.add_note(
                    "temporary artifact cleanup also failed for "
                    f"{relative_path}: {exc}"
                )
            else:
                raise TemporaryFileCleanupError(
                    f"cannot clean temporary artifact for {relative_path}"
                ) from exc


def ensure_exact_file(
    knowledge_base_root: Path,
    relative_path: str,
    content: bytes,
) -> Path:
    _, destination = resolve_destination(knowledge_base_root, relative_path)
    state = classify_file(destination, content)

    if state is FileState.ABSENT:
        try:
            publish_no_replace(destination, relative_path, content)
        except OSError as exc:
            raise KnowledgeBaseError(
                f"cannot publish artifact at {relative_path}"
            ) from exc
        state = classify_file(destination, content)

    if state is not FileState.EXACT:
        _raise_for_existing_state(state, relative_path)
        raise KnowledgeBaseError(
            f"artifact path is absent after publication: {relative_path}"
        )

    return destination
