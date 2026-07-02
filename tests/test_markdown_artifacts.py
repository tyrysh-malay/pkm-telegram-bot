import errno
import os
import uuid
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from pathlib import Path

import pytest

from app.knowledge.errors import AtomicPublicationError
from app.knowledge.errors import FileConflictError
from app.knowledge.errors import KnowledgeBaseError
from app.knowledge.errors import UnsupportedFileEntryError
from app.knowledge.markdown import artifact_file_path
from app.knowledge.markdown import derive_slug
from app.knowledge.markdown import derive_title
from app.knowledge.markdown import normalize_newlines
from app.knowledge.markdown import render_text_note
from app.knowledge.storage import ensure_exact_file
from app.knowledge.storage import publish_no_replace


MESSAGE_ID = uuid.UUID("123e4567-e89b-12d3-a456-426614174000")


def render(raw_text: str = 'Hello,   "World"!\\path\r\nsecond line\r'):
    return render_text_note(
        message_id=MESSAGE_ID,
        telegram_chat_id=-123,
        telegram_message_id=456,
        created_at=datetime(
            2026,
            7,
            2,
            15,
            34,
            56,
            123,
            tzinfo=timezone(timedelta(hours=3)),
        ),
        raw_text=raw_text,
    )


def test_complete_markdown_contract_is_exact_utf8_lf_bytes() -> None:
    note = render()

    assert note.content == (
        '---\n'
        'format_version: 1\n'
        'artifact_type: "note"\n'
        'source: "telegram"\n'
        'source_message_id: "123e4567-e89b-12d3-a456-426614174000"\n'
        'telegram_chat_id: -123\n'
        'telegram_message_id: 456\n'
        'captured_at: "2026-07-02T12:34:56.000123Z"\n'
        'title: "Hello, \\"World\\"!\\\\path"\n'
        'slug: "hello-world-path"\n'
        'tags: []\n'
        'topics: []\n'
        '---\n'
        '\n'
        '# Hello, "World"!\\path\n'
        '\n'
        'Hello,   "World"!\\path\n'
        'second line\n'
    ).encode("utf-8")
    assert note.file_path == (
        "inbox/2026-07-02--123e4567-e89b-12d3-a456-426614174000.md"
    )
    assert b"\r" not in note.content
    assert note.content.endswith(b"\n")
    assert not note.content.endswith(b"\n\n")


def test_body_preservation_and_trailing_newline_normalization() -> None:
    note = render("\r\n  title  \t\rbody trailing  \r\n\r\n")

    assert note.title == "title"
    assert note.content.endswith(b"\n  title  \t\nbody trailing  \n")
    assert note.content.count(b"body trailing  ") == 1


def test_non_ascii_content_is_not_ascii_escaped() -> None:
    note = render("Привет,   мир!\n正文")

    assert note.title == "Привет, мир!"
    assert note.slug == "привет-мир"
    assert "Привет".encode() in note.content
    assert b"\\u" not in note.content


def test_renderer_excludes_mutable_and_current_values() -> None:
    content = render("A note").content.decode()

    for excluded in (
        "artifact_id",
        "username",
        "summary",
        "created_at",
        "updated_at",
        "git_commit",
    ):
        assert excluded not in content


@pytest.mark.parametrize(
    ("source", "expected"),
    (
        ("\n\t\n First\t\u2003title \nSecond", "First title"),
        ("   \n\t", "Untitled note"),
        ("# *Markdown* [title]", "# *Markdown* [title]"),
        ('  "quoted" \\ title  ', '"quoted" \\ title'),
        ("x" * 81, "x" * 80),
    ),
)
def test_title_algorithm(source: str, expected: str) -> None:
    assert derive_title(normalize_newlines(source)) == expected
    assert not expected.endswith("…")


@pytest.mark.parametrize(
    ("title", "expected"),
    (
        ("Hello,   World!", "hello-world"),
        ("Привет, мир!", "привет-мир"),
        ("１２ Cats", "12-cats"),
        ("A___B---C", "a-b-c"),
        ("Cafe\u0301", "café"),
        ("123", "123"),
        ("!!!", "note"),
        ("界" * 81, "界" * 80),
        ("a" * 79 + " ! b", "a" * 79),
    ),
)
def test_slug_algorithm(title: str, expected: str) -> None:
    assert derive_slug(title) == expected
    assert derive_slug(title) == expected


def test_path_uses_utc_source_date_and_is_title_independent() -> None:
    created_at = datetime(
        2026,
        7,
        3,
        1,
        tzinfo=timezone(timedelta(hours=3)),
    )

    assert artifact_file_path(MESSAGE_ID, created_at) == (
        "inbox/2026-07-02--123e4567-e89b-12d3-a456-426614174000.md"
    )
    assert render("one").file_path == render("different title").file_path


