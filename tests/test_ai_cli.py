import asyncio
import uuid
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import func
from sqlalchemy import select

from app.db.models import AIEnrichment
from app.db.models import Artifact
from app.db.models import Message
from app.db.models import User
from app.db.session import dispose_engine
from app.db.session import get_session_factory
from app.knowledge import ai_cli
from app.knowledge.ai_enrichment import enrich_text_message
from app.knowledge.ai_enrichment import AIEnrichmentResult
from app.knowledge.ai_errors import AIEnrichmentSourceError
from app.knowledge.ai_errors import AIProviderResponseError
from app.knowledge.ai_provider import ProviderEnrichmentResult
from app.knowledge.ai_schema import EnrichmentResult
from app.knowledge.enriched_markdown import ENRICHED_ARTIFACT_TYPE
from app.knowledge.processing import process_text_message


MESSAGE_ID = uuid.UUID("123e4567-e89b-12d3-a456-426614174000")


@dataclass
class FakeProvider:
    calls: list[str]

    async def enrich(self, _source_text: str) -> ProviderEnrichmentResult:
        self.calls.append(_source_text)
        return ProviderEnrichmentResult(
            provider="openai",
            model="model",
            response_id="resp",
            enrichment=EnrichmentResult(
                title="CLI enriched title",
                summary="CLI summary",
                key_points=["Point"],
                tags=["tag"],
                action_items=[],
            ),
        )


async def create_done_message(root: Path, raw_text: str = "CLI source") -> uuid.UUID:
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


async def ai_state_counts(message_id: uuid.UUID) -> tuple[int, int]:
    return await enrichment_count(message_id), await enriched_artifact_count(message_id)


def install_settings(
    monkeypatch: pytest.MonkeyPatch,
    *,
    root: Path,
    api_key: str,
    model: str,
) -> None:
    monkeypatch.setattr(
        ai_cli,
        "get_settings",
        lambda: SimpleNamespace(
            knowledge_base_path=root,
            openai_api_key=api_key,
            openai_model=model,
        ),
    )


def test_invalid_uuid_uses_argparse_status_2() -> None:
    with pytest.raises(SystemExit) as caught:
        ai_cli.main(["--message-id", "not-a-uuid"])

    assert caught.value.code == 2


@pytest.mark.parametrize("outcome", ("created", "reconciled", "existing"))
def test_success_output_is_exact(monkeypatch, capsys, outcome: str) -> None:
    async def fake_enrich_text_message(**_kwargs):
        return AIEnrichmentResult(
            message_id=MESSAGE_ID,
            source_artifact_id=uuid.UUID("223e4567-e89b-12d3-a456-426614174000"),
            ai_enrichment_id=uuid.UUID("323e4567-e89b-12d3-a456-426614174000"),
            enriched_artifact_id=uuid.UUID("423e4567-e89b-12d3-a456-426614174000"),
            file_path="processed/2026-07-07--123e4567-e89b-12d3-a456-426614174000.md",
            provider="openai",
            model="gpt-test",
            outcome=outcome,  # type: ignore[arg-type]
        )

    monkeypatch.setattr(ai_cli, "enrich_text_message", fake_enrich_text_message)

    assert ai_cli.main(["--message-id", str(MESSAGE_ID)]) == 0

    assert capsys.readouterr().out == (
        "message_id: 123e4567-e89b-12d3-a456-426614174000\n"
        "source_artifact_id: 223e4567-e89b-12d3-a456-426614174000\n"
        "ai_enrichment_id: 323e4567-e89b-12d3-a456-426614174000\n"
        "enriched_artifact_id: 423e4567-e89b-12d3-a456-426614174000\n"
        "file_path: processed/2026-07-07--123e4567-e89b-12d3-a456-426614174000.md\n"
        "provider: openai\n"
        "model: gpt-test\n"
        f"outcome: {outcome}\n"
    )


def test_expected_error_returns_status_1(monkeypatch, capsys) -> None:
    async def fake_enrich_text_message(**_kwargs):
        raise AIEnrichmentSourceError("safe reason")

    monkeypatch.setattr(ai_cli, "enrich_text_message", fake_enrich_text_message)

    assert ai_cli.main(["--message-id", str(MESSAGE_ID)]) == 1
    assert capsys.readouterr().err == "AI enrichment failed: safe reason\n"


@pytest.mark.parametrize(
    ("api_key", "model", "expected"),
    (
        ("", "gpt-test", "OPENAI_API_KEY is required"),
        ("secret-key", "", "OPENAI_MODEL is required"),
    ),
)
def test_blank_openai_configuration_fails_when_new_request_is_required(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    api_key: str,
    model: str,
    expected: str,
) -> None:
    async def arrange() -> uuid.UUID:
        return await create_done_message(tmp_path)

    message_id = asyncio.run(arrange())
    asyncio.run(dispose_engine())
    install_settings(monkeypatch, root=tmp_path, api_key=api_key, model=model)

    assert ai_cli.main(["--message-id", str(message_id)]) == 1

    captured = capsys.readouterr()
    assert expected in captured.err
    assert "CLI source" not in captured.err
    assert "secret-key" not in captured.err
    asyncio.run(dispose_engine())
    assert asyncio.run(ai_state_counts(message_id)) == (0, 0)
    assert not (tmp_path / "processed").exists()


