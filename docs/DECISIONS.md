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
telegram:562483653:3
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
* Task 008 verified that routing and fixtures keep sender, chat, and message
  identity separate.

**Status:** accepted

**Related task:** Task 001; Task 002; Task 008

---

## D-013 — Verify identity behavior with explicit Telegram fixtures

**Decision**

The test suite makes identity assumptions explicit with fixtures for:

* a private chat;
* a group chat;
* different senders in the same chat;
* repeated delivery of the same message;
* different messages with identical text;
* mutable-profile changes and an unknown sender copying those profile fields.

**Context or problem**

Separate PostgreSQL queries showed chat IDs and user IDs with different values,
but they did not join messages to users. This originally left the exact fixture
mapping unconfirmed. Task 008 added routing and persistence coverage that
resolved that uncertainty.

**Reasoning**

Explicit fixtures make it possible to verify that:

* user identity is not derived from chat identity;
* idempotency is based on chat and message IDs;
* identical text does not imply duplicate delivery;
* different senders in one chat remain distinct users.

**Consequences**

* Private and group contexts are covered explicitly.
* Fixtures distinguish sender IDs from chat IDs and exercise different senders.
* Repeated delivery of one Telegram message is distinguished from different
  message IDs containing identical text.
* Mutable-profile changes preserve the same sender identity, while copying
  profile fields does not grant another sender that identity.

**Status:** accepted

**Related task:** Task 001; Task 002; Task 008

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

## D-023 — Use repository-local workflow and read-only context reports

**Decision**

Repository-local task files and documentation define the development workflow.
Accepted task specifications are normally committed before implementation, and
implementation is reviewed against that accepted contract.

Codex inspects the live local working tree and does not treat documentation as
stronger evidence than repository state. Affected documentation is updated
after behavior is verified.

The standard compact handoff to Web Chat is the read-only Markdown report from:

```bash
python3 scripts/project_context.py
```

The report and uploaded files are point-in-time snapshots, not sources of
truth, and may become stale. Possible future GitHub retrieval would describe
only the committed and pushed baseline, not uncommitted local work.

**Context or problem**

Project facts were spread across Git history, the working tree, documentation,
and uploaded snapshots, making stale context easy to mistake for current state.

**Reasoning**

A small repository-owned lifecycle and deterministic metadata report make
handoffs repeatable without adding synchronization machinery or granting Web
Chat repository access.

**Consequences**

* Task specifications and implementation commits remain distinguishable where
  practical.
* Review compares the implementation with the committed task requirements.
* Generated context must be refreshed after repository changes.
* Automatic commits and automatic rewriting of `docs/CURRENT_STATE.md` are not
  part of this decision.

**Status:** superseded

**Superseded by:** D-028

**Related task:** Task 004

---

## D-024 — Package implementation review as one safe point-in-time bundle

**Decision**

Use the committed task specification as the implementation-review contract,
captured Git evidence as the implementation state, and an explicit Codex
completion report for explanations and verification claims.

Implementation review should normally receive one self-contained Markdown
bundle generated by:

```bash
python3 scripts/review_bundle.py \
  --task tasks/<active-task>.md \
  --report /tmp/<task>-handoff.md \
  > /tmp/<task>-review-bundle.md
```

The bundle is point-in-time evidence, not a new source of truth. Any repository
or completion-report change invalidates it. Separately uploaded conflicting
files do not override bundle evidence; a conflict requires generating a fresh
bundle.

The sole path-level exception to the secret-like filename policy is the exact
repository-root `.env.example` public template when it already exists at HEAD
as a regular tracked blob and is captured as tracked changed evidence. It still
must be non-ignored and pass every ordinary type, content, size, diff, and
consistency validation. The exception does not apply to untracked files,
completion reports, nested templates, or any other `.env` name.

**Context or problem**

The Task 004 context report intentionally contains metadata rather than full
implementation evidence. Reviewing uncommitted work otherwise requires a
manually assembled set of task, diff, untracked-file, and report uploads that
can be incomplete or come from different repository moments.

