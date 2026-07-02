"""Generate a complete, safe Markdown bundle for implementation review."""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import stat
import subprocess
import sys
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from datetime import timezone
from pathlib import Path
from pathlib import PurePosixPath
from typing import Sequence


MAX_EVIDENCE_BYTES = 1_048_576
MAX_TRACKED_DIFF_BYTES = 4_194_304
MAX_BUNDLE_BYTES = 8_388_608

PRIVATE_KEY_PATTERN = re.compile(
    rb"-----BEGIN (?:RSA |EC |DSA |OPENSSH |ENCRYPTED )?PRIVATE KEY-----"
)
SECRET_SUFFIXES = (".pem", ".key", ".p12", ".pfx", ".jks")
SECRET_BASENAMES = ("id_rsa", "id_ed25519")
SECRET_COMPONENTS = ("secret", "secrets", "credential", "credentials")
SECRET_TERM_PATTERN = re.compile(
    r"(?:^|[._\-\s])(?:secret|credential|token|password)(?:$|[._\-\s])",
    re.IGNORECASE,
)
API_KEY_TERM_PATTERN = re.compile(
    r"(?:^|[.\-\s_])api_key(?:$|[.\-\s_])",
    re.IGNORECASE,
)
TRACKED_ENV_TEMPLATE_PATH = ".env.example"

DIFF_ARGUMENTS = (
    "diff",
    "--no-ext-diff",
    "--no-textconv",
    "--no-renames",
    "--full-index",
    "--no-color",
    "--no-indent-heuristic",
    "--diff-algorithm=myers",
    "--src-prefix=a/",
    "--dst-prefix=b/",
    "HEAD",
    "--",
)


class ReviewBundleError(RuntimeError):
    """Raised when complete review evidence cannot be captured safely."""


@dataclass(frozen=True)
class StatusRecord:
    code: str
    path: str

    @property
    def is_untracked(self) -> bool:
        return self.code == "??"


@dataclass(frozen=True)
class GitTreeEntry:
    mode: str
    object_type: str
    object_id: str


@dataclass(frozen=True)
class FileSignature:
    device: int
    inode: int
    mode: int
    size: int
    modified_ns: int
    changed_ns: int


@dataclass(frozen=True)
class FileCapture:
    data: bytes
    signature: FileSignature


@dataclass(frozen=True)
class RepositorySnapshot:
    branch: str | None
    head: str
    head_subject: str
    status_records: tuple[StatusRecord, ...]
    status_evidence: bytes
    tracked_diff: bytes
    untracked_paths: tuple[str, ...]


@dataclass(frozen=True)
class ChangedFile:
    path: str
    status_codes: tuple[str, ...]
    states: tuple[str, ...]
    representations: tuple[str, ...]
    current_data: bytes | None
    head_data: bytes | None


@dataclass(frozen=True)
class EvidenceItem:
    role: str
    source: str
    data: bytes


def run_git(
    repository: Path,
    arguments: Sequence[str],
    *,
    input_data: bytes | None = None,
    allowed_returncodes: tuple[int, ...] = (0,),
) -> subprocess.CompletedProcess[bytes]:
    """Run an explicit Git query without invoking a shell or optional locks."""
    command = ["git", "--no-optional-locks", "-C", str(repository), *arguments]
    try:
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            input=input_data,
        )
    except OSError as exc:
        raise ReviewBundleError(f"could not run git: {exc}") from exc

    if result.returncode not in allowed_returncodes:
        operation = "git " + " ".join(arguments)
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        detail = detail.replace(str(repository), "<repository>")
        if not detail:
            detail = f"exit code {result.returncode}"
        raise ReviewBundleError(f"{operation} failed: {detail}")
    return result


def decode_utf8(data: bytes, label: str, *, reject_nul: bool = True) -> str:
    try:
        text = data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ReviewBundleError(f"{label} is not valid UTF-8 text") from exc
    if reject_nul and b"\0" in data:
        raise ReviewBundleError(f"{label} contains NUL bytes and is not safe text")
    return text


def validate_safe_text(data: bytes, label: str) -> str:
    text = decode_utf8(data, label)
    if PRIVATE_KEY_PATTERN.search(data):
        raise ReviewBundleError(f"{label} contains a private-key header")
    return text


