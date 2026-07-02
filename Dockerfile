FROM python:3.11-slim

WORKDIR /app

ARG INSTALL_DEV=false

RUN if [ "$INSTALL_DEV" = "true" ]; then \
        apt-get update \
        && apt-get install -y --no-install-recommends git \
        && rm -rf /var/lib/apt/lists/*; \
    fi

COPY pyproject.toml README.md ./
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./
COPY docs/WORKFLOW.md ./docs/WORKFLOW.md
COPY tasks/TEMPLATE.md ./tasks/TEMPLATE.md
COPY scripts ./scripts
COPY tests ./tests

RUN if [ "$INSTALL_DEV" = "true" ]; then \
        pip install --no-cache-dir ".[dev]"; \
    else \
        pip install --no-cache-dir .; \
    fi

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
