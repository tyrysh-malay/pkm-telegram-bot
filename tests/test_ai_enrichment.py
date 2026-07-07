import asyncio
import inspect
import uuid
from dataclasses import dataclass
from pathlib import Path

import pytest
from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker

import app.knowledge.ai_enrichment as ai_enrichment
from app.db.models import AIEnrichment
from app.db.models import Artifact
from app.db.models import Message
from app.db.models import User
from app.db.session import get_engine
from app.db.session import get_session_factory
from app.knowledge.ai_enrichment import canonical_source_text
from app.knowledge.ai_enrichment import enrich_text_message
from app.knowledge.ai_enrichment import _file_state_or_absent
from app.knowledge.ai_errors import AIEnrichmentConsistencyError
from app.knowledge.ai_errors import AIEnrichmentSourceError
from app.knowledge.ai_errors import AIProviderResponseError
from app.knowledge.ai_provider import PROMPT_VERSION
from app.knowledge.ai_provider import ProviderEnrichmentResult
from app.knowledge.ai_schema import EnrichmentResult
from app.knowledge.ai_schema import SCHEMA_VERSION
from app.knowledge.enriched_markdown import ENRICHED_ARTIFACT_TYPE
from app.knowledge.enriched_markdown import RenderedEnrichedNote
from app.knowledge.markdown import ARTIFACT_TYPE
from app.knowledge.markdown import render_text_note
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


@dataclass
class MutatingProvider:
    calls: list[str]
    mutation: str
    message_id: uuid.UUID
    root: Path
    result: ProviderEnrichmentResult

    async def enrich(self, source_text: str) -> ProviderEnrichmentResult:
        self.calls.append(source_text)
        session_factory = get_session_factory()
        raw_artifact = await artifact_for(self.message_id, ARTIFACT_TYPE)

        if self.mutation == "replace_raw_artifact":
            async with session_factory() as session:
                async with session.begin():
                    artifact = await session.get(Artifact, raw_artifact.id)
                    assert artifact is not None
                    await session.delete(artifact)
                    await session.flush()
                    session.add(
                        Artifact(
                            message_id=self.message_id,
                            artifact_type=ARTIFACT_TYPE,
                            title=raw_artifact.title,
                            slug=raw_artifact.slug,
                            file_path=raw_artifact.file_path,
                            git_commit_sha=raw_artifact.git_commit_sha,
                        )
                    )
        elif self.mutation == "change_raw_bytes":
            async with session_factory() as session:
                async with session.begin():
                    message = await session.get(Message, self.message_id)
                    assert message is not None
                    message.raw_text = "Title\nchanged exact bytes"
        elif self.mutation == "change_digest_with_exact_file":
            async with session_factory() as session:
                async with session.begin():
                    message = await session.get(Message, self.message_id)
                    assert message is not None
                    message.raw_text = "Title\nchanged digest"
                    rendered = render_text_note(
                        message_id=message.id,
                        telegram_chat_id=message.telegram_chat_id,
                        telegram_message_id=message.telegram_message_id,
                        created_at=message.created_at,
                        raw_text=message.raw_text,
                    )
                    (self.root / raw_artifact.file_path).write_bytes(rendered.content)
        else:
            raise AssertionError(f"unknown mutation {self.mutation}")

        return self.result


@dataclass
class FailingProvider:
    calls: list[str]
    error: Exception

    async def enrich(self, source_text: str) -> ProviderEnrichmentResult:
        self.calls.append(source_text)
        raise self.error


@dataclass
class ReleasingProvider:
    calls: list[str]
    result: ProviderEnrichmentResult
    entered: asyncio.Event
    release: asyncio.Event

    async def enrich(self, source_text: str) -> ProviderEnrichmentResult:
        self.calls.append(source_text)
        self.entered.set()
        await self.release.wait()
        return self.result


