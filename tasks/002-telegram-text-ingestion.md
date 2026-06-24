# Task 002: Telegram text ingestion

## Goal

Receive Telegram text messages through aiogram, persist them in PostgreSQL, and acknowledge successful receipt.

This task should connect the existing persistence foundation to a real Telegram input boundary.

## Scope

Add:

* aiogram;
* Telegram settings;
* optional local long polling;
* `/start` handler;
* ordinary text message handler;
* Telegram user create/update behavior;
* idempotent message persistence;
* acknowledgement after successful persistence;
* automated tests without real Telegram network calls;
* local setup instructions.

## Out of scope

Do not add:

* Redis;
* Dramatiq;
* Celery;
* background workers;
* AI provider calls;
* Markdown rendering;
* Git operations;
* voice processing;
* image processing;
* document processing;
* special link extraction;
* webhook deployment;
* user allowlisting;
* complex repository or service abstractions.

Messages containing URLs remain ordinary text messages.

## Dependencies

Add aiogram to normal application dependencies.

Do not add Telegram testing frameworks unless the existing test suite genuinely requires one.

Use the existing SQLAlchemy and database setup.

## Configuration

Add:

```text
TELEGRAM_BOT_ENABLED
TELEGRAM_BOT_TOKEN
```

Recommended defaults for development and automated tests:

```text
TELEGRAM_BOT_ENABLED=false
TELEGRAM_BOT_TOKEN=
```

Requirements:

* the application starts normally when Telegram is disabled;
* no Telegram API call occurs when Telegram is disabled;
* enabling Telegram without a token produces a clear configuration error;
* secrets are not logged;
* `.env.example` contains placeholders only.

## Runtime integration

Use aiogram long polling for local development.

Integrate polling with the existing FastAPI application lifecycle.

On application startup:

1. start Telegram polling only when enabled;
2. keep a reference to the polling task;
3. avoid blocking FastAPI startup.

On shutdown:

1. stop polling;
2. cancel or await the polling task safely;
3. close the aiogram bot HTTP session.

Keep this implementation small.

Do not introduce a process supervisor or a separate repository.

Do not enable multiple Uvicorn workers while using polling.

## Bot structure

Adapt to the existing repository, but a reasonable structure is:

```text
app/
  bot/
    __init__.py
    handlers.py
    ingestion.py
    runtime.py
```

Responsibilities:

```text
handlers.py
- aiogram routing
- /start response
- text message response

ingestion.py
- user create/update
- message persistence
- idempotency behavior

runtime.py
- Bot and Dispatcher creation
- polling startup and shutdown
```

Do not split modules further unless necessary.

A small ingestion function is acceptable because it creates a testable boundary between Telegram objects and database persistence. Do not add a generic repository layer.

## `/start` handler

Return:

```text
Send me a text note and I will save it for processing.
```

Do not persist the `/start` command as a Message.

## Text handler

Handle non-command text messages.

For every message:

1. ensure usable Telegram user metadata is present;
2. create or update the corresponding User;
3. generate the idempotency key;
4. insert the Message if it is new;
5. handle duplicate insertion safely;
6. acknowledge successful persistence.

Persist:

```text
input_type       = "text"
raw_text         = message.text
status           = "received"
idempotency_key  = "telegram:<chat_id>:<message_id>"
```

Use Telegram chat and message identifiers directly.

Do not generate application knowledge artifacts.

## Idempotency

The unique database constraint on `idempotency_key` is the final authority.

The implementation must remain correct if two attempts race to insert the same Telegram message.

Requirements:

* one database row is created;
* a uniqueness conflict does not terminate polling;
* the database session remains usable after the conflict;
* unrelated database errors are not mistaken for duplicates.

Do not implement distributed locks.

## User updates

Identify users by `telegram_user_id`.

When a user already exists, update these mutable fields when needed:

```text
username
first_name
last_name
```

Do not create duplicate users.

## Logging

Add useful structured or consistently formatted logs for:

* Telegram polling started;
* Telegram polling stopped;
* message persisted;
* duplicate message observed;
* persistence failure.

Include identifiers such as:

```text
telegram_user_id
telegram_chat_id
telegram_message_id
```

Do not log:

```text
TELEGRAM_BOT_TOKEN
full sensitive configuration
```

Logging entire message text is not necessary.

## Tests

Automated tests must not use a real bot token or Telegram network.

At minimum, test:

1. `/start` produces the expected text.
2. A text message creates a User.
3. A text message creates a Message with:

   * correct raw text;
   * `input_type="text"`;
   * `status="received"`;
   * correct idempotency key.
4. Existing user profile fields are updated.
5. Processing the same Telegram message twice creates one Message row.
6. A database failure does not produce a success acknowledgement.
7. Telegram polling remains disabled under default test configuration.

Prefer testing persistence logic directly and keeping handler tests focused.

## Documentation

Update:

* `.env.example`;
* README local development instructions;
* README Telegram configuration instructions.

Document that polling mode expects one app process.

Do not put a real bot token in README examples.

## Acceptance criteria

The existing acceptance commands continue to pass:

```bash
docker compose up -d --build
docker compose exec app alembic upgrade head
docker compose exec app python -m pytest
```

The following also hold:

* `/health` works.
* `/ready` works.
* the app starts without a Telegram token when the bot is disabled;
* no Telegram network request occurs in the default test setup;
* enabling the bot without a token fails with a clear error;
* duplicate Telegram delivery creates one Message row;
* no Redis, worker, AI, Markdown, or Git artifact behavior has been added.

## Manual Telegram verification

After automated tests pass, manual verification may use a local `.env`:

```text
TELEGRAM_BOT_ENABLED=true
TELEGRAM_BOT_TOKEN=<local secret>
```

Recreate the app:

```bash
docker compose up -d --build --force-recreate app
docker compose logs -f app
```

Then:

1. send `/start`;
2. verify the bot response;
3. send an ordinary text message;
4. verify the acknowledgement;
5. confirm one User and one Message are stored.

Never commit the local token.

## Implementation guidance

Before editing:

1. read `AGENTS.md`;
2. read `docs/PROJECT_BRIEF.md`;
3. read `docs/ARCHITECTURE.md`;
4. read `docs/DATA_MODEL.md`;
5. read `docs/TELEGRAM_INGESTION.md`;
6. inspect the existing application lifecycle and database code;
7. present a concise plan.

Make the smallest change that satisfies this task.

Avoid refactoring working persistence code unless required for Telegram ingestion.

After editing:

1. validate Compose configuration;
2. build the app image;
3. start PostgreSQL and the app with Telegram disabled;
4. apply migrations;
5. run the full test suite;
6. verify health and readiness;
7. report anything not verified, especially live Telegram behavior.
