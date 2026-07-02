import hashlib
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

import scripts.review_bundle as review_bundle
from scripts.review_bundle import DIFF_ARGUMENTS
from scripts.review_bundle import ReviewBundleError
from scripts.review_bundle import build_review_bundle


REPOSITORY_ROOT = Path(__file__).parents[1]
SCRIPT = REPOSITORY_ROOT / "scripts/review_bundle.py"
TASK_PATH = "tasks/005-example.md"
TASK_TEXT = "# Task 005: Example\n\n**Status:** planned\n"
REPORT_TEXT = "# Completion report\n\nAll requested checks passed.\n"


def run(
    command: list[str],
    cwd: Path,
    *,
    text: bool = True,
) -> subprocess.CompletedProcess:
    return subprocess.run(
        command,
        cwd=cwd,
        check=False,
        capture_output=True,
        text=text,
        encoding="utf-8" if text else None,
    )


def git(repository: Path, *arguments: str, text: bool = True):
    result = run(["git", *arguments], repository, text=text)
    assert result.returncode == 0, result.stderr
    return result.stdout


def write(path: Path, content: str | bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, bytes):
        path.write_bytes(content)
    else:
        path.write_text(content, encoding="utf-8")


def commit_all(repository: Path, subject: str) -> str:
    git(repository, "add", "-A")
    git(repository, "commit", "-m", subject)
    return git(repository, "rev-parse", "HEAD").strip()


def create_repository(tmp_path: Path) -> tuple[Path, Path, str]:
    repository = tmp_path / "repository"
    repository.mkdir()
    git(repository, "init", "-b", "main")
    git(repository, "config", "user.email", "tests@example.com")
    git(repository, "config", "user.name", "Review Bundle Tests")
    write(repository / TASK_PATH, TASK_TEXT)
    write(repository / "tracked.txt", "base\n")
    head = commit_all(repository, "accepted task")
    report = tmp_path / "task005-handoff.md"
    write(report, REPORT_TEXT)
    return repository, report, head


def invoke(
    repository: Path,
    report: Path,
    task: str = TASK_PATH,
    *extra: str,
) -> subprocess.CompletedProcess[str]:
    return run(
        [
            sys.executable,
            str(SCRIPT),
            "--task",
            task,
            "--report",
            str(report),
            *extra,
        ],
        repository,
    )


def fixed_bundle(repository: Path, report: Path, task: str = TASK_PATH) -> str:
    return build_review_bundle(
        repository,
        task,
        str(report),
        generated_at="2026-01-01T00:00:00+00:00",
    )


@pytest.mark.parametrize(
    "arguments",
    (
        [],
        ["--task", TASK_PATH],
        ["--report", "/tmp/report.md"],
    ),
)
def test_required_arguments_fail_without_stdout(
    tmp_path: Path, arguments: list[str]
) -> None:
    repository, _, _ = create_repository(tmp_path)

    result = run([sys.executable, str(SCRIPT), *arguments], repository)

    assert result.returncode != 0
    assert result.stdout == ""
    assert "usage:" in result.stderr


def test_task_contract_comes_from_head_not_working_tree(tmp_path: Path) -> None:
    repository, report, head = create_repository(tmp_path)
    rewritten = "# Rewritten uncommitted contract\n"
    write(repository / TASK_PATH, rewritten)

    bundle = fixed_bundle(repository, report)

    assert TASK_TEXT in bundle
    assert rewritten in bundle  # The rewrite is evidence in the tracked diff.
    task_section = bundle.split("## Committed task specification", 1)[1].split(
        "## Completion report", 1
    )[0]
    assert TASK_TEXT in task_section
    assert rewritten not in task_section
    assert f"Source commit: `{head}`" in task_section


