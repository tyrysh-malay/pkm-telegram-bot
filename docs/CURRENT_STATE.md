# Current Project State

This document describes the current semantic state of the repository. Live Git
and pull-request inspection provide branch, commit, review-head, and
working-tree facts.

**Active task:** `tasks/013-manual-structured-ai-enrichment.md`

## Working functionality

Confirmed working:

* PostgreSQL starts through Docker Compose.
* FastAPI starts under Uvicorn in the app container.
* Inside the app container, `GET /health` returns `200 OK`.
* Inside the app container, `GET /ready` returns `200 OK`.
* Alembic migrations initialize the test database during pytest.
* Telegram text ingestion is implemented through aiogram long polling, user
  sender-ID authorization, private-chat enforcement, user persistence, atomic
  Message/ProcessingTask persistence, and duplicate protection.
* One shared aiogram message-routing filter silently rejects missing senders,
  unknown senders, and non-private chats before handler response or database
  work. The immutable allowlist is loaded from startup configuration.
* The app-process dispatcher publishes due ProcessingTask UUIDs through Redis.
* One Dramatiq worker process/thread claims PostgreSQL tasks, invokes Task 006,
  and conditionally finalizes attempts.
* Newly ingested text messages are processed automatically into deterministic
  format-version-1 Markdown notes under `knowledge-base/inbox/`.
* Artifact metadata is persisted in PostgreSQL, and successful reconciliation
  establishes `Message.status = "done"`.
* One manual Artifact-UUID CLI validates an existing Artifact and exact file,
  creates or reconciles one local selected-path Git commit, and persists its
  full SHA on `Artifact.git_commit_sha`.
* Successful `generate_note` finalization can atomically establish one durable
  `publish_artifact` ProcessingTask. The generic worker resolves the existing
  note Artifact and reuses the Task 011 local Git publisher.
* Automatic publication creation defaults to disabled. The setting gates only
  new downstream creation; already durable publication tasks continue to run,
  and historical notes are not backfilled.
* Manual Git publication requires `KNOWLEDGE_BASE_PATH` to be the exact
  initialized repository top-level, an attached named branch, repository-local
  author identity, and an empty index. It preserves unrelated unstaged state.
* Same-message processing uses PostgreSQL row locking, uniqueness constraints,
  atomic no-replace file publication, and explicit filesystem/database
  reconciliation.
* Redis is transport only; PostgreSQL owns pending, queued, running, retrying,
  succeeded, and failed state, attempts, availability, and leases.
* Expired queued/running leases recover lost delivery and worker crashes.
* The one-message developer command remains supported, including for legacy
  Messages without ProcessingTask rows:

  ```bash
  python -m app.knowledge.cli --message-id <uuid>
  ```

The automatic data flow is:

```text
Telegram text
→ private chat + configured sender-ID authorization
→ Message + pending ProcessingTask committed atomically
→ app dispatcher → Redis → worker PostgreSQL claim
→ unchanged deterministic Task 006 processing
→ generate_note succeeded + optional publish_artifact committed atomically
→ app dispatcher → Redis → worker PostgreSQL claim
→ unchanged Task 011 local Git publication
→ publish_artifact succeeded + Artifact.git_commit_sha
```

Not implemented:

```text
AI processing
remote Git synchronization
Telegram webhook ingestion
runtime allowlist administration
group, supergroup, or channel ingestion
```

## Repository workflow and pull-request review

The repository-local workflow documentation is:

```text
docs/WORKFLOW.md
```

The reusable task specification template is:

```text
tasks/TEMPLATE.md
```

The collaboration boundaries are:

```text
pushed default branch = accepted shared baseline
pushed task branch + PR = active shared review state
local working tree = Codex-only uncommitted state
task contract = exact task path at recorded contract SHA
PR head SHA = exact implementation state under review
```

One bounded task uses one authorized task branch and one pull request.
Uncommitted work must be committed and pushed before Handoff Review can inspect
it. The PR description supplies implementation and verification claims; those
claims are independent proof only when an available CI check executed them.

The repository is public again, and Web Chat verified public access to the
replacement Task 009 review PR #2. PR #1 remains closed and is not reused.
Connector access to the same evidence while the repository is private remains
unverified and must not be inferred from either public access check.

