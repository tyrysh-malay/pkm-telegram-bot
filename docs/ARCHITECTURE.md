# Architecture

## Current runtime

The repository remains one Python codebase with two runtime processes and two
infrastructure services:

```text
Telegram long polling (optional)
        |
        v
private chat + configured sender-ID gate
        |
        v
FastAPI + aiogram app
        |
        +-- atomic Message + ProcessingTask --> PostgreSQL
        |
        +-- dispatcher: ProcessingTask UUID --> Redis
                                               |
                                               v
                                      Dramatiq worker
                                               |
                          PostgreSQL claim/lease/attempt
                                               |
                                               v
                                  process_text_message(...)
                                               |
                         Artifact + Message done + Markdown
                                               |
                              ProcessingTask finalization
```

PostgreSQL is the durable orchestration authority. Redis carries actor
messages only; it stores no result or authoritative task state. Delivery is at
least once, and duplicate delivery is expected.

## Artifact-processing boundary

The worker and the supported manual CLI both reuse the Task 006 boundary:

```text
worker or developer CLI
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

The worker calls this function with a fresh session after committing its task
claim. The function remains responsible for its own transaction, Message lock,
filesystem reconciliation, Artifact row, and `Message.status = "done"`.

PostgreSQL and the filesystem do not share a transaction. Recovery is by
deterministic reconciliation: an exact file without a row is retained and can
be attached to a new row on the next explicit invocation; a valid row with a
missing file can recreate it. Conflicting files and inconsistent rows fail
without replacement or silent repair.

## Manual Git-publication boundary

Task 011 adds a separate developer-invoked stage:

```text
existing valid Artifact + exact established file
    |
    v
manual Git publisher
    |
    +--> one local selected-path commit
    +--> Artifact.git_commit_sha
```

The publisher locks the Artifact row and takes one repository-wide filesystem
lock while validating Git state, committing, and finalizing PostgreSQL. It
reuses Task 006 rendering and metadata rules only to validate the existing
Artifact and bytes; it never creates or repairs a note and is not called by the
app dispatcher or worker.

Git and PostgreSQL do not share a transaction. A commit that survives a failed
database update remains valid local history and is reconciled on the next
manual invocation through stable Artifact-ID and path trailers. No Git remote
operation is part of this boundary.

## Components

### App process

Current responsibilities:

* expose liveness and database-readiness endpoints;
* run optional single-process Telegram long polling;
* reject non-private, missing-sender, and non-allowlisted Telegram messages
  before any handler response or persistence;
* atomically persist Telegram text Messages and pending ProcessingTasks;
* run one optional dispatcher loop independently of Telegram polling;
* recover expired queued and running leases and publish due task UUIDs.

The handler does not contact Redis. Telegram acknowledgement means durable
PostgreSQL capture, not processing success. Redis failure does not prevent app
startup, ingestion, `/health`, or database-only `/ready`.

The authorization gate belongs to the app process at the aiogram message
routing boundary. It compares `message.from_user.id` with the immutable
startup configuration and requires Telegram chat type `private`; it performs
no Telegram, PostgreSQL, or Redis lookup. Existing durable ProcessingTasks are
not reauthorized, so this trust boundary changes neither worker behavior nor
the two-process runtime topology.

### PostgreSQL

PostgreSQL stores users, messages, ProcessingTasks, and Artifact metadata.
ProcessingTask owns pending, queued, running, retrying, succeeded, and failed
state, attempts, availability, leases, and errors. Conditional updates and row
locking prevent stale dispatchers and workers from overwriting newer state.

### Knowledge base

`KNOWLEDGE_BASE_PATH` defaults to `knowledge-base`. Current notes use only:

```text
knowledge-base/
  inbox/
```

Compose bind-mounts this directory from the host. File publication uses a fully
written same-directory temporary file and a hard-link no-replace operation.
Manual Git publication additionally requires this exact directory to be an
initialized non-bare Git top-level with an attached branch and repository-local
author identity. Git commits are not automated.

### Worker and Redis

One Dramatiq worker process with one thread receives only a canonical
ProcessingTask UUID. It claims the row in PostgreSQL, commits a running lease,
calls the unchanged idempotent Task 006 function with a fresh session, and
conditionally finalizes the claimed attempt. Dramatiq automatic retries and a
Redis result backend are disabled.

Queued leases recover broker loss by returning work to pending. Expired running
leases become retrying with fixed backoff or failed at the attempt limit. A
crash after artifact commit is safe because the later attempt reconciles the
same deterministic Artifact and file.

## Design principles

1. Persist input before downstream processing.
2. Keep one codebase and add runtime processes only when needed.
3. Render durable Markdown bytes deterministically in application code.
4. Make cross-resource recovery explicit rather than pretending PostgreSQL and
   the filesystem are one transaction.
5. Keep Redis as replaceable delivery transport and PostgreSQL as task truth.

## Postponed architecture

Not implemented:

* AI generation;
* voice, image, link, file, or PDF processing;
* automatic Git commits or remote synchronization;
* LangChain, LangGraph, vector databases, RAG, microservices, or Kubernetes.
