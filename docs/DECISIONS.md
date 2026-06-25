# Project Decisions

This file records durable architectural and development decisions for the PKM Telegram Bot.

Statuses:

* **accepted** — currently agreed and in force;
* **tentative** — direction was discussed but is not yet final;
* **superseded** — replaced by a later decision;
* **unresolved** — requires repository inspection or a future decision.

Implementation details in the repository remain the source of truth.

---

## D-001 — Use FastAPI as the application boundary

**Decision**

Use FastAPI as the main application process and HTTP boundary.

The application exposes at least:

* `/health` for process liveness;
* `/ready` for database readiness.

**Context or problem**

The project needs a small application boundary for health checks, lifecycle management, and future webhook or administrative endpoints.

**Reasoning**

FastAPI integrates naturally with the Python async stack and can host application startup and shutdown behavior without requiring a separate API service.

**Consequences**

* FastAPI owns application lifecycle concerns.
* Slow knowledge-processing work must not run directly in request handlers.
* The application can start with Telegram integration disabled.
* Future Telegram webhook support can be added to the same boundary if selected.

**Status:** accepted

**Related task:** Task 000; Task 001; Task 002

---

## D-002 — Store operational state in PostgreSQL

**Decision**

Use PostgreSQL for operational persistence.

Known entities include:

* users;
* incoming messages.

Processing tasks, artifacts, and processing events were planned but were not confirmed as implemented.

**Context or problem**

The bot needs durable state for Telegram identities, received messages, idempotency, statuses, and later processing recovery.

**Reasoning**

PostgreSQL provides:

* durable storage;
* uniqueness constraints;
* transactions;
* migrations;
* a clear separation between operational state and Markdown knowledge artifacts.

**Consequences**

* SQLAlchemy and Alembic are part of the persistence layer.
* Database constraints are the final authority for uniqueness.
* The application does not rely on in-memory state for received messages.
* Markdown remains the planned human-readable knowledge format rather than being replaced by database rows.

**Status:** accepted

**Related task:** Task 001

---

## D-003 — Use Alembic migrations rather than runtime `create_all()`

**Decision**

Create and apply database schema changes through Alembic migrations.

**Context or problem**

The project needs reproducible schema creation from a clean database and reviewable schema history.

**Reasoning**

Alembic makes database changes explicit and allows clean-environment verification.

**Consequences**

The known migration command is:

```bash
docker compose exec app alembic upgrade head
```

The application should not silently create production schema through `create_all()` during startup.

**Status:** accepted

**Related task:** Task 001

---

## D-004 — Use Docker Compose as the local development runtime

**Decision**

Use Docker Compose to run the application and PostgreSQL during local development.

**Context or problem**

The project needs a reproducible environment that does not depend on globally installed Python packages or PostgreSQL.

**Reasoning**

Docker Compose keeps application, dependency, database, and networking configuration reviewable in the repository.

**Consequences**

* The application is built into an `app` image.
* PostgreSQL runs as a Compose service.
* The application reaches PostgreSQL by its Compose service hostname.
* Database data is expected to be stored in a named Docker volume.
* `docker compose down` normally preserves the volume.
* `docker compose down -v` deletes the local database volume and its contents.

**Status:** accepted

**Related task:** Task 000; Task 001

---

## D-005 — Install development dependencies only in development builds

**Decision**

Keep test dependencies in the project’s development dependency group and enable them in the Compose development image through:

```dockerfile
ARG INSTALL_DEV=false
```

with Compose supplying:

```yaml
INSTALL_DEV: "true"
```

**Context or problem**

The initial image installed only runtime dependencies, so `pytest` was unavailable inside the container.

**Reasoning**

Test tools should be available in the development image without becoming mandatory runtime dependencies for every build.

**Consequences**

* Normal builds can remain runtime-dependency-only.
* The Compose development image installs the `dev` extra.
* Tests are copied into the development image.
* A future production image may exclude test sources, but this was intentionally not optimized yet.

**Status:** accepted

**Related task:** Task 000

---

## D-006 — Run the authoritative test suite inside Docker

**Decision**

Use the application container as the authoritative test environment.

Known command:

```bash
docker compose exec app python -m pytest
```

**Context or problem**

The host Python installation initially lacked `pytest`, `pip`, and a usable virtual environment, while application dependencies were installed inside Docker.

**Reasoning**

Running tests in the application container verifies the same dependency environment used by the service.

**Consequences**