class ObservedSession(AsyncSession):
    events: list[tuple[str, str | None, bool | None]] = []
    live_sessions: set[int] = set()

    async def __aenter__(self):
        type(self).events.append(("session_enter", None, None))
        type(self).live_sessions.add(id(self))
        return await super().__aenter__()

    async def __aexit__(self, *args):
        type(self).events.append(
            ("session_exit", None, self.in_transaction())
        )
        type(self).live_sessions.discard(id(self))
        return await super().__aexit__(*args)

    def begin(self):
        manager = super().begin()
        session = self

        class ObservedBegin:
            async def __aenter__(self):
                ObservedSession.events.append(("transaction_enter", None, None))
                return await manager.__aenter__()

            async def __aexit__(self, *args):
                ObservedSession.events.append(
                    ("transaction_exit", None, session.in_transaction())
                )
                return await manager.__aexit__(*args)

        return ObservedBegin()

    async def scalar(self, statement, *args, **kwargs):
        entity = None
        descriptions = getattr(statement, "column_descriptions", ())
        if descriptions:
            entity_value = descriptions[0].get("entity")
            entity = getattr(entity_value, "__name__", None)
        ObservedSession.events.append(
            (
                "scalar",
                entity,
                getattr(statement, "_for_update_arg", None) is not None,
            )
        )
        return await super().scalar(statement, *args, **kwargs)


class ObservingProvider:
    def __init__(self, result: ProviderEnrichmentResult) -> None:
        self.calls: list[str] = []
        self.result = result
        self.live_sessions_during_call: list[int] = []
        self.active_transactions_during_call: list[bool] = []

    async def enrich(self, source_text: str) -> ProviderEnrichmentResult:
        self.calls.append(source_text)
        self.live_sessions_during_call.append(len(ObservedSession.live_sessions))
        self.active_transactions_during_call.append(False)
        await asyncio.sleep(0)
        self.live_sessions_during_call.append(len(ObservedSession.live_sessions))
        self.active_transactions_during_call.append(False)
        ObservedSession.events.append(("provider_return", None, None))
        return self.result


class FakeOrig:
    constraint_name = "unrelated_constraint"


class FlushFailingSession(AsyncSession):
    async def flush(self, *args, **kwargs) -> None:
        if any(
            isinstance(obj, Artifact)
            and obj.artifact_type == ENRICHED_ARTIFACT_TYPE
            for obj in self.new
        ):
            raise RuntimeError("database failed after file publication")
        return await super().flush(*args, **kwargs)


class UnrelatedIntegritySession(AsyncSession):
    async def flush(self, *args, **kwargs) -> None:
        if any(isinstance(obj, AIEnrichment) for obj in self.new):
            raise IntegrityError("statement", {}, FakeOrig())
        return await super().flush(*args, **kwargs)


class MalformedEnrichment:
    def __repr__(self) -> str:
        return "SECRET_PROVIDER_PAYLOAD"


@dataclass(frozen=True)
class RawState:
    message_status: str
    artifact_id: uuid.UUID
    title: str
    slug: str
    file_path: str
    git_commit_sha: str | None
    file_bytes: bytes


def provider_result(
    *,
    model: str = "model",
    response_id: str = "resp",
    title: str = "Enriched title",
    summary: str = "Supported summary",
    key_points: list[str] | None = None,
    tags: list[str] | None = None,
    action_items: list[str] | None = None,
) -> ProviderEnrichmentResult:
    return ProviderEnrichmentResult(
        provider="openai",
        model=model,
        response_id=response_id,
        enrichment=EnrichmentResult(
            title=title,
            summary=summary,
            key_points=key_points if key_points is not None else ["Point"],
            tags=tags if tags is not None else ["tag"],
            action_items=action_items if action_items is not None else [],
        ),
    )


async def raw_state(message_id: uuid.UUID, root: Path) -> RawState:
    session_factory = get_session_factory()
    async with session_factory() as session:
        message = await session.get(Message, message_id)
        assert message is not None
        artifact = await session.scalar(
            select(Artifact).where(
                Artifact.message_id == message_id,
                Artifact.artifact_type == ARTIFACT_TYPE,
            )
        )
        assert artifact is not None
        return RawState(
            message_status=message.status,
            artifact_id=artifact.id,
            title=artifact.title,
            slug=artifact.slug,
            file_path=artifact.file_path,
            git_commit_sha=artifact.git_commit_sha,
            file_bytes=(root / artifact.file_path).read_bytes(),
        )