def test_storage_publishes_exact_bytes_without_temporary_files(tmp_path: Path) -> None:
    note = render()

    destination = ensure_exact_file(tmp_path, note.file_path, note.content)

    assert destination.read_bytes() == note.content
    assert list(destination.parent.glob("*.tmp")) == []
    assert list(destination.parent.glob(".*.tmp")) == []


def test_storage_preserves_conflicting_file(tmp_path: Path) -> None:
    note = render()
    destination = tmp_path / note.file_path
    destination.parent.mkdir()
    destination.write_bytes(b"conflict\r\n")

    with pytest.raises(FileConflictError):
        ensure_exact_file(tmp_path, note.file_path, note.content)

    assert destination.read_bytes() == b"conflict\r\n"


@pytest.mark.parametrize("entry_kind", ("symlink", "directory", "fifo"))
def test_storage_rejects_unsupported_final_entries(
    tmp_path: Path, entry_kind: str
) -> None:
    note = render()
    destination = tmp_path / note.file_path
    destination.parent.mkdir()
    if entry_kind == "symlink":
        target = tmp_path / "target"
        target.write_bytes(note.content)
        destination.symlink_to(target)
    elif entry_kind == "directory":
        destination.mkdir()
    else:
        os.mkfifo(destination)

    with pytest.raises(UnsupportedFileEntryError):
        ensure_exact_file(tmp_path, note.file_path, note.content)


def test_storage_rejects_symlinked_parent(tmp_path: Path) -> None:
    note = render()
    outside = tmp_path / "outside"
    outside.mkdir()
    (tmp_path / "inbox").symlink_to(outside, target_is_directory=True)

    with pytest.raises(KnowledgeBaseError, match="safe directory"):
        ensure_exact_file(tmp_path, note.file_path, note.content)

    assert list(outside.iterdir()) == []


@pytest.mark.parametrize(
    "relative_path",
    ("/absolute.md", "../escape.md", "inbox/../escape.md", "inbox\\file.md"),
)
def test_storage_rejects_unsafe_relative_paths(
    tmp_path: Path, relative_path: str
) -> None:
    with pytest.raises(KnowledgeBaseError, match="unsafe relative"):
        ensure_exact_file(tmp_path, relative_path, b"content")


def test_write_failure_cleans_temporary_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    note = render()

    def fail_write(_descriptor: int, _content: memoryview) -> int:
        raise OSError("simulated write failure")

    monkeypatch.setattr("app.knowledge.storage.os.write", fail_write)

    with pytest.raises(KnowledgeBaseError, match="cannot publish"):
        ensure_exact_file(tmp_path, note.file_path, note.content)

    assert list((tmp_path / "inbox").iterdir()) == []


def test_unsupported_publication_cleans_temporary_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    note = render()

    def fail_link(*_args, **_kwargs) -> None:
        raise OSError(errno.EOPNOTSUPP, "unsupported")

    monkeypatch.setattr("app.knowledge.storage.os.link", fail_link)

    with pytest.raises(AtomicPublicationError):
        ensure_exact_file(tmp_path, note.file_path, note.content)

    assert list((tmp_path / "inbox").iterdir()) == []


def test_publication_error_remains_primary_when_temporary_cleanup_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    note = render()
    destination = tmp_path / note.file_path
    destination.parent.mkdir()

    def fail_directory_flush(_directory: Path) -> None:
        raise OSError("simulated publication failure")

    def fail_temporary_cleanup(self: Path, missing_ok: bool = False) -> None:
        raise PermissionError("simulated cleanup failure")

    monkeypatch.setattr(
        "app.knowledge.storage._flush_directory", fail_directory_flush
    )
    monkeypatch.setattr(Path, "unlink", fail_temporary_cleanup)

    with pytest.raises(OSError, match="simulated publication failure") as caught:
        publish_no_replace(destination, note.file_path, note.content)

    assert any(
        "temporary artifact cleanup also failed" in note
        and "simulated cleanup failure" in note
        for note in caught.value.__notes__
    )
    assert destination.read_bytes() == note.content
    assert len(list(destination.parent.glob(".*.tmp"))) == 1


@pytest.mark.parametrize("concurrent_content", ("exact", "conflicting"))
def test_concurrent_final_path_is_reconciled_without_overwrite(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    concurrent_content: str,
) -> None:
    note = render()
    real_link = os.link

    def racing_link(source, destination, **_kwargs) -> None:
        content = note.content if concurrent_content == "exact" else b"other"
        Path(destination).write_bytes(content)
        raise FileExistsError

    monkeypatch.setattr("app.knowledge.storage.os.link", racing_link)

    if concurrent_content == "exact":
        destination = ensure_exact_file(tmp_path, note.file_path, note.content)
        assert destination.read_bytes() == note.content
    else:
        with pytest.raises(FileConflictError):
            ensure_exact_file(tmp_path, note.file_path, note.content)
        assert (tmp_path / note.file_path).read_bytes() == b"other"

    monkeypatch.setattr("app.knowledge.storage.os.link", real_link)
    assert list((tmp_path / "inbox").glob(".*.tmp")) == []