* Local `.venv` may be used for Pylance and editor tooling.
* Docker remains the authoritative runtime and test environment.
* Pylance import resolution and container execution are separate concerns.
* Tests must be present inside the development image.

**Status:** accepted

**Related task:** Task 000 onward

---

## D-007 — Use long polling for current local Telegram ingestion

**Decision**

Use aiogram long polling for the current local-development Telegram integration.

Do not require Telegram connectivity when the bot is disabled.

**Context or problem**

The first Telegram milestone needed a small local ingestion path without deployment or public webhook infrastructure.

**Reasoning**

Long polling is simpler for local development and permits live bot verification without exposing an HTTP endpoint publicly.

**Consequences**

* `TELEGRAM_BOT_ENABLED=false` allows the application to run without a token.
* `TELEGRAM_BOT_ENABLED=true` requires a valid token.
* Polling is started and stopped through application lifecycle management.
* The polling deployment assumes one application process.
* Multiple app replicas are not currently supported.

**Status:** accepted

**Related task:** Task 002

---

## D-008 — Telegram webhook ingestion is postponed

**Decision**

Do not implement Telegram webhook ingestion during the current text-ingestion milestone.

**Context or problem**

Webhook deployment was part of the possible future architecture, but the current milestone used local long polling.

**Reasoning**

Webhook setup would introduce deployment, routing, HTTPS, and update-delivery concerns before the core persistence flow is complete.

**Consequences**

* Current Telegram ingestion is not webhook-based.
* FastAPI remains a possible future webhook boundary.
* The webhook decision should be revisited when deployment work begins.

**Status:** tentative

**Related task:** future deployment milestone

---

## D-009 — Persist incoming Telegram text before processing it

**Decision**

Persist an incoming Telegram text message before acknowledging successful receipt.

**Context or problem**

The bot must not claim to have saved a message when the database write failed.

**Reasoning**

Durable capture is the first reliable boundary. AI, Markdown generation, and background work can happen later.

**Consequences**

The current path is:

```text
Telegram text update
→ aiogram handler
→ persist or update Telegram user
→ persist incoming message
→ send “Saved for processing.”
```

The acknowledgement currently means only that the raw message was stored. It does not mean that AI or Markdown processing occurred.

**Status:** accepted

**Related task:** Task 002

---

## D-010 — Store newly received text messages with status `received`

**Decision**

Persist a newly accepted Telegram text message with:

```text
input_type = "text"
status = "received"
```

**Context or problem**

The project needs an explicit state showing that ingestion succeeded but downstream processing has not begun.

**Reasoning**

`received` accurately describes the current implementation boundary.

**Consequences**

* The current status must not imply that the message was summarized or converted into a knowledge artifact.
* Future queue work may introduce statuses such as `queued`, `processing`, `done`, or `failed`.
* Status transitions should be persisted and tested when processing is implemented.

**Status:** accepted

**Related task:** Task 002

---

## D-011 — Construct message idempotency keys from Telegram chat ID and message ID

**Decision**

Use the following idempotency-key format:

```text
telegram:<telegram_chat_id>:<telegram_message_id>
```

Example observed in the development database:

```text
telegram:123456789:3
```

**Context or problem**

Telegram updates may be delivered more than once, and the same update must not create duplicate message rows.

**Reasoning**

A Telegram message ID is scoped to its chat. Combining chat ID and message ID identifies one message within Telegram’s messaging model.

**Consequences**

* The `idempotency_key` column has a uniqueness constraint.
* Processing the same update twice should create one message row.
* Sending the same text again as a new Telegram message is not a duplicate because it receives a new message ID.
* A uniqueness conflict must be handled without leaving the database session unusable.

**Status:** accepted

**Related task:** Task 002

---

## D-012 — Treat Telegram chat identity, sender identity, and message identity as separate concepts

**Decision**

The domain model must distinguish:

* `telegram_chat_id` — the conversation where the message appeared;
* `telegram_user_id` — the sender’s Telegram identity;
* `telegram_message_id` — the message identifier within the chat.

**Context or problem**

In a private chat, chat ID and user ID may have the same visible value, which can hide incorrect assumptions.

In group chats or messages from different senders, chat identity and sender identity are separate.

**Reasoning**

User persistence, message ownership, idempotency, authorization, and future group-chat behavior depend on preserving these distinctions.

**Consequences**

* Users are identified by `telegram_user_id`.
* Messages store `telegram_chat_id` and `telegram_message_id`.
* Messages reference their sender through the application user relation.
* The code and fixtures must not derive sender identity from chat ID.
* Existing implementation and fixtures require repository verification for accidental identity conflation.

