class AIEnrichmentError(Exception):
    """Base class for expected manual AI enrichment failures."""


class AIEnrichmentSourceError(AIEnrichmentError):
    """The source Message, raw Artifact, or raw file cannot be enriched safely."""


class AIEnrichmentConsistencyError(AIEnrichmentError):
    """Persisted enrichment or enriched Artifact state violates the contract."""


class AIEnrichmentTransactionError(AIEnrichmentError):
    """The enrichment boundary cannot own the required transaction phases."""


class AIProviderError(AIEnrichmentError):
    """The structured enrichment provider did not return an acceptable result."""


class AIProviderConfigurationError(AIProviderError):
    """A new provider request is missing required local configuration."""


class AIProviderPermanentError(AIProviderError):
    """The provider rejected the request or returned invalid structured data."""


class AIProviderOperationalError(AIProviderError):
    """The provider request failed in a way a later manual invocation may retry."""


class AIProviderAuthenticationError(AIProviderPermanentError):
    """The provider rejected authentication."""


class AIProviderPermissionError(AIProviderPermanentError):
    """The provider rejected permissions."""


class AIProviderInvalidRequestError(AIProviderPermanentError):
    """The provider rejected the request shape."""


class AIProviderRefusalError(AIProviderPermanentError):
    """The provider refused to produce the structured result."""


class AIProviderIncompleteError(AIProviderPermanentError):
    """The provider stopped before a complete structured result was available."""


class AIProviderResponseError(AIProviderPermanentError):
    """The provider response did not match the accepted response contract."""


class AIProviderRateLimitError(AIProviderOperationalError):
    """The provider rate-limited the request."""


class AIProviderConnectionError(AIProviderOperationalError):
    """The provider could not be reached."""


class AIProviderTimeoutError(AIProviderOperationalError):
    """The provider request timed out."""


class AIProviderServerError(AIProviderOperationalError):
    """The provider returned a server-side failure."""
