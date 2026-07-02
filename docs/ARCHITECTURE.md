# Architecture

## Current runtime

The repository is one Python codebase. The current Docker Compose runtime has
an application process and PostgreSQL:

```text
Telegram long polling (optional)
        |
        v
FastAPI + aiogram app
        |
        v
PostgreSQL users and messages
```

The application exposes `/health` and `/ready`. When enabled, aiogram persists
Telegram text input before acknowledging it. No queue or background worker is
running.

## Manual artifact-processing boundary

Task 006 adds an independently invoked processing path:

```text
developer CLI
    |
    v
process_text_message(...)
    |
    +--> lock one persisted text Message
    +--> render deterministic format-version-1 Markdown
    +--> publish knowledge-base/inbox/... without overwrite
    +--> insert or validate one Artifact row
    +--> set Message status to done
```

The command runs in the application environment but does not start FastAPI,
Telegram polling, or a worker. A future worker may reuse the processing
function; Task 006 does not select or enqueue messages automatically.

PostgreSQL and the filesystem do not share a transaction. Recovery is by
deterministic reconciliation: an exact file without a row is retained and can
be attached to a new row on the next explicit invocation; a valid row with a
missing file can recreate it. Conflicting files and inconsistent rows fail
without replacement or silent repair.

## Components

### App process

Current responsibilities:

* expose liveness and database-readiness endpoints;
* run optional single-process Telegram long polling;
* validate and persist Telegram text messages;
* provide the manual one-message artifact CLI and reusable processing code.

Telegram acknowledgement remains persistence-only. The Telegram handler does
not invoke artifact processing.

### PostgreSQL

PostgreSQL stores users, messages, and Artifact metadata. Row locking and
uniqueness constraints serialize and protect same-message note processing.
Markdown files remain the readable knowledge output.

### Knowledge base

`KNOWLEDGE_BASE_PATH` defaults to `knowledge-base`. Current notes use only:

```text
knowledge-base/
  inbox/
```

Compose bind-mounts this directory from the host. Publication uses a fully
written same-directory temporary file and a hard-link no-replace operation.
Git commits are not automated.

### Worker and Redis

A separate Dramatiq worker and Redis broker remain planned architecture, not
implemented behavior. Their future task must define queue semantics, retries,
crash recovery, and status transitions without changing the deterministic
processing contract accidentally.

## Design principles

1. Persist input before downstream processing.
2. Keep one codebase and add runtime processes only when needed.
3. Render durable Markdown bytes deterministically in application code.
4. Make cross-resource recovery explicit rather than pretending PostgreSQL and
   the filesystem are one transaction.
5. Keep AI, multimodal processing, Git writing, and queue orchestration outside
   the current manual slice.

## Postponed architecture

Not implemented:

* automatic message processing;
* Redis or Dramatiq;
* an active worker process;
* AI generation;
* voice, image, link, file, or PDF processing;
* Git commits or synchronization;
* LangChain, LangGraph, vector databases, RAG, microservices, or Kubernetes.
