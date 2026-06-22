# PKM Telegram Bot

A small Python backend for turning Telegram inputs into Git-backed Markdown knowledge artifacts.

Task 000 bootstraps only the runnable foundation: a FastAPI app, settings, Docker Compose, and tests.

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
docker compose up --build
```

The app listens on `http://localhost:8000`.

## Environment variables

The current bootstrap app only uses:

* `APP_NAME`
* `ENVIRONMENT`

The following variables are documented for later milestones and can remain empty for now:

* `TELEGRAM_BOT_TOKEN`
* `OPENAI_API_KEY`
* `DATABASE_URL`
* `REDIS_URL`
