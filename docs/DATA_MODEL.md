# Data Model

## Purpose

PostgreSQL stores operational state required to process Telegram inputs reliably.

It does not replace the Markdown knowledge repository.

The initial schema should remain small and support later extensions without trying to model a full knowledge graph.

## Initial entities

Task 001 introduces:

* users;
* messages;
* processing tasks;
* artifacts;
* processing events.

Only the fields required for current or near-future behavior should be implemented.

## User

Represents a Telegram user known to the application.

Suggested fields:

```text
id                  UUID primary key
telegram_user_id    BIGINT unique, not null
username            TEXT nullable
first_name           TEXT nullable
last_name            TEXT nullable
created_at           TIMESTAMPTZ not null
updated_at           TIMESTAMPTZ not null
```

Constraints:

* `telegram_user_id` must be unique.
* Telegram names are optional and may change.

## Message

Represents one input received from Telegram.

Suggested fields:

```text
id                    UUID primary key
user_id               UUID foreign key to users
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

Initial input types:

```text
text
voice
image
link
file
```

Initial statuses:

```text
received
queued
processing
done
failed
```

Recommended idempotency key:

```text
telegram:<chat_id>:<message_id>
```

A Telegram message should be persisted only once.

## Processing task

Represents background work associated with a message.

Suggested fields:

```text
id             UUID primary key
message_id     UUID foreign key to messages
task_type      TEXT not null
status         TEXT not null
attempts       INTEGER not null, default 0
max_attempts   INTEGER not null, default 3
last_error     TEXT nullable
locked_at      TIMESTAMPTZ nullable
created_at     TIMESTAMPTZ not null
updated_at     TIMESTAMPTZ not null
```

Initial statuses:

```text
queued
running
retrying
succeeded
failed
```

Processing tasks will not be executed in Task 001. The table may be introduced now or postponed until the queue milestone if it would otherwise contain unused logic.

## Artifact

Represents a generated knowledge artifact.

Suggested fields:

```text
id                 UUID primary key
message_id         UUID foreign key to messages
artifact_type      TEXT not null
title              TEXT not null
slug               TEXT not null
file_path          TEXT not null
summary            TEXT nullable
tags               JSON or PostgreSQL ARRAY nullable
topics             JSON or PostgreSQL ARRAY nullable
git_commit_sha     TEXT nullable
created_at         TIMESTAMPTZ not null
updated_at         TIMESTAMPTZ not null
```

Initial artifact types:

```text
note
source_summary
idea_card
draft_article
todo
```

Artifacts will not be generated during Task 001.

## Processing event

Represents an append-only operational event.

Suggested fields:

```text
id             UUID primary key
message_id     UUID nullable, foreign key to messages
task_id        UUID nullable, foreign key to processing tasks
event_type     TEXT not null
payload        JSONB nullable
created_at     TIMESTAMPTZ not null
```

Example event types:

```text
message_received
task_enqueued
task_started
artifact_written
task_failed
```

This table may be postponed until task processing exists.

## Task 001 minimum schema

The smallest useful Task 001 schema is:

```text
users
messages
```

This is enough to support the next task: receiving and persisting Telegram text messages.

`processing_tasks`, `artifacts`, and `processing_events` can be added when their corresponding runtime behavior is implemented.

## Model conventions

* Use UUID application identifiers.
* Use timezone-aware timestamps.
* Keep Telegram identifiers as BIGINT.
* Use explicit foreign keys.
* Add uniqueness constraints at the database level.
* Do not store Python enum names without a migration strategy.
* Avoid database-specific abstractions unless they provide clear value.
* Do not implement soft deletion in the MVP.
* Do not create a generic metadata table.

## Source of truth

Operational state:

```text
PostgreSQL
```

Human-readable knowledge:

```text
Markdown files
```

Repository history:

```text
Git
```
