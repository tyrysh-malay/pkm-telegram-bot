# Current Project State

This document describes the current semantic state of the repository. Generated
context reports and Git commands provide branch, commit, recent-commit, and
working-tree facts.

**Active task:** none selected

## Working functionality

Confirmed working:

* PostgreSQL starts through Docker Compose.
* FastAPI starts under Uvicorn in the app container.
* Inside the app container, `GET /health` returns `200 OK`.
* Inside the app container, `GET /ready` returns `200 OK`.
* Alembic migrations initialize the test database during pytest.
* Telegram text ingestion is implemented through aiogram long polling, user
  persistence, message persistence, and duplicate message protection.
* Persisted text messages can be processed manually into deterministic
  format-version-1 Markdown notes under `knowledge-base/inbox/`.
* Artifact metadata is persisted in PostgreSQL, and successful reconciliation
  establishes `Message.status = "done"`.
* Same-message processing uses PostgreSQL row locking, uniqueness constraints,
  atomic no-replace file publication, and explicit filesystem/database
  reconciliation.
* The one-message developer command is:

  ```bash
  python -m app.knowledge.cli --message-id <uuid>
  ```

The successful manual data flow is:

```text
persisted text Message
→ deterministic Markdown note
→ Artifact row
→ Message status done
```

Not implemented:

```text
queue
worker
AI processing
Git-backed artifact commit
automatic artifact processing
Telegram webhook ingestion
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
python3 scripts/project_context.py > /tmp/pkm-project-context.md
```

Generated reports are point-in-time snapshots. The live repository remains the
source of truth.

For a complete implementation-review handoff, Codex first creates the explicit
completion report outside the repository and then runs:

```bash
python3 scripts/review_bundle.py \
  --task tasks/<active-task>.md \
  --report /tmp/<task>-handoff.md \
  > /tmp/<task>-review-bundle.md
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
6. deletes test `artifacts`, `messages`, and `users` in foreign-key order only
   from the test database.

The application runtime and normal Alembic command still use the development
database.

## Verification notes

The development image includes Git and copies the complete `scripts/` and
`tests/` directories. Repository-aware commands still require execution in a
Git work tree; `.git` is intentionally absent from the image build context.

Task 006 focused rendering, processing, CLI, and migration verification passed:
60 focused artifact tests, one focused migration test, and 55 focused
review-bundle tests. The complete authoritative Docker suite passed 146 tests.
Development database counts remained `users=1`, `messages=1`, and `artifacts=0`
before and after the complete suite.

Migration `0002` upgraded, downgraded to `0001`, and re-upgraded successfully in
the isolated test database while preserving source tables. A disposable CLI row
produced exact expected bytes under `/tmp` and was removed afterward. The
Compose bind mount and hard-link publication primitive were verified without
leaving a marker or note in the repository knowledge base.

An earlier build and host-to-published-port check encountered the documented
local VPN/Docker bridge routing incident. Live rediscovery found active policy
table `51821`, Docker subnet `172.17.0.0/16` on `docker0`, and Compose subnet
`172.19.0.0/16` on `br-bed1c43e4e44`. After adding those two temporary return
routes, the exact `docker compose up -d --build` command succeeded and host
`/health` and `/ready` requests both succeeded. No repository network
configuration changed.

Task 006 implementation verification is complete and its review bundle now
captures the required changed root `.env.example` as tracked evidence. The
general `.env.*` rejection remains in force for untracked paths, reports,
nested templates, and every other filename. Task 006 is completed and no next
task is selected.

## Known limitations

* Only text input is implemented.
* No dedicated link extraction.
* No voice processing.
* No image processing.
* No file or PDF processing.
* No Redis queue.
* No background worker.
* Artifact processing is manual for one message UUID; Telegram ingestion does
  not invoke it.
* No AI provider integration.
* No Git-backed artifact commits.
* No webhook ingestion.
* Long polling assumes a single app process when enabled.
* No confirmed user allowlist.
* Source-message fields are not versioned or made immutable; later manual
  mutation can surface a deterministic artifact conflict.
* Atomic no-replace publication assumes a filesystem that supports same-directory
  hard links, as verified for the current Linux host, pytest temp directories,
  and Compose bind mount.
