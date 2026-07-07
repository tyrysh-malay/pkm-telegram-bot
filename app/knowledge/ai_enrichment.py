import hashlib
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.db.models import AIEnrichment
from app.db.models import Artifact
from app.db.models import Message
from app.db.session import get_session_factory
from app.knowledge.ai_errors import AIEnrichmentConsistencyError
from app.knowledge.ai_errors import AIEnrichmentSourceError
from app.knowledge.ai_errors import AIEnrichmentTransactionError
from app.knowledge.ai_errors import AIProviderResponseError
from app.knowledge.ai_provider import OPENAI_PROVIDER_NAME
from app.knowledge.ai_provider import PROMPT_VERSION
from app.knowledge.ai_provider import EnrichmentProvider
from app.knowledge.ai_provider import ProviderEnrichmentResult
from app.knowledge.ai_provider import validate_provider_result
from app.knowledge.ai_schema import EnrichmentResult
from app.knowledge.ai_schema import SCHEMA_VERSION
from app.knowledge.enriched_markdown import AIEnrichmentSnapshot
from app.knowledge.enriched_markdown import ENRICHED_ARTIFACT_TYPE
from app.knowledge.enriched_markdown import MessageSnapshot
from app.knowledge.enriched_markdown import RenderedEnrichedNote
from app.knowledge.enriched_markdown import render_enriched_note
from app.knowledge.errors import ArtifactConsistencyError
from app.knowledge.errors import FileConflictError
from app.knowledge.errors import KnowledgeBaseError
from app.knowledge.errors import KnowledgeBaseInvariantError
from app.knowledge.errors import SourceMessageError
from app.knowledge.errors import UnsupportedFileEntryError
from app.knowledge.markdown import ARTIFACT_TYPE
from app.knowledge.markdown import normalize_newlines
from app.knowledge.processing import validate_raw_note_artifact
from app.knowledge.storage import FileState
from app.knowledge.storage import classify_file
from app.knowledge.storage import ensure_exact_file
from app.knowledge.storage import resolve_destination


MAX_SOURCE_BYTES = 65_536
AI_ENRICHMENT_UNIQUENESS_CONSTRAINT = "uq_ai_enrichments_message_id"


@dataclass(frozen=True)
class ValidatedEnrichmentSource:
    message_id: uuid.UUID
    source_artifact_id: uuid.UUID
    created_at: datetime
    source_text: str
    source_content_sha256: str


@dataclass(frozen=True)
class AIEnrichmentResult:
    message_id: uuid.UUID
    source_artifact_id: uuid.UUID
    ai_enrichment_id: uuid.UUID
    enriched_artifact_id: uuid.UUID
    file_path: str
    provider: str
    model: str
    outcome: Literal["created", "reconciled", "existing"]


def canonical_source_text(raw_text: str) -> str:
    return normalize_newlines(raw_text).rstrip("\n")


def _source_digest(source_text: str) -> str:
    return hashlib.sha256(source_text.encode("utf-8")).hexdigest()


def _wrap_source_error(exc: Exception) -> AIEnrichmentSourceError:
    return AIEnrichmentSourceError(str(exc))


async def _validated_source(
    session: AsyncSession,
    message_id: uuid.UUID,
    knowledge_base_root: Path,
    *,
    for_update: bool = False,
) -> ValidatedEnrichmentSource:
    message_statement = select(Message).where(Message.id == message_id)
    if for_update:
        message_statement = message_statement.with_for_update()
    message = await session.scalar(message_statement)
    if message is None:
        raise AIEnrichmentSourceError(f"message {message_id} was not found")
    if message.status != "done":
        raise AIEnrichmentSourceError(
            f"message {message_id} has unsupported status {message.status!r}"
        )

    artifact_statement = select(Artifact).where(
        Artifact.message_id == message_id,
        Artifact.artifact_type == ARTIFACT_TYPE,
    )
    if for_update:
        artifact_statement = artifact_statement.with_for_update()
    artifact = await session.scalar(artifact_statement)
    if artifact is None:
        raise AIEnrichmentSourceError(
            f"message {message_id} is missing raw note Artifact"
        )

    try:
        validate_raw_note_artifact(
            message=message,
            artifact=artifact,
            message_id=message_id,
            knowledge_base_root=knowledge_base_root,
        )
    except (
        SourceMessageError,
        ArtifactConsistencyError,
        KnowledgeBaseError,
        FileConflictError,
        UnsupportedFileEntryError,
    ) as exc:
        raise _wrap_source_error(exc) from exc

    if message.raw_text is None:
        raise AIEnrichmentSourceError(f"message {message_id} has null raw_text")
    source_text = canonical_source_text(message.raw_text)
    if not any(not character.isspace() for character in source_text):
        raise AIEnrichmentSourceError(
            f"message {message_id} canonical source is blank"
        )
    if len(source_text.encode("utf-8")) > MAX_SOURCE_BYTES:
        raise AIEnrichmentSourceError(
            f"message {message_id} canonical source is too large"
        )

    return ValidatedEnrichmentSource(
        message_id=message_id,
        source_artifact_id=artifact.id,
        created_at=message.created_at,
        source_text=source_text,
        source_content_sha256=_source_digest(source_text),
    )


