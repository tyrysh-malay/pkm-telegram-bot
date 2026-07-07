import argparse
import asyncio
import sys
import uuid
from collections.abc import Sequence

from sqlalchemy.exc import SQLAlchemyError

from app.db.session import get_session_factory
from app.knowledge.ai_enrichment import enrich_text_message
from app.knowledge.ai_errors import AIEnrichmentError
from app.knowledge.errors import KnowledgeArtifactError
from app.knowledge.openai_provider import OpenAIEnrichmentProvider
from app.settings import get_settings


def _message_id(value: str) -> uuid.UUID:
    try:
        message_id = uuid.UUID(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a canonical UUID") from exc
    if str(message_id) != value:
        raise argparse.ArgumentTypeError("must be a canonical UUID")
    return message_id


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Enrich one completed text message through a manual AI boundary."
    )
    parser.add_argument("--message-id", required=True, type=_message_id)
    return parser


async def _run(message_id: uuid.UUID) -> None:
    settings = get_settings()
    result = await enrich_text_message(
        message_id=message_id,
        knowledge_base_root=settings.knowledge_base_path,
        provider=OpenAIEnrichmentProvider(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
        ),
        session_factory=get_session_factory(),
    )

    print(f"message_id: {result.message_id}")
    print(f"source_artifact_id: {result.source_artifact_id}")
    print(f"ai_enrichment_id: {result.ai_enrichment_id}")
    print(f"enriched_artifact_id: {result.enriched_artifact_id}")
    print(f"file_path: {result.file_path}")
    print(f"provider: {result.provider}")
    print(f"model: {result.model}")
    print(f"outcome: {result.outcome}")


def main(arguments: Sequence[str] | None = None) -> int:
    parser = build_parser()
    parsed = parser.parse_args(arguments)

    try:
        asyncio.run(_run(parsed.message_id))
    except (
        AIEnrichmentError,
        KnowledgeArtifactError,
        SQLAlchemyError,
        OSError,
        RuntimeError,
    ) as exc:
        print(f"AI enrichment failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