async def assert_raw_state_unchanged(
    message_id: uuid.UUID,
    root: Path,
    before: RawState,
) -> None:
    assert await raw_state(message_id, root) == before


async def enrichment_row(message_id: uuid.UUID) -> AIEnrichment:
    session_factory = get_session_factory()
    async with session_factory() as session:
        row = await session.scalar(
            select(AIEnrichment).where(AIEnrichment.message_id == message_id)
        )
        assert row is not None
        return row


async def artifact_count_for_path(file_path: str) -> int:
    session_factory = get_session_factory()
    async with session_factory() as session:
        count = await session.scalar(
            select(func.count()).select_from(Artifact).where(
                Artifact.file_path == file_path
            )
        )
    assert count is not None
    return count


async def set_raw_git_sha(message_id: uuid.UUID, value: str) -> None:
    session_factory = get_session_factory()
    async with session_factory() as session:
        async with session.begin():
            artifact = await session.scalar(
                select(Artifact).where(
                    Artifact.message_id == message_id,
                    Artifact.artifact_type == ARTIFACT_TYPE,
                )
            )
            assert artifact is not None
            artifact.git_commit_sha = value


async def assert_enriched_git_sha_is_null(message_id: uuid.UUID) -> None:
    session_factory = get_session_factory()
    async with session_factory() as session:
        artifact = await session.scalar(
            select(Artifact).where(
                Artifact.message_id == message_id,
                Artifact.artifact_type == ENRICHED_ARTIFACT_TYPE,
            )
        )
        assert artifact is not None
        assert artifact.git_commit_sha is None


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


def test_absent_enriched_artifact_with_exact_orphan_file_is_reconciled(
    tmp_path: Path,
) -> None:
    async def run() -> None:
        message_id = await create_done_message(tmp_path)
        await set_raw_git_sha(message_id, "a" * 40)
        first = await enrich_text_message(
            message_id=message_id,
            knowledge_base_root=tmp_path,
            provider=FakeProvider(calls=[]),
        )
        raw_before = await raw_state(message_id, tmp_path)
        orphan_bytes = (tmp_path / first.file_path).read_bytes()
        session_factory = get_session_factory()
        async with session_factory() as session:
            artifact = await session.get(Artifact, first.enriched_artifact_id)
            assert artifact is not None
            await session.delete(artifact)
            await session.commit()

        provider = FakeProvider(calls=[])
        recovered = await enrich_text_message(
            message_id=message_id,
            knowledge_base_root=tmp_path,
            provider=provider,
        )

        assert recovered.outcome == "reconciled"
        assert provider.calls == []
        assert (tmp_path / recovered.file_path).read_bytes() == orphan_bytes
        assert await enriched_artifact_count(message_id) == 1
        await assert_enriched_git_sha_is_null(message_id)
        await assert_raw_state_unchanged(message_id, tmp_path, raw_before)
        assert not (tmp_path / ".git").exists()

    asyncio.run(run())


def test_valid_enriched_artifact_with_missing_file_is_reconciled(
    tmp_path: Path,
) -> None:
    async def run() -> None:
        message_id = await create_done_message(tmp_path)
        await set_raw_git_sha(message_id, "b" * 40)
        first = await enrich_text_message(
            message_id=message_id,
            knowledge_base_root=tmp_path,
            provider=FakeProvider(calls=[]),
        )
        raw_before = await raw_state(message_id, tmp_path)
        (tmp_path / first.file_path).unlink()

        provider = FakeProvider(calls=[])
        recovered = await enrich_text_message(
            message_id=message_id,
            knowledge_base_root=tmp_path,
            provider=provider,
        )

        assert recovered.enriched_artifact_id == first.enriched_artifact_id
        assert recovered.outcome == "reconciled"
        assert provider.calls == []
        assert (tmp_path / recovered.file_path).exists()
        await assert_enriched_git_sha_is_null(message_id)
        await assert_raw_state_unchanged(message_id, tmp_path, raw_before)
        assert not (tmp_path / ".git").exists()

    asyncio.run(run())


