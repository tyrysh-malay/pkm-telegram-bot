# Telegram Text Ingestion

## Goal

The first Telegram milestone receives plain text messages and persists them reliably in PostgreSQL.

Newly captured text is scheduled durably for background note generation. The
acknowledgement still confirms capture only, not processing completion.

## Supported behavior

The bot supports:

* `/start`;
* ordinary Telegram text messages;
* configured sender-ID authorization in private chats;
* user persistence;
* message persistence;
* duplicate message protection;
* a short acknowledgement after successful persistence.

The bot does not yet support:

* voice messages;
* images;
* links as a separate input type;
* documents;
* commands other than `/start`;
* AI calls;

A message containing a URL is still stored as a normal text message in this milestone.

## Runtime mode

For local development, aiogram should use long polling.

The existing FastAPI process remains responsible for:

* `/health`;
* `/ready`;
* application startup and shutdown;
* starting and stopping the Telegram polling task.
* running the task dispatcher independently of Telegram polling.

The application should continue to start when Telegram polling is disabled.

Expected configuration:

```text
TELEGRAM_BOT_ENABLED=false
TELEGRAM_BOT_TOKEN=
TELEGRAM_ALLOWED_USER_IDS=[]
```

When `TELEGRAM_BOT_ENABLED=false`:

* no Telegram network connection is started;
* FastAPI health and readiness endpoints continue to work;
* automated tests do not require a real Telegram token.

When `TELEGRAM_BOT_ENABLED=true`:

* `TELEGRAM_BOT_TOKEN` must be non-blank;
* `TELEGRAM_ALLOWED_USER_IDS` must be a non-empty JSON array of positive
  numeric Telegram user IDs;
* the application starts one aiogram polling task;
* the polling task is stopped cleanly during application shutdown.

Quoted IDs, booleans, nulls, floats, zero, negative IDs, values above the
positive signed 64-bit range, and malformed JSON are invalid. Duplicate IDs
normalize to one set member. Configuration is loaded once and changes require
an app restart. Disabled polling permits an omitted, empty, or populated
allowlist.

Polling mode assumes one application process. Multiple app replicas would create competing pollers and are out of scope.

A production webhook mode may be introduced later.

## `/start` behavior

The `/start` command should return a short explanation, for example:

```text
Send me a text note and I will save it for processing.
```

The `/start` command does not need to be persisted as a knowledge message.

## Private-owner authorization

Every Telegram message passes through one shared aiogram routing filter before
the `/start` or ordinary-text handler:

```text
Telegram message
→ private chat + configured message.from_user.id
→ existing command or ingestion behavior
```

Authorization uses only the numeric sender ID in `message.from_user.id`.
`message.chat.id`, message ID, username, names, and persisted User profile
fields never grant access. An allowlisted sender remains authorized when their
mutable profile fields change.

Messages without usable sender metadata, messages from unknown senders, and
all group, supergroup, and channel contexts are silently rejected. Rejection
sends no response and occurs before User lookup or mutation, Message or
ProcessingTask insertion, acknowledgement, broker delivery, or artifact
processing. The gate performs no database, Redis, or Telegram lookup.

The allowlist is startup configuration rather than a database permission
model. There is no runtime administration command, and already durable tasks
continue through the worker without reauthorization.

## Text message behavior

For an ordinary text message:

1. authorize a usable sender ID in a private chat;
2. read Telegram user and chat metadata;
3. create the user if they do not exist;
4. update mutable Telegram profile fields when the user already exists;
5. build an idempotency key;
6. persist the message and one pending `generate_note` ProcessingTask in the
   same transaction;
7. send an acknowledgement after commit.

Persisted message values:

```text
input_type       = "text"
raw_text         = Telegram message text
status           = "received"
idempotency_key  = "telegram:<chat_id>:<message_id>"
```

Fields not supplied by text input remain null:

```text
caption
telegram_file_id
source_url
```

## User persistence

Users are identified by:

```text
telegram_user_id
```

On every accepted text message:

* create the user if missing;
* update `username`, `first_name`, and `last_name` if their current Telegram values differ.

Telegram profile fields are mutable and should not be used as stable identifiers.

## Idempotency

Telegram updates may be delivered more than once or replayed during development.

A message must not create multiple database rows.

Idempotency key format:

```text
telegram:<chat_id>:<message_id>
```

The Message idempotency constraint and
`UNIQUE(processing_tasks.message_id, task_type)` are the final protection
against duplicate Messages and tasks.

The implementation should handle a uniqueness conflict safely instead of crashing the polling loop.

Repeated delivery produces:

```text
exactly one Message
exactly one generate_note ProcessingTask
```

A duplicate delivery of a Message that predates ProcessingTask support does not
create a task; existing Messages are not implicitly backfilled.

## Transaction boundary

User upsert, Message insertion, and ProcessingTask insertion occur in one
database transaction. Only the transaction that inserts a new Message creates
the task.

A failed task insert rolls back the Message. A failed database write does not
produce a success acknowledgement.

Avoid committing partial state where practical.

## Acknowledgement

For a newly persisted message, respond with a short temporary acknowledgement:

```text
Saved for processing.
```

The acknowledgement is sent only after PostgreSQL commit. It does not mean the
worker has generated a note or that processing succeeded.

Duplicate delivery keeps the same acknowledgement behavior without creating
another Message or ProcessingTask.

The ingestion transaction and handler never contact Redis or invoke the worker.
Redis downtime therefore does not block persistence or acknowledgement; the
pending PostgreSQL task is dispatched after transport recovers.

## Error handling

Expected failures include:

* database temporarily unavailable;
* invalid or missing Telegram user metadata;
* duplicate message race;
* Telegram API error while sending acknowledgement;
* polling network interruption.

Requirements:

* do not silently swallow exceptions;
* log failures with relevant identifiers;
* do not log the bot token;
* do not persist fake success states;
* keep the polling loop alive when a single update fails.

Processing attempts, fixed retry backoff, and lease recovery are owned by the
ProcessingTask state machine. Telegram completion/failure notifications remain
postponed.

## Testing strategy

Automated tests must not contact Telegram.

Tests should verify:

* a Telegram user can be created;
* only configured sender IDs in private chats reach handlers;
* rejected updates send no response and create no operational state;
* existing mutable user fields are updated;
* a text message is persisted correctly;
* the idempotency key has the expected format;
* processing the same message twice creates one row;
* each new Message is atomic with one pending task;
* duplicates and concurrent duplicates create one task;
* a legacy duplicate is not backfilled;
* `/start` returns the expected response;
* text ingestion sends an acknowledgement after successful persistence;
* Telegram polling is not started when disabled.

Use mocks or constructed aiogram objects where necessary.

Do not build a large fake Telegram framework.
