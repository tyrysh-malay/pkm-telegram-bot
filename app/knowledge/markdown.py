import json
import unicodedata
import uuid
from dataclasses import dataclass
from datetime import datetime
from datetime import timezone

from app.knowledge.errors import SourceMessageError


FORMAT_VERSION = 1
ARTIFACT_TYPE = "note"


@dataclass(frozen=True)
class RenderedNote:
    title: str
    slug: str
    file_path: str
    content: bytes


def normalize_newlines(value: str) -> str:
    return value.replace("\r\n", "\n").replace("\r", "\n")


def derive_title(normalized_text: str) -> str:
    for line in normalized_text.split("\n"):
        if any(not character.isspace() for character in line):
            stripped = line.strip()
            words = stripped.split()
            return " ".join(words)[:80]

    return "Untitled note"


def derive_slug(title: str) -> str:
    normalized = unicodedata.normalize("NFKC", title).casefold()
    parts: list[str] = []
    separating = False

    for character in normalized:
        if character.isalnum():
            parts.append(character)
            separating = False
        elif parts and not separating:
            parts.append("-")
            separating = True

    slug = "".join(parts).strip("-")[:80].rstrip("-")
    return slug or "note"


def artifact_file_path(message_id: uuid.UUID, created_at: datetime) -> str:
    if created_at.tzinfo is None or created_at.utcoffset() is None:
        raise SourceMessageError(
            f"message {message_id} has a naive created_at timestamp"
        )

    utc_date = created_at.astimezone(timezone.utc).date().isoformat()
    return f"inbox/{utc_date}--{str(message_id)}.md"


def captured_at(created_at: datetime, message_id: uuid.UUID) -> str:
    if created_at.tzinfo is None or created_at.utcoffset() is None:
        raise SourceMessageError(
            f"message {message_id} has a naive created_at timestamp"
        )

    return created_at.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _quoted(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def render_text_note(
    *,
    message_id: uuid.UUID,
    telegram_chat_id: int,
    telegram_message_id: int,
    created_at: datetime,
    raw_text: str,
) -> RenderedNote:
    if "\0" in raw_text:
        raise SourceMessageError(f"message {message_id} raw_text contains NUL")

    normalized_text = normalize_newlines(raw_text)
    title = derive_title(normalized_text)
    slug = derive_slug(title)
    file_path = artifact_file_path(message_id, created_at)
    timestamp = captured_at(created_at, message_id)
    body = normalized_text.rstrip("\n")

    lines = [
        "---",
        f"format_version: {FORMAT_VERSION}",
        f"artifact_type: {_quoted(ARTIFACT_TYPE)}",
        f"source: {_quoted('telegram')}",
        f"source_message_id: {_quoted(str(message_id))}",
        f"telegram_chat_id: {telegram_chat_id}",
        f"telegram_message_id: {telegram_message_id}",
        f"captured_at: {_quoted(timestamp)}",
        f"title: {_quoted(title)}",
        f"slug: {_quoted(slug)}",
        "tags: []",
        "topics: []",
        "---",
        "",
        f"# {title}",
        "",
        body,
    ]
    content = ("\n".join(lines) + "\n").encode("utf-8")

    return RenderedNote(
        title=title,
        slug=slug,
        file_path=file_path,
        content=content,
    )