def test_task_absent_from_head_is_rejected(tmp_path: Path) -> None:
    repository, report, _ = create_repository(tmp_path)
    uncommitted_task = repository / "tasks/006-uncommitted.md"
    write(uncommitted_task, "# Uncommitted\n")

    result = invoke(repository, report, "tasks/006-uncommitted.md")

    assert result.returncode != 0
    assert result.stdout == ""
    assert "absent from HEAD" in result.stderr


@pytest.mark.parametrize(
    "task",
    (
        "/tmp/task.md",
        "tasks/../task.md",
        "tasks//task.md",
        "README.md",
        "tasks/task.txt",
    ),
)
def test_invalid_task_paths_are_rejected(tmp_path: Path, task: str) -> None:
    repository, report, _ = create_repository(tmp_path)

    result = invoke(repository, report, task)

    assert result.returncode != 0
    assert result.stdout == ""
    assert "--task" in result.stderr or "task path" in result.stderr


def test_symlink_task_is_rejected(tmp_path: Path) -> None:
    repository, report, _ = create_repository(tmp_path)
    os.symlink("../tracked.txt", repository / "tasks/symlink.md")
    commit_all(repository, "add symlink task")

    result = invoke(repository, report, "tasks/symlink.md")

    assert result.returncode != 0
    assert "not a regular Git blob" in result.stderr


def test_submodule_task_is_rejected(tmp_path: Path) -> None:
    repository, report, _ = create_repository(tmp_path)
    source = tmp_path / "source"
    source.mkdir()
    git(source, "init", "-b", "main")
    git(source, "config", "user.email", "tests@example.com")
    git(source, "config", "user.name", "Submodule Tests")
    write(source / "README.md", "# Source\n")
    commit_all(source, "source")
    git(
        repository,
        "-c",
        "protocol.file.allow=always",
        "submodule",
        "add",
        str(source),
        "tasks/submodule.md",
    )
    commit_all(repository, "add task submodule")

    result = invoke(repository, report, "tasks/submodule.md")

    assert result.returncode != 0
    assert "not a regular Git blob" in result.stderr


def test_branch_head_and_detached_head_are_rendered(tmp_path: Path) -> None:
    repository, report, head = create_repository(tmp_path)
    attached = fixed_bundle(repository, report)
    git(repository, "checkout", "--detach", head)
    detached = fixed_bundle(repository, report)

    assert "branch\tmain" in attached
    assert f"HEAD\t{head}" in attached
    assert "branch\tdetached HEAD" in detached


def test_staged_unstaged_combined_add_delete_and_mode_changes(tmp_path: Path) -> None:
    repository, report, _ = create_repository(tmp_path)
    write(repository / "mixed.txt", "base\n")
    write(repository / "delete.txt", "delete\n")
    write(repository / "mode.sh", "#!/bin/sh\n")
    commit_all(repository, "add fixtures")
    write(repository / "mixed.txt", "base\nstaged\n")
    git(repository, "add", "mixed.txt")
    write(repository / "mixed.txt", "base\nstaged\nunstaged\n")
    write(repository / "unstaged.txt", "new\n")
    git(repository, "add", "unstaged.txt")
    write(repository / "unstaged.txt", "new\nchanged\n")
    git(repository, "rm", "delete.txt")
    os.chmod(repository / "mode.sh", stat.S_IMODE(os.stat(repository / "mode.sh").st_mode) | stat.S_IXUSR)

    bundle = fixed_bundle(repository, report)

    assert "MM\tmixed.txt" in bundle
    assert "AM\tunstaged.txt" in bundle
    assert "D.\tdelete.txt" in bundle
    assert ".M\tmode.sh" in bundle
    assert "+staged" in bundle
    assert "+unstaged" in bundle
    assert "deleted file mode 100644" in bundle
    assert "old mode 100644" in bundle
    assert "new mode 100755" in bundle


