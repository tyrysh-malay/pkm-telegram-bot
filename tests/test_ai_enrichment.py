import asyncio
import inspect
import uuid
from dataclasses import dataclass
from pathlib import Path

import pytest
from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy import update

from app.db.models import AIEnrichment
from app.db.models import Artifact
from app.db.models import Message
from app.db.models import User
from app.db.session import get_session_factory
from app.knowledge.ai_enrichment import canonical_source_text
from app.knowledge.ai_enrichment import enrich_text_message
from app.knowledge.ai_enrichment import _file_state_or_absent
from app.knowledge.ai_errors import AIEnrichmentConsistencyError
from app.knowledge.ai_errors import AIEnrichmentSourceError
from app.knowledge.ai_errors import AIProviderResponseError
from app.knowledge.ai_provider import ProviderEnrichmentResult
from app.knowledge.ai_schema import EnrichmentResult
from app.knowledge.enriched_markdown import ENRICHED_ARTIFACT_TYPE
from app.knowledge.enriched_markdown import RenderedEnrichedNote
from app.knowledge.markdown import ARTIFACT_TYPE
from app.knowledge.errors import FileConflictError
from app.knowledge.errors import KnowledgeBaseInvariantError
from app.knowledge.errors import UnsupportedFileEntryError
from app.knowledge.processing import process_text_message
from app.knowledge.storage import FileState


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


@dataclass
class StaticProvider:
    calls: list[str]
    result: object

    async def enrich(self, source_text: str) -> object:
        self.calls.append(source_text)
        return self.result


class MalformedEnrichment:
    def __repr__(self) -> str:
        return "SECRET_PROVIDER_PAYLOAD"


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


async def enriched_artifact_count(message_id: uuid.UUID) -> int:
    session_factory = get_session_factory()
    async with session_factory() as session:
        count = await session.scalar(
            select(func.count()).select_from(Artifact).where(
                Artifact.message_id == message_id,
                Artifact.artifact_type == ENRICHED_ARTIFACT_TYPE,
            )
        )
    assert count is not None
    return count


async def assert_source_rejected_before_provider(
    *,
    message_id: uuid.UUID,
    root: Path,
    provider: FakeProvider | StaticProvider | None = None,
) -> None:
    provider = provider or FakeProvider(calls=[])
    with pytest.raises(AIEnrichmentSourceError):
        await enrich_text_message(
            message_id=message_id,
            knowledge_base_root=root,
            provider=provider,
        )

    assert provider.calls == []
    assert await enrichment_count(message_id) == 0
    assert await enriched_artifact_count(message_id) == 0
    assert not (root / "processed").exists()


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


@pytest.mark.parametrize(
    "provider_result",
    (
        ProviderEnrichmentResult(
            provider=123,  # type: ignore[arg-type]
            model="model",
            response_id="resp",
            enrichment=EnrichmentResult(
                title="Title",
                summary="Summary",
                key_points=[],
                tags=[],
                action_items=[],
            ),
        ),
        ProviderEnrichmentResult(
            provider="openai",
            model=123,  # type: ignore[arg-type]
            response_id="resp",
            enrichment=EnrichmentResult(
                title="Title",
                summary="Summary",
                key_points=[],
                tags=[],
                action_items=[],
            ),
        ),
        ProviderEnrichmentResult(
            provider="openai",
            model="model",
            response_id=123,  # type: ignore[arg-type]
            enrichment=EnrichmentResult(
                title="Title",
                summary="Summary",
                key_points=[],
                tags=[],
                action_items=[],
            ),
        ),
        ProviderEnrichmentResult(
            provider="openai",
            model="model",
            response_id="resp",
            enrichment=MalformedEnrichment(),  # type: ignore[arg-type]
        ),
        MalformedEnrichment(),
    ),
)
def test_malformed_provider_results_fail_without_persisting_state(
    tmp_path: Path,
    provider_result: object,
) -> None:
    async def run() -> None:
        message_id = await create_done_message(tmp_path)
        provider = StaticProvider(calls=[], result=provider_result)

        with pytest.raises(AIProviderResponseError) as caught:
            await enrich_text_message(
                message_id=message_id,
                knowledge_base_root=tmp_path,
                provider=provider,
            )

        message = str(caught.value)
        assert "SECRET_PROVIDER_PAYLOAD" not in message
        assert "Source" not in message
        assert "Body" not in message
        assert provider.calls == [canonical_source_text("Source\nBody  ")]
        assert await enrichment_count(message_id) == 0
        assert await enriched_artifact_count(message_id) == 0
        assert not (tmp_path / "processed").exists()

    asyncio.run(run())


def test_valid_provider_result_is_normalized_and_accepted(tmp_path: Path) -> None:
    async def run() -> None:
        message_id = await create_done_message(tmp_path)
        provider = StaticProvider(
            calls=[],
            result=ProviderEnrichmentResult(
                provider="openai",
                model="model",
                response_id="resp",
                enrichment=EnrichmentResult(
                    title="  Provider title  ",
                    summary="Provider\t summary",
                    key_points=[" First ", "first", "Second"],
                    tags=[" #Tag ", "tag"],
                    action_items=[" Do it ", "do it"],
                ),
            ),
        )

        result = await enrich_text_message(
            message_id=message_id,
            knowledge_base_root=tmp_path,
            provider=provider,
        )

        session_factory = get_session_factory()
        async with session_factory() as session:
            enrichment = await session.get(AIEnrichment, result.ai_enrichment_id)
            assert enrichment is not None
            assert enrichment.result_json == {
                "title": "Provider title",
                "summary": "Provider summary",
                "key_points": ["First", "Second"],
                "tags": ["Tag"],
                "action_items": ["Do it"],
            }

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


