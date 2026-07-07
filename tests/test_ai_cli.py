import uuid

import pytest

from app.knowledge import ai_cli
from app.knowledge.ai_enrichment import AIEnrichmentResult
from app.knowledge.ai_errors import AIEnrichmentSourceError


MESSAGE_ID = uuid.UUID("123e4567-e89b-12d3-a456-426614174000")


def test_invalid_uuid_uses_argparse_status_2() -> None:
    with pytest.raises(SystemExit) as caught:
        ai_cli.main(["--message-id", "not-a-uuid"])

    assert caught.value.code == 2


def test_success_output_is_exact(monkeypatch, capsys) -> None:
    async def fake_enrich_text_message(**_kwargs):
        return AIEnrichmentResult(
            message_id=MESSAGE_ID,
            source_artifact_id=uuid.UUID("223e4567-e89b-12d3-a456-426614174000"),
            ai_enrichment_id=uuid.UUID("323e4567-e89b-12d3-a456-426614174000"),
            enriched_artifact_id=uuid.UUID("423e4567-e89b-12d3-a456-426614174000"),
            file_path="processed/2026-07-07--123e4567-e89b-12d3-a456-426614174000.md",
            provider="openai",
            model="gpt-test",
            outcome="created",
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
        "outcome: created\n"
    )


def test_expected_error_returns_status_1(monkeypatch, capsys) -> None:
    async def fake_enrich_text_message(**_kwargs):
        raise AIEnrichmentSourceError("safe reason")

    monkeypatch.setattr(ai_cli, "enrich_text_message", fake_enrich_text_message)

    assert ai_cli.main(["--message-id", str(MESSAGE_ID)]) == 1
    assert capsys.readouterr().err == "AI enrichment failed: safe reason\n"
