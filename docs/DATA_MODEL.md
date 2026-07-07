# Data Model

PostgreSQL stores operational state. Markdown files under the configured
knowledge-base root are the human-readable artifacts. A nullable Artifact field
records one validated local publication commit; an immutable AIEnrichment row
records one accepted structured interpretation. Remote Git state is postponed.
Alembic migrations, not runtime `create_all()`, own the schema.

## User

`users` represents a Telegram sender:

```text
id                  UUID primary key
telegram_user_id    BIGINT unique, not null
username            TEXT nullable
first_name           TEXT nullable
last_name            TEXT nullable
created_at           TIMESTAMPTZ not null
updated_at           TIMESTAMPTZ not null
```

Telegram profile fields are mutable. `telegram_user_id` is the stable external
identity.

## Message

`messages` represents one persisted Telegram input:

```text
id                    UUID primary key
user_id               UUID foreign key to users, not null
telegram_chat_id      BIGINT not null
telegram_message_id   BIGINT not null
input_type            TEXT not null
raw_text              TEXT nullable
caption               TEXT nullable
telegram_file_id      TEXT nullable
source_url             TEXT nullable
status                 TEXT not null
idempotency_key        TEXT unique, not null
created_at             TIMESTAMPTZ not null
updated_at             TIMESTAMPTZ not null
```

Current ingestion creates text messages with `status = "received"`. Artifact
processing accepts `received` or `done` text messages and establishes
`status = "done"` only after an exact note and valid Artifact row exist. Status
is unrestricted text at the database level and is not proof of filesystem
consistency.

## Artifact

`artifacts` represents operational metadata for a generated file:

```text
id                 UUID primary key
message_id         UUID foreign key to messages, not null
artifact_type      TEXT not null
title              TEXT not null
slug               TEXT not null
file_path          TEXT not null
git_commit_sha     TEXT nullable
created_at         TIMESTAMPTZ not null
updated_at         TIMESTAMPTZ not null
```

Constraints:

```text
UNIQUE(message_id, artifact_type)
UNIQUE(file_path)
```

Current artifact types are:

```text
note
enriched_note
```

Task 006 processing creates and validates only `artifact_type = "note"`.
Manual AI enrichment creates and validates `artifact_type = "enriched_note"`.
The database uses text rather than an enum or type check. `file_path` is a
POSIX path relative to `KNOWLEDGE_BASE_PATH`. Title and slug are deterministic
metadata but do not identify the file. The message relation has no artifact
cascade-delete policy.

`git_commit_sha = NULL` means no publication commit has been successfully
recorded in PostgreSQL. A non-null value is a canonical full hexadecimal object
ID for one locally validated commit whose trailers, path, and blob match this
Artifact. The field has no index or uniqueness constraint and does not model a
branch, remote, synchronization status, retry, or publication history. If a
commit survives a database failure, a later manual invocation can reconcile it.

The table deliberately has no summary, tags, topics, version, content
hash, processing-task reference, or generic metadata field. Frontmatter tags
and topics are empty format fields, not database columns.

## ProcessingTask

`processing_tasks` is the durable orchestration record for one processing type
per Message:

```text
id                  UUID primary key
message_id          UUID foreign key to messages, not null
task_type           TEXT not null
status              TEXT not null
attempts            INTEGER not null
max_attempts        INTEGER not null
available_at        TIMESTAMPTZ not null
lease_expires_at    TIMESTAMPTZ nullable
last_error          TEXT nullable
created_at          TIMESTAMPTZ not null
updated_at          TIMESTAMPTZ not null
```

Constraints and dispatcher indexes:

```text
UNIQUE(message_id, task_type)
INDEX(status, available_at)
INDEX(status, lease_expires_at)
```

Accepted task types are `generate_note` and `publish_artifact`. New Telegram
text creates a pending `generate_note`; successful generation can atomically
create one pending `publish_artifact` when automatic creation is enabled. Both
start with `attempts = 0`, `max_attempts = 3`, an immediately due
`available_at`, and null lease/error fields. Existing Messages, Artifacts, and
succeeded generation tasks are not backfilled. The relation has no database
cascade-delete policy.

The existing `UNIQUE(message_id, task_type)` constraint permits one task of
each accepted type per Message. A publication task resolves the existing note
Artifact through `message_id`; there is deliberately no Artifact foreign key,
generic target model, or workflow graph. `Artifact.git_commit_sha` remains the
durable publication result.

The complete status set is `pending`, `queued`, `running`, `retrying`,
`succeeded`, and `failed`. Attempts count committed worker claims, not broker
publications. Queued leases are 30 seconds, running leases are 300 seconds, and
processing retry backoff is 5 seconds. Terminal rows have no lease.

Normal transitions are:

```text
pending/retrying -> queued -> running -> succeeded
pending/retrying ---------> running -> succeeded
running -> retrying -> queued/running
queued (expired) -> pending
running (expired) -> retrying or failed
running -> failed
```

The direct pending/retrying-to-running path handles a worker that receives the
actor message before the dispatcher records queued. Unsupported task types and
exhausted non-running tasks become failed without invoking artifact processing.
Finalization is conditional on task ID, running status, and claimed attempt.

`ProcessingTask.status` owns orchestration. `Message.status` remains only
`received` or `done` in current application behavior and is still unrestricted
text at database level.

## AIEnrichment

`ai_enrichments` represents one immutable accepted structured AI result for a
completed text Message:

```text
id                     UUID primary key
message_id             UUID foreign key to messages, not null
source_artifact_id     UUID foreign key to artifacts, not null
source_content_sha256  TEXT not null
provider               TEXT not null
model                  TEXT not null
prompt_version         INTEGER not null
schema_version         INTEGER not null
provider_response_id   TEXT nullable
result_json             JSONB not null
created_at              TIMESTAMPTZ not null
```

Constraint:

```text
UNIQUE(message_id)
```

The row is accepted data, not a task or attempt log. There is no status,
updated timestamp, error, retry count, prompt table, request payload, raw
provider response, usage/cost field, Git SHA, or enriched Artifact foreign key.
Application code never updates an accepted row.

`source_artifact_id` points to the raw `note` Artifact used as input and must
belong to the same Message. `source_content_sha256` is the SHA-256 of the exact
canonical provider input, not the raw Markdown bytes. `provider` is currently
`openai`; `model` and `provider_response_id` are provenance from the accepted
provider response and are not rewritten when current settings change.

`prompt_version = 1` and `schema_version = 1` identify the repository-owned
prompt and strict Pydantic result schema. `result_json` is PostgreSQL JSONB and
contains only the normalized structure:

```text
title
summary
key_points
tags
action_items
```

Every reuse revalidates `result_json`, source provenance, provider metadata,
and supported versions before rendering. The enriched Artifact is resolved
indirectly by `message_id + artifact_type = "enriched_note"`.

## Postponed entities

`processing_events`, artifact history, AI request history, AI retry/attempt
models, provider routing, branch/remote state, and publication attempt models
are not implemented.

## Source ownership

```text
operational state        PostgreSQL
human-readable artifact Markdown file
repository history       local Git (manual or durable automatic publication)
AI accepted result       PostgreSQL JSONB
```
