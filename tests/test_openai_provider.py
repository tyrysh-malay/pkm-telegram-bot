from types import SimpleNamespace
from typing import Callable

import httpx
import openai
import pytest
from pydantic import ValidationError

from app.knowledge.ai_errors import AIProviderAuthenticationError
from app.knowledge.ai_errors import AIProviderConnectionError
from app.knowledge.ai_errors import AIProviderConfigurationError
from app.knowledge.ai_errors import AIProviderIncompleteError
from app.knowledge.ai_errors import AIProviderInvalidRequestError
from app.knowledge.ai_errors import AIProviderOperationalError
from app.knowledge.ai_errors import AIProviderPermissionError
from app.knowledge.ai_errors import AIProviderRateLimitError
from app.knowledge.ai_errors import AIProviderRefusalError
from app.knowledge.ai_errors import AIProviderResponseError
from app.knowledge.ai_errors import AIProviderServerError
from app.knowledge.ai_errors import AIProviderTimeoutError
from app.knowledge.ai_schema import EnrichmentResult
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


def sdk_request() -> httpx.Request:
    return httpx.Request("POST", "https://api.openai.com/v1/responses")


def sdk_response(status_code: int) -> httpx.Response:
    return httpx.Response(status_code, request=sdk_request())


def api_status_error(
    cls: type[openai.APIStatusError],
    status_code: int,
) -> openai.APIStatusError:
    return cls(
        "RAW_PROVIDER_SECRET",
        response=sdk_response(status_code),
        body={"secret": "RAW_BODY_SECRET"},
    )


def api_response_validation_error() -> openai.APIResponseValidationError:
    return openai.APIResponseValidationError(
        sdk_response(200),
        {"secret": "RAW_BODY_SECRET"},
        message="RAW_PROVIDER_SECRET",
    )


def pydantic_validation_error() -> ValidationError:
    try:
        EnrichmentResult.model_validate({})
    except ValidationError as exc:
        return exc
    raise AssertionError("expected validation error")


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


@pytest.mark.parametrize(
    ("make_error", "expected_error"),
    (
        (lambda: openai.APITimeoutError(request=sdk_request()), AIProviderTimeoutError),
        (
            lambda: api_status_error(openai.RateLimitError, 429),
            AIProviderRateLimitError,
        ),
        (
            lambda: openai.APIConnectionError(
                message="RAW_PROVIDER_SECRET",
                request=sdk_request(),
            ),
            AIProviderConnectionError,
        ),
        (
            lambda: api_status_error(openai.AuthenticationError, 401),
            AIProviderAuthenticationError,
        ),
        (
            lambda: api_status_error(openai.PermissionDeniedError, 403),
            AIProviderPermissionError,
        ),
        (
            lambda: api_status_error(openai.BadRequestError, 400),
            AIProviderInvalidRequestError,
        ),
        (
            lambda: api_status_error(openai.NotFoundError, 404),
            AIProviderInvalidRequestError,
        ),
        (
            lambda: api_status_error(openai.UnprocessableEntityError, 422),
            AIProviderInvalidRequestError,
        ),
        (
            lambda: api_status_error(openai.APIStatusError, 409),
            AIProviderInvalidRequestError,
        ),
        (
            lambda: api_status_error(openai.InternalServerError, 500),
            AIProviderServerError,
        ),
        (
            lambda: api_status_error(openai.APIStatusError, 503),
            AIProviderServerError,
        ),
        (
            api_response_validation_error,
            AIProviderResponseError,
        ),
        (
            lambda: openai.APIError(
                "RAW_PROVIDER_SECRET",
                sdk_request(),
                body={"secret": "RAW_BODY_SECRET"},
            ),
            AIProviderOperationalError,
        ),
        (
            pydantic_validation_error,
            AIProviderResponseError,
        ),
    ),
)
def test_sdk_errors_translate_by_type_without_leaking_payloads(
    make_error: Callable[[], Exception],
    expected_error: type[Exception],
) -> None:
    async def run() -> None:
        FakeAsyncOpenAI.error = make_error()
        with pytest.raises(expected_error) as caught:
            await OpenAIEnrichmentProvider(
                api_key="SECRET_API_KEY",
                model="model",
            ).enrich("SECRET_SOURCE_TEXT")

        message = str(caught.value)
        assert "RAW_PROVIDER_SECRET" not in message
        assert "RAW_BODY_SECRET" not in message
        assert "SECRET_API_KEY" not in message
        assert "SECRET_SOURCE_TEXT" not in message
        assert len(FakeAsyncOpenAI.calls) == 1

    import asyncio

    asyncio.run(run())


@pytest.mark.parametrize("reason", ("content_filter", "max_output_tokens"))
def test_incomplete_reasons_are_permanent_failures(reason: str) -> None:
    async def run() -> None:
        FakeAsyncOpenAI.response = parsed_response(
            status="incomplete",
            incomplete_details=SimpleNamespace(reason=reason),
        )
        with pytest.raises(AIProviderIncompleteError):
            await OpenAIEnrichmentProvider(api_key="key", model="model").enrich("x")
        assert len(FakeAsyncOpenAI.calls) == 1

    import asyncio

    asyncio.run(run())


@pytest.mark.parametrize(
    ("response", "expected_error"),
    (
        (parsed_response(status="queued"), AIProviderResponseError),
        (parsed_response(output_parsed=None), AIProviderResponseError),
        (parsed_response(output_parsed={"title": "Only title"}), AIProviderResponseError),
        (parsed_response(model=123), AIProviderResponseError),
        (parsed_response(model=" "), AIProviderResponseError),
        (parsed_response(model="bad\0model"), AIProviderResponseError),
        (parsed_response(id=123), AIProviderResponseError),
        (parsed_response(id=" "), AIProviderResponseError),
        (parsed_response(id="bad\0id"), AIProviderResponseError),
    ),
)
def test_malformed_completed_responses_are_response_errors(
    response: object,
    expected_error: type[Exception],
) -> None:
    async def run() -> None:
        FakeAsyncOpenAI.response = response
        with pytest.raises(expected_error):
            await OpenAIEnrichmentProvider(api_key="key", model="model").enrich(
                "SECRET_SOURCE_TEXT"
            )
        assert len(FakeAsyncOpenAI.calls) == 1

    import asyncio

    asyncio.run(run())