def _validate_metadata(value: str, *, field: str, max_length: int) -> str:
    if not value or not value.strip() or "\0" in value:
        raise AIEnrichmentConsistencyError(f"AIEnrichment has invalid {field}")
    if len(value) > max_length:
        raise AIEnrichmentConsistencyError(f"AIEnrichment {field} is too long")
    return value


def _validate_enrichment_row(
    row: AIEnrichment,
    source: ValidatedEnrichmentSource,
) -> EnrichmentResult:
    if row.message_id != source.message_id:
        raise AIEnrichmentConsistencyError("AIEnrichment message mismatch")
    if row.source_artifact_id != source.source_artifact_id:
        raise AIEnrichmentConsistencyError("AIEnrichment source Artifact mismatch")
    if row.source_content_sha256 != source.source_content_sha256:
        raise AIEnrichmentConsistencyError("AIEnrichment source digest mismatch")
    if row.provider != OPENAI_PROVIDER_NAME:
        raise AIEnrichmentConsistencyError("AIEnrichment provider is unsupported")
    _validate_metadata(row.model, field="model", max_length=255)
    if row.provider_response_id is not None:
        _validate_metadata(
            row.provider_response_id,
            field="provider_response_id",
            max_length=255,
        )
    if row.prompt_version != PROMPT_VERSION:
        raise AIEnrichmentConsistencyError("AIEnrichment prompt version is unsupported")
    if row.schema_version != SCHEMA_VERSION:
        raise AIEnrichmentConsistencyError("AIEnrichment schema version is unsupported")
    try:
        return EnrichmentResult.model_validate(row.result_json)
    except ValidationError as exc:
        raise AIEnrichmentConsistencyError(
            "AIEnrichment result JSON is invalid"
        ) from exc


async def _existing_enrichment(
    session: AsyncSession,
    message_id: uuid.UUID,
    *,
    for_update: bool = False,
) -> AIEnrichment | None:
    statement = select(AIEnrichment).where(AIEnrichment.message_id == message_id)
    if for_update:
        statement = statement.with_for_update()
    return await session.scalar(statement)


def _constraint_name(error: IntegrityError) -> str | None:
    candidates = [error.orig, getattr(error.orig, "__cause__", None)]
    for candidate in candidates:
        name = getattr(candidate, "constraint_name", None)
        if isinstance(name, str):
            return name
    return None


async def _accept_provider_result(
    *,
    message_id: uuid.UUID,
    knowledge_base_root: Path,
    provider_result: ProviderEnrichmentResult,
    source_before_request: ValidatedEnrichmentSource,
    session_factory: async_sessionmaker[AsyncSession],
) -> tuple[AIEnrichment, ValidatedEnrichmentSource, bool]:
    try:
        async with session_factory() as session:
            async with session.begin():
                source = await _validated_source(
                    session,
                    message_id,
                    knowledge_base_root,
                    for_update=True,
                )
                if (
                    source.source_artifact_id
                    != source_before_request.source_artifact_id
                    or source.source_content_sha256
                    != source_before_request.source_content_sha256
                    or source.source_text != source_before_request.source_text
                ):
                    raise AIEnrichmentConsistencyError(
                        "source changed during provider request"
                    )

                existing = await _existing_enrichment(
                    session,
                    message_id,
                    for_update=True,
                )
                if existing is not None:
                    _validate_enrichment_row(existing, source)
                    return existing, source, False

                row = AIEnrichment(
                    message_id=message_id,
                    source_artifact_id=source.source_artifact_id,
                    source_content_sha256=source.source_content_sha256,
                    provider=provider_result.provider,
                    model=provider_result.model,
                    prompt_version=PROMPT_VERSION,
                    schema_version=SCHEMA_VERSION,
                    provider_response_id=provider_result.response_id,
                    result_json=provider_result.enrichment.model_dump(mode="json"),
                )
                session.add(row)
                await session.flush()
                return row, source, True
    except IntegrityError as exc:
        if _constraint_name(exc) != AI_ENRICHMENT_UNIQUENESS_CONSTRAINT:
            raise

    async with session_factory() as session:
        async with session.begin():
            source = await _validated_source(
                session,
                message_id,
                knowledge_base_root,
                for_update=True,
            )
            existing = await _existing_enrichment(session, message_id, for_update=True)
            if existing is None:
                raise AIEnrichmentConsistencyError(
                    "AIEnrichment race did not establish a winner"
                )
            _validate_enrichment_row(existing, source)
            return existing, source, False


def _file_state_or_absent(
    knowledge_base_root: Path,
    rendered: RenderedEnrichedNote,
) -> FileState:
    try:
        _, destination = resolve_destination(
            knowledge_base_root,
            rendered.file_path,
            create_missing=False,
        )
    except KnowledgeBaseInvariantError as exc:
        if "absent" in str(exc):
            return FileState.ABSENT
        raise
    return classify_file(destination, rendered.content)


