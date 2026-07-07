import asyncio
import uuid
from dataclasses import dataclass
from pathlib import Path

import pytest
from sqlalchemy import func
from sqlalchemy import select

from app.db.models import AIEnrichment
from app.db.models import Artifact
from app.db.models import Message
from app.db.models import User
from app.db.session import get_session_factory
from app.knowledge.ai_enrichment import canonical_source_text
from app.knowledge.ai_enrichment import enrich_text_message
from app.knowledge.ai_errors import AIEnrichmentConsistencyError
from app.knowledge.ai_errors import AIEnrichmentSourceError
from app.knowledge.ai_provider import ProviderEnrichmentResult
from app.knowledge.ai_schema import EnrichmentResult
from app.knowledge.enriched_markdown import ENRICHED_ARTIFACT_TYPE
from app.knowledge.markdown import ARTIFACT_TYPE
from app.knowledge.processing import process_text_message


@dataclass
class FakeProvider:
    calls: list[str]
    title: str = "Enriched title"
    wait: asyncio.Event | None = None
    mutate_message_id: uuid.UUID | None = None

    async def enrich(self, source_text: str) -> ProviderEnrichmentResult:
        self.calls.append(source_text)
        if self.wait is not None:
            self.wait.set()
            await asyncio.sleep(0.05)
        if self.mutate_message_id is not None:
            session_factory = get_session_factory()
            async with session_factory() as session:
                message = await session.get(Message, self.mutate_message_id)
                assert message is not None
                message.raw_text = "changed during provider call"
                await session.commit()
        return ProviderEnrichmentResult(
            provider="openai",
            model=f"model-{len(self.calls)}",
            response_id=f"resp-{len(self.calls)}",
            enrichment=EnrichmentResult(
                title=self.title,
                summary="Supported summary",
                key_points=["Point"],
                tags=["tag"],
                action_items=[],
            ),
        )


async def create_done_message(root: Path, raw_text: str = "Source\nBody  ") -> uuid.UUID:
    unique = uuid.uuid4().int % 9_000_000_000_000_000_000
    session_factory = get_session_factory()
    async with session_factory() as session:
        user = User(telegram_user_id=unique)
        session.add(user)
        await session.flush()
        message = Message(
            user_id=user.id,
            telegram_chat_id=-unique,
            telegram_message_id=77,
            input_type="text",
            raw_text=raw_text,
            status="received",
            idempotency_key=f"telegram:{-unique}:77",
        )
        session.add(message)
        await session.commit()
        message_id = message.id

    async with session_factory() as session:
        await process_text_message(session, message_id, root)
    return message_id


async def artifact_for(message_id: uuid.UUID, artifact_type: str) -> Artifact:
    session_factory = get_session_factory()
    async with session_factory() as session:
        artifact = await session.scalar(
            select(Artifact).where(
                Artifact.message_id == message_id,
                Artifact.artifact_type == artifact_type,
            )
        )
        assert artifact is not None
        return artifact


async def enrichment_count(message_id: uuid.UUID) -> int:
    session_factory = get_session_factory()
    async with session_factory() as session:
        count = await session.scalar(
            select(func.count()).select_from(AIEnrichment).where(
                AIEnrichment.message_id == message_id
            )
        )
    assert count is not None
    return count


def test_enrich_text_message_creates_row_artifact_and_file(tmp_path: Path) -> None:
    async def run() -> None:
        message_id = await create_done_message(tmp_path)
        raw_artifact = await artifact_for(message_id, ARTIFACT_TYPE)
        raw_path = tmp_path / raw_artifact.file_path
        raw_before = raw_path.read_bytes()
        provider = FakeProvider(calls=[])

        result = await enrich_text_message(
            message_id=message_id,
            knowledge_base_root=tmp_path,
            provider=provider,
        )

        enriched = await artifact_for(message_id, ENRICHED_ARTIFACT_TYPE)
        assert result.outcome == "created"
        assert result.source_artifact_id == raw_artifact.id
        assert result.enriched_artifact_id == enriched.id
        assert result.file_path.startswith("processed/")
        assert (tmp_path / result.file_path).read_bytes().endswith(b"_None._\n")
        assert raw_path.read_bytes() == raw_before
        assert provider.calls == [canonical_source_text("Source\nBody  ")]
        assert await enrichment_count(message_id) == 1

    asyncio.run(run())


