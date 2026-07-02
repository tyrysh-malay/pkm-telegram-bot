# AGENTS.md

## Project role

You are working on a Python backend/AI project: a Personal Knowledge Management Telegram bot.

The goal is to build a production-minded but small MVP that ingests Telegram inputs and turns them into Git-backed Markdown knowledge artifacts.

## Product priorities

1. Keep the MVP small.
2. Prefer simple code over abstract framework design.
3. Build vertical slices end-to-end.
4. Avoid unnecessary microservices.
5. Use production-minded patterns only when they solve a real problem.
6. Make changes reviewable through small commits.

## Tech stack

Preferred stack:

* Python 3.11+
* aiogram for Telegram bot
* FastAPI for webhook/health endpoints
* PostgreSQL for operational state
* Redis for queue/broker/rate limits
* Dramatiq for background jobs
* SQLAlchemy + Alembic for database
* Pydantic for schemas and structured outputs
* Docker Compose for local development
* pytest for tests

Do not introduce LangChain, LangGraph, Celery, Kubernetes, vector databases, or microservices unless explicitly requested.

## Architecture rule

Use one codebase with two runtime processes:

* app: Telegram bot + FastAPI endpoints
* worker: background processing tasks

Do not split the MVP into multiple repositories or services.

## Development workflow

Before implementing a task:

1. Inspect the current branch, HEAD, status, recent commits, and diff.
2. Read the active task, `docs/CURRENT_STATE.md`, `docs/WORKFLOW.md`, and every
   document referenced by the task.
3. Inspect relevant live code, tests, configuration, and repository structure
   before trusting documentation. Distinguish verified facts from stale or
   aspirational claims and report contradictions.
4. Present a concise implementation plan before editing.
5. Make the smallest in-scope change. Avoid postponed functionality,
   speculative abstractions, and unrelated refactoring.
6. Add or update tests, then run the task's acceptance verification.
7. Update affected documentation only after behavior is verified.
8. Protect secrets and do not expose local configuration values.
9. Do not commit unless explicitly instructed.
10. Produce the completion report required by the active task.

The complete lifecycle, conversation responsibilities, source-of-truth rules,
and documentation update matrix are in `docs/WORKFLOW.md`.

## Code style

* Prefer readable, explicit Python.
* Avoid clever abstractions.
* Do not create helper functions for one-off logic unless they improve clarity.
* Keep modules small and named by responsibility.
* Use type hints for public functions and important internal boundaries.
* Use Pydantic models for structured data crossing boundaries.
* Use deterministic post-processing where possible; do not rely on LLM text when code can render the output.

## Reliability expectations

When implementing ingestion or processing logic, consider:

* idempotency
* retries
* error states
* logging
* task status persistence
* safe recovery after worker crashes

Do not silently swallow exceptions.

## Git and knowledge-base behavior

Generated Markdown files should be written under `knowledge-base/`.

Do not commit generated notes automatically until the Git writer milestone is implemented.

For now, create deterministic file paths and ensure generated Markdown is stable across repeated runs.

## Secrets

Never commit real secrets.

Use `.env.example` for configuration examples.

Expected secret names:

* TELEGRAM_BOT_TOKEN
* OPENAI_API_KEY
* DATABASE_URL
* REDIS_URL

## Testing

Use pytest.

Prioritize tests for:

* slug generation
* idempotency key generation
* Markdown rendering
* Pydantic schema validation
* task status transitions

## Documentation

When architecture or behavior changes, update the relevant document in `docs/`.

Prefer short docs that explain current behavior over aspirational docs.
