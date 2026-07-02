# PKM Telegram Bot

A small Python backend for turning Telegram inputs into Git-backed Markdown knowledge artifacts.

The current foundation includes a FastAPI app, Telegram text persistence,
deterministic Markdown note generation, Artifact persistence, Alembic
migrations, Docker Compose, and tests.

## Requirements

* Python 3.11+
* Docker Compose, optional but recommended

## Local setup

Create a local environment file:

```bash
cp .env.example .env
```

Install dependencies for development:

```bash
python3 -m pip install -e ".[dev]"
```

Run the app locally:

```bash
python3 -m uvicorn app.main:app --reload
```

Check the health endpoint:

```bash
curl http://localhost:8000/health
```

Run tests:

```bash
DATABASE_URL=postgresql+asyncpg://pkm:pkm@localhost:5432/pkm \
TEST_DATABASE_URL=postgresql+asyncpg://pkm:pkm@localhost:5432/pkm_test \
python3 -m pytest
```

Pytest requires `TEST_DATABASE_URL` and refuses to run against the same
database named by `DATABASE_URL`. Host-side pytest uses `localhost` because the
Docker-only hostname `postgres` is available only inside the Compose network.

## Docker Compose

Start the app with Compose:

```bash
docker compose up -d --build
```

The app listens on `http://localhost:8000`.

PostgreSQL is started by Compose with safe development defaults. The app waits for the database health check before starting.

Apply database migrations:

```bash
docker compose exec app alembic upgrade head
```

The Compose app bind-mounts `./knowledge-base` at `/app/knowledge-base`, so
notes generated with the default configuration remain visible on the host.

Run tests inside the development container:

```bash
docker compose exec app python -m pytest
```

The Compose development container sets `TEST_DATABASE_URL` to a separate
`pkm_test` database. Pytest creates that database if needed and initializes its
schema with Alembic migrations.

Check the database readiness endpoint:

```bash
curl http://localhost:8000/ready
```

## Repository context

Print a compact Markdown snapshot of safe repository facts to standard output:

```bash
python3 scripts/project_context.py
```

The command is read-only. To save a handoff outside the repository:

```bash
python3 scripts/project_context.py > /tmp/pkm-project-context.md
```

Use the compact report for orientation and metadata handoff. For review of an
uncommitted task implementation, generate the full implementation-review bundle:

```bash
python3 scripts/review_bundle.py \
  --task tasks/<active-task>.md \
  --report /tmp/<task>-handoff.md \
  > /tmp/<task>-review-bundle.md
```

The completion report and redirected bundle should normally stay outside the
repository. The command is read-only, never includes ignored files, and fails
instead of truncating or packaging unsafe, unsupported, or oversized evidence.
The compact context report and full review bundle serve different purposes.

See `docs/WORKFLOW.md` for the full repository-driven project workflow.

## Telegram polling

Telegram polling is disabled by default so local development and automated tests do not need a bot token.

To run the bot locally, create a real token with BotFather and set these values in your local `.env`:

```text
TELEGRAM_BOT_ENABLED=true
TELEGRAM_BOT_TOKEN=<local secret>
```

Then recreate the app container:

```bash
docker compose up -d --build --force-recreate app
docker compose logs -f app
```

Polling mode expects exactly one app process. Do not run multiple Uvicorn workers while polling is enabled.

## Manual Markdown processing

Artifact processing is currently explicit, not automatic. After migrations are
current, process one already persisted text message by application UUID:

```bash
docker compose exec app \
  python -m app.knowledge.cli --message-id <uuid>
```

Success prints exactly:

```text
artifact_id: <artifact-uuid>
file_path: inbox/YYYY-MM-DD--<message-uuid>.md
```

The command creates or reconciles a deterministic format-version-1 note and
its Artifact row, then marks the Message `done`. Repeating it returns the same
Artifact. It does not contact Telegram, start polling, enqueue work, or commit
the note to Git.

Telegram's `Saved for processing.` acknowledgement still means only that the
raw message was persisted. The Telegram handler does not invoke this command.
See `docs/MARKDOWN_ARTIFACTS.md` for rendering and recovery behavior.

## Environment variables

The app uses:

* `APP_NAME`
* `ENVIRONMENT`
* `DATABASE_URL`
* `TEST_DATABASE_URL`
* `TELEGRAM_BOT_ENABLED`
* `TELEGRAM_BOT_TOKEN`
* `KNOWLEDGE_BASE_PATH` (defaults to `knowledge-base`)

The following variables are documented for later milestones and can remain empty for now:

* `OPENAI_API_KEY`
* `REDIS_URL`