def test_inconsistent_enriched_artifact_metadata_fails_without_replacement(
    tmp_path: Path,
) -> None:
    async def run() -> None:
        message_id = await create_done_message(tmp_path)
        await set_raw_git_sha(message_id, "c" * 40)
        first = await enrich_text_message(
            message_id=message_id,
            knowledge_base_root=tmp_path,
            provider=FakeProvider(calls=[]),
        )
        raw_before = await raw_state(message_id, tmp_path)
        session_factory = get_session_factory()
        async with session_factory() as session:
            async with session.begin():
                artifact = await session.get(Artifact, first.enriched_artifact_id)
                assert artifact is not None
                artifact.title = "wrong enriched title"

        provider = FakeProvider(calls=[])
        with pytest.raises(AIEnrichmentConsistencyError):
            await enrich_text_message(
                message_id=message_id,
                knowledge_base_root=tmp_path,
                provider=provider,
            )

        assert provider.calls == []
        assert await enriched_artifact_count(message_id) == 1
        await assert_raw_state_unchanged(message_id, tmp_path, raw_before)
        assert (tmp_path / first.file_path).exists()

    asyncio.run(run())


def test_deterministic_enriched_path_owned_by_another_artifact_fails(
    tmp_path: Path,
) -> None:
    async def run() -> None:
        message_id = await create_done_message(tmp_path)
        await set_raw_git_sha(message_id, "d" * 40)
        first = await enrich_text_message(
            message_id=message_id,
            knowledge_base_root=tmp_path,
            provider=FakeProvider(calls=[]),
        )
        raw_before = await raw_state(message_id, tmp_path)
        other_message_id = await create_done_message(tmp_path, raw_text="Other")
        session_factory = get_session_factory()
        async with session_factory() as session:
            async with session.begin():
                artifact = await session.get(Artifact, first.enriched_artifact_id)
                assert artifact is not None
                await session.delete(artifact)
                await session.flush()
                session.add(
                    Artifact(
                        message_id=other_message_id,
                        artifact_type="other",
                        title="Other owner",
                        slug="other-owner",
                        file_path=first.file_path,
                    )
                )

        provider = FakeProvider(calls=[])
        with pytest.raises(AIEnrichmentConsistencyError):
            await enrich_text_message(
                message_id=message_id,
                knowledge_base_root=tmp_path,
                provider=provider,
            )

        assert provider.calls == []
        assert await artifact_count_for_path(first.file_path) == 1
        await assert_raw_state_unchanged(message_id, tmp_path, raw_before)

    asyncio.run(run())


def test_database_failure_after_file_publication_leaves_orphan_then_reconciles(
    tmp_path: Path,
) -> None:
    async def run() -> None:
        message_id = await create_done_message(tmp_path)
        await set_raw_git_sha(message_id, "e" * 40)
        raw_before = await raw_state(message_id, tmp_path)
        factory = async_sessionmaker(
            get_engine(),
            expire_on_commit=False,
            class_=FlushFailingSession,
        )

        with pytest.raises(RuntimeError, match="database failed"):
            await enrich_text_message(
                message_id=message_id,
                knowledge_base_root=tmp_path,
                provider=FakeProvider(calls=[]),
                session_factory=factory,
            )

        row = await enrichment_row(message_id)
        assert row.model == "model-1"
        assert await enriched_artifact_count(message_id) == 0
        processed_files = list((tmp_path / "processed").glob("*.md"))
        assert len(processed_files) == 1
        await assert_raw_state_unchanged(message_id, tmp_path, raw_before)

        provider = FakeProvider(calls=[])
        recovered = await enrich_text_message(
            message_id=message_id,
            knowledge_base_root=tmp_path,
            provider=provider,
        )

        assert recovered.ai_enrichment_id == row.id
        assert recovered.outcome == "reconciled"
        assert provider.calls == []
        await assert_enriched_git_sha_is_null(message_id)
        await assert_raw_state_unchanged(message_id, tmp_path, raw_before)

    asyncio.run(run())


