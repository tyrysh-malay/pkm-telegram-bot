import uuid
from datetime import datetime
from datetime import timedelta
from datetime import timezone

from app.knowledge.ai_schema import EnrichmentResult
from app.knowledge.enriched_markdown import AIEnrichmentSnapshot
from app.knowledge.enriched_markdown import MessageSnapshot
from app.knowledge.enriched_markdown import render_enriched_note


MESSAGE_ID = uuid.UUID("123e4567-e89b-12d3-a456-426614174000")
SOURCE_ARTIFACT_ID = uuid.UUID("223e4567-e89b-12d3-a456-426614174000")
ENRICHMENT_ID = uuid.UUID("323e4567-e89b-12d3-a456-426614174000")


def test_enriched_markdown_contract_is_deterministic() -> None:
    result = EnrichmentResult(
        title="Привет, world!",
        summary="Supported summary.",
        key_points=["First", "Second"],
        tags=["тег", "tag two"],
        action_items=[],
    )

    rendered = render_enriched_note(
        message=MessageSnapshot(
            id=MESSAGE_ID,
            created_at=datetime(
                2026,
                7,
                3,
                1,
                2,
                3,
                4,
                tzinfo=timezone(timedelta(hours=3)),
            ),
        ),
        source_artifact_id=SOURCE_ARTIFACT_ID,
        enrichment=AIEnrichmentSnapshot(
            id=ENRICHMENT_ID,
            created_at=datetime(2026, 7, 7, 10, 11, 12, 13, tzinfo=timezone.utc),
            source_content_sha256="a" * 64,
            provider="openai",
            model="gpt-test",
            response_id=None,
            prompt_version=1,
            schema_version=1,
        ),
        result=result,
    )

    assert rendered.title == "Привет, world!"
    assert rendered.slug == "привет-world"
    assert rendered.file_path == (
        "processed/2026-07-02--123e4567-e89b-12d3-a456-426614174000.md"
    )
    assert rendered.content.decode("utf-8") == (
        "---\n"
        "format_version: 1\n"
        'artifact_type: "enriched_note"\n'
        'source: "telegram"\n'
        'source_message_id: "123e4567-e89b-12d3-a456-426614174000"\n'
        'source_artifact_id: "223e4567-e89b-12d3-a456-426614174000"\n'
        f'source_content_sha256: "{"a" * 64}"\n'
        'ai_enrichment_id: "323e4567-e89b-12d3-a456-426614174000"\n'
        'captured_at: "2026-07-02T22:02:03.000004Z"\n'
        'enriched_at: "2026-07-07T10:11:12.000013Z"\n'
        'ai_provider: "openai"\n'
        'ai_model: "gpt-test"\n'
        "provider_response_id: null\n"
        "prompt_version: 1\n"
        "schema_version: 1\n"
        'title: "Привет, world!"\n'
        'slug: "привет-world"\n'
        'tags: ["тег", "tag two"]\n'
        "---\n"
        "\n"
        "# Привет, world!\n"
        "\n"
        "## Summary\n"
        "\n"
        "Supported summary.\n"
        "\n"
        "## Key points\n"
        "\n"
        "- First\n"
        "- Second\n"
        "\n"
        "## Action items\n"
        "\n"
        "_None._\n"
    )


def test_response_id_renders_quoted_and_empty_key_points_render_none() -> None:
    rendered = render_enriched_note(
        message=MessageSnapshot(
            id=MESSAGE_ID,
            created_at=datetime(2026, 7, 7, tzinfo=timezone.utc),
        ),
        source_artifact_id=SOURCE_ARTIFACT_ID,
        enrichment=AIEnrichmentSnapshot(
            id=ENRICHMENT_ID,
            created_at=datetime(2026, 7, 7, tzinfo=timezone.utc),
            source_content_sha256="b" * 64,
            provider="openai",
            model="gpt-test",
            response_id='resp_"x"',
            prompt_version=1,
            schema_version=1,
        ),
        result=EnrichmentResult(
            title="Title",
            summary="Summary",
            key_points=[],
            tags=[],
            action_items=["Act"],
        ),
    ).content.decode()

    assert 'provider_response_id: "resp_\\"x\\""' in rendered
    assert "\n## Key points\n\n_None._\n" in rendered
    assert rendered.endswith("\n")
    assert not rendered.endswith("\n\n")