def test_staged_deletion_and_untracked_recreation_keep_both_roles(tmp_path: Path) -> None:
    repository, report, _ = create_repository(tmp_path)
    git(repository, "rm", "tracked.txt")
    write(repository / "tracked.txt", "recreated\n")

    bundle = fixed_bundle(repository, report)

    assert "D.\ttracked.txt" in bundle
    assert "??\ttracked.txt" in bundle
    manifest_line = next(
        line for line in bundle.splitlines() if line.startswith("tracked.txt\t")
    )
    assert "tracked diff,complete untracked content" in manifest_line
    assert "recreated" in bundle


def test_unmerged_state_is_rejected(tmp_path: Path) -> None:
    repository, report, _ = create_repository(tmp_path)
    git(repository, "checkout", "-b", "other")
    write(repository / "tracked.txt", "other\n")
    commit_all(repository, "other change")
    git(repository, "checkout", "main")
    write(repository / "tracked.txt", "main\n")
    commit_all(repository, "main change")
    merge = run(["git", "merge", "other"], repository)
    assert merge.returncode != 0

    result = invoke(repository, report)

    assert result.returncode != 0
    assert result.stdout == ""
    assert "unmerged Git state" in result.stderr


def test_diff_size_hash_and_payload_match_git_output(tmp_path: Path) -> None:
    repository, report, _ = create_repository(tmp_path)
    write(repository / "tracked.txt", "base\nchanged\n")
    expected = git(repository, *DIFF_ARGUMENTS, text=False)

    bundle = fixed_bundle(repository, report)

    assert f"Byte size: {len(expected)}" in bundle
    assert hashlib.sha256(expected).hexdigest() in bundle
    assert expected.decode("utf-8") in bundle


def test_all_untracked_files_are_complete_sorted_and_ignored_absent(tmp_path: Path) -> None:
    repository, report, _ = create_repository(tmp_path)
    write(repository / ".gitignore", "ignored.txt\nignored-dir/\n")
    commit_all(repository, "add ignores")
    write(repository / "zeta.txt", "zeta body\n")
    write(repository / "nested/alpha.txt", "alpha body\n")
    write(repository / "ignored.txt", "do not emit\n")
    write(repository / "ignored-dir/hidden.txt", "hidden body\n")

    bundle = fixed_bundle(repository, report)

    assert bundle.index("nested/alpha.txt") < bundle.index("zeta.txt")
    assert "alpha body" in bundle
    assert "zeta body" in bundle
    assert "ignored.txt" not in bundle
    assert "do not emit" not in bundle
    assert "hidden body" not in bundle


def test_non_ascii_path_is_preserved(tmp_path: Path) -> None:
    repository, report, _ = create_repository(tmp_path)
    write(repository / "заметка.md", "полное содержимое\n")

    bundle = fixed_bundle(repository, report)

    assert "заметка.md" in bundle
    assert "полное содержимое" in bundle


def test_in_repository_untracked_report_payload_is_emitted_once(tmp_path: Path) -> None:
    repository, _, _ = create_repository(tmp_path)
    report = repository / "handoff.md"
    marker = "unique-report-payload-marker"
    write(report, f"# Report\n\n{marker}\n")

    bundle = fixed_bundle(repository, report)

    assert bundle.count(marker) == 1
    assert "completion report + untracked file" in bundle
    assert "identifies both roles" in bundle
    manifest_line = next(line for line in bundle.splitlines() if line.startswith("handoff.md\t"))
    assert "complete untracked content,explicit completion report" in manifest_line


@pytest.mark.parametrize(
    ("kind", "expected"),
    (
        ("symlink", "symlink"),
        ("binary", "NUL bytes"),
        ("invalid_utf8", "valid UTF-8"),
        ("fifo", "regular file"),
        ("oversized", "maximum"),
    ),
)
def test_unsupported_untracked_evidence_is_rejected(
    tmp_path: Path, kind: str, expected: str
) -> None:
    repository, report, _ = create_repository(tmp_path)
    target = repository / "unsafe-evidence.txt"
    if kind == "symlink":
        os.symlink("tracked.txt", target)
    elif kind == "binary":
        write(target, b"binary\0content")
    elif kind == "invalid_utf8":
        write(target, b"\xff\xfe")
    elif kind == "fifo":
        os.mkfifo(target)
    else:
        with target.open("wb") as output:
            output.truncate(review_bundle.MAX_EVIDENCE_BYTES + 1)

    result = invoke(repository, report)

    assert result.returncode != 0
    assert result.stdout == ""
    assert expected in result.stderr


