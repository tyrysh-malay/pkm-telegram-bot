# Telegram Text Ingestion

## Goal

The first Telegram milestone receives plain text messages and persists them reliably in PostgreSQL.

This milestone does not process the message into a knowledge artifact. It only captures the input and acknowledges receipt.

## Supported behavior

The bot supports:

* `/start`;
* ordinary Telegram text messages;
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
* background processing;
* AI calls;
* Markdown generation.

A message containing a URL is still stored as a normal text message in this milestone.

## Runtime mode

For local development, aiogram should use long polling.

The existing FastAPI process remains responsible for:

* `/health`;
* `/ready`;
* application startup and shutdown;
* starting and stopping the Telegram polling task.

The application should continue to start when Telegram polling is disabled.

Expected configuration:

```text
TELEGRAM_BOT_ENABLED=false
TELEGRAM_BOT_TOKEN=
```

When `TELEGRAM_BOT_ENABLED=false`:

* no Telegram network connection is started;
* FastAPI health and readiness endpoints continue to work;
* automated tests do not require a real Telegram token.

When `TELEGRAM_BOT_ENABLED=true`:

* `TELEGRAM_BOT_TOKEN` is required;
* the application starts one aiogram polling task;
* the polling task is stopped cleanly during application shutdown.

Polling mode assumes one application process. Multiple app replicas would create competing pollers and are out of scope.

A production webhook mode may be introduced later.

## `/start` behavior

The `/start` command should return a short explanation, for example:

```text
Send me a text note and I will save it for processing.
```

The `/start` command does not need to be persisted as a knowledge message.

## Text message behavior

For an ordinary text message:

1. read Telegram user and chat metadata;
2. create the user if they do not exist;
3. update mutable Telegram profile fields when the user already exists;
4. build an idempotency key;
5. persist the message;
6. send an acknowledgement.

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

The database uniqueness constraint is the final protection against duplicates.

The implementation should handle a uniqueness conflict safely instead of crashing the polling loop.

The minimum acceptance requirement is:

```text
processing the same Telegram message twice creates exactly one Message row
```

## Transaction boundary

User upsert and message insertion should occur within a clear database transaction.

A failed database write must not produce a success acknowledgement.

Avoid committing partial state where practical.

## Acknowledgement

For a newly persisted message, respond with a short temporary acknowledgement:

```text
Saved for processing.
```

This text may change when background processing is added.

For a duplicate delivery, the bot must not create another database row. Sending another acknowledgement is acceptable for this milestone, although avoiding duplicate replies is preferable if it stays simple.

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

Retry policies and dead-letter handling belong to later worker milestones.

## Security postponed

The project is intended to become a personal bot, but user allowlisting is postponed to a dedicated reliability/security task.

Until then:

* do not deploy the bot publicly;
* do not advertise its username;
* use it only for local development and controlled testing.

## Testing strategy

Automated tests must not contact Telegram.

Tests should verify:

* a Telegram user can be created;
* existing mutable user fields are updated;
* a text message is persisted correctly;
* the idempotency key has the expected format;
* processing the same message twice creates one row;
* `/start` returns the expected response;
* text ingestion sends an acknowledgement after successful persistence;
* Telegram polling is not started when disabled.

Use mocks or constructed aiogram objects where necessary.

Do not build a large fake Telegram framework.