def test_accepted_enrichment_recovers_missing_parent_without_provider(
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
        (tmp_path / "processed").rmdir()

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


def test_wrong_type_absent_named_root_or_parent_is_not_missing(tmp_path: Path) -> None:
    rendered = RenderedEnrichedNote(
        title="Title",
        slug="title",
        file_path="absent-parent/file.md",
        content=b"expected",
    )
    bad_root = tmp_path / "absent-root"
    bad_root.write_bytes(b"not a directory")
    with pytest.raises(KnowledgeBaseInvariantError):
        _file_state_or_absent(bad_root, rendered)

    parent = tmp_path / "absent-parent"
    parent.write_bytes(b"not a directory")
    with pytest.raises(KnowledgeBaseInvariantError):
        _file_state_or_absent(tmp_path, rendered)


def test_missing_destination_parent_is_classified_without_message_matching(
    tmp_path: Path,
) -> None:
    rendered = RenderedEnrichedNote(
        title="Title",
        slug="title",
        file_path="processed/file.md",
        content=b"expected",
    )

    assert _file_state_or_absent(tmp_path, rendered) is FileState.ABSENT
    forbidden_pattern = '"absent" ' + "in str"
    assert forbidden_pattern not in inspect.getsource(_file_state_or_absent)


@pytest.mark.parametrize(
    ("state", "expected_error"),
    (
        ("conflicting_file", FileConflictError),
        ("unsupported_entry", UnsupportedFileEntryError),
    ),
)
def test_existing_bad_enriched_destination_fails_closed(
    tmp_path: Path,
    state: str,
    expected_error: type[Exception],
) -> None:
    async def run() -> None:
        message_id = await create_done_message(tmp_path)
        first = await enrich_text_message(
            message_id=message_id,
            knowledge_base_root=tmp_path,
            provider=FakeProvider(calls=[]),
        )
        destination = tmp_path / first.file_path
        destination.unlink()
        if state == "conflicting_file":
            destination.write_bytes(b"conflict")
        else:
            destination.mkdir()

        provider = FakeProvider(calls=[])
        with pytest.raises(expected_error):
            await enrich_text_message(
                message_id=message_id,
                knowledge_base_root=tmp_path,
                provider=provider,
            )

        assert provider.calls == []
        assert await enrichment_count(message_id) == 1

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


@pytest.mark.parametrize(
    "mutation",
        (
            "non_text",
            "null_raw_text",
            "not_done",
            "missing_raw_artifact",
        "inconsistent_raw_artifact_metadata",
        "missing_raw_file",
        "conflicting_raw_file",
        "unsupported_raw_entry",
        "blank_canonical_source",
        "oversized_source",
    ),
)
def test_source_eligibility_failures_do_not_call_provider(
    tmp_path: Path,
    mutation: str,
) -> None:
    async def run() -> None:
        raw_text = "Source\nBody"
        if mutation == "blank_canonical_source":
            raw_text = "   \n"
        elif mutation == "oversized_source":
            raw_text = "x" * 65_537

        message_id = await create_done_message(tmp_path, raw_text=raw_text)
        raw_artifact = await artifact_for(message_id, ARTIFACT_TYPE)

        session_factory = get_session_factory()
        async with session_factory() as session:
            async with session.begin():
                if mutation == "non_text":
                    await session.execute(
                        update(Message)
                        .where(Message.id == message_id)
                        .values(input_type="photo")
                    )
                elif mutation == "null_raw_text":
                    await session.execute(
                        update(Message)
                        .where(Message.id == message_id)
                        .values(raw_text=None)
                    )
                elif mutation == "not_done":
                    await session.execute(
                        update(Message)
                        .where(Message.id == message_id)
                        .values(status="received")
                    )
                elif mutation == "missing_raw_artifact":
                    artifact = await session.get(Artifact, raw_artifact.id)
                    assert artifact is not None
                    await session.delete(artifact)
                elif mutation == "inconsistent_raw_artifact_metadata":
                    await session.execute(
                        update(Artifact)
                        .where(Artifact.id == raw_artifact.id)
                        .values(title="wrong title")
                    )

        raw_path = tmp_path / raw_artifact.file_path
        if mutation == "missing_raw_file":
            raw_path.unlink()
        elif mutation == "conflicting_raw_file":
            raw_path.write_bytes(b"conflict")
        elif mutation == "unsupported_raw_entry":
            raw_path.unlink()
            raw_path.mkdir()

        await assert_source_rejected_before_provider(
            message_id=message_id,
            root=tmp_path,
        )

    asyncio.run(run())


def test_missing_message_fails_before_provider(tmp_path: Path) -> None:
    async def run() -> None:
        provider = FakeProvider(calls=[])
        missing_id = uuid.uuid4()

        with pytest.raises(AIEnrichmentSourceError):
            await enrich_text_message(
                message_id=missing_id,
                knowledge_base_root=tmp_path,
                provider=provider,
            )

        assert provider.calls == []
        assert await enrichment_count(missing_id) == 0
        assert await enriched_artifact_count(missing_id) == 0
        assert not (tmp_path / "processed").exists()

    asyncio.run(run())