**Status:** accepted principle; implementation verification unresolved

**Related task:** Task 001; Task 002

---

## D-013 — Verify identity behavior with explicit Telegram fixtures

**Decision**

The test suite should eventually make identity assumptions explicit with fixtures for:

* a private chat;
* a group chat;
* different senders in the same chat;
* repeated delivery of the same message;
* different messages with identical text.

**Context or problem**

Separate PostgreSQL queries showed chat IDs and user IDs with different values, but they did not join messages to users. The exact fixture mapping is therefore not confirmed.

**Reasoning**

Explicit fixtures make it possible to verify that:

* user identity is not derived from chat identity;
* idempotency is based on chat and message IDs;
* identical text does not imply duplicate delivery;
* different senders in one chat remain distinct users.

**Consequences**

* Existing fixtures must be inspected before adding new ones.
* Test data observed in the development database may already cover some cases.
* The repository must be checked before treating this fixture matrix as complete.

**Status:** unresolved

**Related task:** Task 001; Task 002; identity follow-up task

---

## D-014 — Keep `.env.example` and use an ignored local `.env`

**Decision**

Keep `.env.example` as the committed configuration template and create a separate local `.env` containing real credentials.

**Context or problem**

The bot token and future API keys must not be committed.

**Reasoning**

The example file documents configuration, while the local file stores machine-specific secrets.

**Consequences**

* `.env` must remain ignored by Git.
* Real bot tokens must not appear in logs, README examples, commits, or review output.
* Docker Compose remains responsible for passing configured values into containers.
* VS Code terminal environment injection is optional and is not required for Docker Compose.

**Status:** accepted

**Related task:** Task 002

---

## D-015 — Keep Markdown as the planned human-readable knowledge store

**Decision**

Use Git-backed Markdown files as the future human-readable knowledge base.

**Context or problem**

The product should create reviewable, portable knowledge artifacts rather than hiding all knowledge inside a database.

**Reasoning**

Markdown provides:

* readable diffs;
* portability;
* simple Git integration;
* compatibility with multiple PKM tools.

**Consequences**

* PostgreSQL stores operational state.
* Markdown will store human-readable artifacts.
* Git commits can later record generated knowledge changes.
* Markdown generation is not yet implemented.

**Status:** accepted

**Related task:** future Markdown-processing task

---

## D-016 — Keep generated Markdown compatible with Obsidian

**Decision**

Design the future Markdown repository to support:

* YAML frontmatter;
* stable filenames;
* tags;
* topics;
* backlinks or wiki-style links;
* local asset references.

**Context or problem**

Obsidian is a likely consumer of the knowledge repository, though it is not required as the application itself.

**Reasoning**

Obsidian-compatible Markdown remains usable as ordinary Markdown and does not require building an Obsidian plugin.

**Consequences**

* Obsidian is optional.
* No Obsidian plugin is part of the MVP.
* Markdown compatibility requirements should be reflected in rendering tests when artifact generation is implemented.

**Status:** accepted

**Related task:** future Markdown-processing task

---

## D-017 — Separate fast ingestion from future background processing

**Decision**

Use one codebase with separate runtime processes in the future:

* application process;
* background worker process.

Redis and a task queue are planned for the worker boundary.

**Context or problem**

AI calls, transcription, link extraction, image analysis, Markdown writing, and Git operations may be slow or retryable.

**Reasoning**

Telegram ingestion should acknowledge durable receipt quickly, while processing should survive transient failures independently.

**Consequences**

* The current application only performs ingestion and persistence.
* Redis, Dramatiq, and the worker must not be described as implemented yet.
* Future tasks must define queue semantics, retries, state transitions, and crash recovery.
* The project remains one repository rather than becoming a microservice system.

**Status:** accepted architecture; not yet implemented

**Related task:** future queue/worker task

---

## D-018 — Add multimodal input incrementally

**Decision**

Add input types in stages rather than implementing all modalities at once.

Planned modalities include:

* text;
* links;
* voice;
* images;
* later files and PDFs.

**Context or problem**

Each modality introduces separate extraction, error handling, storage, and testing concerns.

**Reasoning**

Text ingestion establishes the reliable persistence boundary before media and external-content processing are introduced.

**Consequences**

* Text is the only confirmed live input type.
* URL-containing messages currently remain ordinary text unless the repository proves otherwise.
* Voice, image, file, and PDF processing are future work.

