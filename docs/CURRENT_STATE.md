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
Not implemented:

```text
queue
worker
AI processing
Markdown generation
Git-backed artifact commit
Telegram webhook ingestion
```

## Repository workflow and context reporting

Task 004 is complete. It adds the repository-local workflow documentation:

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
6. deletes test `messages` and `users` only from the test database.

The application runtime and normal Alembic command still use the development
database.

## Verification notes

The updated Dockerfile includes `git` so the Git-based context utility can run
inside the development image.

The updated development image rebuilt successfully. The focused context suite
passed 10 tests, and the complete authoritative suite passed 25 tests.

Host-to-published-port checks succeeded for both `/health` and `/ready`.

## Known limitations

* Only text input is implemented.
* No dedicated link extraction.
* No voice processing.
* No image processing.
* No file or PDF processing.
* No Redis queue.
* No background worker.
* No AI provider integration.
* No Markdown artifact generation.
* No Git-backed artifact commits.
* No webhook ingestion.
* Long polling assumes a single app process when enabled.
* No confirmed user allowlist.