GitHub Actions provides one `CI` workflow and one `Test` job for pull requests
targeting `main` and pushes to `main`. The observed pull-request check context
is `CI / Test`. Readiness requires that check to succeed for the exact current
pushed head; a later correction invalidates the earlier result.

The job validates the committed event range, builds the development image,
starts only PostgreSQL, and runs pytest in a one-off app container. It uses
separate disposable development and test database names; pytest creates the
test database and applies Alembic migrations. Telegram polling, task dispatch,
and AI-provider access are disabled without live secrets. Cleanup removes the
CI database volume unconditionally. Redis, the worker, custom caching, branch
protection, deployment, and publishing are outside this CI boundary.

## Database test isolation

The development application uses `DATABASE_URL`.

Pytest uses `TEST_DATABASE_URL`, which must target a different database name
from `DATABASE_URL`.

The pytest bootstrap:

1. requires `TEST_DATABASE_URL`;
2. rejects a test URL that targets the same database name as `DATABASE_URL`;
3. sets `DATABASE_URL` to `TEST_DATABASE_URL` inside the pytest process before
   database modules and Alembic run;
4. creates the test database if it is missing;
5. initializes the test database from committed Alembic migrations;
6. deletes test `processing_tasks`, `artifacts`, `messages`, and `users` in
   foreign-key order only from the test database.

The application runtime and normal Alembic command still use the development
database.

## Verification notes

The development image copies the complete application test suite. Repository
collaboration runs from the host checkout rather than from the application
image, whose build context intentionally excludes `.git`.

The `CI / Test` check independently verifies the exact selected source SHA,
committed patch integrity, Compose configuration, a clean development-image
build, PostgreSQL readiness, the complete test suite, and unconditional
cleanup. The local Docker/VPN bridge can still stall a fresh dependency fetch;
the GitHub-hosted clean build is the independent image-build evidence.

Task 012 focused chaining, publication, recovery, configuration, migration,
CLI, and Task 006/007/011 regression coverage passes with real system Git. The
complete suite passes 235 tests.
Migration `0004` downgrades to `0003` and re-upgrades while preserving
User, Message, Artifact, ProcessingTask, and Message-status state; the restored
publication SHA column remains nullable.

Disabled Telegram configuration accepts an empty allowlist; enabled
configuration rejects an empty allowlist and accepts a valid non-empty JSON
array without contacting Telegram. A disposable authorized private-message
smoke reached one succeeded ProcessingTask, one done Message, one Artifact, and
an exact deterministic note, then removed all of its rows and file.

Migration `0003` downgraded to `0002` and re-upgraded in the isolated test
database while preserving User, Message, Artifact, and Message status state.
The four-service Compose runtime was verified with Dramatiq 2.2.0. With Redis
and worker stopped, ingestion created a pending task with zero attempts while
`/health` and `/ready` remained successful. Restoring them without restarting
the app completed the task on attempt 1 with exact Task 006 bytes. All smoke
rows, note files, and temporary files were removed.

The synchronous actor disposes the process-level async SQLAlchemy engine before
each per-delivery event loop closes. Two sequential real actor calls and two
sequential Compose deliveries completed in the same worker process without
cross-event-loop pooled connections.

## Known limitations

* Only text input is implemented.
* No dedicated link extraction.
* No voice processing.
* No image processing.
* No file or PDF processing.
* No AI provider integration.
* No remote Git synchronization.
* No webhook ingestion.
* Long polling assumes a single app process when enabled.
* Telegram owner changes require an app restart; no database-backed permission
  model or runtime allowlist command exists.
* No worker-to-Telegram completion or failure notification.
* Existing Messages are not automatically backfilled with ProcessingTasks.
* Retry timing and leases use fixed first-version constants without heartbeat
  extension or an administration UI.
* Source-message fields are not versioned or made immutable; later manual
  mutation can surface a deterministic artifact conflict.
* Atomic no-replace publication assumes a filesystem that supports same-directory
  hard links, as verified for the current Linux host, pytest temp directories,
  and Compose bind mount.
