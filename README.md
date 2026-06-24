# PKM Telegram Bot

A small Python backend for turning Telegram inputs into Git-backed Markdown knowledge artifacts.

The current foundation includes a FastAPI app, PostgreSQL persistence, Alembic migrations, Docker Compose, and tests.

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
python3 -m pytest
```

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

Run tests inside the development container:

```bash
docker compose exec app python -m pytest
```

Check the database readiness endpoint:

```bash
curl http://localhost:8000/ready
```

## Environment variables

The app uses:

* `APP_NAME`
* `ENVIRONMENT`
* `DATABASE_URL`

The following variables are documented for later milestones and can remain empty for now:

* `TELEGRAM_BOT_TOKEN`
* `OPENAI_API_KEY`
* `REDIS_URL`
