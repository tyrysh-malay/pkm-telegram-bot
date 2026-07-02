import argparse
import asyncio
import sys
import uuid
from collections.abc import Sequence

from sqlalchemy.exc import SQLAlchemyError

from app.db.session import get_session_factory
from app.knowledge.errors import KnowledgeArtifactError
from app.knowledge.processing import process_text_message
from app.settings import get_settings


def _message_id(value: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a valid UUID") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate one deterministic note from a persisted text message."
    )
    parser.add_argument("--message-id", required=True, type=_message_id)
    return parser


async def _run(message_id: uuid.UUID) -> None:
    settings = get_settings()
    session_factory = get_session_factory()
    async with session_factory() as session:
        artifact = await process_text_message(
            session,
            message_id,
            settings.knowledge_base_path,
        )

    print(f"artifact_id: {artifact.id}")
    print(f"file_path: {artifact.file_path}")


def main(arguments: Sequence[str] | None = None) -> int:
    parser = build_parser()
    parsed = parser.parse_args(arguments)

    try:
        asyncio.run(_run(parsed.message_id))
    except (KnowledgeArtifactError, SQLAlchemyError, OSError, RuntimeError) as exc:
        print(f"artifact processing failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
