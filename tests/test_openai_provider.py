from types import SimpleNamespace

import openai
import pytest

from app.knowledge.ai_errors import AIProviderConfigurationError
from app.knowledge.ai_errors import AIProviderIncompleteError
from app.knowledge.ai_errors import AIProviderRefusalError
from app.knowledge.ai_errors import AIProviderTimeoutError
from app.knowledge.openai_provider import OpenAIEnrichmentProvider


class FakeAsyncOpenAI:
    calls: list[dict[str, object]] = []
    response: object | None = None
    error: Exception | None = None
    init_kwargs: dict[str, object] | None = None

    def __init__(self, **kwargs):
        type(self).init_kwargs = kwargs
        self.responses = self

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    async def parse(self, **kwargs):
        type(self).calls.append(kwargs)
        if type(self).error is not None:
            raise type(self).error
        return type(self).response


def parsed_response(**overrides):
    payload = {
        "id": "resp_123",
        "model": "gpt-test-returned",
        "status": "completed",
        "output_parsed": {
            "title": "Title",
            "summary": "Summary",
            "key_points": [],
            "tags": [],
            "action_items": [],
        },
        "output": [],
        "incomplete_details": None,
    }
    payload.update(overrides)
    return SimpleNamespace(**payload)


@pytest.fixture(autouse=True)
def reset_fake(monkeypatch):
    FakeAsyncOpenAI.calls = []
    FakeAsyncOpenAI.response = parsed_response()
    FakeAsyncOpenAI.error = None
    FakeAsyncOpenAI.init_kwargs = None
    monkeypatch.setattr("app.knowledge.openai_provider.AsyncOpenAI", FakeAsyncOpenAI)


def test_missing_configuration_fails_without_client() -> None:
    provider = OpenAIEnrichmentProvider(api_key="", model="")

    async def run() -> None:
        with pytest.raises(AIProviderConfigurationError):
            await provider.enrich("source")

    import asyncio

    asyncio.run(run())
    assert FakeAsyncOpenAI.init_kwargs is None


def test_request_shape_and_response_provenance() -> None:
    provider = OpenAIEnrichmentProvider(api_key=" key ", model=" gpt-test ")

    async def run() -> None:
        result = await provider.enrich("canonical source")
        assert result.provider == "openai"
        assert result.model == "gpt-test-returned"
        assert result.response_id == "resp_123"
        assert result.enrichment.title == "Title"

    import asyncio

    asyncio.run(run())
    assert FakeAsyncOpenAI.init_kwargs == {
        "api_key": "key",
        "max_retries": 0,
        "timeout": 60.0,
    }
    assert len(FakeAsyncOpenAI.calls) == 1
    call = FakeAsyncOpenAI.calls[0]
    assert call["model"] == "gpt-test"
    assert call["input"] == "canonical source"
    assert call["text_format"].__name__ == "EnrichmentResult"
    assert call["store"] is False
    assert call["max_output_tokens"] == 2000
    for prohibited in (
        "tools",
        "conversation",
        "previous_response_id",
        "metadata",
        "user",
    ):
        assert prohibited not in call


def test_refusal_and_incomplete_are_rejected() -> None:
    async def run() -> None:
        FakeAsyncOpenAI.response = parsed_response(
            output=[
                SimpleNamespace(
                    type="message",
                    content=[SimpleNamespace(type="refusal", refusal="hidden")],
                )
            ]
        )
        with pytest.raises(AIProviderRefusalError):
            await OpenAIEnrichmentProvider(api_key="key", model="model").enrich("x")

        FakeAsyncOpenAI.response = parsed_response(
            status="incomplete",
            incomplete_details=SimpleNamespace(reason="max_output_tokens"),
        )
        with pytest.raises(AIProviderIncompleteError):
            await OpenAIEnrichmentProvider(api_key="key", model="model").enrich("x")

    import asyncio

    asyncio.run(run())


def test_timeout_translates_by_type() -> None:
    async def run() -> None:
        import httpx

        FakeAsyncOpenAI.error = openai.APITimeoutError(
            request=httpx.Request("POST", "https://api.openai.com/v1/responses")
        )
        with pytest.raises(AIProviderTimeoutError) as caught:
            await OpenAIEnrichmentProvider(api_key="key", model="model").enrich("x")
        assert "secret" not in str(caught.value)

    import asyncio

    asyncio.run(run())