def test_filesystem_failure_after_acceptance_preserves_row_then_rerun_recovers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def run() -> None:
        message_id = await create_done_message(tmp_path)
        await set_raw_git_sha(message_id, "f" * 40)
        raw_before = await raw_state(message_id, tmp_path)

        def fail_publication(*_args, **_kwargs):
            raise OSError("filesystem unavailable")

        monkeypatch.setattr(ai_enrichment, "ensure_exact_file", fail_publication)
        provider = FakeProvider(calls=[])
        with pytest.raises(OSError, match="filesystem unavailable"):
            await enrich_text_message(
                message_id=message_id,
                knowledge_base_root=tmp_path,
                provider=provider,
            )

        assert provider.calls == [canonical_source_text("Source\nBody  ")]
        row = await enrichment_row(message_id)
        assert row.model == "model-1"
        assert await enriched_artifact_count(message_id) == 0
        assert not (tmp_path / "processed").exists()
        await assert_raw_state_unchanged(message_id, tmp_path, raw_before)

        monkeypatch.setattr(ai_enrichment, "ensure_exact_file", ensure_exact_file)
        rerun_provider = FakeProvider(calls=[])
        recovered = await enrich_text_message(
            message_id=message_id,
            knowledge_base_root=tmp_path,
            provider=rerun_provider,
        )

        assert recovered.ai_enrichment_id == row.id
        assert recovered.outcome == "reconciled"
        assert rerun_provider.calls == []
        assert (tmp_path / recovered.file_path).exists()
        await assert_enriched_git_sha_is_null(message_id)
        await assert_raw_state_unchanged(message_id, tmp_path, raw_before)

    from app.knowledge.storage import ensure_exact_file

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
        await set_raw_git_sha(message_id, "1" * 40)
        first = await enrich_text_message(
            message_id=message_id,
            knowledge_base_root=tmp_path,
            provider=FakeProvider(calls=[]),
        )
        raw_before = await raw_state(message_id, tmp_path)
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
        if state == "conflicting_file":
            assert destination.read_bytes() == b"conflict"
        else:
            assert destination.is_dir()
        await assert_raw_state_unchanged(message_id, tmp_path, raw_before)
        assert not (tmp_path / ".git").exists()

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


def test_nul_source_rejects_before_provider_with_no_state_change(
    tmp_path: Path,
) -> None:
    class NulSession:
        def __init__(self) -> None:
            self.message = Message(
                id=uuid.uuid4(),
                user_id=uuid.uuid4(),
                telegram_chat_id=-123,
                telegram_message_id=77,
                input_type="text",
                raw_text="Source\0Body",
                status="done",
                idempotency_key="telegram:-123:77",
            )
            self.artifact = Artifact(
                message_id=self.message.id,
                artifact_type=ARTIFACT_TYPE,
                title="Source Body",
                slug="source-body",
                file_path="inbox/file.md",
            )
            self.scalar_calls = 0

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        def begin(self):
            return self

        def in_transaction(self) -> bool:
            return False

        async def scalar(self, _statement):
            self.scalar_calls += 1
            return self.message if self.scalar_calls == 1 else self.artifact

    session = NulSession()

    class NulSessionFactory:
        def __call__(self) -> NulSession:
            return session

    async def run() -> None:
        provider = FakeProvider(calls=[])
        original_message = (
            session.message.raw_text,
            session.message.status,
            session.artifact.file_path,
        )

        with pytest.raises(AIEnrichmentSourceError):
            await enrich_text_message(
                message_id=session.message.id,
                knowledge_base_root=tmp_path,
                provider=provider,
                session_factory=NulSessionFactory(),  # type: ignore[arg-type]
            )

        assert provider.calls == []
        assert (session.message.raw_text, session.message.status, session.artifact.file_path) == (
            original_message
        )
        assert await enrichment_count(session.message.id) == 0
        assert await enriched_artifact_count(session.message.id) == 0
        assert not (tmp_path / "processed").exists()

    asyncio.run(run())


