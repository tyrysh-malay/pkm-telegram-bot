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

1. Inspect the current branch, HEAD, status, remotes, expected default-branch
   relationship, recent commits, and current diff.
2. Confirm the active task branch is based on the expected pushed default
   branch and contains no unrelated work.
3. Read the task contract at the exact recorded contract commit, then read
   `docs/CURRENT_STATE.md`, `docs/WORKFLOW.md`, and every referenced document.
4. Inspect relevant live code, tests, configuration, and repository structure
   before trusting documentation. Report contradictions before editing.
5. Present a concise implementation plan, then make the smallest in-scope
   change without speculative abstractions or unrelated refactoring.
6. Add or update tests and run the task's required acceptance verification.
7. Update affected documentation only after behavior is verified.
8. Update the pull-request description with supplied verification claims and
   identify the exact pushed head under review.
9. Protect secrets and leave unrelated local changes untouched.

Codex may create commits or push only when the active task or user explicitly
authorizes the exact branch and commit boundary. Push only the authorized task
branch. Never push directly to the default branch, merge a pull request, or
force-push reviewed work without separate explicit authorization.

The complete lifecycle, conversation responsibilities, source-of-truth rules,
and documentation update matrix are in `docs/WORKFLOW.md`.

When CI is available, inspect its result for the exact pushed task-branch head.
The required CI check must pass before marking a pull request ready or
presenting the implementation as ready for final review. Any correction commit
invalidates an earlier green result. CI success does not authorize a merge.

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
