# Data Model

PostgreSQL stores operational state. Markdown files under the configured
knowledge-base root are the human-readable artifacts; Git history is postponed.
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
created_at         TIMESTAMPTZ not null
updated_at         TIMESTAMPTZ not null
```

Constraints:

```text
UNIQUE(message_id, artifact_type)
UNIQUE(file_path)
```

Task 006 processing supports only `artifact_type = "note"`; the database uses
text rather than an enum or type check. `file_path` is a POSIX path relative to
`KNOWLEDGE_BASE_PATH`. Title and slug are deterministic metadata but do not
identify the file. The message relation has no artifact cascade-delete policy.

The table deliberately has no summary, tags, topics, Git SHA, version, content
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

New Telegram text creates `task_type = "generate_note"`, `status = "pending"`,
`attempts = 0`, `max_attempts = 3`, an immediately due `available_at`, and null
lease/error fields. Existing Messages are not backfilled. The relation has no
database cascade-delete policy.

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

## Postponed entities

`processing_events`, artifact history, and Git commit metadata are not
implemented.

## Source ownership

```text
operational state        PostgreSQL
human-readable artifact Markdown file
repository history       Git (not yet automated)
```