def validate_path_text(path: str, label: str = "repository path") -> str:
    if not path:
        raise ReviewBundleError(f"{label} is empty")
    if any(unicodedata.category(character).startswith("C") for character in path):
        raise ReviewBundleError(f"{label} contains control or formatting characters")
    pure_path = PurePosixPath(path)
    if pure_path.is_absolute() or ".." in pure_path.parts:
        raise ReviewBundleError(f"{label} is not a safe repository-relative path")
    return path


def is_secret_like_path(path: str) -> bool:
    components = tuple(component.casefold() for component in PurePosixPath(path).parts)
    if not components:
        return False
    basename = components[-1]
    if basename == ".env" or basename.startswith(".env."):
        return True
    if basename in SECRET_BASENAMES or basename.endswith(SECRET_SUFFIXES):
        return True
    if any(component in SECRET_COMPONENTS for component in components):
        return True
    return bool(
        SECRET_TERM_PATTERN.search(basename) or API_KEY_TERM_PATTERN.search(basename)
    )


def require_safe_path(path: str, label: str = "evidence path") -> None:
    validate_path_text(path, label)
    if is_secret_like_path(path):
        raise ReviewBundleError(f"{label} is secret-like and cannot be bundled: {path}")


def require_safe_changed_path(
    repository: Path,
    path: str,
    records: Sequence[StatusRecord],
) -> None:
    """Validate a changed path, with one tracked-template-only exception."""
    validate_path_text(path, "evidence path")
    if not is_secret_like_path(path):
        return

    is_tracked = any(not record.is_untracked for record in records)
    is_untracked = any(record.is_untracked for record in records)
    if path == TRACKED_ENV_TEMPLATE_PATH and is_tracked and not is_untracked:
        head_entry = tree_entry(repository, "HEAD", path)
        if head_entry is not None:
            require_regular_git_blob(head_entry, f"HEAD blob {path}")
            return

    raise ReviewBundleError(
        f"evidence path is secret-like and cannot be bundled: {path}"
    )


def discover_repository(start: Path) -> Path:
    result = run_git(start, ("rev-parse", "--show-toplevel"))
    root_text = decode_utf8(result.stdout, "repository root").strip()
    if not root_text:
        raise ReviewBundleError("git returned no repository root")
    repository = Path(root_text).resolve()
    if start.resolve() != repository:
        raise ReviewBundleError("run the review-bundle command from the repository root")
    run_git(repository, ("rev-parse", "--verify", "HEAD^{commit}"))
    return repository


def validate_task_path(raw_path: str) -> str:
    if "\\" in raw_path:
        raise ReviewBundleError("--task must use a normalized repository-relative path")
    pure_path = PurePosixPath(raw_path)
    normalized = pure_path.as_posix()
    if (
        pure_path.is_absolute()
        or normalized != raw_path
        or ".." in pure_path.parts
        or len(pure_path.parts) < 2
        or pure_path.parts[0] != "tasks"
        or pure_path.suffix != ".md"
    ):
        raise ReviewBundleError(
            "--task must be a normalized repository-relative Markdown path under tasks/"
        )
    require_safe_path(raw_path, "task path")
    return raw_path


def parse_tree_entry(data: bytes, expected_path: str, label: str) -> GitTreeEntry | None:
    if not data:
        return None
    entries = [entry for entry in data.split(b"\0") if entry]
    if len(entries) != 1 or b"\t" not in entries[0]:
        raise ReviewBundleError(f"git returned malformed metadata for {label}")
    metadata, raw_path = entries[0].split(b"\t", 1)
    path = decode_utf8(raw_path, f"{label} path")
    if path != expected_path:
        raise ReviewBundleError(f"git returned unexpected path metadata for {label}")
    fields = metadata.decode("ascii", errors="strict").split()
    if len(fields) != 3:
        raise ReviewBundleError(f"git returned malformed object metadata for {label}")
    return GitTreeEntry(fields[0], fields[1], fields[2])


