import pytest
from pydantic import ValidationError

from app.knowledge.ai_schema import EnrichmentResult
from app.knowledge.ai_schema import canonical_enrichment_json_bytes


def test_valid_result_normalizes_and_preserves_unicode() -> None:
    result = EnrichmentResult(
        title="  Привет\tмир  ",
        summary="One\r\nparagraph\nwith\tspace",
        key_points=[" Point  one ", "point one", "Second"],
        tags=[" #Тег ", "тег", "next tag"],
        action_items=[" Do  it ", "do it"],
    )

    assert result.title == "Привет мир"
    assert result.summary == "One paragraph with space"
    assert result.key_points == ["Point one", "Second"]
    assert result.tags == ["Тег", "next tag"]
    assert result.action_items == ["Do it"]


@pytest.mark.parametrize("field", ("key_points", "tags", "action_items"))
def test_duplicate_entries_collapse_before_list_limit(field: str) -> None:
    payload = {
        "title": "Title",
        "summary": "Summary",
        "key_points": [],
        "tags": [],
        "action_items": [],
    }
    payload[field] = ["  Example  ", "ｅｘａｍｐｌｅ", "EXAMPLE"] * 5

    result = EnrichmentResult(**payload)

    assert getattr(result, field) == ["Example"]


@pytest.mark.parametrize("field", ("key_points", "tags", "action_items"))
def test_more_than_twelve_distinct_normalized_items_fail(field: str) -> None:
    payload = {
        "title": "Title",
        "summary": "Summary",
        "key_points": [],
        "tags": [],
        "action_items": [],
    }
    payload[field] = [f"Item {index}" for index in range(13)]

    with pytest.raises(ValidationError):
        EnrichmentResult(**payload)


@pytest.mark.parametrize("field", ("key_points", "tags", "action_items"))
def test_exactly_twelve_distinct_normalized_items_are_accepted(field: str) -> None:
    payload = {
        "title": "Title",
        "summary": "Summary",
        "key_points": [],
        "tags": [],
        "action_items": [],
    }
    payload[field] = [f"Item {index}" for index in range(12)]

    result = EnrichmentResult(**payload)

    assert getattr(result, field) == [f"Item {index}" for index in range(12)]


def test_list_deduplication_preserves_first_display_value_and_order() -> None:
    result = EnrichmentResult(
        title="Title",
        summary="Summary",
        key_points=[" Beta ", "Alpha", "beta", "Gamma", "ALPHA"],
        tags=[" #Second ", "First", "second", "Third", "#first"],
        action_items=["Later", " Now ", "later", "Done"],
    )

    assert result.key_points == ["Beta", "Alpha", "Gamma"]
    assert result.tags == ["Second", "First", "Third"]
    assert result.action_items == ["Later", "Now", "Done"]


@pytest.mark.parametrize("field", ("key_points", "tags", "action_items"))
def test_list_fields_reject_non_lists_and_non_string_items(field: str) -> None:
    payload = {
        "title": "Title",
        "summary": "Summary",
        "key_points": [],
        "tags": [],
        "action_items": [],
    }
    payload[field] = "not a list"
    with pytest.raises(ValidationError):
        EnrichmentResult(**payload)

    payload[field] = ["valid", 123]
    with pytest.raises(ValidationError):
        EnrichmentResult(**payload)


def test_extra_missing_empty_and_nul_values_fail() -> None:
    with pytest.raises(ValidationError):
        EnrichmentResult(
            title="Title",
            summary="Summary",
            key_points=[],
            tags=[],
            action_items=[],
            extra="nope",
        )
    with pytest.raises(ValidationError):
        EnrichmentResult(
            title=" ",
            summary="Summary",
            key_points=[],
            tags=[],
            action_items=[],
        )
    with pytest.raises(ValidationError):
        EnrichmentResult(
            title="Title",
            summary="bad\0summary",
            key_points=[],
            tags=[],
            action_items=[],
        )


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("title", "x" * 161),
        ("summary", "x" * 2001),
        ("key_points", [f"x{index}" for index in range(13)]),
        ("tags", [f"x{index}" for index in range(13)]),
        ("action_items", [f"x{index}" for index in range(13)]),
        ("key_points", ["x" * 501]),
        ("tags", ["x" * 65]),
        ("action_items", ["x" * 501]),
    ),
)
def test_limits_are_enforced(field: str, value: object) -> None:
    payload = {
        "title": "Title",
        "summary": "Summary",
        "key_points": [],
        "tags": [],
        "action_items": [],
    }
    payload[field] = value

    with pytest.raises(ValidationError):
        EnrichmentResult(**payload)


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("key_points", ["  " + ("x" * 501) + "  "]),
        ("tags", ["  #" + ("x" * 65) + "  "]),
        ("action_items", ["  " + ("x" * 501) + "  "]),
    ),
)
def test_item_length_limits_apply_after_normalization(
    field: str,
    value: list[str],
) -> None:
    payload = {
        "title": "Title",
        "summary": "Summary",
        "key_points": [],
        "tags": [],
        "action_items": [],
    }
    payload[field] = value

    with pytest.raises(ValidationError):
        EnrichmentResult(**payload)


def test_canonical_json_bytes_are_stable() -> None:
    result = EnrichmentResult(
        title="Title",
        summary="Summary",
        key_points=["B", "A"],
        tags=["тег"],
        action_items=[],
    )

    assert canonical_enrichment_json_bytes(result) == (
        '{"action_items":[],"key_points":["B","A"],'
        '"summary":"Summary","tags":["тег"],"title":"Title"}'
    ).encode("utf-8")
