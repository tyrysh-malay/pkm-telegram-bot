# Task 001: PostgreSQL persistence foundation

## Goal

Add a minimal PostgreSQL persistence layer that prepares the application for Telegram text ingestion.

This task should introduce database infrastructure and the first models, but should not implement Telegram handling, background workers, Redis, AI calls, or Markdown generation.

## Scope

Add:

* PostgreSQL service to Docker Compose;
* SQLAlchemy 2.x;
* Alembic;
* PostgreSQL database driver;
* application database settings;
* async database engine and session factory;
* `User` model;
* `Message` model;
* initial Alembic migration;
* database connectivity test;
* model constraint tests where practical.

## Out of scope

Do not add:

* aiogram;
* Telegram handlers;
* Redis;
* Dramatiq;
* Celery;
* background jobs;
* AI provider integrations;
* Markdown rendering;
* Git operations;
* repository pattern abstractions;
* service layer abstractions that are not yet used.

## Database configuration

Expected environment variable:

```text
DATABASE_URL
```

Example development value:

```text
postgresql+asyncpg://pkm:pkm@postgres:5432/pkm
```

Add only placeholder values to `.env.example`.

Do not commit real credentials.

## Initial models

### User

Required fields:

```text
id
telegram_user_id
username
first_name
last_name
created_at
updated_at
```

Requirements:

* UUID primary key;
* unique `telegram_user_id`;
* Telegram names nullable;
* timezone-aware timestamps.

### Message

Required fields:

```text
id
user_id
telegram_chat_id
telegram_message_id
input_type
raw_text
caption
telegram_file_id
source_url
status
idempotency_key
created_at
updated_at
```

Requirements:

* UUID primary key;
* foreign key to `users`;
* unique `idempotency_key`;
* Telegram IDs stored as BIGINT;
* nullable fields where the input type may not provide a value;
* timezone-aware timestamps.

Do not implement `ProcessingTask`, `Artifact`, or `ProcessingEvent` unless they are required for a concrete acceptance criterion in this task.

## Suggested package structure

Adapt to the existing repository when necessary:

```text
app/
  db/
    __init__.py
    base.py
    models.py
    session.py
  settings.py
alembic/
  versions/
alembic.ini
tests/
  test_database.py
  test_models.py
```

Do not split every model into a separate file at this stage unless the existing code structure clearly benefits from it.

## Health behavior

Keep the existing `/health` endpoint lightweight.

Add a separate database readiness endpoint only if it remains simple, for example:

```text
/ready
```

Expected behavior:

* `/health` confirms that the process is running;
* `/ready` confirms that the database connection works.

Do not make `/health` fail solely because PostgreSQL is temporarily unavailable.

## Docker Compose

Add a PostgreSQL service with:

* a named persistent volume;
* development credentials sourced from environment variables or safe defaults;
* a health check;
* the app configured with `DATABASE_URL`.

The app should not start accepting database-dependent requests before PostgreSQL is ready.

Avoid complicated shell wait scripts when Compose health checks and dependency conditions are sufficient.

## Migrations

Create an initial Alembic migration for `users` and `messages`.

The migration must be committed to the repository.

Do not rely on automatic `create_all()` during application startup.

## Tests

At minimum, verify:

* the app can connect to the test/development database;
* `telegram_user_id` is unique;
* `idempotency_key` is unique;
* a message can reference a user;
* migrations can be applied successfully.

Keep integration test setup small.

Do not introduce a separate production-grade test database system unless necessary.

## Acceptance criteria

The following commands succeed from a clean environment:

```bash
docker compose up -d --build
docker compose exec app alembic upgrade head
docker compose exec app python -m pytest
```

The following are also true:

* PostgreSQL is running and healthy.
* The initial migration creates `users` and `messages`.
* `/health` still works.
* Database readiness can be verified.
* No Telegram, Redis, worker, AI, or Markdown behavior has been added.
* `.env.example` contains safe example database configuration.
* README documents database startup and migration commands.

## Implementation guidance

Before editing:

1. Read `AGENTS.md`.
2. Read `docs/PROJECT_BRIEF.md`.
3. Read `docs/ARCHITECTURE.md`.
4. Read `docs/DATA_MODEL.md`.
5. Inspect the existing bootstrap implementation.
6. Present a concise implementation plan.

Make the smallest implementation that satisfies this task.

After editing:

1. run Compose configuration validation;
2. build the development image;
3. start PostgreSQL and the app;
4. apply migrations;
5. run tests;
6. report any verification that could not be completed.

