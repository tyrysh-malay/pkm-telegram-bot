# Current Project State

This document is intentionally short-lived. Replace or substantially update it after each completed task.

## Repository checkpoint

**Branch:** Needs repository verification
**Latest commit:** Needs repository verification
**Working tree status:** Needs repository verification

The conversation confirms that Task 001 and Task 002 were implemented, but it does not confirm the exact current commit boundary.

## Working functionality

Confirmed working:

* Docker Compose builds and starts the application.

* PostgreSQL starts through Docker Compose.

* FastAPI starts under Uvicorn.

* `GET /health` returned `200 OK`.

* `GET /ready` returned `200 OK`.

* Alembic migrations can be applied with:

  ```bash
  docker compose exec app alembic upgrade head
  ```

* Task 001 acceptance commands were reported as successful.

* Telegram polling was configured with a real local bot token.

* A live Telegram text message received the response:

  ```text
  Saved for processing.
  ```

* The live message and Telegram user were persisted in PostgreSQL.

* Development dependencies are installed in the Compose development image.

* The earlier pytest/httpx deprecation warning was resolved.

Needs repository verification:

* exact current pytest result after the latest Task 002 edits;
* exact number and names of tests;
* whether every Task 002 acceptance criterion is covered;
* whether Task 001 and Task 002 changes are committed;
* whether the current tests leave persistent fixture rows in the development database.

## Current data flow

Implemented path:

```text
Telegram text message
→ aiogram long-polling handler
→ create or update Telegram User
→ insert incoming Message in PostgreSQL
→ acknowledge with “Saved for processing.”
```

Not implemented:

```text
queue
worker
AI processing
Markdown generation
Git-backed artifact commit
```

The acknowledgement currently confirms raw persistence only.

## Current data model

Known incoming-message fields from the task specification and observed SQL output:

* `user_id` — application foreign key to the sender;

* `telegram_chat_id` — Telegram conversation identity;

* `telegram_message_id` — message identity within the chat;

* `input_type` — observed value: `text`;

* `raw_text` — original Telegram text;

* `caption` — nullable for text input;

* `telegram_file_id` — nullable for text input;

* `source_url` — nullable for current text input;

* `status` — observed value: `received`;

* `idempotency_key` — format:

  ```text
  telegram:<chat_id>:<message_id>
  ```

* `created_at`;

* `updated_at`.

Known user fields include:

* `telegram_user_id`;
* `username`;
* `first_name`;
* `last_name`;
* timestamps.

Exact SQLAlchemy definitions, constraints, and current migration state need repository verification.

## Completed tasks

### Task 000 — Bootstrap

Implemented Dockerized FastAPI application, health endpoint, development test dependencies, and pytest execution inside the application container.

### Task 001 — PostgreSQL persistence foundation

Implemented PostgreSQL, SQLAlchemy/Alembic persistence, migrations, readiness behavior, and initial user/message storage. Acceptance commands were reported as successful.

Commit status and any later corrective changes need repository verification.

### Task 002 — Telegram text ingestion

Implemented aiogram text ingestion through local long polling, user/message persistence, and the acknowledgement:

```text
Saved for processing.
```

Live manual verification succeeded. Final review, test verification, and commit status need repository verification.

## Current work

The immediate work is to:

1. inspect `git status`, current diff, and recent commits;
2. determine which Task 001 and Task 002 changes remain uncommitted;
3. review the implementation against both task specifications;
4. inspect tests and fixtures;
5. finish only existing Task 001/002 requirements;
6. run migration, pytest, Docker, health, readiness, and live-ingestion verification;
7. create a clean commit boundary.

Possible fixture-related work must remain bounded to existing Task 001/002 correctness.

A broader Telegram identity redesign and separate test-isolation improvement were intentionally postponed until this boundary is clean.

## Newly discovered Telegram identity issue

Observed live private-chat data:

```text
telegram_chat_id:    562483653
telegram_message_id: 3
idempotency_key:     telegram:562483653:3
raw_text:            jd
telegram_user_id:    562483653
username:            argentum049
first_name:          Bulat
```

In this private-chat example, `telegram_chat_id` and `telegram_user_id` have the same numeric value.

Other database rows showed different chat-ID and user-ID values, for example:

```text
message chat IDs:
729325876923368477
2716053121147414981
6730992646434093629

user IDs:
3953215589399744121
2654857603187326050
3698983740294443113
487070298430702399
```

These rows appeared to be test fixtures, but that interpretation requires repository verification.

Important distinction:

* chat ID identifies the conversation;
* user ID identifies the sender;
* message ID identifies a message within a chat.

The separate SQL queries did not join messages to their users, so they do not prove that the implementation maps any message to the wrong sender.

The confirmed concern is that private-chat equality can hide accidental conflation of chat and sender identity. The actual implementation bug, if any, remains unconfirmed.

The issue was postponed to avoid mixing a new identity correction with unfinished Task 001/002 review and commits.

## Known limitations

* Only text input is confirmed working.
* No dedicated link extraction.
* No voice processing.
* No image processing.
* No file or PDF processing.
* No Redis queue.
* No background worker.
* No AI provider integration.
* No agent, skill, command, or subagent runtime.
* No Markdown artifact generation.
* No Git-backed artifact commits.
* No webhook ingestion.
* Long polling assumes a single app process.
* No confirmed user allowlist.
* Test isolation from the development database may be incomplete.

## Immediate next actions

1. Run:

   ```bash
   git status --short
   git diff
   git log --oneline --decorate -10
   ```

2. Review current code against all three task specifications.

3. Inspect test fixtures and determine whether pytest writes into the development database.

4. Finish only remaining Task 001/002 work.

5. Run:

   ```bash
   docker compose up -d --build
   docker compose exec app alembic upgrade head
   docker compose exec app python -m pytest
   ```

6. Verify:

   ```bash
   curl --retry 5 --retry-all-errors --retry-delay 1 \
     http://localhost:8000/health

   curl --retry 5 --retry-all-errors --retry-delay 1 \
     http://localhost:8000/ready
   ```

7. Update this file from repository facts.

8. Create and push a clean commit boundary.

9. Start a separate Telegram identity/test-isolation follow-up only after the current boundary is clean.


## Active task

Task 003 isolates automated database tests from development data.

Confirmed bug:

- the development database contained live Telegram messages;
- after `docker compose exec app python -m pytest`, the development
  `messages` count dropped to zero;
- the exact destructive fixture still requires repository inspection.

Until Task 003 is complete, do not run pytest against a development database
containing data that must be preserved.