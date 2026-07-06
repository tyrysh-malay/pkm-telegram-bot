import argparse
import asyncio
import sys
import uuid
from collections.abc import Sequence

from sqlalchemy.exc import SQLAlchemyError

from app.db.session import get_session_factory
from app.knowledge.errors import KnowledgeArtifactError
from app.knowledge.git_publication import publish_artifact_to_git
from app.settings import get_settings


def _artifact_id(value: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a valid UUID") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Publish one existing Markdown Artifact to local Git."
    )
    parser.add_argument("--artifact-id", required=True, type=_artifact_id)
    return parser


async def _run(artifact_id: uuid.UUID) -> None:
    settings = get_settings()
    session_factory = get_session_factory()
    async with session_factory() as session:
        result = await publish_artifact_to_git(
            session,
            artifact_id,
            settings.knowledge_base_path,
        )

    print(f"artifact_id: {result.artifact_id}")
    print(f"file_path: {result.file_path}")
    print(f"git_commit_sha: {result.git_commit_sha}")
    print(f"outcome: {result.outcome}")


def main(arguments: Sequence[str] | None = None) -> int:
    parser = build_parser()
    parsed = parser.parse_args(arguments)

    try:
        asyncio.run(_run(parsed.artifact_id))
    except (KnowledgeArtifactError, SQLAlchemyError, OSError, RuntimeError) as exc:
        print(f"artifact Git publication failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
