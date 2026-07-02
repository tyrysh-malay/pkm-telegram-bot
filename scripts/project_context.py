"""Print a compact, read-only Markdown report about the current repository."""

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from datetime import timezone
from pathlib import Path
from typing import Sequence


RECENT_COMMIT_LIMIT = 10
DOCUMENT_PATHS = (
    "AGENTS.md",
    "README.md",
    "docs/ARCHITECTURE.md",
    "docs/CURRENT_STATE.md",
    "docs/DATA_MODEL.md",
    "docs/DECISIONS.md",
    "docs/PROJECT_BRIEF.md",
    "docs/TELEGRAM_INGESTION.md",
    "docs/WORKFLOW.md",
)
STATUS_PATTERN = re.compile(r"^\*\*Status:\*\*\s*(.*?)\s*$", re.MULTILINE)
ACTIVE_TASK_PATTERN = re.compile(
    r"^\*\*Active task:\*\*\s*(?:`([^`]+)`|(.+?))\s*$",
    re.MULTILINE,
)
SECRET_PATH_MARKERS = (
    ".env",
    ".key",
    ".pem",
    "credential",
    "secret",
    "token",
)


class RepositoryContextError(RuntimeError):
    """Raised when verified Git context cannot be collected."""


@dataclass(frozen=True)
class Commit:
    commit_hash: str
    subject: str


@dataclass(frozen=True)
class Task:
    path: str
    status: str


@dataclass(frozen=True)
class Document:
    path: str
    exists: bool
    title: str | None


@dataclass(frozen=True)
class RepositoryContext:
    generated_at: str
    branch: str | None
    head: Commit
    status_lines: tuple[str, ...]
    recent_commits: tuple[Commit, ...]
    tasks: tuple[Task, ...]
    active_task: str
    documents: tuple[Document, ...]


def run_git(
    repository: Path,
    arguments: Sequence[str],
    *,
    allow_failure: bool = False,
) -> subprocess.CompletedProcess[str]:
    """Run one explicit, read-only Git command without invoking a shell."""
    command = ["git", "-C", str(repository), *arguments]
    try:
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    except OSError as exc:
        raise RepositoryContextError(f"could not run git: {exc}") from exc

    if result.returncode != 0 and not allow_failure:
        operation = "git " + " ".join(arguments)
        detail = result.stderr.strip() or f"exit code {result.returncode}"
        raise RepositoryContextError(f"{operation} failed: {detail}")
    return result


def find_repository_root(start: Path) -> Path:
    result = run_git(start, ("rev-parse", "--show-toplevel"))
    root = result.stdout.strip()
    if not root:
        raise RepositoryContextError("git rev-parse returned no repository root")
    return Path(root)


def parse_commit(line: str) -> Commit:
    commit_hash, separator, subject = line.partition("\0")
    if not separator or not commit_hash:
        raise RepositoryContextError("git returned malformed commit metadata")
    return Commit(commit_hash=commit_hash, subject=subject)


def status_line_path_text(line: str) -> str:
    if len(line) <= 3:
        return ""
    return line[3:]


def is_secret_like_path(path_text: str) -> bool:
    return any(marker in path_text.lower() for marker in SECRET_PATH_MARKERS)


def safe_status_line(line: str) -> str:
    path_text = status_line_path_text(line)
    if is_secret_like_path(path_text):
        return f"{line[:3]}[redacted secret-like path]"
    return line