**Status:** accepted

**Related task:** future multimodal tasks

---

## D-019 — Keep AI orchestration structured but postpone agent frameworks

**Decision**

The future AI pipeline should use:

* structured outputs;
* explicit skills or commands;
* deterministic post-processing;
* an orchestrator boundary.

Subagents may later be introduced when parallel work provides clear value.

Do not introduce LangChain, LangGraph, or a general agent framework prematurely.

**Context or problem**

The product aims to demonstrate AI-agent orchestration, but the current system has not reached AI processing.

**Reasoning**

A small explicit pipeline is easier to test, debug, and review than a generic autonomous-agent framework.

**Consequences**

* AI calls are not yet implemented.
* Markdown rendering should be deterministic code rather than free-form LLM output.
* Skills, commands, and subagents remain design directions rather than current runtime facts.
* Agent-framework adoption requires a concrete task and decision.

**Status:** tentative architecture direction

**Related task:** future AI-processing task

---

## D-020 — Avoid premature dependencies and abstractions

**Decision**

Add dependencies and abstractions only when required by the active task.

**Context or problem**

The project is intended to be production-minded without becoming over-engineered.

**Reasoning**

Small vertical slices are easier to verify, review, and present in a portfolio.

**Consequences**

Postponed until needed:

* Redis;
* Dramatiq;
* Celery;
* LangChain;
* LangGraph;
* vector databases;
* RAG;
* Kubernetes;
* generic repository frameworks;
* unnecessary service layers;
* microservices.

**Status:** accepted

**Related task:** all tasks

---

## D-021 — Finish the current Task 001/002 commit boundary before starting the identity follow-up

**Decision**

Complete review, fixes, verification, and commits for existing Task 001 and Task 002 work before beginning a separate Telegram identity correction.

**Context or problem**

An identity concern and possible test-fixture contamination were noticed while Task 002 work had not yet reached a confirmed clean commit boundary.

**Reasoning**

Mixing a new identity redesign into unfinished persistence and ingestion work would make review and history harder to understand.

**Consequences**

* First inspect current Git status, diff, and recent commits.
* Finish only existing Task 001/002 requirements.
* Commit that work cleanly.
* Handle identity corrections or test-isolation changes in a separate follow-up unless current Task 001/002 behavior is already incorrect.

**Status:** accepted

**Related task:** Task 001; Task 002; future identity follow-up

---

## D-022 — Isolate pytest from the development PostgreSQL database

**Decision**

Use separate PostgreSQL databases for development runtime data and automated
test data.

The development application uses `DATABASE_URL`, currently pointing at:

```text
pkm
```

Pytest uses `TEST_DATABASE_URL`, currently pointing at:

```text
pkm_test
```

The pytest bootstrap must fail closed when:

* `TEST_DATABASE_URL` is missing;
* `TEST_DATABASE_URL` targets the same database name as `DATABASE_URL`.

Pytest creates the test database if needed, initializes it with committed
Alembic migrations, and performs test cleanup only inside the test database.

Docker remains the authoritative test environment.

**Context or problem**

The development database contained live Telegram messages. Running the test
suite previously deleted rows from the same development `messages` table because
pytest used the normal application database URL and its cleanup fixture deleted
`messages` and `users`.

**Reasoning**

Application code opens its own sessions and commits transactions during tests,
so rollback-only test isolation is too easy to bypass. A separate test database
keeps fixture cleanup simple while protecting live development data.

Alembic-driven initialization verifies that a clean database can be built from
committed migrations rather than relying on runtime `create_all()`.

**Consequences**

* Development rows are not deleted, modified, or populated by pytest cleanup.
* Test fixture rows such as `duplicate_user`, `new_username`, `original_user`,
  and `pkm_user` remain confined to `pkm_test`.
* Local host-side pytest needs database URLs that are reachable from the host,
  for example `localhost` instead of the Compose-only `postgres` hostname.
* A database user running tests must be able to create the configured test
  database when it does not exist.
* Normal application runtime and normal Alembic commands continue to use
  `DATABASE_URL`.

**Status:** accepted

**Related task:** Task 003

---

# Possible future ADR split

If this file becomes too large, the following decisions are good candidates for individual ADR files:

* FastAPI application boundary and lifecycle;
* PostgreSQL as operational state;
* Docker Compose development environment;
* Telegram polling versus webhook;
* Telegram identity and idempotency model;
* Git-backed Markdown knowledge storage;
* application/worker separation;
* AI orchestration without an agent framework.
