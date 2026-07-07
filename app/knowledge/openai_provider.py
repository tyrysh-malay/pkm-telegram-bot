from typing import Any

import openai
from openai import AsyncOpenAI
from pydantic import ValidationError

from app.knowledge.ai_errors import AIProviderAuthenticationError
from app.knowledge.ai_errors import AIProviderConfigurationError
from app.knowledge.ai_errors import AIProviderConnectionError
from app.knowledge.ai_errors import AIProviderIncompleteError
from app.knowledge.ai_errors import AIProviderInvalidRequestError
from app.knowledge.ai_errors import AIProviderOperationalError
from app.knowledge.ai_errors import AIProviderPermissionError
from app.knowledge.ai_errors import AIProviderRateLimitError
from app.knowledge.ai_errors import AIProviderRefusalError
from app.knowledge.ai_errors import AIProviderResponseError
from app.knowledge.ai_errors import AIProviderServerError
from app.knowledge.ai_errors import AIProviderTimeoutError
from app.knowledge.ai_provider import OPENAI_PROVIDER_NAME
from app.knowledge.ai_provider import PROMPT_V1
from app.knowledge.ai_provider import ProviderEnrichmentResult
from app.knowledge.ai_schema import EnrichmentResult


OPENAI_REQUEST_TIMEOUT_SECONDS = 60.0
OPENAI_MAX_OUTPUT_TOKENS = 2000


class OpenAIEnrichmentProvider:
    def __init__(
        self,
        *,
        api_key: str | None,
        model: str | None,
    ) -> None:
        self._api_key = api_key
        self._model = model

    def _configuration(self) -> tuple[str, str]:
        api_key = self._api_key.strip() if self._api_key is not None else ""
        model = self._model.strip() if self._model is not None else ""
        if not api_key:
            raise AIProviderConfigurationError("OPENAI_API_KEY is required")
        if not model:
            raise AIProviderConfigurationError("OPENAI_MODEL is required")
        return api_key, model

    async def enrich(self, source_text: str) -> ProviderEnrichmentResult:
        api_key, model = self._configuration()
        try:
            async with AsyncOpenAI(
                api_key=api_key,
                max_retries=0,
                timeout=OPENAI_REQUEST_TIMEOUT_SECONDS,
            ) as client:
                response = await client.responses.parse(
                    model=model,
                    instructions=PROMPT_V1,
                    input=source_text,
                    text_format=EnrichmentResult,
                    store=False,
                    max_output_tokens=OPENAI_MAX_OUTPUT_TOKENS,
                )
        except openai.APITimeoutError as exc:
            raise AIProviderTimeoutError("OpenAI request timed out") from exc
        except openai.RateLimitError as exc:
            raise AIProviderRateLimitError("OpenAI request was rate limited") from exc
        except openai.APIConnectionError as exc:
            raise AIProviderConnectionError("OpenAI connection failed") from exc
        except openai.AuthenticationError as exc:
            raise AIProviderAuthenticationError("OpenAI authentication failed") from exc
        except openai.PermissionDeniedError as exc:
            raise AIProviderPermissionError("OpenAI permission denied") from exc
        except (
            openai.BadRequestError,
            openai.NotFoundError,
            openai.UnprocessableEntityError,
        ) as exc:
            raise AIProviderInvalidRequestError("OpenAI rejected the request") from exc
        except openai.InternalServerError as exc:
            raise AIProviderServerError("OpenAI server error") from exc
        except openai.APIStatusError as exc:
            if 400 <= exc.status_code < 500:
                raise AIProviderInvalidRequestError(
                    "OpenAI rejected the request"
                ) from exc
            if exc.status_code >= 500:
                raise AIProviderServerError("OpenAI server error") from exc
            raise AIProviderOperationalError("OpenAI API status error") from exc
        except openai.APIError as exc:
            raise AIProviderOperationalError("OpenAI API error") from exc
        except ValidationError as exc:
            raise AIProviderResponseError("OpenAI response failed schema parsing") from exc

        self._validate_response_status(response)
        parsed = getattr(response, "output_parsed", None)
        if parsed is None:
            raise AIProviderResponseError("OpenAI response did not include parsed output")
        try:
            enrichment = EnrichmentResult.model_validate(parsed)
        except ValidationError as exc:
            raise AIProviderResponseError("OpenAI parsed output is invalid") from exc

        response_model = getattr(response, "model", None)
        response_id = getattr(response, "id", None)
        if not isinstance(response_model, str):
            raise AIProviderResponseError("OpenAI response model is invalid")
        if response_id is not None and not isinstance(response_id, str):
            raise AIProviderResponseError("OpenAI response id is invalid")
        response_id = response_id.strip() if isinstance(response_id, str) else None

        return ProviderEnrichmentResult(
            provider=OPENAI_PROVIDER_NAME,
            model=response_model,
            response_id=response_id or None,
            enrichment=enrichment,
        )

    def _validate_response_status(self, response: Any) -> None:
        if _has_refusal(response):
            raise AIProviderRefusalError("OpenAI refused the structured request")

        status = getattr(response, "status", None)
        incomplete_details = getattr(response, "incomplete_details", None)
        incomplete_reason = getattr(incomplete_details, "reason", None)
        if status == "incomplete" and incomplete_reason in {
            "content_filter",
            "max_output_tokens",
        }:
            raise AIProviderIncompleteError("OpenAI response was incomplete")
        if status != "completed":
            raise AIProviderResponseError("OpenAI response was not completed")


def _has_refusal(response: Any) -> bool:
    output = getattr(response, "output", None)
    if output is None:
        return False
    for item in output:
        if getattr(item, "type", None) != "message":
            continue
        for content in getattr(item, "content", []) or []:
            if getattr(content, "type", None) == "refusal":
                return True
    return False
