# Task 007: Add durable background processing for Telegram text messages

**Status:** completed
**Depends on:** Tasks 000–006  
**Target file:** `tasks/007-durable-background-processing.md`  
**Expected commit boundary:** one reviewable implementation commit containing the minimal ProcessingTask persistence, Telegram-ingestion integration, app-process dispatcher, Dramatiq actor, Redis and worker runtime configuration, tests, migration, and verified documentation changes required by this task; the accepted task specification must be committed before implementation, and Codex must not commit implementation changes unless explicitly instructed

## Goal

Implement automatic, durable background processing for newly ingested Telegram text messages:

```text
Telegram text
→ Message + ProcessingTask committed atomically
→ dispatcher publishes processing_task_id to Redis
→ Dramatiq worker reloads PostgreSQL state
→ existing process_text_message(...)
→ ProcessingTask succeeded
```

The task must establish at-least-once delivery with PostgreSQL as the durable orchestration authority. Redis is a delivery transport, not the source of task state.

Task 007 must reuse the Task 006 processing function unchanged. It must not duplicate or move deterministic rendering, filesystem publication, Artifact reconciliation, source-message locking, or the logic that establishes `Message.status = "done"`.

## Confirmed current boundary

The user has confirmed the following architectural starting boundary:

* Tasks 000–006 are complete.
* The repository contains one reusable Task 006 processing boundary equivalent to:

  ```text
  persisted text Message
  → process_text_message(...)
  → deterministic Markdown note
  → Artifact row
  → Message status done
  ```

* Task 006 processing is manually invocable for one existing Message UUID.
* Task 006 owns:

  * deterministic Markdown rendering;
  * deterministic note paths;
  * safe atomic no-overwrite file publication;
  * Artifact-row reconciliation;
  * source-Message row locking;
  * idempotent recovery across PostgreSQL and the filesystem;
  * the successful transition of `Message.status` to `done`.

* Telegram text ingestion currently persists and acknowledges messages without automatic processing.
* The Telegram acknowledgement remains exactly:

  ```text
  Saved for processing.
  ```

* The accepted runtime target is one repository with:

  ```text
  app:
  FastAPI + aiogram + task dispatcher

  worker:
  Dramatiq worker

  infrastructure:
  PostgreSQL
  Redis
  local Markdown knowledge base
  ```

* `ProcessingTask` is the new orchestration-state owner.
* `Message.status` remains limited by application behavior to the ingestion/processing meanings `received` and `done`; Task 007 must not use it as a queue-state field.
* Existing messages created before Task 007 are not automatically backfilled. They remain manually processable through the Task 006 CLI.
* Redis, Dramatiq, a worker process, a dispatcher loop, and automatic Telegram-triggered artifact processing remain unimplemented unless newer live-repository evidence proves otherwise.
* Completion reports, context reports, committed-contract copies, and review bundles must use a user-owned repository-external directory such as `~/pkm-handoffs/`. Do not use `/tmp`.

Uploaded documents are point-in-time snapshots. Codex must verify every repository-specific fact against the live repository before editing.

## Repository verification requirements

Before editing, Codex must inspect the live repository and report the results.

### Fresh repository context and Git state

Create the repository-external handoff directory and generate a fresh context report:

```bash
mkdir -p "$HOME/pkm-handoffs"
python3 scripts/project_context.py \
  > "$HOME/pkm-handoffs/task007-context.md"
```

Then inspect and report:

```bash
git branch --show-current
git rev-parse HEAD
git status --short
git log --oneline --decorate -10
git diff --stat
git diff --check
```

Verify:

* Task 006 implementation and review corrections are committed;
* the working tree is clean before Task 007 implementation;
* Tasks 000–006 are marked consistently with repository conventions;
* no Task 007 file or later conflicting task already exists;
* the proposed target path `tasks/007-durable-background-processing.md` is the next repository-consistent task filename;
* the accepted Task 007 specification is committed at `HEAD` before implementation begins;
* no later architecture or decision entry contradicts this task.

After the task specification is committed, capture the committed contract outside the repository:

```bash
git show HEAD:tasks/007-durable-background-processing.md \
  > "$HOME/pkm-handoffs/task007-contract-from-head.md"
```

If the live repository uses a different Task 007 filename, Codex must report the contradiction before editing and must not silently rename or rewrite this specification.

### Persistence and migration structure

Inspect:

* current Alembic heads and revision files;
* `app/db/base.py`;
* `app/db/models.py` and any model modules;
* `app/db/session.py`;
* UUID, timestamp, foreign-key, relationship, index, and constraint conventions;
* whether model sessions use `expire_on_commit=False`;
* existing transaction patterns;
* test-database bootstrap and cleanup order;
* every fixture or verification script that deletes `Artifact`, `Message`, or `User` rows.

Determine and report:

* the current Alembic head;
* the next available migration revision and filename;
* whether `Message.status` remains unrestricted text at database level;
* whether an existing task-related model, table, status helper, or migration already exists;
* the exact foreign-key and relationship conventions that the new `ProcessingTask` model must follow.

Do not invent a migration revision identifier. Use the next live-confirmed revision.

### Telegram ingestion boundary

Inspect the complete current Telegram ingestion path, including:

* aiogram handlers;
* ingestion input structures;
* user create/update logic;
* Message insertion;
* duplicate-key handling and race recovery;
* session and transaction ownership;
* acknowledgement timing;
* logging;
* ingestion tests.

Confirm:

* where the transaction begins and commits;
* whether the success acknowledgement is sent only after commit;
* how a newly inserted Message is distinguished from a duplicate delivery;
* how duplicate conflicts leave the session usable;
* how to add a `ProcessingTask` only for the transaction that creates a new Message;
* that no Redis or Dramatiq call currently occurs in the handler or ingestion transaction.

### Task 006 processing boundary

Inspect the live Task 006 implementation and tests, including:

* the exact `process_text_message(...)` import path and signature;
* its session ownership and fresh-session requirement;
* commit and rollback behavior;
* return type;
* exception hierarchy and the semantic meaning of each expected exception;
* Task 006 idempotency and cross-resource recovery tests;
* the normal settings path for `KNOWLEDGE_BASE_PATH`;
* the current CLI and manual-processing behavior.

Codex must identify the exact permanent deterministic exceptions and the exact operational exceptions that can be retried.

The Task 006 processing function, renderer, storage contract, reconciliation behavior, and successful `Message.status = "done"` behavior are fixed dependencies of Task 007. They must remain unchanged.

### Application lifecycle and settings

Inspect:

* `app/main.py` and application lifespan handling;
* Telegram polling startup and shutdown;
* how background asyncio tasks are stored, cancelled, and awaited;
* settings validation and `.env.example` conventions;
* `/health` and `/ready` implementations;
* logging conventions;
* how tests construct application settings and run lifespan tests.

Confirm how to add one dispatcher task that is independent of `TELEGRAM_BOT_ENABLED` and cannot block application startup when Redis is unavailable.

### Dependencies, Dramatiq, Redis, and Docker Compose

Inspect:

* `pyproject.toml` and the repository’s dependency/lock-file conventions;
* `Dockerfile`;
* `docker-compose.yml` or the actual Compose filename;
* existing app service environment, command, health checks, volumes, and working directory;
* the existing knowledge-base bind mount;
* whether the same application image can run the worker;
* current Compose dependency and restart conventions;
* whether any Redis or Dramatiq dependency is already present.

Determine:

* the smallest normal dependency change required for Dramatiq with its Redis broker;
* the worker actor-module import path;
* the exact worker command supported by the installed Dramatiq version;
* how Compose will enforce one worker process and one worker thread;
* how the app and worker receive `DATABASE_URL`, `REDIS_URL`, and `KNOWLEDGE_BASE_PATH`;
* how the worker receives the same host-visible knowledge-base bind mount;
* how Redis health can be represented without making app startup, `/health`, or `/ready` depend on Redis.