def _validate_enriched_artifact(
    artifact: Artifact,
    *,
    message_id: uuid.UUID,
    rendered: RenderedEnrichedNote,
) -> None:
    expected = {
        "message_id": message_id,
        "artifact_type": ENRICHED_ARTIFACT_TYPE,
        "title": rendered.title,
        "slug": rendered.slug,
        "file_path": rendered.file_path,
    }
    mismatches = [
        field for field, value in expected.items() if getattr(artifact, field) != value
    ]
    if mismatches:
        raise AIEnrichmentConsistencyError(
            "enriched Artifact metadata mismatch: " + ", ".join(mismatches)
        )


async def _materialize_enriched_artifact(
    *,
    message_id: uuid.UUID,
    knowledge_base_root: Path,
    session_factory: async_sessionmaker[AsyncSession],
    created_enrichment: bool,
) -> AIEnrichmentResult:
    async with session_factory() as session:
        async with session.begin():
            source = await _validated_source(
                session,
                message_id,
                knowledge_base_root,
                for_update=True,
            )
            enrichment = await session.scalar(
                select(AIEnrichment)
                .where(AIEnrichment.message_id == message_id)
                .with_for_update()
            )
            if enrichment is None:
                raise AIEnrichmentConsistencyError("AIEnrichment is missing")

            result = _validate_enrichment_row(enrichment, source)
            rendered = render_enriched_note(
                message=MessageSnapshot(id=message_id, created_at=source.created_at),
                source_artifact_id=source.source_artifact_id,
                enrichment=AIEnrichmentSnapshot(
                    id=enrichment.id,
                    created_at=enrichment.created_at,
                    source_content_sha256=enrichment.source_content_sha256,
                    provider=enrichment.provider,
                    model=enrichment.model,
                    response_id=enrichment.provider_response_id,
                    prompt_version=enrichment.prompt_version,
                    schema_version=enrichment.schema_version,
                ),
                result=result,
            )

            artifact = await session.scalar(
                select(Artifact)
                .where(
                    Artifact.message_id == message_id,
                    Artifact.artifact_type == ENRICHED_ARTIFACT_TYPE,
                )
                .with_for_update()
            )
            if artifact is not None:
                _validate_enriched_artifact(
                    artifact,
                    message_id=message_id,
                    rendered=rendered,
                )

            path_owner = await session.scalar(
                select(Artifact).where(Artifact.file_path == rendered.file_path)
            )
            if path_owner is not None and (
                artifact is None or path_owner.id != artifact.id
            ):
                raise AIEnrichmentConsistencyError(
                    f"enriched Artifact path {rendered.file_path} is owned"
                )

            file_state = _file_state_or_absent(knowledge_base_root, rendered)
            exact_existing_state = artifact is not None and file_state is FileState.EXACT
            ensure_exact_file(
                knowledge_base_root,
                rendered.file_path,
                rendered.content,
            )

            if artifact is None:
                artifact = Artifact(
                    message_id=message_id,
                    artifact_type=ENRICHED_ARTIFACT_TYPE,
                    title=rendered.title,
                    slug=rendered.slug,
                    file_path=rendered.file_path,
                )
                session.add(artifact)
                await session.flush()

            if created_enrichment:
                outcome: Literal["created", "reconciled", "existing"] = "created"
            elif exact_existing_state:
                outcome = "existing"
            else:
                outcome = "reconciled"

            return AIEnrichmentResult(
                message_id=message_id,
                source_artifact_id=source.source_artifact_id,
                ai_enrichment_id=enrichment.id,
                enriched_artifact_id=artifact.id,
                file_path=rendered.file_path,
                provider=enrichment.provider,
                model=enrichment.model,
                outcome=outcome,
            )


async def enrich_text_message(
    *,
    message_id: uuid.UUID,
    knowledge_base_root: Path,
    provider: EnrichmentProvider,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
) -> AIEnrichmentResult:
    factory = session_factory or get_session_factory()
    existing_found = False

    try:
        async with factory() as session:
            if session.in_transaction():
                raise AIEnrichmentTransactionError(
                    "initial enrichment session must not start in a transaction"
                )
            async with session.begin():
                source = await _validated_source(
                    session,
                    message_id,
                    knowledge_base_root,
                )
                existing = await _existing_enrichment(session, message_id)
                if existing is not None:
                    _validate_enrichment_row(existing, source)
                    existing_found = True
    except AIEnrichmentSourceError:
        raise

    if existing_found:
        return await _materialize_enriched_artifact(
            message_id=message_id,
            knowledge_base_root=knowledge_base_root,
            session_factory=factory,
            created_enrichment=False,
        )

    provider_result = validate_provider_result(await provider.enrich(source.source_text))
    accepted, _accepted_source, created = await _accept_provider_result(
        message_id=message_id,
        knowledge_base_root=knowledge_base_root,
        provider_result=provider_result,
        source_before_request=source,
        session_factory=factory,
    )
    if accepted.provider != OPENAI_PROVIDER_NAME:
        raise AIProviderResponseError("accepted provider is unsupported")

    return await _materialize_enriched_artifact(
        message_id=message_id,
        knowledge_base_root=knowledge_base_root,
        session_factory=factory,
        created_enrichment=created,
    )
