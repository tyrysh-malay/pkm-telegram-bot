# PKM Telegram Bot

A small Python backend for turning Telegram inputs into Git-backed Markdown knowledge artifacts.

The current foundation includes a FastAPI app, Telegram text persistence,
deterministic Markdown note generation, Artifact persistence, Alembic
migrations, durable PostgreSQL-backed processing, Redis/Dramatiq delivery,
Docker Compose, and tests.

## Requirements

* Python 3.11+
* Docker Compose, optional but recommended
* Git (installed in the shared app/worker development image)

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

PostgreSQL and Redis are started by Compose with safe development defaults.
Compose also starts one Dramatiq worker process with one thread. The app waits
for PostgreSQL but does not wait for Redis, so broker downtime does not block
FastAPI startup or Telegram persistence.

Apply database migrations:

```bash
docker compose exec app alembic upgrade head
```

The app and worker share the same image and bind-mount `./knowledge-base` at
`/app/knowledge-base`, so generated notes remain visible on the host.

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

## Continuous integration

GitHub Actions runs one workflow and job for every pull request targeting
`main` and every push to `main`. The observed pull-request check context is
`CI / Test`. It validates the committed patch, builds the development app image
through Docker Compose, starts only PostgreSQL, and runs the complete pytest
suite in a one-off app container.

CI uses separate disposable `pkm` and `pkm_test` databases. Pytest creates the
test database and applies the committed Alembic migrations. Telegram polling,
the task dispatcher, and AI-provider access are disabled, so the job requires
no Telegram or AI secrets. Compose resources and the CI database volume are
removed after every run.

For local parity, use the isolated environment and command sequence in
[Task 010](tasks/010-github-actions-ci.md#local-ci-parity-verification). Branch
protection is not configured; adding it remains separate future work.

## Contributing through pull requests

Repository-owned task specifications remain the review contract. For each
authorized task:

1. synchronize the local default branch with its remote;
2. create the task's dedicated branch;
3. commit the accepted task contract and open a draft pull request;
4. confirm connected review access;
5. implement and verify locally;
6. commit and push only the authorized task branch;
7. require the available CI check to pass for the exact pushed head;
8. review the exact pushed pull-request head;
9. merge only after approval and separate explicit authorization.

Uncommitted local work is not visible through GitHub and cannot be included in
pull-request review. See `docs/WORKFLOW.md` for authority boundaries, evidence
precedence, correction handling, and documentation responsibilities.

## Telegram polling

Telegram polling is disabled by default so local development and automated tests do not need a bot token.

To run the bot locally, create a real token with BotFather and set these values in your local `.env`:

```text
TELEGRAM_BOT_ENABLED=true
TELEGRAM_BOT_TOKEN=<local secret>
TELEGRAM_ALLOWED_USER_IDS=[123456789]
```

`TELEGRAM_ALLOWED_USER_IDS` is one JSON array of positive numeric Telegram
sender user IDs. It authorizes `from_user.id`, not chat IDs, usernames, or
profile names. Enabled polling requires at least one ID, and the bot accepts
commands and text only from allowlisted senders in private chats. Unknown,
missing-sender, group, supergroup, and channel updates are silently ignored
before any response or database write.

Then recreate the app container:

```bash
docker compose up -d --build --force-recreate app
docker compose logs -f app
```

Polling mode expects exactly one app process. Do not run multiple Uvicorn workers while polling is enabled.
Allowlist changes are loaded only at startup, so recreate or restart the app
after changing the value. There is no runtime owner-management command or
database-backed permission model.

## Background Markdown processing

New Telegram text Messages are committed atomically with a pending
`generate_note` ProcessingTask. The app dispatcher publishes task UUIDs to
Redis, and the worker reloads and claims PostgreSQL state before calling the
deterministic processor. PostgreSQL owns attempts, fixed retry backoff, leases,
and terminal state; Redis is delivery transport only.

Inspect current state with the existing database conventions, for example:

```bash
docker compose exec postgres psql -U pkm -d pkm \
  -c 'select id, message_id, status, attempts, max_attempts, available_at, lease_expires_at from processing_tasks order by created_at;'
```

Redis downtime leaves tasks pending or queued for lease recovery and does not
block ingestion. `/health` remains process liveness and `/ready` remains
database-only readiness.

The worker processes tasks that are already durable in PostgreSQL without
rechecking the Telegram allowlist. Removing an owner therefore blocks new
updates after app restart but does not cancel existing tasks.

The manual Task 006 command remains available for existing Messages without a
ProcessingTask. After migrations are current, process one Message UUID with:

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

Telegram's `Saved for processing.` acknowledgement means that the Message and
task were durably persisted, not that processing completed. There is no
worker-to-Telegram completion notification, AI processing, or Git automation.
See `docs/MARKDOWN_ARTIFACTS.md` for rendering and recovery behavior.

## Manual Git publication

Git publication is a separate developer action. Initialize the configured
knowledge-base root explicitly and set a repository-local identity; the
application never initializes a repository or changes branches:

```bash
git -C knowledge-base init
git -C knowledge-base config --local user.name "<desired commit author>"
git -C knowledge-base config --local user.email "<desired commit email>"
```

`KNOWLEDGE_BASE_PATH` must resolve to that repository's exact top-level, not a
child of the application repository or another parent repository. The current
branch must be attached (an unborn named branch is allowed), repository-local
author values must be nonblank, and the Git index must be empty. Unrelated
unstaged and untracked files are allowed and preserved.

After migrations are current and an Artifact's deterministic file already
exists, publish one Artifact UUID:

```bash
docker compose exec app \
  python -m app.knowledge.git_cli --artifact-id <artifact-uuid>
```

Success prints exactly:

```text
artifact_id: <artifact-uuid>
file_path: <repository-relative-path>
git_commit_sha: <full-commit-sha>
outcome: created|reconciled|existing
```

The command validates Task 006 metadata and bytes, stages only the selected
path, creates one local commit, and stores its SHA. It disables repository
hooks and performs no clone, fetch, pull, push, remote configuration, or
worker/ingestion integration. If the Git commit succeeds but the database
update fails, the commit is retained; rerunning reconciles its stable Artifact
trailers without creating a second commit. See `docs/GIT_PUBLICATION.md` for
the complete safety and recovery boundary.

## Environment variables

The app uses:

* `APP_NAME`
* `ENVIRONMENT`
* `DATABASE_URL`
* `TEST_DATABASE_URL`
* `TELEGRAM_BOT_ENABLED`
* `TELEGRAM_BOT_TOKEN`
* `TELEGRAM_ALLOWED_USER_IDS` (JSON array; required and non-empty when polling is enabled)
* `KNOWLEDGE_BASE_PATH` (defaults to `knowledge-base`)
* `REDIS_URL` (defaults to `redis://redis:6379/0`)
* `TASK_DISPATCHER_ENABLED` (defaults to `false`; Compose enables it for app)

The following variable is documented for later milestones and can remain empty:

* `OPENAI_API_KEY`