### Tests and documentation

Inspect:

* `tests/conftest.py`;
* database, migration, Telegram ingestion, application-lifespan, Task 006 processing, and Docker/Compose-related tests;
* async and concurrent PostgreSQL test conventions;
* current fake/mock conventions;
* whether Dramatiq provides an already-installed stub broker or whether a narrow project fake is clearer;
* `AGENTS.md`;
* `docs/WORKFLOW.md`;
* `tasks/TEMPLATE.md`;
* `docs/CURRENT_STATE.md`;
* `docs/DECISIONS.md`;
* `docs/ARCHITECTURE.md`;
* `docs/DATA_MODEL.md`;
* `docs/TELEGRAM_INGESTION.md`;
* `docs/MARKDOWN_ARTIFACTS.md`;
* `docs/PROJECT_BRIEF.md` at its repository-confirmed path;
* `README.md`;
* `.env.example`.

Verify the next available durable decision number. The number must not be assumed from uploaded snapshots.

Any material contradiction must be reported before implementation. It must not be concealed by rewriting this task after the implementation exists.

## Problem or motivation

Task 006 proves deterministic, idempotent note generation for one explicitly selected persisted text message. It intentionally stops before orchestration.

Without Task 007:

* newly ingested Telegram messages remain in `received` until a developer runs the CLI;
* there is no durable record that processing is pending, queued, running, retrying, exhausted, or complete;
* Redis delivery loss cannot be recovered from PostgreSQL state;
* a worker crash cannot be distinguished from an active attempt;
* broker failures would either block ingestion or silently lose work if the handler published directly;
* future AI or multimodal processing would lack a proven durable task lifecycle.

The smallest next vertical slice is to add one durable `generate_note` task per newly inserted Telegram text message and execute the existing Task 006 function through a PostgreSQL-backed dispatcher/worker lifecycle.

## Scope

Implement the following bounded outcome:

1. add a minimal `ProcessingTask` SQLAlchemy model and one Alembic migration;
2. create one `generate_note` task atomically with each newly inserted Telegram text Message;
3. preserve duplicate Telegram idempotency with exactly one Message and one ProcessingTask;
4. add a small dispatcher loop to the existing app process;
5. recover expired queued and running leases from PostgreSQL;
6. publish only a ProcessingTask UUID to one Dramatiq actor;
7. add one Dramatiq worker process using one process and one thread;
8. claim tasks through PostgreSQL row locking and attempt-number ownership;
9. invoke the existing Task 006 `process_text_message(...)` function with a fresh SQLAlchemy session;
10. finalize orchestration state conditionally on the claimed attempt number;
11. implement bounded PostgreSQL-owned retries and fixed backoff;
12. add Redis and the worker service to Docker Compose;
13. add the minimal settings and dependency changes;
14. add focused, integration, migration, lifecycle, and regression tests;
15. perform and clean up one end-to-end Compose smoke message;
16. update documentation and add one durable decision only after behavior is verified;
17. produce the completion report and review bundle outside the repository under `~/pkm-handoffs/` or another user-owned repository-external directory.

## Out of scope

Do not add:

* changes to the Task 006 renderer;
* changes to Task 006 title, slug, timestamp, frontmatter, path, or file-byte contracts;
* changes to Task 006 filesystem publication or Artifact reconciliation;
* changes to Task 006 source-Message locking;
* a second implementation of `Message.status = "done"`;
* AI calls, summaries, tags, or topics;
* voice, image, link, document, file, or PDF processing;
* Git staging, commits, pushes, or synchronization for generated artifacts;
* worker-to-Telegram completion or failure notifications;
* a changed Telegram acknowledgement;
* `ProcessingEvent`;
* a separate dispatcher service or process;
* an outbox table separate from `ProcessingTask`;
* automatic task backfill for existing Messages;
* a backfill command;
* a failed-task retry CLI;
* an administration API or web UI;
* task cancellation;
* task priorities;
* multiple task types beyond `generate_note`;
* multiple queues;
* rate limiting;
* user-visible scheduling;
* Redis result storage;
* Redis as the source of task truth;
* more than one worker process or thread;
* multiple app replicas;
* running-lease heartbeat or lease extension;
* distributed locks;
* a generic repository layer;
* a generic service framework;
* a generic scheduler framework;
* a generic unit-of-work abstraction;
* a generic event bus;
* Celery, RQ, APScheduler, LangChain, LangGraph, or another orchestration framework;
* unrelated Telegram, database, Docker, or documentation refactoring.

## Affected components

### Database and models

Expected changes:

* add `ProcessingTask` to the repository’s existing model structure;
* add one migration after the live Task 006 head;
* add the minimal Message relationship only when consistent with current model conventions;
* update test cleanup to delete ProcessingTask rows before their source Messages.

### Telegram ingestion

Expected changes:

* create a `generate_note` ProcessingTask only when a new Message is inserted;
* keep User, Message, and ProcessingTask changes in one PostgreSQL transaction;
* preserve the current duplicate-delivery behavior and acknowledgement text.

The Telegram handler must not publish to Redis or invoke Task 006 processing.

### App process

Expected changes:

* configure a Dramatiq Redis broker for publication;
* start one optional dispatcher asyncio loop during FastAPI lifespan;
* stop it cleanly during shutdown;
* keep dispatcher enablement independent of Telegram polling.

The app remains the FastAPI, aiogram, and dispatcher process. Do not add a separate dispatcher service.

### Worker process

Expected changes:

* add one generic Dramatiq actor with one argument: ProcessingTask UUID;
* use PostgreSQL to claim, lease, retry, and finalize work;
* invoke the existing Task 006 function with a fresh session;
* disable Dramatiq-managed automatic retries.

### Redis

Expected changes:

* add one Redis broker service to Compose;
* use Redis only for message delivery;
* add no result backend and no task-state authority in Redis.

Redis persistence is not required for correctness because PostgreSQL task rows and lease recovery must republish lost work.

### Knowledge base

The worker must use the existing `KNOWLEDGE_BASE_PATH` and the same host-visible bind mount as the app.

Task 006 knowledge modules are consumers, not implementation targets. The live equivalents of the following should remain behaviorally unchanged:

```text
app/knowledge/markdown.py
app/knowledge/storage.py
app/knowledge/processing.py
```

### Dependencies and configuration

Expected changes:

* add Dramatiq and Redis-broker support using repository dependency conventions;
* add `REDIS_URL`;
* add `TASK_DISPATCHER_ENABLED` unless live settings conventions establish a clearer equivalent;
* configure Compose app, worker, and Redis services.

No new secret-bearing configuration is required for the local Redis service.

### Tests

Expected additions or changes:

* ProcessingTask model and migration tests;
* Telegram ingestion transaction/idempotency tests;
* dispatcher tests;
* worker claim/finalization tests;
* lifecycle tests with Redis unavailable;
* real-Compose smoke verification;
* Task 006 regression coverage;
* test-database cleanup and isolation checks.

### Documentation

Expected verified updates:

* `docs/ARCHITECTURE.md`;
* `docs/DATA_MODEL.md`;
* `docs/TELEGRAM_INGESTION.md`;
* `docs/CURRENT_STATE.md`;
* `docs/DECISIONS.md`;
* `README.md`;
* `.env.example`;
* this task file.

### Components expected to remain unchanged

Unless live repository evidence demonstrates a direct contradiction, do not modify:

* Task 006 deterministic Markdown rules;
* `docs/MARKDOWN_ARTIFACTS.md`;
* the Task 006 manual CLI contract;
* `/health` response semantics;
* `/ready` database-only semantics;
* `docs/PROJECT_BRIEF.md`;
* `docs/WORKFLOW.md`;
* `AGENTS.md`;
* Task 004/005 workflow tooling;
* user allowlisting or webhook behavior.

## Data, state, migration, and configuration impact

## ProcessingTask model

Add one `ProcessingTask` table and ORM model with exactly these business fields:

```text
id
message_id
task_type
status
attempts
max_attempts
available_at
lease_expires_at
last_error
created_at
updated_at
```

Required meanings and initial values:

```text
task_type       = "generate_note"
status          = "pending"
attempts        = 0
max_attempts    = 3
available_at    = creation time
lease_expires_at = null
last_error      = null
```

Required constraint:

```text
UNIQUE(message_id, task_type)
```

Required field semantics:

* `id` is a UUID primary key following live model conventions.
* `message_id` is a non-null foreign key to `messages.id`.
* `task_type` is non-null text.
* `status` is non-null text.
* `attempts` is a non-null integer.
* `max_attempts` is a non-null integer.
* `available_at` is a non-null timezone-aware timestamp.
* `lease_expires_at` is a nullable timezone-aware timestamp.
* `last_error` is nullable text.
* `created_at` and `updated_at` follow existing timezone-aware audit conventions.
* No cascade delete is added unless that is already the strict repository convention for dependent operational rows.
* No database enum is introduced.
* No `ProcessingEvent`, payload JSON, priority, result, queue name, actor name, artifact ID, or traceback column is added.

Add non-unique indexes supporting the actual dispatcher queries:

```text
(status, available_at)
(status, lease_expires_at)
```

Use repository-confirmed naming conventions for constraints and indexes.

The database does not need a status check constraint in this task. Application code and tests own the state-machine contract. Codex must not add extra task states.

## ProcessingTask statuses

The complete status set is:

```text
pending
queued
running
retrying
succeeded
failed
```

State ownership:

```text
ProcessingTask.status = orchestration state
Message.status        = received or done
```

Required invariants:

* `pending` is due when `available_at <= now`; it has no active lease.
* `queued` means publication succeeded and a queue-delivery lease exists.
* `running` means a worker claimed an attempt and a worker lease exists.
* `retrying` is due only when `available_at <= now`; it has no active lease.
* `succeeded` and `failed` are terminal and have no lease.
* `attempts` counts worker claims, not dispatcher publications.
* Broker failures and queued-lease expiry do not increment `attempts`.
* One worker claim increments `attempts` exactly once.
* `attempts` must never exceed `max_attempts` through normal application behavior.
* `max_attempts = 3` means at most three calls to `process_text_message(...)` for the task.
* A permanent Task 006 contract failure may become `failed` before attempts are exhausted.
* A terminal task is never made dispatchable automatically.
* Every successful state transition updates `updated_at` through the repository's normal timestamp convention.

## Migration requirements

Add the next live-confirmed Alembic revision after Task 006.

Upgrade must:

1. create the `processing_tasks` table;
2. create its primary key;
3. create the Message foreign key;
4. create `UNIQUE(message_id, task_type)`;
5. create the two dispatcher-supporting indexes;
6. create no task rows for existing Messages;
7. preserve all existing Users, Messages, Artifacts, and Markdown files;
8. leave all existing Message statuses unchanged.

Downgrade must:

1. drop only the ProcessingTask indexes, constraints, and table introduced by this migration;
2. preserve Users, Messages, Artifacts, and generated Markdown files;
3. not change `Message.status`;
4. not delete or alter Artifact rows;
5. permit a subsequent upgrade to recreate the empty table.

Migration upgrade/downgrade verification must use the isolated test database.

## Configuration

Add:

```text
REDIS_URL
TASK_DISPATCHER_ENABLED
```

Preferred safe defaults, subject to live settings conventions:

```text
REDIS_URL=redis://redis:6379/0
TASK_DISPATCHER_ENABLED=false
```

Requirements:

* `REDIS_URL` uses the existing settings mechanism.
* Reading or validating settings must not connect to Redis.
* `TASK_DISPATCHER_ENABLED` is independent of `TELEGRAM_BOT_ENABLED`.
* The Python settings default keeps the dispatcher disabled unless explicitly enabled.
* Docker Compose enables the dispatcher for the app service.
* Automated tests can leave it disabled unless a lifecycle test explicitly enables it.
* The worker uses the same `REDIS_URL`, `DATABASE_URL`, and `KNOWLEDGE_BASE_PATH` settings.
* Do not add environment variables for poll interval, batch size, leases, retry backoff, error length, or queue name in this task.

Use small named code constants for the first version:

```text
dispatch poll interval:        1 second
dispatch batch size:           25 tasks
broker failure retry delay:    5 seconds
queued lease duration:         30 seconds
running lease duration:        300 seconds
processing retry backoff:      5 seconds
maximum stored error length:   500 characters
```

Tests may replace these constants or inject a clock through a narrow test seam. Do not build a general scheduler or configuration framework.

## Behavioral requirements

## Telegram ingestion transaction

For each ordinary Telegram text message that is newly inserted:

1. create or update the Telegram User according to existing behavior;
2. insert the Message with `status = "received"`;
3. insert one ProcessingTask with:

   ```text
   message_id      = new Message.id
   task_type       = "generate_note"
   status          = "pending"
   attempts        = 0
   max_attempts    = 3
   available_at    = current transaction time
   lease_expires_at = null
   last_error      = null
   ```

4. commit User, Message, and ProcessingTask in one PostgreSQL transaction;
5. send `Saved for processing.` only after that transaction commits.

Required behavior:

* a ProcessingTask insert failure rolls back the new Message and does not produce a success acknowledgement;
* no partially committed Message without its required Task is allowed for a newly accepted Task 007 message;
* the Telegram handler and ingestion transaction must not contact Redis;
* the handler must not call a Dramatiq actor;
* the handler must not call `process_text_message(...)`;
* Redis unavailability must not prevent persistence or acknowledgement;
* Telegram acknowledgement continues to mean that durable PostgreSQL capture succeeded, not that artifact processing completed.

## Duplicate Telegram delivery

The database uniqueness constraint on Message idempotency remains authoritative.

Required results when the same Telegram message is delivered repeatedly after Task 007 is active:

```text
exactly one User identity
exactly one Message
exactly one generate_note ProcessingTask
```

Requirements:

* duplicate handling must not create a second task;
* the `UNIQUE(message_id, task_type)` constraint is the final task-level duplicate protection;
* expected duplicate conflicts must leave the session usable;
* unrelated database failures must not be mistaken for duplicates;
* acknowledgement behavior remains consistent with the existing duplicate-delivery contract.

Only the transaction that successfully inserts a new Message creates its ProcessingTask.

If a duplicate Telegram update refers to a Message that already existed before Task 007 and has no ProcessingTask, the duplicate path must not synthesize a task. That would be an implicit backfill and is out of scope.

## Dispatcher lifecycle

Run one small dispatcher loop inside the existing app process.

Startup requirements:

* dispatcher startup is controlled only by `TASK_DISPATCHER_ENABLED` or the repository-confirmed equivalent;
* it is independent of Telegram polling enablement;
* when disabled, no dispatcher task and no Redis connection attempt is started;
* when enabled, FastAPI startup must complete even if Redis is unavailable;
* store one dispatcher task reference and do not start duplicate loops within one app process.

Shutdown requirements:

* request dispatcher cancellation;
* await it safely;
* close any app-owned broker/client resource according to library conventions;
* do not delay shutdown indefinitely when Redis is unavailable.

The dispatcher must log startup, shutdown, recoveries, publication failures, and unexpected loop failures with task identifiers where applicable. It must not log raw Telegram text, database URLs, Redis credentials, or bot tokens.

## Dispatcher loop

Each dispatcher iteration must:

1. recover expired leases in one bounded PostgreSQL transaction;
2. select a deterministic bounded batch of due `pending` and `retrying` task IDs;
3. release the database transaction before contacting Redis;
4. publish each ProcessingTask UUID as the actor’s only payload;
5. after successful publication, conditionally update that task to `queued` and establish a queued lease;
6. sleep for the normal interval or the broker-failure delay.

Due-task selection:

```text
status in (pending, retrying)
available_at <= now
attempts < max_attempts
```

Order candidates deterministically by:

```text
available_at
created_at
id
```

Do not hold a database row lock or open transaction across a Redis network call.

## Publish and queued-state race

The required publication ordering is:

```text
publish actor message
then conditionally record queued
```

A successful publication must be followed by a conditional update equivalent to:

```text
WHERE id = :processing_task_id
  AND status = :previous_status
  AND attempts = :observed_attempts
  AND available_at <= :dispatch_observation_time
```

On a successful conditional update:

```text
status = queued
lease_expires_at = now + 30 seconds
```

The exact predicate may include stronger repository-safe guards, but it must not overwrite a task already claimed or finalized by a fast worker.

Required race behavior:

* a worker may receive and claim the actor message before the dispatcher records `queued`;
* therefore the worker must be able to claim a due `pending` or `retrying` row;
* when the fast worker has already changed the row, the dispatcher update affects zero rows and must leave the worker-owned state unchanged;
* zero affected rows after successful publication is an accepted race outcome, not a reason to force `queued`;
* a process crash after publication but before the conditional update may cause duplicate publication later;
* duplicate publication is acceptable because delivery is at least once.

## Broker publication failure

When actor publication fails:

* do not change the ProcessingTask row;
* leave it in due `pending` or `retrying` state;
* do not establish a lease;
* do not increment `attempts`;
* do not write the broker exception into `last_error`;
* log a concise sanitized failure;
* wait the fixed broker-failure delay before retrying the loop;
* keep the app process, Telegram polling, `/health`, and `/ready` operational.

## Expired lease recovery

Before dispatching new work, recover expired leases using PostgreSQL time or one consistently timezone-aware application time boundary.

### Expired queued lease

```text
status = queued
lease_expires_at <= now
```

Transition:

```text
queued → pending
attempts unchanged
available_at = now
lease_expires_at = null
last_error unchanged
```

This recovers publication that never produced a durable worker claim, including Redis loss or worker unavailability.

### Expired running lease with attempts remaining

```text
status = running
lease_expires_at <= now
attempts < max_attempts
```

Transition:

```text
running → retrying
attempts unchanged
available_at = now + 5 seconds
lease_expires_at = null
last_error = concise fixed worker-lease-expired message
```

### Expired running lease with no attempts remaining

```text
status = running
lease_expires_at <= now
attempts >= max_attempts
```

Transition:

```text
running → failed
attempts unchanged
lease_expires_at = null
last_error = concise fixed maximum-attempts/worker-lease-expired message
```

Recovery updates must be conditional on the row still being in the expired state so they cannot overwrite a concurrent worker finalization.

## Dramatiq actor and payload

Add one generic actor for this task boundary.

The actor payload is exactly one canonical ProcessingTask UUID, represented in the safest encoder-compatible form supported by the installed Dramatiq version. A canonical UUID string is preferred.

Do not include:

* Message contents;
* Message UUID as a separate payload;
* Artifact fields;
* attempt number;
* database URL;
* knowledge-base path;
* serialized ORM objects;
* result-backend metadata.

Disable Dramatiq-managed retries for this actor using the installed version’s supported actor option, expected to be equivalent to:

```text
max_retries = 0
```

PostgreSQL is the only retry authority.

## Worker claim

When an actor message is received:

1. parse the ProcessingTask UUID;
2. open a fresh SQLAlchemy session;
3. reload and lock the ProcessingTask with PostgreSQL `SELECT ... FOR UPDATE` semantics;
4. decide whether the delivery is claimable;
5. for a claimable row, increment `attempts`, set `running`, establish the worker lease, and commit the claim;
6. close that transaction before running Task 006 processing.

Claimable rows:

* `queued` with `attempts < max_attempts`;
* due `pending` with `available_at <= now` and `attempts < max_attempts`;
* due `retrying` with `available_at <= now` and `attempts < max_attempts`.

A `queued` actor delivery may be claimed even when its queued lease is close to or past expiry, provided the row is still `queued` when locked. Row locking serializes the worker claim with dispatcher recovery.

Claim transition:

```text
previous status → running
attempts = attempts + 1
lease_expires_at = now + 300 seconds
last_error = null
```

The committed `attempts` value is the claimed attempt number used for finalization ownership.

Non-claim behavior:

* missing task: log concise stale delivery and return;
* `succeeded` or `failed`: return without changes;
* `running` with an active lease: treat as duplicate delivery and return;
* `running` with an expired lease: do not claim directly; leave recovery to the dispatcher and return;
* `pending` or `retrying` with future `available_at`: return;
* a nonterminal row with `attempts >= max_attempts`: conditionally mark `failed` without calling Task 006, clear the lease, store a bounded fixed error, and return;
* malformed UUID payload: fail the actor invocation clearly without reading arbitrary database state; the task row remains queued and is later recovered by queued-lease expiry;
* unsupported `task_type`: conditionally mark the nonterminal row `failed` without incrementing attempts or invoking Task 006, clear any lease, store a bounded fixed error, and return.

Duplicate actor delivery must not create two simultaneous attempts for the same ProcessingTask.

## Task 006 invocation

After the claim transaction commits:

1. open a new fresh SQLAlchemy session;
2. call the existing `process_text_message(...)` using:

   * the claimed task’s `message_id`;
   * the normal configured `KNOWLEDGE_BASE_PATH`;
   * no caller-owned active transaction;

3. allow Task 006 to own its own transaction, Message lock, Artifact reconciliation, file publication, commit, rollback, and `Message.status = "done"` logic;
4. close the Task 006 session before opening the orchestration-finalization transaction.

Task 007 must import and call the existing function. It must not copy its code or add an orchestration-specific alternative.

A crash after Task 006 commits but before ProcessingTask success is recorded is an expected recovery case. The running lease eventually expires, a later attempt calls Task 006 again, and Task 006 idempotency returns the same Artifact/file state before the ProcessingTask becomes `succeeded`.

## Failure classification

Codex must map the live Task 006 exception hierarchy into these two orchestration classes without changing Task 006 exceptions.

### Permanent deterministic failure

Known deterministic source or artifact-contract failures must become `failed` immediately after the claimed attempt, even when attempts remain.

This category includes the live equivalents of:

* Message not found;
* unsupported input type;
* null, NUL-containing, or otherwise invalid persisted source text;
* invalid or naive source timestamp;
* missing required persisted Telegram identifiers;
* invalid deterministic source/path data;
* inconsistent Artifact metadata;
* expected path owned by another Artifact;
* conflicting deterministic final file;
* unsupported final filesystem entry;
* another explicit Task 006 contract violation that cannot be repaired by retrying unchanged input.

### Retryable operational failure

Retryable failures include the live equivalents of:

* transient database availability, serialization, deadlock, or commit failures;
* transient filesystem I/O, permission, capacity, or publication failures;
* temporary knowledge-base availability failures;
* unexpected exceptions not classified as permanent deterministic contract failures.

Do not retry actor payload validation errors or unsupported task types as processing work.

If a live Task 006 exception has ambiguous semantics, Codex must report the mapping before editing rather than silently changing Task 006 behavior.

## Worker finalization

After Task 006 returns or raises, open a separate SQLAlchemy session and transaction.

Every final update must be conditional on:

```text
id = processing_task_id
status = running
attempts = claimed_attempt_number
```

A stronger guard may include the observed lease value, but the claimed attempt number must remain the ownership token.

### Success

When Task 006 succeeds:

```text
running → succeeded
lease_expires_at = null
last_error = null
```

Do not update Message status directly. Task 006 has already established the Message and Artifact state.

### Retryable failure with attempts remaining

When Task 006 raises a retryable failure and:

```text
claimed_attempt_number < max_attempts
```

transition:

```text
running → retrying
available_at = now + 5 seconds
lease_expires_at = null
last_error = sanitized bounded error
```

### Retryable failure with attempts exhausted