**Reasoning**

One deterministic bundle gives review a complete evidence boundary while
preserving distinct authority: committed requirements, captured implementation
state, and Codex's supplied claims. Rejecting unsafe evidence keeps the bundle
complete without leaking or silently omitting content.

**Consequences**

* Review packaging remains separate from the compact Task 004 context report.
* Ignored, secret-like, binary, invalid-text, symlinked, submodule, special, or
  oversized changed evidence causes bundle generation to fail.
* Exact tracked root `.env.example` is the only path-level exception and remains
  subject to all non-path safety checks.
* The tool neither redacts nor truncates required evidence.
* The tool performs no upload, commit, push, repository write, or network
  operation.
* Reviewers regenerate rather than reconciling conflicting snapshots manually.

**Status:** superseded

**Superseded by:** D-028

**Related task:** Task 005

---

## D-025 — Render and reconcile deterministic Markdown notes explicitly

**Decision**

Render text-message notes deterministically in application code using
`format_version = 1`. Identify a note file by the source Message's UTC date and
full UUID:

```text
inbox/YYYY-MM-DD--<full-message-uuid>.md
```

Artifact rows store operational metadata and a relative path. Title and slug
are deterministic metadata but do not determine file identity.

Processing locks the source Message and relies on database uniqueness as final
duplicate protection. Files are published atomically without replacing an
existing name. An exact file left without a row after database failure is
preserved and reconciled on the next invocation; conflicting files and
inconsistent rows fail rather than being overwritten or silently repaired.

Set the Message to `done` only when the exact file and valid Artifact row are
both established. Task 006 invokes this boundary manually for one UUID and does
not add a queue or worker.

**Context or problem**

PostgreSQL and the filesystem cannot share a transaction. The first artifact
slice needs stable bytes, idempotency, and recoverability before background
orchestration is introduced.

**Reasoning**

A source-derived path and pure renderer make repeated output comparable.
No-replace publication protects user-visible files, while accepting exact
orphans provides a small recovery rule without an outbox, transaction log, or
compensating deletion.

**Consequences**

* PostgreSQL remains the operational metadata store and Markdown remains the
  readable artifact.
* Repeated and concurrent calls establish one note row and one exact file.
* Database failure may leave a safe exact orphan file by design.
* Source fields are not versioned; later manual mutation can surface a conflict.
* Automatic selection, retries, queues, workers, AI, and Git commits remain
  separate future work.

**Status:** accepted

**Related task:** Task 006

---

## D-026 — Keep durable task orchestration in PostgreSQL

**Decision**

Atomically persist one `generate_note` ProcessingTask with each new Telegram
text Message. PostgreSQL owns task status, attempts, availability, leases,
retry backoff, and terminal outcomes. Redis and Dramatiq provide at-least-once
delivery only.

Run the dispatcher inside the app process and one generic Dramatiq actor in a
separate one-process, one-thread worker. The actor payload contains only the
ProcessingTask UUID. Disable Dramatiq automatic retries and Redis result
storage; the worker reloads and locks PostgreSQL state for every claim.

Keep Task 006 unchanged as the deterministic, idempotent artifact boundary.
Recover lost queued delivery and worker crashes through expiring PostgreSQL
leases and Task 006 reconciliation. App startup, Telegram ingestion,
`/health`, and database-only `/ready` do not depend on Redis availability.

**Context or problem**

Manual processing did not automatically advance newly ingested Messages, and
publishing directly from the Telegram transaction would either couple capture
to Redis or lose work when broker publication failed.

**Reasoning**

The task row acts as both durable scheduling record and orchestration state,
so Redis can be restarted or lose messages without losing work. Conditional
queued/final updates plus attempt-number ownership tolerate fast workers,
duplicate delivery, and late finalizers without an additional outbox or event
table.

**Consequences**