def test_existing_enrichment_cli_reconciles_with_blank_configuration(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    class NoRequestProvider:
        calls: list[str] = []

        def __init__(self, **_kwargs) -> None:
            pass

        async def enrich(self, source_text: str):
            self.calls.append(source_text)
            raise AssertionError("provider request should not run")

    async def arrange() -> tuple[uuid.UUID, uuid.UUID, str]:
        message_id = await create_done_message(tmp_path)
        result = await enrich_text_message(
            message_id=message_id,
            knowledge_base_root=tmp_path,
            provider=FakeProvider(calls=[]),
        )
        session_factory = get_session_factory()
        async with session_factory() as session:
            artifact = await session.get(Artifact, result.enriched_artifact_id)
            assert artifact is not None
            await session.delete(artifact)
            await session.commit()
        (tmp_path / result.file_path).unlink()
        return message_id, result.ai_enrichment_id, result.file_path

    message_id, enrichment_id, file_path = asyncio.run(arrange())
    asyncio.run(dispose_engine())
    install_settings(monkeypatch, root=tmp_path, api_key="", model="")
    monkeypatch.setattr(ai_cli, "OpenAIEnrichmentProvider", NoRequestProvider)

    assert ai_cli.main(["--message-id", str(message_id)]) == 0

    captured = capsys.readouterr()
    assert f"message_id: {message_id}\n" in captured.out
    assert f"ai_enrichment_id: {enrichment_id}\n" in captured.out
    assert f"file_path: {file_path}\n" in captured.out
    assert "outcome: reconciled\n" in captured.out
    assert NoRequestProvider.calls == []
    assert (tmp_path / file_path).exists()
    asyncio.run(dispose_engine())
    assert asyncio.run(enriched_artifact_count(message_id)) == 1


@pytest.mark.parametrize("failure_kind", ("source", "provider", "domain"))
def test_cli_failures_are_sanitized(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    failure_kind: str,
) -> None:
    secret_key = "SECRET_OPENAI_KEY"
    secret_source = "SECRET_SOURCE_TEXT"
    secret_payload = "SECRET_PROVIDER_PAYLOAD"

    class FailingProvider:
        def __init__(self, **_kwargs) -> None:
            pass

        async def enrich(self, _source_text: str):
            raise AIProviderResponseError("provider failed safely")

    async def arrange() -> uuid.UUID:
        if failure_kind == "source":
            return await create_done_message(tmp_path, raw_text="   \n")
        message_id = await create_done_message(tmp_path, raw_text=secret_source)
        if failure_kind == "domain":
            result = await enrich_text_message(
                message_id=message_id,
                knowledge_base_root=tmp_path,
                provider=FakeProvider(calls=[]),
            )
            session_factory = get_session_factory()
            async with session_factory() as session:
                async with session.begin():
                    artifact = await session.get(Artifact, result.enriched_artifact_id)
                    assert artifact is not None
                    artifact.title = "wrong title"
        return message_id

    message_id = asyncio.run(arrange())
    asyncio.run(dispose_engine())
    install_settings(monkeypatch, root=tmp_path, api_key=secret_key, model="model")
    if failure_kind == "provider":
        monkeypatch.setattr(ai_cli, "OpenAIEnrichmentProvider", FailingProvider)

    assert ai_cli.main(["--message-id", str(message_id)]) == 1

    captured = capsys.readouterr()
    assert "AI enrichment failed:" in captured.err
    assert secret_key not in captured.err
    assert secret_source not in captured.err
    assert secret_payload not in captured.err


def test_cli_does_not_start_application_runtimes(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    calls: list[str] = []

    async def fake_enrich_text_message(**_kwargs):
        calls.append("enrich")
        return AIEnrichmentResult(
            message_id=MESSAGE_ID,
            source_artifact_id=uuid.UUID("223e4567-e89b-12d3-a456-426614174000"),
            ai_enrichment_id=uuid.UUID("323e4567-e89b-12d3-a456-426614174000"),
            enriched_artifact_id=uuid.UUID("423e4567-e89b-12d3-a456-426614174000"),
            file_path="processed/2026-07-07--123e4567-e89b-12d3-a456-426614174000.md",
            provider="openai",
            model="gpt-test",
            outcome="existing",
        )

    monkeypatch.setattr(ai_cli, "enrich_text_message", fake_enrich_text_message)

    assert ai_cli.main(["--message-id", str(MESSAGE_ID)]) == 0

    assert calls == ["enrich"]
    assert "outcome: existing\n" in capsys.readouterr().out
