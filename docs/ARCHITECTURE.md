# Architecture

## Current goal

Build a small but production-minded Telegram ingestion pipeline that converts user inputs into structured Markdown artifacts.

The system should be developed incrementally. Each task should introduce one clear responsibility and keep the repository runnable.

## Runtime architecture

The planned MVP uses one codebase with two runtime processes:

```text
Telegram
   |
   v
App process
- FastAPI
- aiogram
- input validation
- persistence
- enqueue processing task
   |
   +------> PostgreSQL
   |
   +------> Redis
               |
               v
          Worker process
          - extraction
          - AI processing
          - Markdown rendering
          - Git writing
               |
               v
        knowledge-base/
```

## Components

### App process

Responsibilities:

* expose health endpoints;
* receive Telegram updates;
* validate and normalize incoming messages;
* persist raw message metadata;
* create background processing jobs;
* return a fast acknowledgement to the user.

The app process must not perform slow AI or media-processing work directly.

### Worker process

Responsibilities:

* load persisted messages;
* download or extract input content;
* call transcription, vision, or text AI services;
* validate structured outputs;
* render deterministic Markdown;
* write artifacts to the knowledge repository;
* update processing status.

The worker will be introduced after text ingestion is working.

### PostgreSQL

PostgreSQL stores operational state:

* users;
* Telegram messages;
* processing tasks;
* artifacts;
* processing events.

Markdown files, not PostgreSQL rows, are the human-readable knowledge artifacts.

### Redis

Redis will later provide:

* task queue broker;
* temporary locks;
* rate limiting;
* short-lived processing state.

Redis is not needed for the persistence foundation task.

### Knowledge repository

Generated knowledge artifacts are stored under:

```text
knowledge-base/
  inbox/
  notes/
  sources/
  ideas/
  drafts/
  assets/
```

Markdown files should use YAML frontmatter and deterministic filenames.

Git commits will be introduced after deterministic Markdown generation is working.

## Deployment model

The MVP uses Docker Compose.

Planned services:

```text
app
worker
postgres
redis
```

During early milestones, only the services required by the current task should be enabled.

## Design principles

1. Build vertical slices incrementally.
2. Keep one codebase.
3. Avoid microservices.
4. Persist operational state before introducing asynchronous processing.
5. Keep AI outputs structured.
6. Render Markdown deterministically in code.
7. Make failure states visible.
8. Prefer small, reviewable commits.

## Planned implementation stages

### Stage 0: Bootstrap

* FastAPI application;
* health endpoint;
* Docker development environment;
* pytest setup.

### Stage 1: Persistence foundation

* PostgreSQL;
* SQLAlchemy;
* Alembic;
* initial database models;
* database connectivity checks.

### Stage 2: Telegram text ingestion

* aiogram;
* Telegram update handling;
* user and message persistence;
* duplicate update protection.

### Stage 3: Background Markdown processing

* Redis;
* Dramatiq;
* processing tasks;
* raw Markdown rendering;
* artifact persistence.

### Stage 4: AI note generation

* structured AI output;
* schema validation;
* deterministic Markdown rendering;
* fallback behavior.

### Stage 5: Multi-modal inputs

* links;
* voice;
* images;
* later PDFs and files.

## Postponed architecture

Do not introduce yet:

* LangChain;
* LangGraph;
* vector databases;
* RAG;
* microservices;
* Kubernetes;
* web UI;
* multi-user permissions;
* GitHub synchronization;
* autonomous multi-agent behavior.