When:

```text
claimed_attempt_number >= max_attempts
```

transition:

```text
running → failed
lease_expires_at = null
last_error = sanitized bounded error
```

### Permanent deterministic failure

Transition immediately:

```text
running → failed
lease_expires_at = null
last_error = sanitized bounded error
```

### Late finalizer

If the conditional update affects zero rows:

* do not retry or force the update;
* do not overwrite a newer attempt, terminal state, or recovered state;
* log a concise stale-finalizer message containing task ID and claimed attempt number;
* return without changing orchestration state.

This rule applies to both late success and late failure.

### Finalization database failure

If the finalization transaction itself cannot commit:

* do not call Task 006 again inside the same actor invocation;
* do not use a Dramatiq retry;
* allow the actor invocation to fail/log according to Dramatiq conventions;
* leave the last committed ProcessingTask state as `running`;
* rely on running-lease expiry and dispatcher recovery.

## Error sanitization

`last_error` is operational summary text, not evidence storage.

Before storing an error:

1. use an approved stable message for known exceptions where possible;
2. include at most the exception class and concise safe message;
3. replace CR/LF and repeated whitespace with single spaces;
4. remove or avoid database URLs, Redis URLs, Telegram tokens, credentials, absolute secret paths, and raw Telegram message text;
5. truncate to at most 500 Unicode code points;
6. store no traceback.

Logging may include task ID, Message UUID, attempt number, status transition, and relative artifact path when already supplied safely by Task 006. Do not log raw message text or secrets.

## Runtime and Docker Compose

Add one Redis service and one worker service.

### Redis service

Requirements:

* use the repository’s normal official-image versioning convention;
* make Redis reachable to app and worker by Compose service name;
* add a health check when consistent with current Compose style;
* no host-published Redis port is required for acceptance;
* no Redis result backend;
* no Redis task-status store;
* no correctness dependency on Redis persistence or a Redis volume.

### App service

Requirements:

* retain its current FastAPI/aiogram command;
* receive `REDIS_URL`;
* enable the dispatcher through `TASK_DISPATCHER_ENABLED=true` in Compose;
* do not make service startup depend on Redis becoming healthy;
* continue to expose `/health` and `/ready` with their current semantics;
* continue to persist Telegram messages while Redis is down.

### Worker service

Requirements:

* use the same application image/codebase as the app service;
* run the repository-confirmed actor module;
* use an explicit Dramatiq command equivalent to:

  ```text
  dramatiq <actor-module> --processes 1 --threads 1
  ```

* receive `DATABASE_URL`, `REDIS_URL`, and `KNOWLEDGE_BASE_PATH`;
* mount the same host knowledge-base directory at the same container path;
* use one worker process and one worker thread;
* use no result backend;
* run no FastAPI server and no Telegram polling;
* not contain a separate copy of Task 006 processing code.

The worker may depend on PostgreSQL and Redis service availability according to Compose conventions. The app must not be blocked by Redis.

## Health and readiness

Do not change the user-visible meaning of existing endpoints.

* `/health` remains application-process liveness.
* `/ready` remains the current database readiness boundary.
* Redis and worker availability must not become readiness dependencies in Task 007.
* Redis failures are visible through logs and pending/retrying ProcessingTask state, not through a failing app startup or readiness endpoint.

## Delivery guarantee

The implemented guarantee is:

```text
at least once delivery
idempotent processing
PostgreSQL-owned task state and retries
Redis used only as transport
```

Duplicate actor messages, publish-before-queued races, app crashes after publish, worker crashes after claim, and worker crashes after Task 006 success are all expected cases.

Exactly-once broker delivery is not required and must not be claimed.

## Investigation requirements

Before choosing implementation details, Codex must determine:

* the exact Task 006 function and exception import paths;
* whether Task 006 returns an ORM entity or immutable result after commit;
* how to create a fresh session for each claim, processing, and finalization phase;
* whether the existing session factory is safe in the Dramatiq worker process;
* how SQLAlchemy and async code are invoked from the synchronous Dramatiq actor boundary;
* whether the actor should use one `asyncio.run(...)` per message or a smaller repository-consistent adapter;
* how the installed Dramatiq version configures `RedisBroker` and disables retries;
* whether broker configuration at import time can be done without opening a Redis connection;
* how to avoid opening Redis during tests that do not enable the dispatcher;
* how current application lifespan stores and cancels background tasks;
* how database time is currently represented and tested;
* how `updated_at` is advanced for bulk/conditional SQL updates;
* how PostgreSQL reports row counts for conditional updates;
* how duplicate Message insertion currently exposes whether the Message was newly created;
* how a duplicate pre-Task-007 Message without a task remains untouched;
* how migration tests must preserve Users, Messages, and Artifacts across downgrade;
* how the resolved Compose configuration proves exactly one worker process and thread;
* how the end-to-end smoke can use the actual ingestion persistence boundary without contacting Telegram;
* how smoke rows and the generated note can be removed safely afterward;
* whether any live environment limitation, including local Docker/VPN routing, affects verification without justifying a repository workaround.

Do not introduce a general abstraction solely to hide these findings.

## Expected failure modes and recovery behavior

### PostgreSQL failure during Telegram ingestion

Behavior:

* rollback User/Message/ProcessingTask changes from the transaction;
* send no success acknowledgement;
* create no task with a missing Message;
* preserve polling-loop error handling.

Recovery:

* Telegram may redeliver the update;
* the normal idempotent ingestion path retries durable capture.

### ProcessingTask uniqueness race

Behavior:

* exactly one `generate_note` task survives;
* expected uniqueness conflict is handled without treating unrelated integrity errors as duplicates;
* the session remains usable after rollback/recovery.

Recovery:

* return the already established Message/task outcome according to current duplicate-delivery behavior.

### Redis unavailable during ingestion

Behavior:

* no Redis call occurs in the ingestion transaction or handler;
* Message and ProcessingTask commit normally;
* acknowledgement is sent normally;
* task remains `pending` until the dispatcher can publish it.

Recovery:

* dispatcher resumes publication when Redis is available.

### Redis unavailable during app startup

Behavior:

* app process starts;
* FastAPI lifespan completes;
* optional Telegram polling can start independently;
* `/health` and `/ready` retain current behavior;
* dispatcher logs bounded failures and retries without a busy loop.

Recovery:

* no app restart is required when Redis becomes reachable unless the library proves otherwise and Codex reports that limitation before editing.

### Broker publication failure

Behavior:

* task remains due `pending` or `retrying`;
* no attempt is consumed;
* no lease is set;
* failure is logged safely.

Recovery:

* later dispatcher iteration republishes.

### Publication succeeds but queued update is lost

Behavior:

* task may remain `pending` or `retrying`;
* actor may claim it directly;
* later duplicate publication is acceptable;
* conditional queued update must not overwrite worker state.

Recovery:

* worker claim or later dispatch establishes progress.

### Published actor is lost or Redis is restarted

Behavior:

* task remains `queued` until queued lease expiry;
* attempts remain unchanged.

Recovery:

* dispatcher transitions expired `queued → pending` and republishes.

### Duplicate actor delivery

Behavior:

* terminal task is ignored;
* active `running` lease is ignored;
* row locking prevents two claims for one attempt;
* only one claim increments attempts.

Recovery:

* no special recovery is needed.

### Worker crash after claim

Behavior:

* task remains `running` with the consumed attempt and lease;
* no Dramatiq retry authority is used.

Recovery:

* expired running lease becomes `retrying` or `failed` based on attempts.

### Retryable Task 006 failure

Behavior:

* attempts remain the already claimed number;
* task becomes `retrying` with fixed backoff when attempts remain;
* task becomes `failed` when exhausted;
* Message status and Task 006 filesystem/database state follow Task 006 rollback/recovery semantics.

Recovery:

* dispatcher publishes the retry when due.

### Permanent Task 006 contract failure

Behavior:

* task becomes `failed` immediately;
* no automatic retry occurs;
* `last_error` is bounded and sanitized;
* Task 006 preserves conflicting/inconsistent resources according to its contract.

Recovery:

* manual investigation outside this task; no retry CLI or admin API is added.

### Worker crash after Task 006 commit but before task success

Behavior:

* Message may already be `done` with one Artifact and exact file;
* ProcessingTask remains `running` until lease expiry.

Recovery:

* dispatcher schedules another attempt;
* Task 006 reconciles idempotently;
* final task becomes `succeeded` with the same Artifact and exact file.

### Late worker finalization

Behavior:

* conditional update affects zero rows when a newer attempt or terminal state owns the task;
* old worker does not overwrite newer state.

Recovery:

* current state remains authoritative.

### Finalization database failure

Behavior:

* actor does not fabricate success;
* task remains at its last committed state, normally `running`;
* no Dramatiq retry is scheduled.

Recovery:

* lease expiry and PostgreSQL recovery schedule the next attempt.

### Worker cannot access knowledge-base mount

Behavior:

* Task 006 raises an operational storage failure;
* orchestration records bounded retry or failure according to attempts;
* no partial Artifact success is invented.

Recovery:

* fix mount/permissions; a due retry or recovered attempt uses Task 006 reconciliation.

### App dispatcher loop raises unexpectedly

Behavior:

* log the exception safely;
* keep the app process alive;
* continue or restart the loop through the smallest explicit lifespan boundary;
* avoid a tight failure loop.

Recovery:

* a later iteration resumes PostgreSQL recovery and publication.

## Tests

Automated tests must not contact Telegram and should not require real Redis except where explicitly testing the Compose integration boundary.

Prefer focused tests around small state-transition functions plus PostgreSQL integration for locking and conditional updates. Do not create a large fake queue framework.

Expected new test paths are equivalent to:

```text
tests/test_processing_tasks.py
tests/test_task_dispatcher.py
tests/test_task_worker.py
```

Codex may use stronger existing naming conventions but must report the selected paths before editing.

### Model and migration tests

Test:

1. exact ProcessingTask columns, nullability, types, foreign key, unique constraint, and indexes;
2. initial application-created values;
3. duplicate `(message_id, task_type)` rejection;
4. upgrade from the Task 006 head;
5. downgrade preserves User, Message, and Artifact rows;
6. re-upgrade recreates an empty ProcessingTask table;
7. no existing Message is backfilled.

### Ingestion tests

Test:

1. a newly inserted Telegram text creates one Message and one pending `generate_note` ProcessingTask in the same transaction;
2. the task uses attempts `0`, max attempts `3`, due `available_at`, null lease, and null error;
3. forced task insertion failure rolls back the new Message and suppresses acknowledgement;
4. acknowledgement is sent only after commit and remains exactly `Saved for processing.`;
5. duplicate delivery creates one Message and one ProcessingTask;
6. concurrent duplicate insertion remains correct under database uniqueness;
7. duplicate delivery of an existing pre-Task-007 Message with no task does not create a task;
8. broker publication function is never called by ingestion;
9. simulated Redis unavailability does not prevent commit or acknowledgement.

### Dispatcher tests

Test:

1. due pending task publishes only its ProcessingTask UUID;
2. successful publication conditionally marks the unchanged row queued and sets a lease;
3. retrying task with future `available_at` is not published;
4. deterministic batch ordering and batch limit;
5. publication failure leaves status, lease, and attempts unchanged;
6. publication failure waits/retries without crashing the app loop;
7. publish-before-queued race in which a fast worker changes the row to running; dispatcher conditional update affects zero rows and does not overwrite running;
8. publication success followed by no queued update remains safe for duplicate dispatch;
9. expired queued becomes pending with attempts unchanged;
10. expired running with attempts remaining becomes retrying with backoff;
11. expired running at max attempts becomes failed;
12. nonexpired queued and running leases are not recovered;
13. recovery updates do not overwrite a concurrent finalizer;
14. dispatcher start/stop is independent of Telegram polling;
15. disabled dispatcher makes no Redis connection attempt.

### Worker tests

Test:

1. queued task claim increments attempts once, sets running, and creates a lease;
2. due pending and retrying tasks can be claimed, covering the publish-before-queued race;
3. future retrying task is ignored;
4. missing task is ignored safely;
5. succeeded and failed duplicate deliveries are ignored;
6. duplicate actor delivery during an active running lease does not increment attempts again;
7. worker uses a fresh Task 006 session with no caller-owned active transaction;
8. successful Task 006 call conditionally marks the claimed attempt succeeded;
9. Task 007 does not directly update Message status;
10. permanent Task 006 error becomes failed immediately;
11. retryable error becomes retrying with fixed backoff when attempts remain;
12. third retryable claimed attempt becomes failed;
13. `last_error` is one-line, sanitized, bounded to 500 code points, and contains no raw message text or credentials;
14. Dramatiq automatic retries are disabled;
15. late success cannot overwrite a newer attempt;
16. late failure cannot overwrite a newer attempt;
17. finalization database failure leaves running state for lease recovery;
18. malformed actor UUID fails safely without arbitrary lookup;
19. unknown task type is not processed as `generate_note`;
20. one worker process/thread configuration is represented by resolved Compose configuration.

### End-to-end processing tests

Test:

1. pending task progresses through dispatcher publication and worker processing to `succeeded`;
2. source Message becomes `done` only through Task 006;
3. exactly one Artifact row exists;
4. exactly one deterministic Markdown file exists with Task 006 exact bytes;
5. crash/failure after Task 006 commit but before orchestration success recovers through another idempotent Task 006 call;
6. repeated or duplicate actor delivery preserves the same Artifact ID and file bytes;
7. existing Task 006 manual CLI remains usable for messages without ProcessingTask rows.

### Lifecycle and infrastructure tests

Test:

1. app startup succeeds with dispatcher disabled and no Redis;
2. app startup succeeds with dispatcher enabled and Redis unreachable;
3. `/health` and `/ready` do not call Redis and preserve current response semantics;
4. Telegram polling setting and dispatcher setting are independent;
5. Compose defines app, worker, PostgreSQL, and Redis;
6. worker shares database, Redis, and knowledge-base settings;
7. worker shares the host knowledge-base bind mount;
8. worker command resolves to one process and one thread;
9. app service does not have a Redis-health dependency that blocks startup;
10. no Redis result backend is configured.

### Regression and isolation tests

Test:

1. every Task 006 rendering, storage, reconciliation, concurrency, CLI, and migration test still passes unchanged;
2. Telegram `/start`, persistence, profile update, and idempotency behavior remain correct;
3. the full test suite uses the isolated test database;
4. ProcessingTask fixture rows never appear in the development database;
5. development User, Message, Artifact, and ProcessingTask counts and marker rows remain unchanged after pytest;
6. test cleanup deletes ProcessingTask before Message and preserves foreign-key correctness;
7. generated test files remain under isolated temporary knowledge-base roots and are cleaned.

## Acceptance criteria

### Schema and migration

* One ProcessingTask table exists with exactly the required business fields.
* `UNIQUE(message_id, task_type)` exists.
* Dispatcher query indexes exist.
* No ProcessingEvent, payload JSON, priority, result, or extra future fields exist.
* Migration upgrade creates no task for existing Messages.
* Isolated downgrade preserves Users, Messages, Artifacts, Message statuses, and Markdown files.
* Re-upgrade succeeds.

### Ingestion durability

* Every newly inserted Telegram text Message is committed atomically with one pending `generate_note` ProcessingTask.
* A transaction failure creates neither the Message nor its task and sends no success acknowledgement.
* Duplicate Telegram delivery produces exactly one Message and one ProcessingTask.
* A duplicate of a pre-Task-007 Message does not backfill a task.
* Redis is not contacted from ingestion.
* Redis unavailability does not prevent persistence or the exact acknowledgement `Saved for processing.`.