def test_existing_enrichment_skips_provider_and_returns_existing(
    tmp_path: Path,
) -> None:
    async def run() -> None:
        message_id = await create_done_message(tmp_path)
        first_provider = FakeProvider(calls=[])
        first = await enrich_text_message(
            message_id=message_id,
            knowledge_base_root=tmp_path,
            provider=first_provider,
        )
        failing_provider = FakeProvider(calls=[])
        second = await enrich_text_message(
            message_id=message_id,
            knowledge_base_root=tmp_path,
            provider=failing_provider,
        )

        assert first.ai_enrichment_id == second.ai_enrichment_id
        assert first.enriched_artifact_id == second.enriched_artifact_id
        assert second.outcome == "existing"
        assert failing_provider.calls == []

    asyncio.run(run())


def test_accepted_enrichment_recovers_missing_artifact_without_provider(
    tmp_path: Path,
) -> None:
    async def run() -> None:
        message_id = await create_done_message(tmp_path)
        first = await enrich_text_message(
            message_id=message_id,
            knowledge_base_root=tmp_path,
            provider=FakeProvider(calls=[]),
        )
        session_factory = get_session_factory()
        async with session_factory() as session:
            artifact = await session.get(Artifact, first.enriched_artifact_id)
            assert artifact is not None
            await session.delete(artifact)
            await session.commit()
        (tmp_path / first.file_path).unlink()

        provider = FakeProvider(calls=[])
        recovered = await enrich_text_message(
            message_id=message_id,
            knowledge_base_root=tmp_path,
            provider=provider,
        )

        assert recovered.ai_enrichment_id == first.ai_enrichment_id
        assert recovered.outcome == "reconciled"
        assert provider.calls == []
        assert (tmp_path / recovered.file_path).exists()

    asyncio.run(run())


def test_source_change_during_provider_call_rejects_result(tmp_path: Path) -> None:
    async def run() -> None:
        message_id = await create_done_message(tmp_path)

        with pytest.raises((AIEnrichmentConsistencyError, AIEnrichmentSourceError)):
            await enrich_text_message(
                message_id=message_id,
                knowledge_base_root=tmp_path,
                provider=FakeProvider(calls=[], mutate_message_id=message_id),
            )

        assert await enrichment_count(message_id) == 0
        assert not (tmp_path / "processed").exists()

    asyncio.run(run())


def test_concurrent_invocations_accept_one_winner(tmp_path: Path) -> None:
    async def run() -> None:
        message_id = await create_done_message(tmp_path)
        provider = FakeProvider(calls=[], wait=asyncio.Event())

        results = await asyncio.gather(
            enrich_text_message(
                message_id=message_id,
                knowledge_base_root=tmp_path,
                provider=provider,
            ),
            enrich_text_message(
                message_id=message_id,
                knowledge_base_root=tmp_path,
                provider=provider,
            ),
        )

        assert len(provider.calls) == 2
        assert len({result.ai_enrichment_id for result in results}) == 1
        assert await enrichment_count(message_id) == 1
        assert {result.outcome for result in results} <= {
            "created",
            "reconciled",
            "existing",
        }

    asyncio.run(run())


def test_invalid_source_fails_before_provider(tmp_path: Path) -> None:
    async def run() -> None:
        message_id = await create_done_message(tmp_path, raw_text="   \n")
        provider = FakeProvider(calls=[])

        with pytest.raises(AIEnrichmentSourceError):
            await enrich_text_message(
                message_id=message_id,
                knowledge_base_root=tmp_path,
                provider=provider,
            )

        assert provider.calls == []
        assert await enrichment_count(message_id) == 0

    asyncio.run(run())
