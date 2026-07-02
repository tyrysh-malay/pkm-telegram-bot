import subprocess
import sys
from pathlib import Path

from scripts.project_context import active_task
from scripts.project_context import collect_context
from scripts.project_context import index_documents
from scripts.project_context import render_markdown
from scripts.project_context import task_status


REPOSITORY_ROOT = Path(__file__).parents[1]
SCRIPT = REPOSITORY_ROOT / "scripts/project_context.py"
REQUIRED_WORKFLOW_PATHS = (
    Path("docs/WORKFLOW.md"),
    Path("tasks/TEMPLATE.md"),
)


def run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def git(repository: Path, *arguments: str) -> str:
    result = run(["git", *arguments], repository)
    assert result.returncode == 0, result.stderr
    return result.stdout


def commit_file(repository: Path, path: str, content: str, subject: str) -> str:
    target = repository / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    git(repository, "add", path)
    git(repository, "commit", "-m", subject)
    return git(repository, "rev-parse", "HEAD").strip()


def create_repository(tmp_path: Path) -> Path:
    repository = tmp_path / "repository"
    repository.mkdir()
    git(repository, "init", "-b", "main")
    git(repository, "config", "user.email", "tests@example.com")
    git(repository, "config", "user.name", "Project Context Tests")
    commit_file(repository, "README.md", "# Example repository\n", "initial commit")
    return repository


def invoke(repository: Path) -> subprocess.CompletedProcess[str]:
    return run([sys.executable, str(SCRIPT)], repository)


def test_required_task004_workflow_files_are_present() -> None:
    missing_paths = [
        path.as_posix()
        for path in REQUIRED_WORKFLOW_PATHS
        if not (REPOSITORY_ROOT / path).is_file()
    ]

    assert missing_paths == []


def test_markdown_includes_branch_head_and_changed_paths(tmp_path: Path) -> None:
    repository = create_repository(tmp_path)
    head = git(repository, "rev-parse", "HEAD").strip()
    (repository / "untracked note.txt").write_text("private body", encoding="utf-8")

    report = render_markdown(
        collect_context(repository, generated_at="2026-01-01T00:00:00+00:00")
    )

    assert "Branch: `main`" in report
    assert f"HEAD: `{head}` — initial commit" in report
    assert "Working tree: **dirty**" in report
    assert "?? \"untracked note.txt\"" in report
    assert "private body" not in report


def test_recent_commits_are_bounded_and_newest_first(tmp_path: Path) -> None:
    repository = create_repository(tmp_path)
    for number in range(12):
        commit_file(
            repository,
            f"commits/{number:02}.txt",
            str(number),
            f"commit-{number:02}",
        )

    context = collect_context(repository)

    assert len(context.recent_commits) == 10
    assert [commit.subject for commit in context.recent_commits] == [
        f"commit-{number:02}" for number in reversed(range(2, 12))
    ]


def test_tasks_are_sorted_with_explicit_and_unspecified_statuses(tmp_path: Path) -> None:
    repository = create_repository(tmp_path)
    tasks = repository / "tasks"
    tasks.mkdir()
    (tasks / "002-second.md").write_text("# Second\n", encoding="utf-8")
    (tasks / "001-first.md").write_text(
        "# First\n\n**Status:** completed\n", encoding="utf-8"
    )

    context = collect_context(repository)

    assert [(task.path, task.status) for task in context.tasks] == [
        ("tasks/001-first.md", "completed"),
        ("tasks/002-second.md", "unspecified"),
    ]
    assert task_status(tasks / "002-second.md") == "unspecified"


def test_active_task_is_read_from_current_state(tmp_path: Path) -> None:
    current_state = tmp_path / "CURRENT_STATE.md"
    current_state.write_text(
        "# State\n\n**Active task:** `tasks/004-example.md`\n", encoding="utf-8"
    )

    assert active_task(current_state) == "tasks/004-example.md"


def test_missing_optional_document_is_reported_without_claim(tmp_path: Path) -> None:
    repository = create_repository(tmp_path)

    documents = index_documents(repository, ("docs/OPTIONAL.md",))

    assert documents[0].exists is False
    assert documents[0].title is None
    context = collect_context(repository)
    report = render_markdown(
        context.__class__(
            generated_at=context.generated_at,
            branch=context.branch,
            head=context.head,
            status_lines=context.status_lines,
            recent_commits=context.recent_commits,
            tasks=context.tasks,
            active_task=context.active_task,
            documents=documents,
        )
    )
    assert "`docs/OPTIONAL.md` — missing" in report


def test_detached_head_is_reported(tmp_path: Path) -> None:
    repository = create_repository(tmp_path)
    head = git(repository, "rev-parse", "HEAD").strip()
    git(repository, "checkout", "--detach", head)

    report = render_markdown(collect_context(repository))

    assert "Branch: `detached HEAD`" in report
    assert f"HEAD: `{head}`" in report


def test_command_is_read_only_and_does_not_create_files(tmp_path: Path) -> None:
    repository = create_repository(tmp_path)
    before_status = git(repository, "status", "--porcelain=v1", "--untracked-files=all")
    before_paths = sorted(path.relative_to(repository) for path in repository.rglob("*"))

    result = invoke(repository)

    after_status = git(repository, "status", "--porcelain=v1", "--untracked-files=all")
    after_paths = sorted(path.relative_to(repository) for path in repository.rglob("*"))
    assert result.returncode == 0, result.stderr
    assert before_status == after_status
    assert before_paths == after_paths


def test_secret_file_contents_are_not_emitted(tmp_path: Path) -> None:
    repository = create_repository(tmp_path)
    secret = "never-emit-this-test-secret"
    (repository / ".env").write_text(
        f"TELEGRAM_BOT_TOKEN={secret}\nDATABASE_URL={secret}\n",
        encoding="utf-8",
    )

    result = invoke(repository)

    assert result.returncode == 0, result.stderr
    assert secret not in result.stdout
    assert ".env" not in result.stdout
    assert "TELEGRAM_BOT_TOKEN=" not in result.stdout
    assert "DATABASE_URL=" not in result.stdout


def test_running_outside_git_repository_fails_clearly(tmp_path: Path) -> None:
    result = invoke(tmp_path)

    assert result.returncode != 0
    assert result.stdout == ""
    assert "project context error:" in result.stderr
    assert "not a git repository" in result.stderr
