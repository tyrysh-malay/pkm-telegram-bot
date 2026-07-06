class KnowledgeArtifactError(Exception):
    """Base class for expected deterministic artifact processing failures."""


class SourceMessageError(KnowledgeArtifactError):
    """The persisted source message is missing or cannot be rendered safely."""


class ArtifactConsistencyError(KnowledgeArtifactError):
    """Persisted artifact metadata conflicts with deterministic expectations."""


class KnowledgeBaseError(KnowledgeArtifactError):
    """The configured knowledge-base filesystem cannot establish an exact file."""


class KnowledgeBaseInvariantError(KnowledgeBaseError):
    """Knowledge-base data or paths violate deterministic artifact invariants."""


class KnowledgeBaseOperationalError(KnowledgeBaseError):
    """A retryable knowledge-base filesystem operation could not complete."""


class FileConflictError(KnowledgeBaseInvariantError):
    """A regular file exists at the expected path with different bytes."""


class UnsupportedFileEntryError(KnowledgeBaseInvariantError):
    """A non-regular filesystem entry exists at the expected path."""


class AtomicPublicationError(KnowledgeBaseOperationalError):
    """The filesystem cannot provide the required no-replace publication."""


class TemporaryFileCleanupError(KnowledgeBaseOperationalError):
    """A publication temporary file could not be removed."""


class ProcessingTransactionError(KnowledgeArtifactError):
    """The supplied session cannot be used as an owned transaction boundary."""


class DuplicateArtifactRaceError(KnowledgeArtifactError):
    """A duplicate race did not reconcile to one valid artifact."""


class GitPublicationError(KnowledgeArtifactError):
    """A validated artifact cannot be published safely to local Git."""


class GitPublicationInvariantError(GitPublicationError):
    """Publication data or repository state violates the durable contract."""


class GitPublicationOperationalError(GitPublicationError):
    """Publication failed because a retryable operation could not complete."""


class GitPublicationBusyError(GitPublicationOperationalError):
    """Another publication currently owns the repository lock."""


class GitPublicationTransactionError(GitPublicationInvariantError):
    """The supplied session cannot own the publication transaction."""