def test_secret_like_path_is_rejected_but_tokenizer_is_allowed(tmp_path: Path) -> None:
    repository, report, _ = create_repository(tmp_path)
    write(repository / "auth-token.txt", "unsafe name\n")

    rejected = invoke(repository, report)

    assert rejected.returncode != 0
    assert rejected.stdout == ""
    assert "secret-like" in rejected.stderr
    (repository / "auth-token.txt").unlink()
    write(repository / "tokenizer.py", "class Tokenizer: pass\n")
    allowed = invoke(repository, report)
    assert allowed.returncode == 0, allowed.stderr
    assert "tokenizer.py" in allowed.stdout


def test_private_key_content_is_rejected(tmp_path: Path) -> None:
    repository, report, _ = create_repository(tmp_path)
    write(
        repository / "ordinary.txt",
        "-----BEGIN " + "PRIVATE KEY-----\nnot-a-real-key\n",
    )

    result = invoke(repository, report)

    assert result.returncode != 0
    assert result.stdout == ""
    assert "private-key header" in result.stderr


def test_ignored_in_repository_report_is_rejected(tmp_path: Path) -> None:
    repository, _, _ = create_repository(tmp_path)
    write(repository / ".gitignore", "handoff.md\n")
    commit_all(repository, "ignore reports")
    report = repository / "handoff.md"
    write(report, REPORT_TEXT)

    result = invoke(repository, report)

    assert result.returncode != 0
    assert result.stdout == ""
    assert "inside the repository is ignored" in result.stderr


@pytest.mark.parametrize(
    ("kind", "expected"),
    (
        ("missing", "cannot be read"),
        ("symlink", "symlink"),
        ("binary", "NUL bytes"),
        ("invalid_utf8", "valid UTF-8"),
    ),
)
def test_missing_or_unsupported_completion_report_is_rejected(
    tmp_path: Path, kind: str, expected: str
) -> None:
    repository, report, _ = create_repository(tmp_path)
    if kind == "missing":
        report.unlink()
    elif kind == "symlink":
        report.unlink()
        os.symlink(repository / "tracked.txt", report)
    elif kind == "binary":
        write(report, b"report\0body")
    else:
        write(report, b"\xff\xfe")

    result = invoke(repository, report)

    assert result.returncode != 0
    assert result.stdout == ""
    assert expected in result.stderr


def test_changed_tracked_path_matching_ignore_rule_is_rejected(tmp_path: Path) -> None:
    repository, report, _ = create_repository(tmp_path)
    write(repository / "generated.log", "base\n")
    commit_all(repository, "track log fixture")
    write(repository / ".gitignore", "*.log\n")
    commit_all(repository, "ignore log files")
    write(repository / "generated.log", "changed\n")

    result = invoke(repository, report)

    assert result.returncode != 0
    assert "matches an ignore rule" in result.stderr


def test_tracked_binary_change_is_rejected(tmp_path: Path) -> None:
    repository, report, _ = create_repository(tmp_path)
    write(repository / "binary.dat", b"base\0data")
    commit_all(repository, "add binary")
    write(repository / "binary.dat", b"changed\0data")

    result = invoke(repository, report)

    assert result.returncode != 0
    assert result.stdout == ""
    assert "tracked binary evidence" in result.stderr


