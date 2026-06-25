# Current Project State

This document is intentionally short-lived. Replace or substantially update it
after each completed task.

## Repository checkpoint

**Branch:** `main`

**Latest commit before Task 003 implementation:** `6df74b6 docs: Define database test isolation task`

**Working tree status:** contains uncommitted Task 003 changes.

## Working functionality

Confirmed working:

* Docker Compose builds and starts the application.
* PostgreSQL starts through Docker Compose.
* FastAPI starts under Uvicorn.
* `GET /health` returns `200 OK`.
* `GET /ready` returns `200 OK`.
* Alembic migrations apply to the development database with:

  ```bash
  docker compose exec app alembic upgrade head
  ```

* The full pytest suite passes inside the application container:

  ```text
  15 passed in 5.42s
  ```

* Telegram text ingestion remains implemented through aiogram long polling, user
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

## Database test isolation

Task 003 is implemented.

The development application uses:

```text
DATABASE_URL=postgresql+asyncpg://pkm:pkm@postgres:5432/pkm
```

Pytest uses:

```text
TEST_DATABASE_URL=postgresql+asyncpg://pkm:pkm@postgres:5432/pkm_test
```

The pytest bootstrap:

1. requires `TEST_DATABASE_URL`;
2. rejects a test URL that targets the same database name as `DATABASE_URL`;
3. sets `DATABASE_URL` to `TEST_DATABASE_URL` inside the pytest process before
   database modules and Alembic run;
4. creates `pkm_test` if it is missing;
5. initializes `pkm_test` from committed Alembic migrations;
6. deletes test `messages` and `users` only from `pkm_test`.

The application runtime and normal Alembic command still use the development
database.

## Task 003 verification

Before pytest, a development marker row existed:

```text
users=1
messages=1
marker_messages=1
fixture_users=0
```

The rebuilt Compose services were verified with:

```bash
docker compose up -d --build
docker compose config --quiet
docker compose exec app alembic upgrade head
docker compose exec app python -m pytest
```

The `docker compose up -d --build` command succeeded. Docker Compose printed a
warning that Bake is configured but `buildx` is not installed.

The test database was migrated and cleaned:

```text
database=pkm_test
alembic_version=0001
test_users=0
test_messages=0
```

After pytest, the development database was unchanged:

```text
users=1
messages=1
marker_messages=1
fixture_users=0
```

The checked fixture usernames were absent from the development database:

```text
duplicate_user
new_username
original_user
pkm_user
```

Endpoint checks after the pytest run:

```text
/health -> {"status":"ok","app":"PKM Telegram Bot","environment":"development"}
/ready  -> {"status":"ready","database":"ok"}
```

The rebuilt local app configuration has Telegram polling enabled and a token
present. A live Telegram regression message was not sent from this environment,
so live Telegram acknowledgement and row creation remain unverified for Task 003
finalization.

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

## Immediate next actions

1. Review and commit the Task 003 isolation changes.
2. Keep the Telegram identity concern separate unless repository evidence shows
   a confirmed bug.
