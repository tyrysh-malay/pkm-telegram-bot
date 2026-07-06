class KnowledgeArtifactError(Exception):
    """Base class for expected deterministic artifact processing failures."""


class SourceMessageError(KnowledgeArtifactError):
    """The persisted source message is missing or cannot be rendered safely."""


class ArtifactConsistencyError(KnowledgeArtifactError):
    """Persisted artifact metadata conflicts with deterministic expectations."""


class KnowledgeBaseError(KnowledgeArtifactError):
    """The configured knowledge-base filesystem cannot establish an exact file."""


class FileConflictError(KnowledgeBaseError):
    """A regular file exists at the expected path with different bytes."""


class UnsupportedFileEntryError(KnowledgeBaseError):
    """A non-regular filesystem entry exists at the expected path."""


class AtomicPublicationError(KnowledgeBaseError):
    """The filesystem cannot provide the required no-replace publication."""


class TemporaryFileCleanupError(KnowledgeBaseError):
    """A publication temporary file could not be removed."""


class ProcessingTransactionError(KnowledgeArtifactError):
    """The supplied session cannot be used as an owned transaction boundary."""


class DuplicateArtifactRaceError(KnowledgeArtifactError):
    """A duplicate race did not reconcile to one valid artifact."""


class GitPublicationError(KnowledgeArtifactError):
    """A validated artifact cannot be published safely to local Git."""


class GitPublicationTransactionError(GitPublicationError):
    """The supplied session cannot own the publication transaction."""