def test_tracked_symlink_change_is_rejected(tmp_path: Path) -> None:
    repository, report, _ = create_repository(tmp_path)
    os.symlink("tracked.txt", repository / "link.txt")
    git(repository, "add", "link.txt")

    result = invoke(repository, report)

    assert result.returncode != 0
    assert result.stdout == ""
    assert "not a regular Git blob" in result.stderr


def test_changed_submodule_is_rejected(tmp_path: Path) -> None:
    repository, report, _ = create_repository(tmp_path)
    source = tmp_path / "submodule-source"
    source.mkdir()
    git(source, "init", "-b", "main")
    git(source, "config", "user.email", "tests@example.com")
    git(source, "config", "user.name", "Submodule Tests")
    write(source / "value.txt", "one\n")
    commit_all(source, "one")
    git(
        repository,
        "-c",
        "protocol.file.allow=always",
        "submodule",
        "add",
        str(source),
        "vendor/example",
    )
    commit_all(repository, "add submodule")
    write(source / "value.txt", "two\n")
    commit_all(source, "two")
    git(repository / "vendor/example", "fetch")
    git(repository / "vendor/example", "checkout", "FETCH_HEAD")

    result = invoke(repository, report)

    assert result.returncode != 0
    assert result.stdout == ""
    assert "not a regular Git blob" in result.stderr


