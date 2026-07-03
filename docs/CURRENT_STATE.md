# Current Project State

This document describes the current semantic state of the repository. Generated
context reports and Git commands provide branch, commit, recent-commit, and
working-tree facts.

**Active task:** `tasks/009-github-backed-collaboration.md`

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
→ ProcessingTask succeeded
```

Not implemented:

```text
AI processing
Git-backed artifact commit
Telegram webhook ingestion
runtime allowlist administration
group, supergroup, or channel ingestion
```

## Repository workflow and review reporting

The repository-local workflow documentation is:

```text
docs/WORKFLOW.md
```

The reusable task specification template is:

```text
tasks/TEMPLATE.md
```

The read-only project context report command is:

```bash
python3 scripts/project_context.py
```

The command prints Markdown to standard output. It uses read-only Git queries
and whitelisted task/document metadata, writes nothing, does not read `.env` or
environment variables, and redacts secret-like changed-path names.

To create a handoff file outside the repository:

```bash
mkdir -p "$HOME/pkm-handoffs"
python3 scripts/project_context.py > "$HOME/pkm-handoffs/pkm-project-context.md"
```

Generated reports are point-in-time snapshots. The live repository remains the
source of truth.

For a complete implementation-review handoff, Codex first creates the explicit
completion report outside the repository and then runs:

```bash
python3 scripts/review_bundle.py \
  --task tasks/<active-task>.md \
  --report "$HOME/pkm-handoffs/<task>-handoff.md" \
  > "$HOME/pkm-handoffs/<task>-review-bundle.md"
```

The review bundle reads the committed task contract from `HEAD`, captures the
complete safe tracked diff and non-ignored untracked text files, and includes
deterministic changed-file and evidence manifests. It fails before stdout output
for ignored, secret-like, unsupported, inconsistent, or oversized evidence. It
does not write repository files, use the network, upload, or run the verification
claims in the supplied completion report.

The compact context report remains the metadata-oriented command; the review
bundle is the separate full implementation-evidence command. Both outputs are
point-in-time snapshots and must be regenerated after their source state changes.

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

The development image includes Git and copies the complete `scripts/` and
`tests/` directories. Repository-aware commands still require execution in a
Git work tree; `.git` is intentionally absent from the image build context.

Task 008 authorization and ingestion coverage passed 44 focused tests, and 91
focused Task 006/007 processing regressions passed unchanged. The full suite
passed 219 tests. Development counts and stable identity hashes remained
unchanged at `users=1`, `messages=1`, `artifacts=0`, and
`processing_tasks=0`.

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
* No Git-backed artifact commits.
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
