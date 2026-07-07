import json
import re
import unicodedata

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator


SCHEMA_VERSION = 1

_WHITESPACE = re.compile(r"\s+", re.UNICODE)


def _normalize_text(value: str, *, field_name: str, max_length: int) -> str:
    if "\0" in value:
        raise ValueError(f"{field_name} contains NUL")
    normalized = value.replace("\r\n", "\n").replace("\r", "\n")
    normalized = _WHITESPACE.sub(" ", normalized).strip()
    if not normalized:
        raise ValueError(f"{field_name} must be non-empty")
    if len(normalized) > max_length:
        raise ValueError(f"{field_name} is too long")
    return normalized


def _normalize_tag(value: str) -> str:
    if "\0" in value:
        raise ValueError("tag contains NUL")
    normalized = unicodedata.normalize("NFKC", value).strip()
    if normalized.startswith("#"):
        normalized = normalized[1:].strip()
    normalized = _WHITESPACE.sub(" ", normalized).strip()
    if not normalized:
        raise ValueError("tag must be non-empty")
    if len(normalized) > 64:
        raise ValueError("tag is too long")
    return normalized


def _deduplicate(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduplicated: list[str] = []
    for value in values:
        key = unicodedata.normalize("NFKC", value).casefold()
        if key in seen:
            continue
        seen.add(key)
        deduplicated.append(value)
    return deduplicated


class EnrichmentResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    title: str
    summary: str
    key_points: list[str] = Field(max_length=12)
    tags: list[str] = Field(max_length=12)
    action_items: list[str] = Field(max_length=12)

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str) -> str:
        return _normalize_text(value, field_name="title", max_length=160)

    @field_validator("summary")
    @classmethod
    def normalize_summary(cls, value: str) -> str:
        return _normalize_text(value, field_name="summary", max_length=2000)

    @field_validator("key_points")
    @classmethod
    def normalize_key_points(cls, values: list[str]) -> list[str]:
        return _deduplicate(
            [
                _normalize_text(value, field_name="key point", max_length=500)
                for value in values
            ]
        )

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, values: list[str]) -> list[str]:
        return _deduplicate([_normalize_tag(value) for value in values])

    @field_validator("action_items")
    @classmethod
    def normalize_action_items(cls, values: list[str]) -> list[str]:
        return _deduplicate(
            [
                _normalize_text(value, field_name="action item", max_length=500)
                for value in values
            ]
        )


def canonical_enrichment_json(enrichment: EnrichmentResult) -> str:
    return json.dumps(
        enrichment.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def canonical_enrichment_json_bytes(enrichment: EnrichmentResult) -> bytes:
    return canonical_enrichment_json(enrichment).encode("utf-8")