def test_per_file_diff_and_bundle_limits_are_enforced(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository, report, _ = create_repository(tmp_path)
    monkeypatch.setattr(review_bundle, "MAX_EVIDENCE_BYTES", len(TASK_TEXT.encode()) + 5)
    write(report, "x" * (review_bundle.MAX_EVIDENCE_BYTES + 1))
    with pytest.raises(ReviewBundleError, match="maximum"):
        fixed_bundle(repository, report)

    write(report, REPORT_TEXT)
    write(repository / "tracked.txt", "base\nlarge change\n")
    monkeypatch.setattr(review_bundle, "MAX_EVIDENCE_BYTES", 1_048_576)
    monkeypatch.setattr(review_bundle, "MAX_TRACKED_DIFF_BYTES", 8)
    with pytest.raises(ReviewBundleError, match="tracked diff"):
        fixed_bundle(repository, report)

    monkeypatch.setattr(review_bundle, "MAX_TRACKED_DIFF_BYTES", 4_194_304)
    monkeypatch.setattr(review_bundle, "MAX_BUNDLE_BYTES", 100)
    with pytest.raises(ReviewBundleError, match="final Markdown bundle"):
        fixed_bundle(repository, report)


def test_errors_leave_stdout_empty_and_command_is_read_only(tmp_path: Path) -> None:
    repository, report, _ = create_repository(tmp_path)
    write(repository / "safe.txt", "safe\n")
    before_status = git(repository, "status", "--porcelain=v1", "--untracked-files=all")
    before_paths = sorted(path.relative_to(repository) for path in repository.rglob("*"))

    success = invoke(repository, report)

    after_status = git(repository, "status", "--porcelain=v1", "--untracked-files=all")
    after_paths = sorted(path.relative_to(repository) for path in repository.rglob("*"))
    assert success.returncode == 0, success.stderr
    assert before_status == after_status
    assert before_paths == after_paths

    write(repository / "unsafe-password.txt", "value\n")
    failure = invoke(repository, report)
    assert failure.returncode != 0
    assert failure.stdout == ""


def test_external_diff_and_textconv_cannot_change_diff(tmp_path: Path) -> None:
    repository, report, _ = create_repository(tmp_path)
    marker = tmp_path / "external-diff-ran"
    external = tmp_path / "external-diff.sh"
    write(external, f"#!/bin/sh\ntouch '{marker}'\nprintf 'INJECTED_EXTERNAL_DIFF\\n'\n")
    os.chmod(external, 0o755)
    write(repository / ".gitattributes", "tracked.txt diff=review\n")
    commit_all(repository, "add textconv fixture")
    git(repository, "config", "diff.review.textconv", str(external))
    git(repository, "config", "diff.external", str(external))
    write(repository / "tracked.txt", "base\nchanged\n")

    bundle = fixed_bundle(repository, report)

    assert not marker.exists()
    assert "INJECTED_EXTERNAL_DIFF" not in bundle
    assert "+changed" in bundle


def test_status_and_changed_file_hashes_match_source_bytes(tmp_path: Path) -> None:
    repository, report, _ = create_repository(tmp_path)
    original = (repository / "tracked.txt").read_bytes()
    current = b"base\nchanged\n"
    untracked = b"new payload\n"
    write(repository / "tracked.txt", current)
    write(repository / "note.md", untracked)
    status_bytes = b"??\tnote.md\n.M\ttracked.txt\n"

    bundle = fixed_bundle(repository, report)

    assert hashlib.sha256(status_bytes).hexdigest() in bundle
    tracked_line = next(
        line for line in bundle.splitlines() if line.startswith("tracked.txt\t")
    )
    assert str(len(current)) in tracked_line
    assert hashlib.sha256(current).hexdigest() in tracked_line
    assert str(len(original)) in tracked_line
    assert hashlib.sha256(original).hexdigest() in tracked_line
    note_line = next(line for line in bundle.splitlines() if line.startswith("note.md\t"))
    assert hashlib.sha256(untracked).hexdigest() in note_line


def test_bundle_structure_integrity_dynamic_fence_and_no_absolute_paths(
    tmp_path: Path,
) -> None:
    repository, report, head = create_repository(tmp_path)
    write(repository / "ticks.md", "before\n``````\nafter\n")

    bundle = fixed_bundle(repository, report)

    required_sections = [
        "# Implementation Review Bundle",
        "## Evidence precedence",
        "## Repository revision",
        "## Complete Git status",
        "## Changed-file manifest",
        "## Evidence manifest",
        "## Committed task specification",
        "## Completion report",
        "## Tracked working-tree diff against HEAD",
        "## Untracked file contents",
        "## Regeneration warning",
    ]
    positions = [bundle.index(section) for section in required_sections]
    assert positions == sorted(positions)
    assert "2026-01-01T00:00:00+00:00" in bundle
    assert "bundler does not independently execute or validate" in bundle
    assert "Separately uploaded files must not silently override" in bundle
    assert "```````text" in bundle
    assert "``````" in bundle
    assert str(repository) not in bundle
    assert str(report) not in bundle
    assert head in bundle
    assert hashlib.sha256(TASK_TEXT.encode()).hexdigest() in bundle
    assert hashlib.sha256(REPORT_TEXT.encode()).hexdigest() in bundle


def test_empty_diff_and_untracked_set_are_explicit(tmp_path: Path) -> None:
    repository, report, _ = create_repository(tmp_path)

    bundle = fixed_bundle(repository, report)

    assert "The working tree is clean." in bundle
    assert "The tracked diff is empty." in bundle
    assert "No non-ignored untracked files were present." in bundle
    assert hashlib.sha256(b"").hexdigest() in bundle


def test_repository_mutation_during_capture_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository, report, _ = create_repository(tmp_path)
    original = review_bundle.capture_snapshot
    calls = 0

    def mutating_snapshot(path: Path):
        nonlocal calls
        calls += 1
        if calls == 2:
            write(repository / "arrived-during-capture.txt", "changed\n")
        return original(path)

    monkeypatch.setattr(review_bundle, "capture_snapshot", mutating_snapshot)

    with pytest.raises(ReviewBundleError, match="repository changed during capture"):
        fixed_bundle(repository, report)


def test_command_requires_repository_root(tmp_path: Path) -> None:
    repository, report, _ = create_repository(tmp_path)
    subdirectory = repository / "subdirectory"
    subdirectory.mkdir()

    result = invoke(subdirectory, report)

    assert result.returncode != 0
    assert result.stdout == ""
    assert "repository root" in result.stderr