def test_provider_request_occurs_after_initial_session_closes_and_acceptance_relocks(
    tmp_path: Path,
) -> None:
    async def run() -> None:
        message_id = await create_done_message(tmp_path)
        ObservedSession.events = []
        ObservedSession.live_sessions = set()
        factory = async_sessionmaker(
            get_engine(),
            expire_on_commit=False,
            class_=ObservedSession,
        )
        provider = ObservingProvider(provider_result())

        await enrich_text_message(
            message_id=message_id,
            knowledge_base_root=tmp_path,
            provider=provider,
            session_factory=factory,
        )

        assert provider.calls == [canonical_source_text("Source\nBody  ")]
        assert provider.live_sessions_during_call == [0, 0]
        assert provider.active_transactions_during_call == [False, False]
        provider_index = ObservedSession.events.index(("provider_return", None, None))
        assert ("session_exit", None, False) in ObservedSession.events[:provider_index]
        after_provider = ObservedSession.events[provider_index + 1 :]
        assert ("session_enter", None, None) in after_provider
        assert ("transaction_enter", None, None) in after_provider
        assert ("scalar", "Message", True) in after_provider
        assert ("scalar", "Artifact", True) in after_provider

    asyncio.run(run())


@pytest.mark.parametrize(
    "mutation",
    ("replace_raw_artifact", "change_raw_bytes", "change_digest_with_exact_file"),
)
def test_post_provider_source_revalidation_rejects_mutated_source(
    tmp_path: Path,
    mutation: str,
) -> None:
    async def run() -> None:
        initial_text = "Title\noriginal body"
        message_id = await create_done_message(tmp_path, raw_text=initial_text)
        before = await raw_state(message_id, tmp_path)
        provider = MutatingProvider(
            calls=[],
            mutation=mutation,
            message_id=message_id,
            root=tmp_path,
            result=provider_result(title="Candidate after mutation"),
        )

        with pytest.raises((AIEnrichmentConsistencyError, AIEnrichmentSourceError)):
            await enrich_text_message(
                message_id=message_id,
                knowledge_base_root=tmp_path,
                provider=provider,
            )

        assert provider.calls == [canonical_source_text(initial_text)]
        assert await enrichment_count(message_id) == 0
        assert await enriched_artifact_count(message_id) == 0
        assert not (tmp_path / "processed").exists()
        if mutation == "replace_raw_artifact":
            assert (tmp_path / before.file_path).read_bytes() == before.file_bytes

    asyncio.run(run())


def test_provider_failure_persists_no_state(tmp_path: Path) -> None:
    async def run() -> None:
        message_id = await create_done_message(tmp_path)
        before = await raw_state(message_id, tmp_path)
        provider = FailingProvider(
            calls=[],
            error=AIProviderResponseError("provider failed safely"),
        )

        with pytest.raises(AIProviderResponseError):
            await enrich_text_message(
                message_id=message_id,
                knowledge_base_root=tmp_path,
                provider=provider,
            )

        assert provider.calls == [canonical_source_text("Source\nBody  ")]
        assert await enrichment_count(message_id) == 0
        assert await enriched_artifact_count(message_id) == 0
        assert not (tmp_path / "processed").exists()
        await assert_raw_state_unchanged(message_id, tmp_path, before)

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