* Telegram acknowledgement confirms atomic Message/task capture only.
* Delivery is at least once rather than exactly once.
* Attempts count worker claims, not broker publications.
* Queued and running work is recoverable after fixed lease expiry.
* Existing Messages are not backfilled automatically.
* ProcessingEvent, heartbeats, multiple queues/workers, admin retry tools, AI,
  notifications, and Git automation remain postponed.

**Status:** accepted

**Related task:** Task 007

---

## D-027 — Restrict Telegram ingestion at a configured private-owner boundary

**Decision**

Authorize Telegram message handling only when the update is from a private
chat and `message.from_user.id` belongs to the configured startup allowlist.
Silently reject every other Telegram message before handler response or
operational-state mutation.

Authorization must not use chat ID, message ID, username, names, persisted User
profile fields, or another mutable identity attribute. Enabled polling requires
a non-empty allowlist represented as a JSON array of positive numeric Telegram
user IDs.

**Context or problem**

The bot is a personal ingestion boundary. Content-based aiogram routing alone
allowed an unknown sender or a group participant to create durable User,
Message, and ProcessingTask state and trigger downstream processing.

**Reasoning**

Telegram sender user ID is the stable identity already kept separate from chat
and message identity. A shared app-process routing filter applies the check to
every current message handler before persistence while avoiding database,
Redis, or Telegram lookups.

**Consequences**

* Only allowlisted senders in private chats can use `/start` or text ingestion.
* Missing-sender, unknown-sender, group, supergroup, and channel messages receive
  no response and create no state.
* The allowlist is immutable for the process lifetime; changes require restart.
* No database permission model or runtime owner-management command is added.
* Existing durable ProcessingTasks are not reauthorized or cancelled, and the
  worker does not need the allowlist.
* Group ingestion and runtime owner management remain postponed.

**Status:** accepted

**Related task:** Task 008

---

## D-028 — Review bounded tasks through exact GitHub pull-request heads

**Decision**

Repository-owned task specifications remain the implementation-review
contracts. Each active task uses one pushed task branch and one GitHub pull
request, with the contract pinned by its repository path and exact full commit
SHA. Normal task work is not committed or pushed directly to the default
branch.

GitHub represents committed and pushed state only. Codex's local uncommitted
working tree remains a distinct authority for editing and local verification;
Handoff Review cannot inspect it. The PR base and exact pushed head, commits,
and patch replace generated review packaging. The PR description replaces the
separate external completion summary, but its verification results remain
supplied claims unless an available CI check executed them independently.

Handoff Review identifies the exact PR head SHA reviewed. Corrections use
bounded commits on the same task branch and require review of the new head.
Codex does not force-push reviewed history, push directly to the default branch,
or merge without separate explicit authorization. The normal accepted merge
method is a merge commit so contract and implementation commit identities are
preserved.

The Task 004 and Task 005 reporting mechanisms are superseded only because the
Task 009 access gate succeeded for the explicitly accepted public-repository
pilot. Connector access while the repository is private remains unverified and
must be established separately before making that claim.

**Context or problem**

Generated reports and review packages were a compatibility boundary when the
review surface could not inspect the repository. Once connected review could
inspect an exact contract commit and PR patch, maintaining parallel generated
evidence added avoidable staleness and upload risk.

**Reasoning**

The branch and PR model preserves the principles behind D-023 and D-024 while
using Git's native immutable identities. The repository still owns the
workflow, the contract still precedes implementation, requirements are not
rewritten to fit code, summaries are not independent sources of truth, and
review evidence still names one exact repository state.

**Consequences**

* Task specifications define their own exact commit, push, PR, correction, and
  merge authority.
* The task path at the recorded contract SHA outranks later branch-head edits.
* PR descriptions must distinguish reported local verification from CI.
* Any new pushed commit invalidates approval of the previous head.
* Private-repository connector access remains an explicit unverified item after
  the public Task 009 pilot.

**Status:** accepted

**Related task:** Task 009

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