def task_status(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    match = STATUS_PATTERN.search(text)
    if not match or not match.group(1):
        return "unspecified"
    return match.group(1)


def active_task(current_state_path: Path) -> str:
    if not current_state_path.is_file():
        return "unavailable"
    text = current_state_path.read_text(encoding="utf-8")
    match = ACTIVE_TASK_PATTERN.search(text)
    if not match:
        return "unspecified"
    return (match.group(1) or match.group(2)).strip()


def first_markdown_heading(path: Path) -> str | None:
    with path.open(encoding="utf-8") as document:
        for line in document:
            if line.startswith("# "):
                return line[2:].strip() or None
    return None


def index_documents(
    repository: Path,
    document_paths: Sequence[str] = DOCUMENT_PATHS,
) -> tuple[Document, ...]:
    documents = []
    for relative_path in sorted(document_paths):
        path = repository / relative_path
        exists = path.is_file()
        title = first_markdown_heading(path) if exists else None
        documents.append(Document(relative_path, exists, title))
    return tuple(documents)


def collect_context(repository: Path, generated_at: str | None = None) -> RepositoryContext:
    repository = find_repository_root(repository)

    branch_result = run_git(
        repository,
        ("symbolic-ref", "--quiet", "--short", "HEAD"),
        allow_failure=True,
    )
    if branch_result.returncode not in (0, 1):
        detail = branch_result.stderr.strip() or f"exit code {branch_result.returncode}"
        raise RepositoryContextError(f"git symbolic-ref failed: {detail}")
    branch = branch_result.stdout.strip() if branch_result.returncode == 0 else None

    head_line = run_git(repository, ("log", "-1", "--format=%H%x00%s")).stdout.rstrip(
        "\n"
    )
    head = parse_commit(head_line)

    status_output = run_git(
        repository,
        ("status", "--porcelain=v1", "--untracked-files=all"),
    ).stdout
    status_lines = tuple(
        sorted(safe_status_line(line) for line in status_output.splitlines() if line)
    )

    log_output = run_git(
        repository,
        ("log", f"-{RECENT_COMMIT_LIMIT}", "--format=%H%x00%s"),
    ).stdout
    recent_commits = tuple(
        parse_commit(line) for line in log_output.splitlines() if line
    )

    tasks_directory = repository / "tasks"
    task_paths = sorted(tasks_directory.glob("*.md")) if tasks_directory.is_dir() else []
    tasks = tuple(
        Task(path.relative_to(repository).as_posix(), task_status(path))
        for path in task_paths
    )

    if generated_at is None:
        generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    return RepositoryContext(
        generated_at=generated_at,
        branch=branch,
        head=head,
        status_lines=status_lines,
        recent_commits=recent_commits,
        tasks=tasks,
        active_task=active_task(repository / "docs/CURRENT_STATE.md"),
        documents=index_documents(repository),
    )


def render_markdown(context: RepositoryContext) -> str:
    branch = context.branch if context.branch is not None else "detached HEAD"
    tree_state = "dirty" if context.status_lines else "clean"
    lines = [
        "# Project Context",
        "",
        f"**Generated at (UTC):** {context.generated_at}",
        "",
        "> Point-in-time snapshot only. The live repository remains authoritative.",
        "",
        "## Git",
        "",
        f"- Branch: `{branch}`",
        f"- HEAD: `{context.head.commit_hash}` — {context.head.subject}",
        f"- Working tree: **{tree_state}**",
        "",
        "### Changed paths",
        "",
    ]
    if context.status_lines:
        lines.extend(("```text", *context.status_lines, "```"))
        lines.append("Git porcelain status is shown as staged/unstaged status plus path.")
    else:
        lines.append("None.")

    lines.extend(("", f"### Recent commits (latest {RECENT_COMMIT_LIMIT})", ""))
    if context.recent_commits:
        lines.extend(
            f"- `{commit.commit_hash}` — {commit.subject}"
            for commit in context.recent_commits
        )
    else:
        lines.append("None.")

    lines.extend(("", "## Tasks", "", f"**Active task:** {context.active_task}", ""))
    if context.tasks:
        lines.extend(f"- `{task.path}` — status: {task.status}" for task in context.tasks)
    else:
        lines.append("No task files found.")

    lines.extend(("", "## Documentation index", ""))
    for document in context.documents:
        if not document.exists:
            lines.append(f"- `{document.path}` — missing")
        elif document.title:
            lines.append(f"- `{document.path}` — {document.title}")
        else:
            lines.append(f"- `{document.path}` — exists; title unavailable")

    lines.extend(
        (
            "",
            "> Generated reports and uploaded Web Chat files can become stale; verify claims against the live repository.",
            "",
        )
    )
    return "\n".join(lines)


def main() -> int:
    try:
        context = collect_context(Path.cwd())
    except (RepositoryContextError, OSError, UnicodeError) as exc:
        print(f"project context error: {exc}", file=sys.stderr)
        return 1

    print(render_markdown(context), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