def test_distinct_concurrent_candidates_preserve_single_winner_immutably(
    tmp_path: Path,
) -> None:
    async def run() -> None:
        message_id = await create_done_message(tmp_path)
        raw_before = await raw_state(message_id, tmp_path)
        release = asyncio.Event()
        first_entered = asyncio.Event()
        second_entered = asyncio.Event()
        first_provider = ReleasingProvider(
            calls=[],
            entered=first_entered,
            release=release,
            result=provider_result(
                model="model-winner-a",
                response_id="resp-winner-a",
                title="Winner A title",
                summary="Winner A summary",
                key_points=["A point"],
                tags=["tag-a"],
                action_items=["A action"],
            ),
        )
        second_provider = ReleasingProvider(
            calls=[],
            entered=second_entered,
            release=release,
            result=provider_result(
                model="model-loser-b",
                response_id="resp-loser-b",
                title="Loser B title",
                summary="Loser B summary",
                key_points=["B point"],
                tags=["tag-b"],
                action_items=["B action"],
            ),
        )

        first_task = asyncio.create_task(
            enrich_text_message(
                message_id=message_id,
                knowledge_base_root=tmp_path,
                provider=first_provider,
            )
        )
        second_task = asyncio.create_task(
            enrich_text_message(
                message_id=message_id,
                knowledge_base_root=tmp_path,
                provider=second_provider,
            )
        )
        await asyncio.wait_for(first_entered.wait(), timeout=5)
        await asyncio.wait_for(second_entered.wait(), timeout=5)
        release.set()
        results = await asyncio.gather(first_task, second_task)

        assert first_provider.calls == [canonical_source_text("Source\nBody  ")]
        assert second_provider.calls == [canonical_source_text("Source\nBody  ")]
        assert len({result.ai_enrichment_id for result in results}) == 1
        assert len({result.enriched_artifact_id for result in results}) == 1
        assert await enrichment_count(message_id) == 1

        row = await enrichment_row(message_id)
        accepted_candidates = [
            (
                "model-winner-a",
                "resp-winner-a",
                {
                    "title": "Winner A title",
                    "summary": "Winner A summary",
                    "key_points": ["A point"],
                    "tags": ["tag-a"],
                    "action_items": ["A action"],
                },
            ),
            (
                "model-loser-b",
                "resp-loser-b",
                {
                    "title": "Loser B title",
                    "summary": "Loser B summary",
                    "key_points": ["B point"],
                    "tags": ["tag-b"],
                    "action_items": ["B action"],
                },
            ),
        ]
        accepted = (row.model, row.provider_response_id, row.result_json)
        assert accepted in accepted_candidates
        rejected = next(
            candidate for candidate in accepted_candidates if candidate != accepted
        )
        assert row.model != rejected[0]
        assert row.provider_response_id != rejected[1]
        assert row.result_json != rejected[2]
        assert row.source_artifact_id == raw_before.artifact_id
        assert row.source_content_sha256
        assert row.prompt_version == PROMPT_VERSION
        assert row.schema_version == SCHEMA_VERSION
        await assert_raw_state_unchanged(message_id, tmp_path, raw_before)
        await assert_enriched_git_sha_is_null(message_id)

    asyncio.run(run())


def test_unrelated_integrity_error_propagates(tmp_path: Path) -> None:
    async def run() -> None:
        message_id = await create_done_message(tmp_path)
        factory = async_sessionmaker(
            get_engine(),
            expire_on_commit=False,
            class_=UnrelatedIntegritySession,
        )

        with pytest.raises(IntegrityError):
            await enrich_text_message(
                message_id=message_id,
                knowledge_base_root=tmp_path,
                provider=StaticProvider(calls=[], result=provider_result()),
                session_factory=factory,
            )

        assert await enrichment_count(message_id) == 0
        assert await enriched_artifact_count(message_id) == 0

    asyncio.run(run())


@pytest.mark.parametrize(
    ("field", "bad_value"),
    (("prompt_version", 999), ("schema_version", 999)),
)
def test_unsupported_persisted_versions_fail_without_provider_or_row_mutation(
    tmp_path: Path,
    field: str,
    bad_value: int,
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
            async with session.begin():
                row = await session.get(AIEnrichment, first.ai_enrichment_id)
                assert row is not None
                setattr(row, field, bad_value)
        before = await enrichment_row(message_id)
        provider = FakeProvider(calls=[])

        with pytest.raises(AIEnrichmentConsistencyError):
            await enrich_text_message(
                message_id=message_id,
                knowledge_base_root=tmp_path,
                provider=provider,
            )

        after = await enrichment_row(message_id)
        assert provider.calls == []
        assert getattr(after, field) == bad_value
        assert after.model == before.model
        assert after.provider_response_id == before.provider_response_id
        assert after.result_json == before.result_json

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
