import uuid
from datetime import datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Artifact
from app.db.models import Message
from app.knowledge.errors import ArtifactConsistencyError
from app.knowledge.errors import DuplicateArtifactRaceError
from app.knowledge.errors import FileConflictError
from app.knowledge.errors import KnowledgeBaseInvariantError
from app.knowledge.errors import ProcessingTransactionError
from app.knowledge.errors import SourceMessageError
from app.knowledge.errors import UnsupportedFileEntryError
from app.knowledge.markdown import ARTIFACT_TYPE
from app.knowledge.markdown import RenderedNote
from app.knowledge.markdown import render_text_note
from app.knowledge.storage import FileState
from app.knowledge.storage import classify_file
from app.knowledge.storage import ensure_exact_file
from app.knowledge.storage import resolve_destination


ARTIFACT_UNIQUENESS_CONSTRAINTS = {
    "uq_artifacts_message_id_artifact_type",
    "uq_artifacts_file_path",
}


def _validate_source_message(message: Message, message_id: uuid.UUID) -> RenderedNote:
    if message.input_type != "text":
        raise SourceMessageError(
            f"message {message_id} has unsupported input_type {message.input_type!r}"
        )
    if message.raw_text is None:
        raise SourceMessageError(f"message {message_id} has null raw_text")
    if message.status not in {"received", "done"}:
        raise SourceMessageError(
            f"message {message_id} has unsupported status {message.status!r}"
        )
    if (
        not isinstance(message.created_at, datetime)
        or message.created_at.tzinfo is None
        or message.created_at.utcoffset() is None
    ):
        raise SourceMessageError(
            f"message {message_id} has a naive created_at timestamp"
        )
    if (
        isinstance(message.telegram_chat_id, bool)
        or not isinstance(message.telegram_chat_id, int)
        or isinstance(message.telegram_message_id, bool)
        or not isinstance(message.telegram_message_id, int)
    ):
        raise SourceMessageError(
            f"message {message_id} has invalid Telegram source identifiers"
        )

    return render_text_note(
        message_id=message.id,
        telegram_chat_id=message.telegram_chat_id,
        telegram_message_id=message.telegram_message_id,
        created_at=message.created_at,
        raw_text=message.raw_text,
    )


def _validate_artifact(
    artifact: Artifact,
    message_id: uuid.UUID,
    expected: RenderedNote,
) -> None:
    expected_metadata = {
        "message_id": message_id,
        "artifact_type": ARTIFACT_TYPE,
        "title": expected.title,
        "slug": expected.slug,
        "file_path": expected.file_path,
    }
    mismatches = [
        field
        for field, value in expected_metadata.items()
        if getattr(artifact, field) != value
    ]
    if mismatches:
        raise ArtifactConsistencyError(
            f"message {message_id} artifact metadata mismatch: {', '.join(mismatches)}"
        )


def validate_raw_note_artifact(
    *,
    message: Message,
    artifact: Artifact,
    message_id: uuid.UUID,
    knowledge_base_root: Path,
) -> tuple[RenderedNote, bytes]:
    expected = _validate_source_message(message, message_id)
    _validate_artifact(artifact, message_id, expected)

    _, destination = resolve_destination(
        knowledge_base_root,
        artifact.file_path,
        create_missing=False,
    )
    state = classify_file(destination, expected.content)
    if state is FileState.ABSENT:
        raise KnowledgeBaseInvariantError(
            f"artifact file is absent at {artifact.file_path}"
        )
    if state is FileState.CONFLICTING:
        raise FileConflictError(
            f"conflicting file exists at artifact path {artifact.file_path}"
        )
    if state is FileState.UNSUPPORTED:
        raise UnsupportedFileEntryError(
            "unsupported filesystem entry exists at artifact path "
            f"{artifact.file_path}"
        )

    return expected, expected.content


async def validate_existing_artifact(
    session: AsyncSession,
    artifact_id: uuid.UUID,
    knowledge_base_root: Path,
    *,
    for_update: bool = False,
) -> tuple[Artifact, bytes]:
    statement = select(Artifact).where(Artifact.id == artifact_id)
    if for_update:
        statement = statement.with_for_update()
    artifact = await session.scalar(statement)
    if artifact is None:
        raise ArtifactConsistencyError(f"artifact {artifact_id} was not found")

    message = await session.scalar(
        select(Message).where(Message.id == artifact.message_id)
    )
    if message is None:
        raise SourceMessageError(
            f"artifact {artifact_id} source message {artifact.message_id} was not found"
        )

    _, content = validate_raw_note_artifact(
        message=message,
        artifact=artifact,
        message_id=message.id,
        knowledge_base_root=knowledge_base_root,
    )

    return artifact, content


async def _process_attempt(
    session: AsyncSession,
    message_id: uuid.UUID,
    knowledge_base_root: Path,
    *,
    reconciliation_only: bool,
) -> Artifact:
    message = await session.scalar(
        select(Message).where(Message.id == message_id).with_for_update()
    )
    if message is None:
        raise SourceMessageError(f"message {message_id} was not found")

    expected = _validate_source_message(message, message_id)
    artifact = await session.scalar(
        select(Artifact).where(
            Artifact.message_id == message_id,
            Artifact.artifact_type == ARTIFACT_TYPE,
        )
    )

    if artifact is not None:
        _validate_artifact(artifact, message_id, expected)

    path_owner = await session.scalar(
        select(Artifact).where(Artifact.file_path == expected.file_path)
    )
    if path_owner is not None and (
        artifact is None or path_owner.id != artifact.id
    ):
        raise ArtifactConsistencyError(
            f"artifact path {expected.file_path} is owned by artifact {path_owner.id}"
        )

    if reconciliation_only and artifact is None:
        raise DuplicateArtifactRaceError(
            f"message {message_id} duplicate race did not establish an artifact"
        )

    ensure_exact_file(
        knowledge_base_root,
        expected.file_path,
        expected.content,
    )

    if artifact is None:
        artifact = Artifact(
            message_id=message_id,
            artifact_type=ARTIFACT_TYPE,
            title=expected.title,
            slug=expected.slug,
            file_path=expected.file_path,
        )
        session.add(artifact)
        await session.flush()

    if message.status != "done":
        message.status = "done"

    return artifact


def _constraint_name(error: IntegrityError) -> str | None:
    candidates = [error.orig, getattr(error.orig, "__cause__", None)]
    for candidate in candidates:
        name = getattr(candidate, "constraint_name", None)
        if isinstance(name, str):
            return name
    return None


def _is_expected_artifact_uniqueness_error(error: IntegrityError) -> bool:
    return _constraint_name(error) in ARTIFACT_UNIQUENESS_CONSTRAINTS


async def process_text_message(
    session: AsyncSession,
    message_id: uuid.UUID,
    knowledge_base_root: Path,
) -> Artifact:
    if session.in_transaction():
        raise ProcessingTransactionError(
            "process_text_message requires a session without an active transaction"
        )

    try:
        artifact = await _process_attempt(
            session,
            message_id,
            knowledge_base_root,
            reconciliation_only=False,
        )
        await session.commit()
        return artifact
    except IntegrityError as exc:
        await session.rollback()
        if not _is_expected_artifact_uniqueness_error(exc):
            raise
    except Exception:
        await session.rollback()
        raise

    try:
        artifact = await _process_attempt(
            session,
            message_id,
            knowledge_base_root,
            reconciliation_only=True,
        )
        await session.commit()
        return artifact
    except Exception:
        await session.rollback()
        raise
