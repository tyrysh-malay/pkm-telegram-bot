# Task 000: Bootstrap repository

## Goal

Create the initial Python project skeleton for the PKM Telegram bot.

This task should not implement Telegram handling, database models, queue processing, or AI calls yet.

## Scope

Create:

* Python package structure;
* Docker Compose skeleton;
* `.env.example`;
* basic settings module;
* FastAPI app with `/health`;
* pytest setup;
* README with local development instructions.

## Expected structure

```text
app/
  __init__.py
  main.py
  settings.py
  bot/
    __init__.py
  worker/
    __init__.py
  db/
    __init__.py
  knowledge/
    __init__.py
tests/
  test_health.py
docs/
tasks/
knowledge-base/
docker-compose.yml
.env.example
pyproject.toml
README.md
```

## Technical choices

Use:

* Python 3.11+
* FastAPI
* Pydantic Settings
* pytest
* Docker Compose

Do not add:

* aiogram
* SQLAlchemy
* Alembic
* Redis client
* Dramatiq
* OpenAI SDK

Those will be added in later tasks.

## Acceptance criteria

* `docker compose up` starts the app.
* `GET /health` returns a JSON response.
* `pytest` passes.
* `.env.example` documents expected environment variables.
* README explains how to run the project locally.

## Implementation notes

Keep this task minimal.

Do not create abstractions for future features.

Do not implement fake bot behavior.

Do not add AI code.

The goal is a clean, runnable foundation.
