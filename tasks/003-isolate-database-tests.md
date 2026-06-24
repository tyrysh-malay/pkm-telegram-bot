# Task 003: Isolate database tests from development data

## Goal

Ensure that running the automated test suite cannot delete, modify, or populate the PostgreSQL database used by the locally running development bot.

## Confirmed problem

The development database contained live Telegram message records.

After running:

```bash
docker compose exec app python -m pytest
```

the development `messages` table count dropped to zero.

Therefore, the current test setup destructively modifies the same database used by the development application.

The exact fixture or cleanup mechanism responsible for this behavior still requires repository inspection.

## Scope

Investigate and fix database isolation for automated tests.

The implementation should ensure that:

* the development application uses the development database;
* pytest uses an isolated test database;
* test setup and cleanup affect only the test database;
* existing development users and messages remain unchanged after pytest;
* test fixture rows never appear in the development database;
* the test database can be initialized from committed migrations.

## Preferred design

Prefer a separate PostgreSQL test database, for example:

```text
development database: pkm
test database:        pkm_test
```

Possible configuration:

```text
DATABASE_URL
TEST_DATABASE_URL
```

The exact implementation should be chosen after inspecting the current settings, Compose configuration, and pytest fixtures.

A transaction-rollback-only approach is acceptable only if it remains reliable when application code creates its own sessions and commits transactions.

## Investigation requirements

Before editing, inspect:

* all `conftest.py` files;
* all database-related pytest fixtures;
* application database settings;
* test database settings, if any;
* SQLAlchemy engine and session creation;
* cleanup code using:

  * `DELETE`;
  * `TRUNCATE`;
  * `drop_all`;
  * `create_all`;
* Docker Compose PostgreSQL configuration;
* migration setup.

Determine:

1. whether pytest uses the normal `DATABASE_URL`;
2. which fixture or test clears the development tables;
3. whether cleanup occurs before tests, after tests, or both;
4. whether tests commit fixture rows;
5. whether a separate test database already partially exists.

## Out of scope

Do not add or change:

* Redis;
* task queues;
* background workers;
* AI processing;
* Markdown generation;
* Git-backed artifact writing;
* voice or image processing;
* Telegram webhook support;
* Telegram identity redesign;
* application authorization or allowlisting;
* unrelated persistence refactoring.

The Telegram identity concern is separate and remains unconfirmed.

## Acceptance criteria

### Test isolation

Given a marker row in the development database:

1. run the complete pytest suite;
2. confirm that the marker row still exists;
3. confirm that development user and message counts remain unchanged;
4. confirm that test fixture rows are absent from the development database.

### Test database behavior

* pytest uses a database distinct from the development database;
* migrations can initialize the test database from scratch;
* test cleanup affects only the test database;
* the complete test suite passes.

### Existing application behavior

The following continue to succeed:

```bash
docker compose config
docker compose up -d --build
docker compose exec app alembic upgrade head
docker compose exec app python -m pytest
```

The following continue to return success:

```bash
curl --retry 5 --retry-all-errors --retry-delay 1 \
  http://localhost:8000/health

curl --retry 5 --retry-all-errors --retry-delay 1 \
  http://localhost:8000/ready
```

Live Telegram ingestion must remain unchanged.

## Required verification

Before pytest, record development database counts:

```sql
SELECT COUNT(*) FROM users;
SELECT COUNT(*) FROM messages;
```

Run:

```bash
docker compose exec app python -m pytest
```

Then repeat the count queries.

The counts and existing live rows must remain unchanged.

Also confirm that fixture users such as the following are not present in the development database:

```text
duplicate_user
new_username
original_user
pkm_user
```

## Documentation

Update:

* `docs/CURRENT_STATE.md`;
* existing development documentation if new test-database commands or variables are introduced;
* `.env.example` if `TEST_DATABASE_URL` or equivalent configuration is added.

Add a durable entry to `docs/DECISIONS.md` only after the isolation design is implemented and accepted.

## Completion report

Report:

* the original cause;
* changed files;
* final database-isolation design;
* commands run;
* migration behavior;
* pytest result;
* development database counts before and after testing;
* anything that could not be verified.
