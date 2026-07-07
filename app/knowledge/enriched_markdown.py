import json
import uuid
from dataclasses import dataclass
from datetime import datetime
from datetime import timezone

from app.knowledge.ai_provider import OPENAI_PROVIDER_NAME
from app.knowledge.ai_provider import PROMPT_VERSION
from app.knowledge.ai_schema import EnrichmentResult
from app.knowledge.ai_schema import SCHEMA_VERSION
from app.knowledge.errors import SourceMessageError
from app.knowledge.markdown import captured_at
from app.knowledge.markdown import derive_slug


ENRICHED_MARKDOWN_FORMAT_VERSION = 1
ENRICHED_ARTIFACT_TYPE = "enriched_note"


@dataclass(frozen=True)
class MessageSnapshot:
    id: uuid.UUID
    created_at: datetime


@dataclass(frozen=True)
class AIEnrichmentSnapshot:
    id: uuid.UUID
    created_at: datetime
    source_content_sha256: str
    provider: str
    model: str
    response_id: str | None
    prompt_version: int
    schema_version: int


@dataclass(frozen=True)
class RenderedEnrichedNote:
    title: str
    slug: str
    file_path: str
    content: bytes


def enriched_artifact_file_path(message_id: uuid.UUID, created_at: datetime) -> str:
    if created_at.tzinfo is None or created_at.utcoffset() is None:
        raise SourceMessageError(
            f"message {message_id} has a naive created_at timestamp"
        )
    utc_date = created_at.astimezone(timezone.utc).date().isoformat()
    return f"processed/{utc_date}--{str(message_id)}.md"


def _quoted(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _timestamp(value: datetime, *, owner: str) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise SourceMessageError(f"{owner} has a naive created_at timestamp")
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _list_body(values: list[str]) -> list[str]:
    if not values:
        return ["_None._"]
    return [f"- {value}" for value in values]


def render_enriched_note(
    *,
    message: MessageSnapshot,
    source_artifact_id: uuid.UUID,
    enrichment: AIEnrichmentSnapshot,
    result: EnrichmentResult,
) -> RenderedEnrichedNote:
    title = result.title
    slug = derive_slug(title)
    file_path = enriched_artifact_file_path(message.id, message.created_at)

    provider_response_id = (
        "null" if enrichment.response_id is None else _quoted(enrichment.response_id)
    )
    tags = json.dumps(result.tags, ensure_ascii=False)
    lines = [
        "---",
        f"format_version: {ENRICHED_MARKDOWN_FORMAT_VERSION}",
        f"artifact_type: {_quoted(ENRICHED_ARTIFACT_TYPE)}",
        f"source: {_quoted('telegram')}",
        f"source_message_id: {_quoted(str(message.id))}",
        f"source_artifact_id: {_quoted(str(source_artifact_id))}",
        f"source_content_sha256: {_quoted(enrichment.source_content_sha256)}",
        f"ai_enrichment_id: {_quoted(str(enrichment.id))}",
        f"captured_at: {_quoted(captured_at(message.created_at, message.id))}",
        f"enriched_at: {_quoted(_timestamp(enrichment.created_at, owner='enrichment'))}",
        f"ai_provider: {_quoted(OPENAI_PROVIDER_NAME)}",
        f"ai_model: {_quoted(enrichment.model)}",
        f"provider_response_id: {provider_response_id}",
        f"prompt_version: {PROMPT_VERSION}",
        f"schema_version: {SCHEMA_VERSION}",
        f"title: {_quoted(title)}",
        f"slug: {_quoted(slug)}",
        f"tags: {tags}",
        "---",
        "",
        f"# {title}",
        "",
        "## Summary",
        "",
        result.summary,
        "",
        "## Key points",
        "",
        *_list_body(result.key_points),
        "",
        "## Action items",
        "",
        *_list_body(result.action_items),
    ]
    return RenderedEnrichedNote(
        title=title,
        slug=slug,
        file_path=file_path,
        content=("\n".join(lines) + "\n").encode("utf-8"),
    )