def tree_entry(repository: Path, revision: str, path: str) -> GitTreeEntry | None:
    output = run_git(repository, ("ls-tree", "-z", revision, "--", path)).stdout
    return parse_tree_entry(output, path, f"{revision}:{path}")


def require_regular_git_blob(entry: GitTreeEntry, label: str) -> None:
    if entry.object_type != "blob" or entry.mode not in ("100644", "100755"):
        raise ReviewBundleError(f"{label} is not a regular Git blob")


def read_git_blob(repository: Path, entry: GitTreeEntry, label: str) -> bytes:
    require_regular_git_blob(entry, label)
    size_output = run_git(repository, ("cat-file", "-s", entry.object_id)).stdout
    try:
        size = int(size_output.strip())
    except ValueError as exc:
        raise ReviewBundleError(f"git returned an invalid byte size for {label}") from exc
    if size > MAX_EVIDENCE_BYTES:
        raise ReviewBundleError(
            f"{label} is {size} bytes; maximum is {MAX_EVIDENCE_BYTES} bytes"
        )
    data = run_git(repository, ("cat-file", "blob", entry.object_id)).stdout
    if len(data) != size:
        raise ReviewBundleError(f"git returned inconsistent blob data for {label}")
    validate_safe_text(data, label)
    return data


def read_task_contract(repository: Path, task_path: str) -> bytes:
    entry = tree_entry(repository, "HEAD", task_path)
    if entry is None:
        raise ReviewBundleError(
            "task specification is absent from HEAD; commit the accepted task before review"
        )
    return read_git_blob(repository, entry, f"committed task {task_path}")


def signature(file_stat: os.stat_result) -> FileSignature:
    return FileSignature(
        device=file_stat.st_dev,
        inode=file_stat.st_ino,
        mode=file_stat.st_mode,
        size=file_stat.st_size,
        modified_ns=file_stat.st_mtime_ns,
        changed_ns=file_stat.st_ctime_ns,
    )