### Dispatcher behavior

* Dispatcher runs in the app process and is independent of Telegram polling.
* App startup remains successful when Redis is unavailable.
* Due pending/retrying rows are published by ProcessingTask UUID only.
* A task becomes queued only after successful publication.
* The queued update is conditional and cannot overwrite a fast worker claim.
* Broker failures leave tasks dispatchable and consume no attempt.
* Expired queued/running leases follow the required recovery transitions.
* Delivery is explicitly documented and tested as at least once.

### Worker behavior

* One generic actor reloads and locks ProcessingTask state from PostgreSQL.
* A claim increments attempts once, commits running state, and establishes a lease before Task 006 starts.
* The worker can claim queued and due pending/retrying rows.
* Duplicate and terminal deliveries are safe no-ops.
* The worker calls the unchanged Task 006 processing function with a fresh session.
* Dramatiq retries are disabled.
* PostgreSQL controls retries, attempts, backoff, and terminal failure.
* Final updates are conditional on task ID, running status, and claimed attempt number.
* A late worker cannot overwrite a newer attempt.

### Retry and recovery

* `max_attempts = 3` produces no more than three Task 006 calls through normal behavior.
* Retryable failures use the fixed bounded backoff.
* Permanent deterministic contract failures fail immediately.
* Errors are sanitized and bounded.
* Worker crash after claim recovers by lease expiry.
* Worker crash after Task 006 commit recovers through Task 006 idempotency and reaches succeeded without duplicate Artifact or file state.
* Redis restart/lost queue delivery recovers through queued-lease expiry and republish.

### Runtime and infrastructure

* Docker Compose includes PostgreSQL, Redis, app, and worker services.
* App remains FastAPI + aiogram + dispatcher.
* Worker uses the same codebase and image.
* Worker is configured with exactly one process and one thread.
* Worker receives the same PostgreSQL, Redis, and knowledge-base configuration and bind mount.
* `/health` and `/ready` do not depend on Redis.
* No Redis result backend or separate dispatcher service exists.

### End-to-end smoke

A disposable text message processed through the live Compose app/dispatcher/Redis/worker path reaches:

```text
ProcessingTask.status = succeeded
Message.status = done
exactly one Artifact row
exactly one exact deterministic Markdown file
```

The smoke must also prove:

* attempts is at least `1` and no greater than `3`;
* the Artifact/file matches Task 006 deterministic output;
* no duplicate Artifact or task exists;
* smoke User, Message, ProcessingTask, Artifact, and generated file are removed afterward;
* development row counts and pre-existing rows return to their pre-smoke values;
* the knowledge base contains no smoke note or temporary publication file afterward.

### Regression and scope protection

* Full authoritative Docker pytest suite passes.
* Development database data remains unchanged by pytest.
* Task 006 implementation and exact format contract remain unchanged.
* Existing manual CLI remains functional.
* No AI, multimodal, Git automation, completion notification, backfill, administration API, ProcessingEvent, separate outbox, generic framework, or unrelated refactor is introduced.
* Documentation describes only verified behavior.

## Required verification commands

Codex must adapt only repository-specific filenames or module paths discovered during inspection and report every deviation.

### Initial and contract verification

```bash
mkdir -p "$HOME/pkm-handoffs"
python3 scripts/project_context.py \
  > "$HOME/pkm-handoffs/task007-context.md"

git branch --show-current
git rev-parse HEAD
git status --short
git log --oneline --decorate -10
git diff --check

git show HEAD:tasks/007-durable-background-processing.md \
  > "$HOME/pkm-handoffs/task007-contract-from-head.md"
```

### Compose, migration, and service verification

```bash
docker compose config --quiet
docker compose up -d --build
docker compose ps
docker compose exec app alembic upgrade head
docker compose exec app alembic current
```

Inspect the resolved worker command and environment from:

```bash
docker compose config
```

The resolved configuration must show one worker process and one thread, the shared knowledge-base mount, and no Redis health dependency blocking the app service.

### Focused tests

Run the exact repository-confirmed focused files. The expected command boundary is equivalent to:

```bash
docker compose exec app python -m pytest \
  tests/test_processing_tasks.py \
  tests/test_task_dispatcher.py \
  tests/test_task_worker.py \
  tests/test_migrations.py
```

Also run the existing Telegram-ingestion, application-lifespan, and Task 006 focused suites by their live filenames.

### Isolated migration cycle

Use the existing isolated test database configuration:

```bash
docker compose exec app sh -lc '
  DATABASE_URL="$TEST_DATABASE_URL" alembic upgrade head &&
  DATABASE_URL="$TEST_DATABASE_URL" alembic downgrade -1 &&
  DATABASE_URL="$TEST_DATABASE_URL" alembic upgrade head
'
```

Confirm source rows survive the downgrade and no existing Message is backfilled after re-upgrade.

### Full authoritative suite and database isolation

Record development counts and stable marker identities before pytest for:

```text
users
messages
artifacts
processing_tasks
```

Run:

```bash
docker compose exec app python -m pytest
```

Repeat the development counts and marker checks. They must be unchanged, and test fixture identities must be absent from the development database.

### Redis-unavailable app check

With the normal Compose configuration built:

```bash
docker compose stop worker redis
docker compose restart app
docker compose ps
```

Verify from inside the app container that `/health` and `/ready` return their current successful responses while Redis is stopped. Use the repository’s available in-container HTTP client or Python standard library.

Then restore broker and worker:

```bash
docker compose up -d redis worker
docker compose ps
```

Confirm the app dispatcher resumes without requiring an app restart, unless live Dramatiq behavior proves that impossible and the contradiction is escalated before implementation.

### End-to-end Compose smoke

Run one disposable smoke using the actual ingestion persistence boundary or its repository-confirmed lower-level input function, without contacting Telegram.

The smoke procedure must:

1. record pre-smoke development counts and knowledge-base paths;
2. create a unique disposable Telegram User/Message through the ingestion transaction so its ProcessingTask is created automatically;
3. wait with a bounded timeout for the task to reach terminal state;
4. assert `succeeded`, Message `done`, one Artifact, and exact Task 006 file bytes;
5. record task ID, Message ID, attempt count, Artifact ID, and relative file path in the completion report;
6. delete the disposable ProcessingTask, Artifact, Message, and User in foreign-key-safe order;
7. delete only the disposable generated note and any disposable temporary files;
8. confirm pre-smoke counts and knowledge-base cleanliness are restored.

The one-off verification code and any output files must remain outside the repository under `~/pkm-handoffs/` when persisted. Do not add a permanent smoke/admin CLI.

### Endpoint and final checks

Run the repository’s normal endpoint checks. When host-published networking is affected by the documented local VPN/Docker issue, verify inside the container and report the host limitation honestly rather than changing repository networking.

Finally run:

```bash
git diff --check
git status --short
git diff --stat
```

### Completion report and review bundle

Write the completion report outside the repository:

```text
~/pkm-handoffs/task007-handoff.md
```

Generate the review bundle outside the repository:

```bash
python3 scripts/review_bundle.py \
  --task tasks/007-durable-background-processing.md \
  --report "$HOME/pkm-handoffs/task007-handoff.md" \
  > "$HOME/pkm-handoffs/task007-review-bundle.md"
```

Regenerate the bundle after any implementation, documentation, task-status, or completion-report change. Do not use `/tmp` for any Task 007 workflow artifact.

## Documentation impact

Update documentation only after the corresponding behavior is verified.

### `docs/ARCHITECTURE.md`

Update the runtime topology to show:

```text
Telegram → app ingestion → PostgreSQL Message + ProcessingTask
app dispatcher → Redis
Redis → Dramatiq worker
worker → PostgreSQL claim → existing Task 006 processing
worker → PostgreSQL ProcessingTask finalization
```

Document:

* app and worker process responsibilities;
* Redis as transport only;
* PostgreSQL as orchestration truth;
* at-least-once delivery;
* lease recovery;
* Task 006 as the unchanged deterministic/idempotent processing boundary;
* `/health` and `/ready` remaining independent of Redis.

### `docs/DATA_MODEL.md`

Add the exact ProcessingTask fields, constraints, indexes, statuses, initial values, attempt meaning, lease meaning, transitions, and relation to Message.

Keep `Message.status` and ProcessingTask status ownership distinct.

### `docs/TELEGRAM_INGESTION.md`

Update verified ingestion behavior:

* new Message and `generate_note` ProcessingTask commit atomically;
* acknowledgement remains `Saved for processing.` and occurs after commit;
* no Redis call occurs in the handler/transaction;
* Redis failure does not block ingestion;
* duplicate delivery creates no duplicate Message or task;
* old Messages are not backfilled;
* acknowledgement does not mean processing succeeded.

### `docs/CURRENT_STATE.md`

After implementation and verification:

* describe automatic processing and the exact runtime services;
* describe the current state transitions and known limitations;
* preserve the Task 006 manual CLI as supported behavior;
* record authoritative test and smoke results without turning the file into a changelog;
* set active task to `none selected` unless another task has been explicitly selected.

Also replace stale workflow examples that use `/tmp` with the repository-approved user-owned external handoff directory if those examples are present in the live current-state document. Do not broaden this into a workflow-tooling redesign.

### `README.md`

Document concisely:

* Redis and worker startup through Compose;
* required configuration;
* automatic processing behavior;
* worker process/thread limit;
* how to inspect ProcessingTask state using existing developer conventions;
* that Redis downtime does not block ingestion;
* that the manual Task 006 CLI remains available for old messages;
* that no completion notification, AI, or Git automation exists.

### `.env.example`

Add safe examples for:

```text
REDIS_URL
TASK_DISPATCHER_ENABLED
```

Preserve the Task 005 tracked-template review-bundle safety contract. Commit no real credential.

### `docs/DECISIONS.md`

Add the next live-confirmed decision number covering the durable orchestration boundary:

* Message and ProcessingTask are atomically persisted;
* PostgreSQL owns task state, retries, attempts, and leases;
* Redis/Dramatiq provide at-least-once transport;
* dispatcher runs in the app process;
* one generic actor carries only ProcessingTask UUID;
* Task 006 remains the unchanged idempotent processing boundary;
* queue and worker crashes recover through leases and reconciliation;
* Dramatiq automatic retries and Redis result storage are disabled;
* app health/readiness and ingestion do not depend on Redis.

Do not guess the decision number.

### Task file

After verification:

* update status according to repository conventions;
* append concise completion evidence without rewriting the accepted contract;
* record explicit amendments only when architecture/planning approves them;
* do not invent Task 008.

### Documents expected to remain unchanged

Unless live evidence demonstrates a direct need:

* `docs/MARKDOWN_ARTIFACTS.md`;
* `docs/PROJECT_BRIEF.md`;
* `docs/WORKFLOW.md`;
* `AGENTS.md`;
* completed task contracts other than a narrowly required status/reference correction;
* local Docker/VPN runbooks.

## Completion-report requirements

The completion report at `~/pkm-handoffs/task007-handoff.md` must include:

1. **Initial repository state**
   * branch;
   * starting HEAD;
   * clean/dirty status;
   * recent relevant commits;
   * context-report path;
   * proof that Task 006 is committed;
   * proof that the committed Task 007 contract existed at HEAD before implementation.

2. **Repository inspection findings**
   * exact migration head and selected revision;
   * exact ingestion transaction and duplicate behavior;
   * exact Task 006 function signature, session ownership, return type, and exception mapping;
   * exact settings/lifecycle conventions;
   * exact Dramatiq and Redis dependency choices;
   * exact worker command;
   * next durable decision number;
   * every contradiction or deviation.

3. **Implementation summary**
   * data flow from Telegram persistence through succeeded task;
   * PostgreSQL durability model;
   * dispatcher behavior;
   * actor/worker behavior;
   * retry and lease behavior;
   * why Task 006 remained unchanged.

4. **Changed files by responsibility**
   * migration/model;
   * ingestion;
   * dispatcher;
   * worker/actor;
   * settings/dependencies/Compose;
   * tests;
   * documentation.

5. **ProcessingTask schema and state machine**
   * fields, constraints, indexes;
   * initial values;
   * every allowed transition;
   * attempt semantics;
   * lease durations;
   * retry backoff;
   * permanent/retryable exception mapping.

6. **Race and recovery evidence**
   * publish-before-queued race;
   * duplicate actor delivery;
   * lost queued delivery;
   * stale running recovery;
   * late-worker conditional finalization;
   * finalization DB failure;
   * crash after Task 006 commit.

7. **Test results**
   * focused commands and exact pass counts;
   * migration cycle;
   * full suite;
   * Redis-unavailable lifecycle check;
   * Task 006 regression results;
   * database-isolation counts before and after.

8. **End-to-end Compose smoke evidence**
   * setup method;
   * task, Message, and Artifact UUIDs;
   * attempts;
   * final statuses;
   * relative file path;
   * exact-byte verification;
   * bounded wait result;
   * cleanup commands/results;
   * restored row counts and knowledge-base cleanliness.

9. **Acceptance matrix**
   * every acceptance criterion marked pass, fail, or unverified;
   * direct evidence for each result.

10. **Documentation updates**
    * what changed and why;
    * what intentionally remained unchanged.

11. **Scope and postponed work**
    * explicit confirmation that no out-of-scope feature or abstraction was added.

12. **Risks and unverified items**
    * local environment limitations;
    * any command not run;
    * any behavior inferred rather than directly verified.

13. **Final repository boundary**
    * `git diff --check` result;
    * final `git status --short`;
    * `git diff --stat`;
    * review-bundle path and generation result;
    * confirmation that no handoff, smoke, Redis-data, generated note, or temporary file is inside the repository.

The completion report contains claims for review; the review-bundle command does not independently execute them.

## Expected commit boundary

The accepted Task 007 specification should be committed separately before implementation begins.

The implementation commit may include only the smallest verified Task 007 outcome:

* ProcessingTask model and one migration;
* Telegram-ingestion transaction change;
* dispatcher and narrow state-transition code;
* Dramatiq broker/actor/worker wiring;
* Redis and worker Compose configuration;
* settings and normal dependency metadata;
* test-database cleanup changes;
* focused and regression tests;
* verified architecture, data-model, Telegram-ingestion, current-state, README, `.env.example`, decision, and task-status updates.

It must not include:

* Task 006 renderer/storage/processing changes;
* generated Markdown notes;
* smoke rows or database dumps;
* Redis data;
* completion reports, context reports, committed-contract copies, or review bundles;
* local VPN/Docker changes;
* AI or multimodal code;
* Git artifact automation;
* worker notification behavior;
* backfill/admin tools;
* Task 008 planning;
* unrelated refactoring.

Suggested implementation commit message:

```text
feat: add durable background processing
```

Codex must not create the implementation commit unless explicitly instructed.

## Completion evidence

Implemented and verified on 2026-07-03 without changing the accepted contract.
Migration `0003` adds ProcessingTask durability; Telegram ingestion creates the
task atomically; the app dispatcher and one-process/one-thread Dramatiq worker
use PostgreSQL-owned leases and retries while reusing Task 006 unchanged.

Focused Task 007 tests passed 39 cases, focused Task 006/Telegram/database
regressions passed 77 cases, and the complete suite passed 181 cases. The
isolated migration cycle, Redis-unavailable app check, four-service Compose
topology, and disposable exact-byte end-to-end smoke all passed. Development
database identities/counts were unchanged, and the smoke rows and generated
file were removed. Sequential real actor and Compose deliveries also completed
in one worker process after per-delivery engine disposal was added. Full
evidence is in the repository-external Task 007 handoff and review bundle.