def read_regular_file(path: Path, label: str) -> FileCapture:
    try:
        initial_stat = os.lstat(path)
    except OSError as exc:
        raise ReviewBundleError(f"{label} cannot be read: {exc.strerror}") from exc
    if stat.S_ISLNK(initial_stat.st_mode):
        raise ReviewBundleError(f"{label} is a symlink and cannot be bundled")
    if not stat.S_ISREG(initial_stat.st_mode):
        raise ReviewBundleError(f"{label} is not a regular file")
    if initial_stat.st_size > MAX_EVIDENCE_BYTES:
        raise ReviewBundleError(
            f"{label} is {initial_stat.st_size} bytes; maximum is "
            f"{MAX_EVIDENCE_BYTES} bytes"
        )

    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    flags |= getattr(os, "O_NONBLOCK", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise ReviewBundleError(f"{label} cannot be opened safely: {exc.strerror}") from exc
    try:
        opened_stat = os.fstat(descriptor)
        if not stat.S_ISREG(opened_stat.st_mode):
            raise ReviewBundleError(f"{label} changed type while being read")
        if signature(opened_stat) != signature(initial_stat):
            raise ReviewBundleError(f"{label} changed while being opened; rerun the command")
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(descriptor, min(65_536, MAX_EVIDENCE_BYTES + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > MAX_EVIDENCE_BYTES:
                raise ReviewBundleError(
                    f"{label} exceeds the {MAX_EVIDENCE_BYTES}-byte maximum"
                )
        final_stat = os.fstat(descriptor)
    finally:
        os.close(descriptor)

    try:
        path_stat = os.lstat(path)
    except OSError as exc:
        raise ReviewBundleError(f"{label} changed while being read") from exc
    final_signature = signature(final_stat)
    if final_signature != signature(opened_stat) or signature(path_stat) != final_signature:
        raise ReviewBundleError(f"{label} changed while being read; rerun the command")
    data = b"".join(chunks)
    if len(data) != final_stat.st_size:
        raise ReviewBundleError(f"{label} changed size while being read; rerun the command")
    validate_safe_text(data, label)
    return FileCapture(data=data, signature=final_signature)


def ensure_inside_repository(repository: Path, path: Path, label: str) -> None:
    try:
        path.resolve(strict=False).relative_to(repository)
    except ValueError as exc:
        raise ReviewBundleError(f"{label} resolves outside the repository") from exc


def parse_status(output: bytes) -> tuple[StatusRecord, ...]:
    records: list[StatusRecord] = []
    for raw_record in (record for record in output.split(b"\0") if record):
        if len(raw_record) < 4 or raw_record[2:3] != b" ":
            raise ReviewBundleError("git returned malformed porcelain status")
        try:
            code = raw_record[:2].decode("ascii", errors="strict")
        except UnicodeDecodeError as exc:
            raise ReviewBundleError("git returned malformed status codes") from exc
        path = decode_utf8(raw_record[3:], "changed repository path")
        validate_path_text(path, "changed repository path")
        if code == "!!":
            raise ReviewBundleError("ignored paths unexpectedly appeared in Git status")
        if "U" in code or code in ("AA", "DD"):
            raise ReviewBundleError(f"unmerged Git state is not supported: {path}")
        records.append(StatusRecord(code=code, path=path))
    return tuple(sorted(records, key=lambda record: (record.path, record.code)))


def canonical_status(records: Sequence[StatusRecord]) -> bytes:
    return "".join(
        f"{record.code.replace(' ', '.')}\t{record.path}\n" for record in records
    ).encode("utf-8")


def parse_nul_paths(output: bytes, label: str) -> tuple[str, ...]:
    paths = []
    for raw_path in (item for item in output.split(b"\0") if item):
        path = decode_utf8(raw_path, label)
        validate_path_text(path, label)
        paths.append(path)
    return tuple(sorted(paths))


def current_branch(repository: Path) -> str | None:
    result = run_git(
        repository,
        ("symbolic-ref", "--quiet", "--short", "HEAD"),
        allowed_returncodes=(0, 1),
    )
    if result.returncode == 1:
        return None
    branch = decode_utf8(result.stdout, "branch name").strip()
    validate_path_text(branch, "branch name")
    return branch


def capture_snapshot(repository: Path) -> RepositorySnapshot:
    head = decode_utf8(
        run_git(repository, ("rev-parse", "--verify", "HEAD^{commit}")).stdout,
        "HEAD commit",
    ).strip()
    log_output = run_git(repository, ("log", "-1", "--format=%H%x00%s")).stdout
    log_text = decode_utf8(log_output, "HEAD metadata", reject_nul=False).rstrip("\n")
    log_head, separator, subject = log_text.partition("\0")
    if not separator or log_head != head:
        raise ReviewBundleError("git returned inconsistent HEAD metadata")

    status_output = run_git(
        repository,
        ("status", "--porcelain=v1", "-z", "--untracked-files=all", "--no-renames"),
    ).stdout
    status_records = parse_status(status_output)
    untracked_output = run_git(
        repository,
        ("ls-files", "--others", "--exclude-standard", "-z"),
    ).stdout
    untracked_paths = parse_nul_paths(untracked_output, "untracked repository path")
    status_untracked = tuple(
        sorted(record.path for record in status_records if record.is_untracked)
    )
    if status_untracked != untracked_paths:
        raise ReviewBundleError("Git status and untracked-file discovery disagree")

    tracked_diff = run_git(repository, DIFF_ARGUMENTS).stdout
    if len(tracked_diff) > MAX_TRACKED_DIFF_BYTES:
        raise ReviewBundleError(
            f"tracked diff is {len(tracked_diff)} bytes; maximum is "
            f"{MAX_TRACKED_DIFF_BYTES} bytes"
        )
    validate_safe_text(tracked_diff, "tracked diff")
    return RepositorySnapshot(
        branch=current_branch(repository),
        head=head,
        head_subject=subject,
        status_records=status_records,
        status_evidence=canonical_status(status_records),
        tracked_diff=tracked_diff,
        untracked_paths=untracked_paths,
    )


def ignored_paths(repository: Path, paths: Sequence[str]) -> tuple[str, ...]:
    if not paths:
        return ()
    input_data = b"".join(path.encode("utf-8") + b"\0" for path in paths)
    result = run_git(
        repository,
        ("check-ignore", "--no-index", "-z", "--stdin"),
        input_data=input_data,
        allowed_returncodes=(0, 1),
    )
    return parse_nul_paths(result.stdout, "ignored repository path")


def index_entries(repository: Path, path: str) -> tuple[GitTreeEntry, ...]:
    output = run_git(repository, ("ls-files", "--stage", "-z", "--", path)).stdout
    entries = []
    for raw_entry in (entry for entry in output.split(b"\0") if entry):
        if b"\t" not in raw_entry:
            raise ReviewBundleError(f"git returned malformed index metadata for {path}")
        metadata, raw_path = raw_entry.split(b"\t", 1)
        returned_path = decode_utf8(raw_path, f"index path {path}")
        if returned_path != path:
            raise ReviewBundleError(f"git returned unexpected index path for {path}")
        fields = metadata.decode("ascii", errors="strict").split()
        if len(fields) != 3:
            raise ReviewBundleError(f"git returned malformed index object for {path}")
        mode, object_id, stage = fields
        if stage != "0":
            raise ReviewBundleError(f"unmerged Git index state is not supported: {path}")
        entries.append(GitTreeEntry(mode, "blob" if mode != "160000" else "commit", object_id))
    return tuple(entries)


def binary_diff_paths(repository: Path) -> tuple[str, ...]:
    arguments = list(DIFF_ARGUMENTS)
    arguments.insert(1, "--numstat")
    arguments.insert(2, "-z")
    output = run_git(repository, tuple(arguments)).stdout
    binary_paths = []
    for raw_record in (record for record in output.split(b"\0") if record):
        fields = raw_record.split(b"\t", 2)
        if len(fields) != 3:
            raise ReviewBundleError("git returned malformed diff statistics")
        additions, deletions, raw_path = fields
        path = decode_utf8(raw_path, "diff statistics path")
        validate_path_text(path, "diff statistics path")
        if additions == b"-" or deletions == b"-":
            binary_paths.append(path)
    return tuple(sorted(binary_paths))


def reject_untracked_special_files(
    repository: Path, git_untracked_paths: Sequence[str]
) -> None:
    """Reject non-ignored special files that Git's untracked query cannot list."""
    git_untracked = set(git_untracked_paths)
    candidates = []
    for directory, directory_names, file_names in os.walk(
        repository, topdown=True, followlinks=False
    ):
        directory_path = Path(directory)
        if directory_path == repository:
            directory_names[:] = [name for name in directory_names if name != ".git"]
        names = tuple(directory_names) + tuple(file_names)
        for name in names:
            path = directory_path / name
            try:
                path_stat = os.lstat(path)
            except OSError as exc:
                raise ReviewBundleError(
                    "repository entry changed while special-file safety was checked"
                ) from exc
            if stat.S_ISDIR(path_stat.st_mode) and not stat.S_ISLNK(path_stat.st_mode):
                continue
            if stat.S_ISREG(path_stat.st_mode):
                continue
            relative_path = path.relative_to(repository).as_posix()
            validate_path_text(relative_path, "repository special-file path")
            if relative_path not in git_untracked:
                candidates.append(relative_path)
            if stat.S_ISLNK(path_stat.st_mode) and name in directory_names:
                directory_names.remove(name)

    ignored = set(ignored_paths(repository, tuple(sorted(candidates))))
    for path in sorted(set(candidates) - ignored):
        tracked = run_git(
            repository,
            ("ls-files", "--error-unmatch", "--", path),
            allowed_returncodes=(0, 1),
        )
        if tracked.returncode == 1:
            raise ReviewBundleError(
                f"untracked evidence is not a regular file: {path}"
            )


def status_states(records: Sequence[StatusRecord]) -> tuple[str, ...]:
    states = []
    if any(record.code[0] != " " and not record.is_untracked for record in records):
        states.append("staged")
    if any(record.code[1] != " " and not record.is_untracked for record in records):
        states.append("unstaged")
    if any(record.is_untracked for record in records):
        states.append("untracked")
    if any("D" in record.code for record in records if not record.is_untracked):
        states.append("deleted")
    return tuple(states)


def collect_changed_files(
    repository: Path,
    snapshot: RepositorySnapshot,
    report_repository_path: str | None,
) -> tuple[tuple[ChangedFile, ...], dict[str, FileCapture]]:
    records_by_path: dict[str, list[StatusRecord]] = {}
    for record in snapshot.status_records:
        records_by_path.setdefault(record.path, []).append(record)

    for path, records in records_by_path.items():
        require_safe_changed_path(repository, path, records)
    reject_untracked_special_files(repository, snapshot.untracked_paths)
    tracked_paths = tuple(
        sorted(
            path
            for path, records in records_by_path.items()
            if any(not record.is_untracked for record in records)
        )
    )
    ignored_tracked = ignored_paths(repository, tracked_paths)
    if ignored_tracked:
        raise ReviewBundleError(
            f"changed tracked path matches an ignore rule: {ignored_tracked[0]}"
        )
    binary_paths = binary_diff_paths(repository)
    if binary_paths:
        raise ReviewBundleError(f"tracked binary evidence is not supported: {binary_paths[0]}")

    current_files: dict[str, FileCapture] = {}
    changed_files = []
    for path in sorted(records_by_path):
        records = records_by_path[path]
        is_tracked = any(not record.is_untracked for record in records)
        is_untracked = any(record.is_untracked for record in records)
        file_path = repository / PurePosixPath(path)
        ensure_inside_repository(repository, file_path, f"changed path {path}")

        if is_tracked:
            for entry in index_entries(repository, path):
                require_regular_git_blob(entry, f"index entry {path}")
            head_entry = tree_entry(repository, "HEAD", path)
            if head_entry is not None:
                head_data = read_git_blob(repository, head_entry, f"HEAD blob {path}")
            else:
                head_data = None
        else:
            head_data = None

        try:
            os.lstat(file_path)
        except FileNotFoundError:
            current_capture = None
        except OSError as exc:
            raise ReviewBundleError(f"changed path {path} cannot be inspected: {exc.strerror}") from exc
        else:
            current_capture = read_regular_file(file_path, f"working-tree file {path}")
            current_files[path] = current_capture

        representations = []
        if is_tracked:
            representations.append("tracked diff")
        if is_untracked:
            representations.append("complete untracked content")
        if report_repository_path == path:
            representations.append("explicit completion report")
        changed_files.append(
            ChangedFile(
                path=path,
                status_codes=tuple(record.code.replace(" ", ".") for record in records),
                states=status_states(records),
                representations=tuple(representations),
                current_data=current_capture.data if current_capture is not None else None,
                head_data=head_data,
            )
        )
    return tuple(changed_files), current_files


def report_location(repository: Path, raw_path: str) -> tuple[Path, str | None]:
    requested = Path(raw_path).expanduser()
    absolute = requested if requested.is_absolute() else Path.cwd() / requested
    try:
        resolved = absolute.resolve(strict=False)
        relative = resolved.relative_to(repository)
    except ValueError:
        repository_path = None
    else:
        repository_path = relative.as_posix()
        validate_path_text(repository_path, "completion report path")
        require_safe_path(repository_path, "completion report path")
        if ignored_paths(repository, (repository_path,)):
            raise ReviewBundleError("completion report inside the repository is ignored")

    safe_name = absolute.name
    validate_path_text(safe_name, "completion report filename")
    if repository_path is None and is_secret_like_path(safe_name):
        raise ReviewBundleError("completion report filename is secret-like")
    return absolute, repository_path


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def dynamic_fence(text: str, language: str = "text") -> str:
    longest = max((len(match.group(0)) for match in re.finditer(r"`+", text)), default=0)
    fence = "`" * max(3, longest + 1)
    body = text if text.endswith("\n") or not text else text + "\n"
    return f"{fence}{language}\n{body}{fence}"


def inline_code(text: str) -> str:
    longest = max((len(match.group(0)) for match in re.finditer(r"`+", text)), default=0)
    fence = "`" * max(1, longest + 1)
    return f"{fence}{text}{fence}"


def payload_block(data: bytes, language: str = "text") -> str:
    return dynamic_fence(decode_utf8(data, "captured evidence"), language)


def size_and_hash(data: bytes | None) -> tuple[str, str]:
    if data is None:
        return "absent", "absent"
    return str(len(data)), sha256(data)


def render_bundle(
    snapshot: RepositorySnapshot,
    task_path: str,
    task_data: bytes,
    report_label: str,
    report_data: bytes,
    report_repository_path: str | None,
    changed_files: Sequence[ChangedFile],
    current_files: dict[str, FileCapture],
    generated_at: str,
) -> str:
    untracked_report = report_repository_path in snapshot.untracked_paths
    evidence_items = [
        EvidenceItem("canonical Git status", "git status", snapshot.status_evidence),
        EvidenceItem("committed task contract", f"HEAD:{task_path}", task_data),
    ]
    report_role = "completion report"
    if untracked_report:
        report_role += " + untracked file"
    evidence_items.append(EvidenceItem(report_role, report_label, report_data))
    evidence_items.append(
        EvidenceItem("complete tracked diff", "git diff HEAD --", snapshot.tracked_diff)
    )
    for path in snapshot.untracked_paths:
        if path == report_repository_path:
            continue
        evidence_items.append(
            EvidenceItem("untracked file", path, current_files[path].data)
        )

    branch = snapshot.branch if snapshot.branch is not None else "detached HEAD"
    lines = [
        "# Implementation Review Bundle",
        "",
        f"**Generated at (UTC):** {generated_at}",
        "",
        "> This is point-in-time evidence. The live repository remains authoritative.",
        "> Regenerate this bundle after any repository, task, documentation, implementation, or completion-report change.",
        "",
        "## Evidence precedence",
        "",
        "1. The committed task specification defines the requirements and review contract.",
        "2. Captured Git status, tracked diff, and untracked-file contents define the implementation state.",
        "3. The completion report provides Codex explanations and verification claims; the bundler does not independently execute or validate those claims.",
        "",
        "Separately uploaded files must not silently override this bundle. Any conflict requires generating a fresh bundle.",
        "",
        "## Repository revision",
        "",
        dynamic_fence(
            f"branch\t{branch}\nHEAD\t{snapshot.head}\nsubject\t{snapshot.head_subject}\n"
        ),
        "",
        "## Complete Git status",
        "",
        f"Byte size: {len(snapshot.status_evidence)}  ",
        f"SHA-256: `{sha256(snapshot.status_evidence)}`",
        "",
    ]
    if snapshot.status_evidence:
        lines.append(payload_block(snapshot.status_evidence))
    else:
        lines.append("The working tree is clean.")

    lines.extend(("", "## Changed-file manifest", ""))
    if changed_files:
        manifest_lines = [
            "path\tGit status\tstate\tevidence\tcurrent bytes\tcurrent SHA-256\tHEAD bytes\tHEAD SHA-256"
        ]
        for changed in changed_files:
            current_size, current_hash = size_and_hash(changed.current_data)
            head_size, head_hash = size_and_hash(changed.head_data)
            manifest_lines.append(
                "\t".join(
                    (
                        changed.path,
                        ",".join(changed.status_codes),
                        ",".join(changed.states),
                        ",".join(changed.representations),
                        current_size,
                        current_hash,
                        head_size,
                        head_hash,
                    )
                )
            )
        lines.append(dynamic_fence("\n".join(manifest_lines) + "\n"))
    else:
        lines.append("No changed files.")

    lines.extend(("", "## Evidence manifest", ""))
    evidence_lines = ["role\tsafe source label\tbytes\tSHA-256"]
    evidence_lines.extend(
        f"{item.role}\t{item.source}\t{len(item.data)}\t{sha256(item.data)}"
        for item in evidence_items
    )
    lines.append(dynamic_fence("\n".join(evidence_lines) + "\n"))

    lines.extend(
        (
            "",
            "## Committed task specification",
            "",
            f"Source: {inline_code(f'HEAD:{task_path}')}  ",
            f"Source commit: `{snapshot.head}`  ",
            f"Byte size: {len(task_data)}  ",
            f"SHA-256: `{sha256(task_data)}`",
            "",
            payload_block(task_data, "markdown"),
            "",
            "## Completion report",
            "",
            "This report contains Codex explanations and verification claims supplied for review. The bundler does not independently execute or validate those claims.",
            "",
            f"Safe source label: {inline_code(report_label)}  ",
            f"Byte size: {len(report_data)}  ",
            f"SHA-256: `{sha256(report_data)}`",
            "",
            payload_block(report_data, "markdown"),
            "",
            "## Tracked working-tree diff against HEAD",
            "",
            f"Byte size: {len(snapshot.tracked_diff)}  ",
            f"SHA-256: `{sha256(snapshot.tracked_diff)}`",
            "",
        )
    )
    if snapshot.tracked_diff:
        lines.append(payload_block(snapshot.tracked_diff, "diff"))
    else:
        lines.append("The tracked diff is empty.")

    lines.extend(("", "## Untracked file contents", ""))
    if not snapshot.untracked_paths:
        lines.append("No non-ignored untracked files were present.")
    else:
        for number, path in enumerate(snapshot.untracked_paths, start=1):
            lines.extend(
                (f"### Untracked file {number}", "", f"Repository path: {inline_code(path)}", "")
            )
            if path == report_repository_path:
                lines.append(
                    "The complete payload appears once in the Completion report section above; its evidence-manifest entry identifies both roles."
                )
            else:
                capture = current_files[path]
                lines.extend(
                    (
                        f"Byte size: {len(capture.data)}  ",
                        f"SHA-256: `{sha256(capture.data)}`",
                        "",
                        payload_block(capture.data),
                        "",
                    )
                )
    lines.extend(
        (
            "",
            "## Regeneration warning",
            "",
            "This bundle is valid only for the captured point in time. Regenerate it after any repository or completion-report change, and regenerate rather than combining it with conflicting separately uploaded evidence.",
            "",
        )
    )
    return "\n".join(lines)


def build_review_bundle(
    start: Path,
    task_argument: str,
    report_argument: str,
    *,
    generated_at: str | None = None,
) -> str:
    repository = discover_repository(start)
    task_path = validate_task_path(task_argument)
    initial = capture_snapshot(repository)
    task_data = read_task_contract(repository, task_path)

    report_path, report_repository_path = report_location(repository, report_argument)
    report_capture = read_regular_file(report_path, "completion report")
    report_label = report_repository_path or report_path.name

    changed_files, current_files = collect_changed_files(
        repository, initial, report_repository_path
    )
    if report_repository_path in current_files:
        repository_report = current_files[report_repository_path]
        if repository_report != report_capture:
            raise ReviewBundleError(
                "completion report changed while repository evidence was captured"
            )

    final = capture_snapshot(repository)
    if final != initial:
        raise ReviewBundleError("repository changed during capture; rerun the command")
    reject_untracked_special_files(repository, final.untracked_paths)
    for path, captured in current_files.items():
        recaptured = read_regular_file(
            repository / PurePosixPath(path), f"working-tree file {path}"
        )
        if recaptured != captured:
            raise ReviewBundleError(
                f"working-tree file changed during capture: {path}; rerun the command"
            )
    if read_regular_file(report_path, "completion report") != report_capture:
        raise ReviewBundleError("completion report changed during capture; rerun the command")

    if generated_at is None:
        generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    bundle = render_bundle(
        initial,
        task_path,
        task_data,
        report_label,
        report_capture.data,
        report_repository_path,
        changed_files,
        current_files,
        generated_at,
    )
    bundle_size = len(bundle.encode("utf-8"))
    if bundle_size > MAX_BUNDLE_BYTES:
        raise ReviewBundleError(
            f"final Markdown bundle is {bundle_size} bytes; maximum is "
            f"{MAX_BUNDLE_BYTES} bytes"
        )
    return bundle


def parse_arguments(arguments: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a self-contained implementation review bundle."
    )
    parser.add_argument("--task", required=True, help="committed task path under tasks/")
    parser.add_argument("--report", required=True, help="explicit completion-report file")
    return parser.parse_args(arguments)


def main(arguments: Sequence[str] | None = None) -> int:
    parsed = parse_arguments(arguments)
    try:
        bundle = build_review_bundle(Path.cwd(), parsed.task, parsed.report)
    except (ReviewBundleError, OSError, UnicodeError) as exc:
        print(f"review bundle error: {exc}", file=sys.stderr)
        return 1
    sys.stdout.write(bundle)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
