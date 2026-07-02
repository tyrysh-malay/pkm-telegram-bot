# Task 006: Generate deterministic Markdown artifacts from persisted text messages

**Status:** planned
**Depends on:** Tasks 001–005
**Target file:** `tasks/006-deterministic-markdown-artifacts.md`
**Expected commit boundary:** one reviewable implementation commit containing the minimal persistence, rendering, storage, processing, CLI, tests, migration, and documentation changes required by this task; Codex must not commit unless explicitly instructed

## Goal

Implement one explicit, manually invoked processing boundary:

```text
persisted text Message
→ deterministic Markdown note
→ Artifact database row
→ Message status = done
```

The outcome must be idempotent, concurrency-safe, recoverable across the PostgreSQL/filesystem boundary, and independently invocable for one existing message UUID.

This task must not connect processing to Telegram delivery, a background queue, or a worker.

## Confirmed current boundary

The supplied repository evidence confirms:

* Tasks 000–005 are completed.
* PostgreSQL persistence exists for `User` and `Message`.
* Alembic migrations are the schema authority.
* Telegram text messages are persisted with:

  * `input_type = "text"`;
  * `status = "received"`;
  * `raw_text`;
  * Telegram chat and message identifiers;
  * timezone-aware creation timestamps.
* Telegram ingestion acknowledges persistence only.
* Automated tests use a PostgreSQL database isolated from development data.
* Markdown artifact generation is not implemented.
* The current data-model documentation describes a future `Artifact` entity but does not confirm an implemented artifact table.
* `app/knowledge/` was part of the repository bootstrap direction, but its current contents require live inspection.
* `scripts/project_context.py` and `scripts/review_bundle.py` are repository workflow tools and are unrelated to runtime knowledge-artifact generation.
* Task 005 established the required completion-report and review-bundle handoff.
* The supplied task sequence ends at Task 005, making `006` the expected next task number.
* The supplied current-state snapshot records no active task.

The expected filename is:

```text
tasks/006-deterministic-markdown-artifacts.md
```

Codex must verify that this remains the next unused task filename in the live repository before editing.

## Repository verification requirements

Before editing, Codex must inspect and report:

### Git and task state

* current branch;
* current HEAD;
* staged, unstaged, and untracked state;
* recent commits;
* whether the Task 005 implementation is committed;
* whether the working tree is clean;
* whether any Task 006 file already exists;
* whether `tasks/006-deterministic-markdown-artifacts.md` exists at `HEAD`;
* whether the accepted Task 006 specification was committed before implementation began;
* whether a later task or conflicting architectural decision already exists.

If Task 005 is not closed at a clean commit boundary, Codex must report that contradiction and avoid mixing Task 005 corrections into Task 006.

### Application and persistence structure

Inspect:

* `app/settings.py`;
* `app/db/base.py`;
* `app/db/models.py` and any model modules;
* `app/db/session.py`;
* `app/knowledge/`;
* `app/main.py`;
* all Alembic configuration and migrations;
* current SQLAlchemy naming, UUID, timestamp, relationship, and session conventions;
* whether `expire_on_commit` is enabled;
* existing database transaction patterns;
* existing message-status handling;
* whether `Message.status` has a database check constraint or is unrestricted text;
* current migration revision identifiers and the next available revision;
* current test-database setup and cleanup order;
* every test fixture that deletes `Message` or `User` rows.

### Runtime and filesystem structure

Inspect:

* `Dockerfile`;
* `docker-compose.yml` or the repository’s actual Compose filename;
* `.dockerignore`;
* `.gitignore`;
* `.env.example`;
* current application working directory inside the container;
* whether `knowledge-base/` already exists;
* whether it contains tracked placeholders or existing files;
* whether the Compose app service already mounts the host knowledge-base directory;
* whether the configured path would be host-visible when the CLI runs inside the app container;
* filesystem and ownership assumptions relevant to atomic publication.

### Documentation and decisions

Read:

* `AGENTS.md`;
* `docs/WORKFLOW.md`;
* `docs/CURRENT_STATE.md`;
* `docs/DECISIONS.md`;
* `docs/ARCHITECTURE.md`;
* `docs/DATA_MODEL.md`;
* `docs/PROJECT_BRIEF.md`;
* `docs/TELEGRAM_INGESTION.md`;
* `README.md`;
* `tasks/TEMPLATE.md`;
* `tasks/005-implementation-review-bundles.md`.

Confirm:

* D-024 exists;
* the next available decision identifier, expected to be D-025;
* whether `docs/MARKDOWN_ARTIFACTS.md` already exists;
* whether the architecture document currently contains the ingestion or processing data flow and therefore requires an update.

### Test conventions

Inspect:

* `tests/conftest.py`;
* all database and migration tests;
* Telegram ingestion tests;
* Task 004 and Task 005 tooling tests;
* existing async test conventions;
* existing subprocess or CLI test conventions;
* whether PostgreSQL integration tests can run concurrent sessions;
* whether the authoritative development image already copies all new application and test modules.

Contradictory live repository evidence must be reported before editing. It must not be silently resolved by changing this specification after implementation.

## Problem or motivation

The project currently has a durable ingestion boundary:

```text
Telegram text
→ User and Message rows
→ “Saved for processing.”
```

The next smallest useful product slice is deterministic artifact generation from an already persisted message.

Without this task:

* a persisted message cannot become a human-readable note;
* there is no database record connecting a message to a knowledge-base file;
* the `received` status cannot transition to `done`;
* filesystem/database recovery behavior remains undefined;
* future queue or worker work would have no reusable processing function to invoke;
* Markdown rendering rules remain aspirational rather than executable and tested.

This task isolates artifact generation from orchestration. It proves the processing behavior manually for one message before Redis, Dramatiq, retries, scheduling, or automatic Telegram-triggered execution are introduced.

## Scope

Implement the smallest complete slice comprising:

1. a minimal `Artifact` SQLAlchemy model;
2. one Alembic migration creating the `artifacts` table;
3. deterministic title, slug, path, timestamp, and Markdown rendering;
4. safe knowledge-base path handling;
5. atomic, non-overwriting file publication;
6. one reusable async processing function;
7. source-message locking and database uniqueness protection;
8. reconciliation between the deterministic file and `Artifact` row;
9. transition of the source `Message` to `status = "done"` only after both resources are established;
10. one developer CLI for processing an existing message UUID;
11. focused unit and PostgreSQL integration tests;
12. migration upgrade and downgrade verification;
13. configuration and Compose changes required for a host-visible knowledge base;
14. documentation updates and one durable decision;
15. Task 006 completion reporting and review-bundle generation.

## Out of scope

Do not add:

* Redis;
* Dramatiq;
* Celery;
* a worker process;
* a queue;
* periodic processing;
* message polling for unprocessed rows;
* automatic processing from the Telegram handler;
* changed Telegram acknowledgements;
* Telegram retries;
* `ProcessingTask`;
* `ProcessingEvent`;
* task status machinery;
* `queued`, `processing`, `retrying`, or processing-specific `failed` transitions;
* AI calls;
* summarization;
* generated tags or topics;
* database tags or topics;
* link extraction;
* voice processing;
* image processing;
* file or PDF processing;
* Git commits;
* Git pushes;
* Git staging;
* artifact versioning;
* artifact history;
* artifact replacement;
* artifact deletion;
* artifact update commands;
* bulk-processing commands;
* a REST endpoint for processing;
* a generic repository abstraction;
* a generic service framework;
* a generic filesystem abstraction;
* a generic unit-of-work framework;
* distributed locks;
* a new YAML dependency;
* unrelated persistence or Telegram refactoring.

## Affected components

### Application

Expected additions or changes:

* settings for the knowledge-base root;
* minimal knowledge rendering and processing modules;
* one developer CLI module.

No FastAPI endpoint is required.

### Database

Expected additions or changes:

* `Artifact` model;
* relation to `Message` where consistent with current model conventions;
* one Alembic migration;
* test cleanup order updated to remove artifacts before messages;
* `Message.status` transition to `done`.

### Filesystem

Expected additions or changes:

* deterministic notes under the configured knowledge-base root;
* safe creation of the `inbox/` directory;
* atomic no-replace publication;
* temporary-file cleanup.

### Telegram bot

No handler, polling, acknowledgement, or Telegram API behavior changes.

### Worker and queue

No worker or queue changes.

### Infrastructure

A minimal Compose environment or bind-mount change is allowed only when required to make the configured knowledge-base path persist on the host.

### Documentation

Expected updates:

* `docs/DATA_MODEL.md`;
* new `docs/MARKDOWN_ARTIFACTS.md`;
* `docs/ARCHITECTURE.md` when live inspection confirms that the new data-flow boundary belongs there;
* `README.md`;
* `.env.example`;
* `docs/CURRENT_STATE.md`;
* `docs/DECISIONS.md`;
* this task file.

### Components expected to remain unchanged

Unless live repository evidence demonstrates a direct requirement:

* `docs/TELEGRAM_INGESTION.md`;
* `docs/PROJECT_BRIEF.md`;
* `docs/WORKFLOW.md`;
* `AGENTS.md`;
* Task 004 and Task 005 repository tooling;
* Telegram handlers;
* health and readiness behavior.

## Data, state, migration, and configuration impact

## Artifact model

Add an `Artifact` table and SQLAlchemy model with exactly the following business fields:

```text
id
message_id
artifact_type
title
slug
file_path
created_at
updated_at
```

Required semantics:

```text
artifact_type = "note"
```

Required constraints:

```text
UNIQUE(message_id, artifact_type)
UNIQUE(file_path)
```

Requirements:

* `id` is a UUID primary key following existing application conventions.
* `message_id` is a non-null foreign key to `messages.id`.
* `artifact_type` is non-null text.
* `title` is non-null text.
* `slug` is non-null text.
* `file_path` is non-null text.
* `created_at` and `updated_at` are timezone-aware and follow existing timestamp conventions.
* `file_path` stores a POSIX-style path relative to the configured knowledge-base root.
* `title` and `slug` are not unique.
* no database enum is introduced;
* no artifact-type check constraint is required in this task;
* application processing supports only `artifact_type = "note"`;
* no nullable future fields are added.

Do not add:

```text
summary
tags
topics
git_commit_sha
version
content_hash
processing_task_id
metadata
```

A relation from `Message` to artifacts may be added only in the smallest form consistent with current SQLAlchemy conventions. Do not introduce cascade deletion or a generic collection abstraction without a present requirement.

## Migration requirements

Add the next live-confirmed Alembic revision, expected to be the revision immediately after the existing users/messages migration.

The upgrade must:

1. create `artifacts`;
2. create its primary key;
3. create the foreign key to `messages`;
4. create `UNIQUE(message_id, artifact_type)`;
5. create `UNIQUE(file_path)`;
6. preserve existing users and messages;
7. perform no data backfill;
8. leave existing message statuses unchanged.

The downgrade must:

1. drop only the `artifacts` table and its constraints;
2. leave `users` and `messages` intact;
3. not delete or modify knowledge-base files;
4. not attempt to reverse any message status;
5. permit a subsequent upgrade to recreate the table successfully.

Migration rollback verification must run against an isolated test database, not a development database containing data that must be preserved.

Runtime application startup must not call `create_all()`.

## Configuration

Introduce:

```text
KNOWLEDGE_BASE_PATH
```

Recommended application default:

```text
knowledge-base
```

Requirements:

* add the setting through the existing settings mechanism;
* represent it as a filesystem path;
* document it in `.env.example`;
* use no real machine-specific path in committed configuration;
* tests must pass an isolated temporary directory directly or through test settings;
* relative paths resolve consistently from the application working directory;
* absolute configured paths are allowed;
* the developer CLI uses the normal setting;
* the reusable processing function receives the resolved root explicitly and must not read global settings internally.

Codex must inspect Compose behavior.

If the app container does not already expose the local knowledge base on the host, add the smallest bind mount consistent with the repository, preferably equivalent to:

```text
./knowledge-base:/app/knowledge-base
```

The final container path must match the actual working directory and settings behavior discovered in the repository.

Do not add a new Docker volume when a simple bind mount provides the intended developer-visible Markdown files.

## Behavioral requirements

## Public processing boundary

Add one reusable async function with a boundary equivalent to:

```python
async def process_text_message(
    session: AsyncSession,
    message_id: UUID,
    knowledge_base_root: Path,
) -> Artifact:
    ...
```

The exact module may follow stronger live conventions, but the preferred location is under:

```text
app/knowledge/
```

Requirements:

* it processes exactly one message;
* it accepts a fresh SQLAlchemy async session;
* it owns the processing transaction;
* it commits on success;
* it rolls back on failure;
* it returns the established `Artifact`;
* it does not create a Telegram client;
* it does not call Telegram;
* it does not read application settings internally;
* it does not process multiple messages;
* it does not enqueue work;
* it does not introduce a generic service or repository layer.

If existing session conventions make returning an ORM entity after commit unsafe, a small immutable result containing the artifact ID and relative path is acceptable only when Codex explains the repository-specific reason before editing. The database row must still be represented by the `Artifact` model.

The session supplied to the function must not already contain a caller-owned active transaction. The function must fail clearly rather than silently committing unrelated caller work.

## Eligible source message

Processing succeeds only when:

* a `Message` with the supplied UUID exists;
* `input_type == "text"`;
* `raw_text` is not null;
* `created_at` is timezone-aware;
* Telegram chat and message identifiers are present;
* the message is lockable and readable from the current database transaction.

The current message status may be:

```text
received
done
```

The function must not trust `status = "done"` as proof that the row and file are consistent. It must run reconciliation.

Reject:

* missing messages;
* non-text messages;
* text messages with null `raw_text`;
* messages with invalid source timestamps;
* malformed persisted source data required by the Markdown contract.

On rejection, preserve the previous message status.

## Source-message locking

Inside the processing transaction, select the source `Message` using row-level locking where supported, with PostgreSQL `SELECT ... FOR UPDATE` semantics.

The lock must serialize processing attempts for the same source message.

Do not lock unrelated messages.

Database uniqueness constraints remain the final protection against duplicate artifacts.

When an expected duplicate-related uniqueness race still occurs:

1. roll back the failed transaction;
2. distinguish the expected artifact uniqueness conflict from unrelated integrity errors;
3. perform at most one bounded reconciliation retry in a fresh transaction;
4. return the established existing artifact when the second pass finds a valid row and exact file;
5. surface unrelated integrity failures.

Do not loop indefinitely.

## Deterministic relative path

The relative artifact path is:

```text
inbox/YYYY-MM-DD--<full-message-uuid>.md
```

Rules:

* use the source message’s `created_at`;
* convert the timestamp to UTC before taking the date;
* use four-digit year, two-digit month, and two-digit day;
* use the canonical lowercase full UUID with hyphens;
* do not use the title or slug in the path;
* do not use Telegram username or mutable profile data;
* do not use the current clock;
* do not use the artifact UUID;
* use `/` as the stored path separator;
* store no leading slash;
* store no `.` or `..` component.

Example:

```text
inbox/2026-07-02--123e4567-e89b-12d3-a456-426614174000.md
```

The path is stable even when title-generation rules are changed in a future explicitly versioned task. Task 006 itself does not update existing artifacts to new rules.

## Newline normalization

Normalize source text before title selection and body rendering:

```text
CRLF → LF
CR   → LF
```

No other body transformation is allowed except the final-newline rule below.

Do not:

* trim leading whitespace;
* trim ordinary trailing spaces;
* collapse body whitespace;
* normalize Unicode;
* rewrite Markdown characters;
* escape the body;
* add AI-generated text.

A NUL character in `raw_text` is invalid and must cause processing to fail.

## Title derivation

Use this exact algorithm:

1. normalize source newlines;
2. split on LF;
3. select the first line containing at least one non-whitespace Unicode character;
4. strip leading and trailing Unicode whitespace from that line;
5. replace each maximal run of Unicode whitespace within that line with one ASCII space;
6. truncate to at most 80 Unicode code points;
7. if no non-empty line exists, use:

   ```text
   Untitled note
   ```

The 80-code-point limit applies after whitespace normalization.

Do not append an ellipsis.

Do not use the source UUID in the title.

The derived title must contain no newline.

## Slug derivation

Derive the slug from the final derived title using this exact algorithm:

1. normalize with Unicode NFKC;
2. apply Unicode `casefold`;
3. retain Unicode alphanumeric characters;
4. replace each maximal run of every other character with one ASCII hyphen;
5. remove leading and trailing hyphens;
6. truncate to at most 80 Unicode code points;
7. remove any trailing hyphen introduced by truncation;
8. if the result is empty, use:

   ```text
   note
   ```

Requirements:

* do not transliterate to ASCII;
* preserve letters from non-Latin scripts;
* do not include underscores;
* do not include repeated hyphens;
* slug uniqueness is not required;
* the slug does not determine the file path.

Examples:

```text
"Hello,   World!" → "hello-world"
"Привет, мир!"    → "привет-мир"
"!!!"             → "note"
```

## Captured timestamp rendering

Render `captured_at` from `Message.created_at` after conversion to UTC.

Use exactly:

```text
YYYY-MM-DDTHH:MM:SS.ffffffZ
```

Requirements:

* always include six fractional-second digits;
* always use the literal `Z`;
* do not use `+00:00`;
* do not use the current clock;
* reject a naive source timestamp rather than guessing its timezone.

Example:

```text
2026-07-02T12:34:56.000000Z
```

## YAML-safe quoting

Use deterministic JSON-compatible double-quoted string encoding for every string-valued frontmatter field.

The encoding must:

* use double quotes;
* escape embedded double quotes;
* escape backslashes;
* escape control characters;
* preserve non-ASCII text rather than converting it to `\uXXXX` sequences;
* produce a scalar valid under YAML 1.2;
* require no PyYAML dependency.

A standard-library implementation equivalent to:

```python
json.dumps(value, ensure_ascii=False)
```

is preferred.

Integer values must be rendered as unquoted base-10 integers.

Empty arrays must be rendered exactly as:

```yaml
[]
```

## Exact Markdown contract

Render UTF-8 bytes with LF line endings and frontmatter keys in exactly this order:

```yaml
---
format_version: 1
artifact_type: "note"
source: "telegram"
source_message_id: "<application-message-uuid>"
telegram_chat_id: 123
telegram_message_id: 456
captured_at: "<message-created-at-in-UTC>"
title: "<derived-title>"
slug: "<derived-slug>"
tags: []
topics: []
---
```

Then render:

```markdown
# <derived-title>

<normalized original Telegram text>
```

The complete structure is:

```text
---
<fixed frontmatter fields>
---

# <derived-title>

<body>
```

Requirements:

* `format_version` is the integer `1`;
* `artifact_type` is `"note"`;
* `source` is `"telegram"`;
* `source_message_id` is the canonical lowercase application UUID;
* Telegram IDs are unquoted integers;
* `title` and `slug` use the deterministic rules above;
* `tags` and `topics` are empty frontmatter arrays only;
* tags and topics are not persisted in the database;
* there is one empty line after the closing frontmatter delimiter;
* there is one empty line after the H1;
* the H1 uses the derived title without additional escaping or rewriting;
* body text uses normalized LF line endings;
* remove all trailing LF characters from the normalized body;
* append exactly one final LF to the complete file;
* therefore, every generated note ends in exactly one LF;
* no current-clock field is included;
* no artifact-row UUID is included;
* no mutable Telegram profile field is included;
* no generated summary is included.

The renderer must be a pure deterministic boundary: identical source fields produce identical bytes.

## File and path safety

The configured knowledge-base root is operator-controlled configuration.

For every processing call:

1. resolve the configured root to an absolute normalized path;
2. derive the relative path only from trusted date and UUID values;
3. join the relative path under the root;
4. verify that the normalized destination remains inside the resolved root;
5. create the root and `inbox/` directory when absent;
6. reject a destination parent that is not a directory;
7. reject a destination parent symlink when it could redirect publication outside the configured root;
8. inspect existing final paths without following a final symlink;
9. treat an existing symlink, directory, or special file at the final path as a conflict;
10. never store an absolute path in PostgreSQL.

Do not accept a file path supplied by the user, Telegram text, title, slug, or database artifact row as a filesystem target without validating it against the deterministic expected path.

## Deterministic file states

Classify the expected final path as exactly one of:

```text
absent
exact
conflicting
unsupported
```

Definitions:

* `absent` — no filesystem entry exists;
* `exact` — a regular file exists and its bytes exactly equal the deterministic rendered bytes;
* `conflicting` — a regular file exists with different bytes;
* `unsupported` — a symlink, directory, socket, FIFO, device, or other non-regular entry exists.

A differing newline style counts as conflicting.

A differing final newline counts as conflicting.

Do not rewrite or normalize an existing file during comparison.

## Atomic no-replace publication

When the final file is absent:

1. create a uniquely named temporary regular file in the destination directory;
2. open it with exclusive creation;
3. write the complete deterministic bytes;
4. flush and close it successfully;
5. flush file contents to the filesystem with `fsync` where supported by the target platform;
6. publish it atomically without replacing an existing final path;
7. remove the temporary name after successful publication;
8. clean the temporary file in a `finally` boundary after every handled failure.

The publication primitive must have no-overwrite semantics.

On the project’s Linux/Docker environment, a standard-library approach using a same-directory hard link from the fully written temporary file to the final path is preferred when live filesystem verification supports it.

Do not use plain `os.replace()` or a rename operation that can overwrite the final path.

If publication observes that the final path appeared concurrently:

* inspect the newly existing entry;
* continue only when it is a regular file with exact deterministic bytes;
* otherwise fail as a conflict;
* never overwrite it.

If the target filesystem cannot provide the required atomic no-replace behavior, fail clearly rather than falling back to a potentially overwriting operation.

Tests must confirm that no temporary file remains after:

* successful publication;
* a conflicting final path;
* a simulated write failure;
* a simulated publish failure;
* a database failure occurring after publication.

Abrupt process termination such as `SIGKILL` is outside the guarantee of Python `finally`; Task 006 must not add a broad stale-temporary-file cleanup service.

## Artifact metadata validity

For a note artifact to be valid, it must have:

```text
message_id   = source Message.id
artifact_type = "note"
title         = expected derived title
slug          = expected derived slug
file_path     = expected deterministic relative path
```

`id`, `created_at`, and `updated_at` are database-managed identity and audit fields and are not part of deterministic file content.

If a note artifact exists for the source message but any deterministic metadata differs, fail clearly.

Do not silently repair or update inconsistent artifact metadata.

If another artifact row already owns the expected `file_path`, fail clearly.

Do not repoint either artifact.

## Full reconciliation matrix

Let:

```text
A = note Artifact row for the source message
F = expected final filesystem path
```

### Case 1 — no row, no file

```text
A = absent
F = absent
```

Required behavior:

1. publish the deterministic file;
2. insert the Artifact row;
3. set the source Message status to `done`;
4. commit;
5. return the new artifact.

If the database transaction later fails, preserve the exact final file. A later invocation must reconcile it through Case 2.

### Case 2 — no row, exact deterministic file

```text
A = absent
F = exact
```

Required behavior:

1. do not rewrite the file;
2. insert the Artifact row;
3. set the source Message status to `done`;
4. commit;
5. return the new artifact.

This is the primary recovery path after file publication followed by database failure.

### Case 3 — no row, conflicting file

```text
A = absent
F = conflicting or unsupported
```

Required behavior:

* fail;
* do not insert an Artifact;
* do not overwrite, delete, rename, or modify the existing filesystem entry;
* leave the previous Message status unchanged.

### Case 4 — valid row, no file

```text
A = valid
F = absent
```

Required behavior:

1. recreate the deterministic file through atomic no-replace publication;
2. set Message status to `done` if it is not already `done`;
3. commit;
4. return the existing Artifact.

Do not create another row.

Do not change artifact identity, title, slug, path, or timestamps merely because the file was recreated.

### Case 5 — valid row, exact deterministic file

```text
A = valid
F = exact
```

Required behavior:

1. do not rewrite the file;
2. do not create another Artifact;
3. set Message status to `done` only when needed;
4. commit only required state changes;
5. return the existing Artifact.

When the message is already `done`, repeated processing must be a semantic no-op:

* same Artifact ID;
* same artifact row;
* same artifact timestamps;
* identical file bytes;
* no file rewrite;
* unchanged file modification time where the filesystem permits reliable checking.

### Case 6 — valid row, conflicting file

```text
A = valid
F = conflicting or unsupported
```

Required behavior:

* fail;
* do not overwrite or delete the filesystem entry;
* do not modify the Artifact row;
* leave the previous Message status unchanged.

### Case 7 — inconsistent artifact row

```text
A = present but metadata or file_path is inconsistent
```

Required behavior:

* fail before publishing or modifying a file;
* do not update the Artifact row;
* do not create a second Artifact;
* leave the previous Message status unchanged.

### Case 8 — expected path owned by another Artifact

Required behavior:

* fail clearly;
* do not create or modify a file;
* do not modify either Artifact;
* leave the source Message status unchanged.

## Message status

Set:

```text
status = "done"
```

only after, within the success path:

* the expected deterministic final file exists with exact bytes;
* a valid Artifact row exists or is ready to be committed;
* no reconciliation inconsistency remains.

Requirements:

* do not set `done` before file validation;
* do not set `done` before artifact validation;
* do not introduce an intermediate status;
* do not set `failed` on error;
* on failure, preserve the status value that existed before processing;
* if the status was already `done`, a failure leaves it `done`;
* status is not itself proof of artifact consistency.

Do not change the Telegram acknowledgement in this task. It continues to mean only that the raw message was persisted.

## PostgreSQL/filesystem transaction boundary

There is no distributed transaction across PostgreSQL and the filesystem.

Use this recovery rule:

```text
an exact deterministic final file may safely exist without an Artifact row
```

Therefore:

* publish or establish the exact final file before committing a newly inserted Artifact;
* if Artifact insertion, flush, or commit fails after publication, preserve the file;
* rollback database changes;
* leave Message status unchanged after rollback;
* allow the next invocation to detect the exact file and create the row;
* never delete the exact final file as compensation for a database failure.

For an existing valid Artifact whose missing file is recreated:

* preserve the recreated exact file if the subsequent database status commit fails;
* rollback database state;
* allow the next invocation to verify the exact row and file again.

If filesystem publication fails before a new Artifact is committed:

* rollback the transaction;
* do not leave an Artifact row;
* leave Message status unchanged;
* clean the temporary file.

Do not implement a transaction log, processing event, outbox, or compensating deletion.

## Source-message mutability assumption

Task 006 renders from the current persisted source-message fields.

It does not add:

* message versioning;
* source snapshots;
* artifact content hashes;
* source immutability constraints.

The processing code itself must not modify:

* `raw_text`;
* `created_at`;
* Telegram chat ID;
* Telegram message ID;
* message input type.

If source fields are manually altered after artifact creation:

* existing exact-file comparison may detect a conflict;
* inconsistent title, slug, or path metadata must fail;
* Task 006 does not attempt artifact versioning or historical recovery.

This limitation must be documented.

## Logging and errors

Use explicit, small processing exceptions or existing project error conventions.

Expected errors include:

* message not found;
* unsupported input type;
* null or invalid source text;
* invalid timestamp;
* invalid knowledge-base root;
* artifact metadata mismatch;
* expected path already owned by another Artifact;
* conflicting file;
* unsupported filesystem entry;
* atomic publication unsupported;
* permission or disk failure;
* database failure;
* unrelated integrity violation;
* duplicate race that remains inconsistent after one retry.

Requirements:

* do not silently swallow exceptions;
* CLI failures must be concise and actionable;
* include the application message UUID in logs or errors where safe;
* include the relative artifact path where relevant;
* do not log full raw message text;
* do not log database credentials or Telegram tokens;
* do not change Message status on failure.

## Developer CLI

Add a small command, preferably:

```bash
python3 -m app.knowledge.cli --message-id <uuid>
```

The exact module may change only when live repository conventions strongly justify another location.

Requirements:

* `--message-id` is required;
* parse it as a UUID before opening processing work;
* load normal application settings;
* use the normal async session factory;
* use `KNOWLEDGE_BASE_PATH`;
* process exactly one existing message;
* make no Telegram request;
* start no polling;
* start no FastAPI server;
* enqueue nothing;
* return zero on success;
* return non-zero on failure;
* write concise errors to standard error;
* do not print a traceback for an expected processing error;
* do not print raw message text.

On success print exactly:

```text
artifact_id: <artifact-uuid>
file_path: <relative-posix-path>
```

with one final LF after the second line.

Repeated successful execution for the same message must print the same artifact ID and path.

No `--force`, `--overwrite`, `--all`, or `--retry` option is allowed.

## Investigation requirements

Before choosing implementation details, Codex must determine:

* the existing SQLAlchemy UUID and timestamp implementation;
* whether models are in one file or multiple files;
* whether the session factory uses `expire_on_commit=False`;
* how to return the artifact safely after commit;
* the current transaction style;
* how Alembic imports model metadata;
* the current migration naming convention;
* the existing constraint naming convention;
* how test cleanup must be ordered once `artifacts` references `messages`;
* whether PostgreSQL row locking is already used anywhere;
* whether the test database can run two concurrent sessions reliably;
* whether a hard-link-based no-replace publication works on:

  * the host test filesystem;
  * temporary pytest directories;
  * the Compose knowledge-base bind mount;
* whether an equivalent standard-library atomic no-replace primitive is needed;
* whether the existing `knowledge-base/` directory or mount introduces symlinks;
* whether the app container user can create directories and files there;
* whether running the CLI with the default path makes files visible on the host;
* whether Docker or application packaging already includes new `app/knowledge` modules automatically;
* whether architecture documentation currently shows the data flow through persisted messages.

Do not introduce a generic abstraction merely to hide these findings.

## Expected failure modes and recovery behavior

### Message does not exist

Behavior:

* fail clearly;
* no Artifact;
* no file;
* no status change.

Recovery:

* supply an existing Message UUID.

### Unsupported or malformed source message

Behavior:

* fail clearly for non-text input, null text, invalid timestamp, or missing required source identifiers;
* no filesystem or database artifact changes;
* status unchanged.

Recovery:

* correct the persisted source data through an explicitly separate maintenance action.

### Invalid knowledge-base root

Examples:

* root is an existing non-directory;
* root is inaccessible;
* destination escapes the root;
* destination parent is unsafe.

Behavior:

* fail before Artifact insertion or status change;
* do not write outside the configured root.

Recovery:

* correct `KNOWLEDGE_BASE_PATH` or filesystem permissions.

### Exact orphan file after database failure

Behavior:

* next processing invocation recognizes exact bytes;
* creates the missing Artifact row;
* sets status to `done`;
* does not rewrite the file.

Recovery is automatic on explicit re-invocation.

### Artifact row with missing file

Behavior:

* recreate exact deterministic bytes;
* return the existing Artifact;
* set status to `done` when needed.

Recovery is automatic on explicit re-invocation.

### Conflicting final file

Behavior:

* fail;
* preserve the conflicting entry;
* do not create or change an Artifact;
* preserve Message status.

Recovery:

* inspect and manually resolve the conflict outside this command;
* rerun after the deterministic path is absent or contains exact expected bytes.

### Inconsistent Artifact row

Behavior:

* fail;
* preserve row, file, and Message status;
* do not silently repair metadata.

Recovery:

* investigate the inconsistency and use a future explicit maintenance path.

### Concurrent processing

Behavior:

* row lock serializes same-message work under PostgreSQL;
* atomic no-replace publication prevents file replacement;
* uniqueness constraints prevent duplicate rows;
* one bounded duplicate reconciliation retry handles a genuine race;
* all successful callers return the same Artifact identity;
* exactly one final file exists.

### Database failure after file publication

Behavior:

* rollback database work;
* preserve exact file;
* status remains as before the failed transaction;
* next invocation reconciles.

### Filesystem failure

Behavior:

* rollback pending database work;
* clean temporary file on handled failure;
* preserve previous Message status;
* do not create a partial final file;
* do not create a committed Artifact without its exact file.

### Temporary-file cleanup failure

Behavior:

* preserve the primary error;
* report cleanup failure without pretending processing succeeded;
* do not remove an existing final file.

### Migration downgrade

Behavior:

* isolated test database returns to the prior schema;
* users and messages remain;
* filesystem notes are untouched.

Recovery:

* reapply `alembic upgrade head`.

## Tests

## Rendering unit tests

Add exact golden-byte tests for:

1. the complete preferred frontmatter and Markdown structure;
2. fixed key ordering;
3. UTF-8 output;
4. LF-only line endings;
5. exactly one final LF;
6. CRLF and CR normalization;
7. preservation of body leading whitespace;
8. preservation of ordinary trailing spaces;
9. normalization of multiple trailing LFs to one final LF;
10. YAML-safe quotes and backslashes;
11. non-ASCII title and body text;
12. source UUID formatting;
13. UTC timestamp conversion;
14. exactly six timestamp fractional digits;
15. negative Telegram chat IDs;
16. absence of current-clock, artifact-ID, username, summary, database tags, and database topics.

## Title tests

Test:

* leading empty lines;
* internal tabs and multiple Unicode spaces;
* first non-empty line selection;
* leading and trailing whitespace removal;
* 80-code-point truncation;
* no ellipsis;
* whitespace-only source fallback;
* title containing Markdown punctuation;
* title containing quotes and backslashes.

## Slug tests

Test:

* ASCII casefolding;
* punctuation collapse;
* repeated separators;
* Unicode NFKC behavior;
* non-Latin letters;
* digits;
* combining characters;
* 80-code-point limit;
* trailing-hyphen removal after truncation;
* empty-slug fallback;
* no transliteration;
* deterministic repeated rendering.

## Path tests

Test:

* UTC date extraction;
* source timestamps with non-UTC offsets;
* canonical full UUID;
* POSIX relative path;
* title independence;
* slug independence;
* no current date;
* containment within configured root;
* unsafe parent entry handling;
* final symlink rejection;
* final directory and special-entry rejection.

## Model and migration tests

Verify:

* the Artifact model maps all required fields;
* an Artifact references a Message;
* duplicate `(message_id, artifact_type)` is rejected;
* duplicate `file_path` is rejected;
* different artifact types for the same message remain schema-valid, even though processing supports only `note`;
* migration from the previous revision creates `artifacts`;
* downgrade removes `artifacts`;
* downgrade preserves `users` and `messages`;
* re-upgrade succeeds;
* no `ProcessingTask`, `ProcessingEvent`, summary, tags, topics, Git SHA, or version column exists;
* Alembic, not runtime `create_all()`, owns the table.

## Reconciliation integration tests

Use PostgreSQL and temporary knowledge-base roots.

Cover every matrix case:

1. no row + no file;
2. no row + exact file;
3. no row + conflicting file;
4. valid row + no file;
5. valid row + exact file;
6. valid row + conflicting file;
7. row with wrong title;
8. row with wrong slug;
9. row with wrong path;
10. expected path owned by another Artifact.

For each case verify:

* resulting row count;
* Artifact identity;
* exact file bytes;
* Message status;
* no overwrite;
* no duplicate;
* temporary-file cleanup.

## Idempotency tests

Verify:

* repeated processing returns the same Artifact ID;
* only one Artifact row exists;
* only one final file exists;
* exact file bytes do not change;
* already-`done` repeated processing does not change artifact timestamps;
* already-`done` repeated processing does not rewrite the file;
* a `received` message with valid existing row and file becomes `done`.

## Concurrency tests

Using separate PostgreSQL sessions, process the same message concurrently.

Verify:

* all successful calls return the same Artifact ID;
* exactly one note Artifact exists;
* exactly one final file exists;
* file bytes are exact;
* Message status is `done`;
* no temporary files remain;
* no unrelated integrity error is swallowed.

Also test a forced duplicate uniqueness race where practical, including the one bounded retry.

## Failure-injection tests

Simulate:

* temporary-file write failure;
* publication failure;
* final path appearing concurrently with exact bytes;
* final path appearing concurrently with conflicting bytes;
* Artifact flush failure after file publication;
* transaction commit failure after file publication;
* status commit failure for an existing Artifact;
* permission error;
* unsupported no-replace publication.

Verify:

* previous Message status is preserved after database rollback;
* exact published file remains after database failure;
* next normal invocation reconciles it;
* no committed Artifact exists after a failed new-row transaction;
* no conflicting entry is overwritten;
* no handled path leaves a temporary file.

## Source validation tests

Verify failures for:

* missing message UUID;
* malformed CLI UUID;
* non-text message;
* null raw text;
* NUL-containing text;
* naive `created_at`;
* malformed required Telegram identifiers.

## CLI tests

Test:

* `--message-id` is required;
* malformed UUID exits non-zero before processing;
* successful processing prints exactly two specified lines;
* repeated CLI execution prints the same values;
* expected processing errors use standard error and non-zero exit;
* no Telegram bot or polling runtime is created;
* CLI uses `KNOWLEDGE_BASE_PATH`;
* subprocess execution can use the isolated test database and temporary root.

## Regression and isolation tests

Verify:

* existing Telegram ingestion tests remain unchanged and pass;
* existing database-isolation behavior remains intact;
* test cleanup deletes artifacts before messages;
* tests never write generated notes under the repository’s real `knowledge-base/`;
* development database rows remain unaffected by pytest;
* Task 004 and Task 005 tooling tests continue to pass;
* complete authoritative pytest suite passes;
* `/health` and `/ready` remain successful.

## Acceptance criteria

Task 006 is complete only when all criteria below pass.

### Schema

* an `artifacts` table exists;
* it has only the required Task 006 fields and ordinary model infrastructure;
* `(message_id, artifact_type)` is unique;
* `file_path` is unique;
* `message_id` references `messages.id`;
* upgrade, downgrade, and re-upgrade work in an isolated database;
* users and messages survive the downgrade;
* no postponed processing tables or artifact metadata fields are added.

### Deterministic rendering

* identical persisted source fields produce byte-identical Markdown;
* the exact frontmatter order is implemented;
* string values use deterministic JSON-compatible YAML quoting;
* source timestamps use fixed six-digit UTC `Z` format;
* title derivation follows the specified first-line, whitespace, fallback, and 80-code-point rules;
* slug derivation follows the NFKC, casefold, Unicode-alphanumeric, separator, fallback, and 80-code-point rules;
* body text is preserved except for newline and final-newline normalization;
* output is UTF-8 with LF line endings;
* every file ends in exactly one LF;
* no current-clock or artifact-row value appears in file content.

### Path and storage safety

* path format is exactly:

  ```text
  inbox/YYYY-MM-DD--<full-message-uuid>.md
  ```

* path date comes from source-message UTC creation time;

* stored path is relative and POSIX-style;

* path is independent of title and slug;

* destination remains inside the configured root;

* existing symlinks and unsupported entries are rejected;

* conflicting files are never overwritten;

* publication is atomic and no-replace;

* temporary files are cleaned on every handled path;

* the default Compose development setup makes generated notes host-visible when a mount is required.

### Processing behavior

* the reusable async function processes one existing text message;
* PostgreSQL source-message locking is used;
* database constraints remain final duplicate protection;
* every reconciliation matrix case behaves as specified;
* repeated processing returns the same Artifact;
* concurrent processing creates one Artifact and one final file;
* invalid Artifact metadata fails rather than being silently repaired;
* an exact orphan file can be reconciled into a row;
* a missing file can be recreated for a valid row.

### Status behavior

* `Message.status` changes to `done` only after exact file and valid Artifact are established;
* no intermediate status is introduced;
* failures preserve the previous status;
* processing does not change Telegram acknowledgement behavior.

### Failure recovery

* database failure after file publication preserves the exact file;
* the next invocation reconciles that file;
* filesystem failure does not commit a new Artifact;
* conflicting existing content is preserved;
* no compensating file deletion is used;
* no infinite uniqueness retry exists.

### CLI

* the documented module command runs;
* it requires one message UUID;
* it uses normal settings and sessions;
* it makes no Telegram request;
* it prints the Artifact ID and relative path exactly as specified;
* expected failures return non-zero.

### Configuration and infrastructure

* `KNOWLEDGE_BASE_PATH` exists with a safe documented example;
* tests use temporary knowledge-base roots;
* the smallest required Compose mount or environment change is used;
* no queue, worker, Redis, AI, or Git automation is added.

### Documentation

* `docs/DATA_MODEL.md` describes the implemented Artifact schema;
* `docs/MARKDOWN_ARTIFACTS.md` records the exact rendering, path, reconciliation, safety, and recovery contract;
* `docs/ARCHITECTURE.md` is updated if live inspection confirms that it owns the persisted-message-to-artifact data flow;
* README documents configuration, migration, CLI use, and current manual boundary;
* `.env.example` documents `KNOWLEDGE_BASE_PATH`;
* the next live-confirmed durable decision records deterministic artifact and reconciliation rules;
* `docs/CURRENT_STATE.md` reflects verified behavior;
* Task 006 is marked completed only after verification and contains appended completion evidence;
* `docs/TELEGRAM_INGESTION.md` remains unchanged;
* project workflow documentation remains unchanged unless a concrete workflow defect is discovered separately.

### Regression and scope protection

* focused tests pass;
* migration tests pass;
* complete authoritative suite passes;
* `/health` and `/ready` still work;
* development database isolation remains intact;
* no automatic Telegram processing exists;
* no worker or queue exists;
* no AI behavior exists;
* no artifact Git commit or push exists;
* no generated test or verification note remains in the repository working tree;
* `git diff --check` passes.

## Required verification commands

## Initial Git state

```bash
git branch --show-current
git rev-parse HEAD
git status --short
git log --oneline --decorate -10
git diff --check
```

Confirm Task 006 numbering and committed contract:

```bash
find tasks -maxdepth 1 -type f -name '*.md' -print | sort
git ls-tree -r --name-only HEAD -- tasks/
git show HEAD:tasks/006-deterministic-markdown-artifacts.md \
  > /tmp/task006-contract-from-head.md
test -s /tmp/task006-contract-from-head.md
```

The `git show` command is expected to succeed only after the accepted Task 006 specification has been committed separately.

## Repository inspection

```bash
find app app/db app/knowledge alembic tests docs -maxdepth 3 -type f -print | sort
sed -n '1,260p' app/settings.py
sed -n '1,360p' app/db/models.py
sed -n '1,260p' app/db/session.py
sed -n '1,320p' tests/conftest.py
sed -n '1,260p' docker-compose.yml
sed -n '1,220p' .env.example
grep -n '^## D-' docs/DECISIONS.md | tail -10
```

Adapt filenames only when the repository uses different confirmed paths.

## Compose and development schema

```bash
docker compose config --quiet
docker compose up -d --build
docker compose exec app alembic upgrade head
docker compose exec app alembic current
```

Verify health and readiness:

```bash
curl --retry 5 --retry-all-errors --retry-delay 1 \
  http://localhost:8000/health

curl --retry 5 --retry-all-errors --retry-delay 1 \
  http://localhost:8000/ready
```

## Migration rollback and re-upgrade

Run the migration round trip only against the isolated test database:

```bash
docker compose exec app sh -lc '
  DATABASE_URL="$TEST_DATABASE_URL" alembic upgrade head &&
  DATABASE_URL="$TEST_DATABASE_URL" alembic downgrade -1 &&
  DATABASE_URL="$TEST_DATABASE_URL" alembic upgrade head
'
```

Codex must confirm from live revision history that `-1` targets only the Task 006 Artifact migration.

If repository inspection shows that the shared test database cannot safely support this direct command, implement and run an isolated migration test that creates a disposable database, performs the exact upgrade/downgrade/re-upgrade sequence, and drops only that disposable database afterward.

Do not run Task 006 downgrade verification against the development database.

## Focused tests

Preferred focused commands:

```bash
docker compose exec app python -m pytest \
  tests/test_markdown_artifacts.py \
  tests/test_artifact_processing.py \
  tests/test_knowledge_cli.py
```

If migration tests are in a separate file:

```bash
docker compose exec app python -m pytest tests/test_migrations.py -k artifact
```

If live repository conventions produce different focused filenames, Codex must report the final exact commands.

## Full regression suite

```bash
docker compose exec app python -m pytest
```

## CLI verification

Show help without processing:

```bash
docker compose exec app python -m app.knowledge.cli --help
```

Run the end-to-end CLI verification against an isolated database row and a temporary knowledge-base root outside the repository.

Preferred boundary:

```bash
docker compose exec app sh -lc '
  DATABASE_URL="$TEST_DATABASE_URL" \
  KNOWLEDGE_BASE_PATH=/tmp/task006-cli-kb \
  python -m app.knowledge.cli --message-id "<isolated-test-message-uuid>"
'
```

Codex must provide the exact safe setup command used to create the disposable test message and the exact cleanup command used afterward.

The CLI verification must not:

* process a development message that must be preserved;
* leave an Artifact or fixture Message in the development database;
* leave a generated note under the repository’s `knowledge-base/`;
* contact Telegram.

Verify the printed path exists under the temporary root and contains the exact expected bytes.

## Host-visible mount verification

If Task 006 adds or relies on a Compose bind mount, verify it without leaving a repository change.

A permissible temporary check is:

```bash
rm -f knowledge-base/.task006-mount-check
docker compose exec app sh -lc '
  touch "${KNOWLEDGE_BASE_PATH:-knowledge-base}/.task006-mount-check"
'
test -f knowledge-base/.task006-mount-check
rm -f knowledge-base/.task006-mount-check
```

Adapt the container path to the verified Compose configuration.

The check must leave no marker file.

## Test-isolation verification

Before the complete pytest run, record development counts for:

```text
users
messages
artifacts
```

Run the complete suite, then repeat the counts.

Existing development rows and artifacts must remain unchanged.

The exact PostgreSQL commands must follow live Compose credentials and be included in the completion report.

## Repository cleanliness after tests

Confirm that tests and CLI verification did not write into the real knowledge base:

```bash
git status --short
find knowledge-base -maxdepth 3 -type f -print | sort
```

Any pre-existing tracked knowledge-base placeholders must be distinguished from generated notes.

No Task 006 test artifact may remain.

## Final application and migration checks

```bash
docker compose exec app alembic current
docker compose exec app python -m pytest
curl --retry 5 --retry-all-errors --retry-delay 1 \
  http://localhost:8000/health
curl --retry 5 --retry-all-errors --retry-delay 1 \
  http://localhost:8000/ready
git diff --check
```

## Completion report

After implementation, verification, and documentation updates, create:

```text
/tmp/task006-handoff.md
```

The report must follow the completion-report requirements below.

## Review-bundle generation

Generate a candidate bundle:

```bash
python3 scripts/review_bundle.py \
  --task tasks/006-deterministic-markdown-artifacts.md \
  --report /tmp/task006-handoff.md \
  > /tmp/task006-review-bundle-candidate.md
```

Inspect it and record the result in the completion report.

Then regenerate the finalized report and final bundle:

```bash
python3 scripts/review_bundle.py \
  --task tasks/006-deterministic-markdown-artifacts.md \
  --report /tmp/task006-handoff.md \
  > /tmp/task006-review-bundle.md
```

Verify:

```bash
test -s /tmp/task006-review-bundle.md
grep -F '# Implementation Review Bundle' \
  /tmp/task006-review-bundle.md
grep -F 'HEAD:tasks/006-deterministic-markdown-artifacts.md' \
  /tmp/task006-review-bundle.md
grep -F '## Completion report' \
  /tmp/task006-review-bundle.md
grep -F '## Tracked working-tree diff against HEAD' \
  /tmp/task006-review-bundle.md
grep -F '## Untracked file contents' \
  /tmp/task006-review-bundle.md
```

After final bundle generation, do not modify:

* implementation files;
* migrations;
* tests;
* documentation;
* Task 006 completion evidence;
* `/tmp/task006-handoff.md`.

Any change requires regenerating the bundle.

## Final Git checks

```bash
git diff --check
git status --short
git diff --stat
git diff -- \
  app/ \
  alembic/ \
  tests/ \
  docker-compose.yml \
  .env.example \
  README.md \
  docs/ARCHITECTURE.md \
  docs/DATA_MODEL.md \
  docs/MARKDOWN_ARTIFACTS.md \
  docs/CURRENT_STATE.md \
  docs/DECISIONS.md \
  tasks/006-deterministic-markdown-artifacts.md
```

Adapt the Compose filename and exact migration/test paths to verified repository conventions.

## Documentation impact

### Required updates

#### `docs/DATA_MODEL.md`

Update it to describe the now-implemented minimal `Artifact` entity:

```text
id
message_id
artifact_type
title
slug
file_path
created_at
updated_at
```

Document:

* foreign key;
* uniqueness constraints;
* `artifact_type = "note"` processing support;
* relative path ownership;
* PostgreSQL as operational metadata;
* Markdown file as human-readable artifact;
* postponed fields and entities.

Remove or revise wording that says artifacts are not implemented.

#### `docs/MARKDOWN_ARTIFACTS.md`

Create this focused contract document.

It must describe:

* source-message eligibility;
* title algorithm;
* slug algorithm;
* path algorithm;
* timestamp format;
* exact frontmatter order;
* quoting rules;
* body and final-newline behavior;
* format version;
* deterministic bytes;
* storage-root safety;
* atomic no-replace publication;
* complete reconciliation matrix;
* concurrency;
* PostgreSQL/filesystem failure recovery;
* status transition;
* manual CLI boundary;
* postponed automatic processing and Git behavior.

#### `README.md`

Document:

* `KNOWLEDGE_BASE_PATH`;
* migration command;
* manual processing command;
* expected CLI output;
* the fact that processing is not automatic;
* the fact that Telegram acknowledgement remains persistence-only;
* host-visible local knowledge-base behavior;
* no automatic Git commit.

#### `.env.example`

Add:

```text
KNOWLEDGE_BASE_PATH=knowledge-base
```

Use no real machine path.

#### `docs/CURRENT_STATE.md`

After verification, record:

* deterministic text-note generation is implemented;

* Artifact persistence is implemented;

* manual one-message CLI is implemented;

* successful data flow:

  ```text
  persisted text Message
  → deterministic Markdown note
  → Artifact row
  → Message status done
  ```

* automatic processing remains unimplemented;

* queue and worker remain unimplemented;

* Git-backed artifact commits remain unimplemented;

* final test and migration verification facts;

* active task becomes `none selected` unless the user explicitly selects another task.

Do not invent Task 007.

#### `docs/DECISIONS.md`

Add the next live-confirmed decision, expected to be D-025.

It must establish:

* Markdown notes are rendered deterministically in application code;
* `format_version = 1`;
* artifact paths use UTC source date and full source-message UUID;
* Artifact rows store operational metadata and relative paths;
* title and slug do not determine file identity;
* source-message row locking plus database uniqueness protects idempotency;
* files publish atomically without overwrite;
* exact orphan files are preserved and reconciled after database failure;
* conflicting files and inconsistent rows fail rather than being replaced;
* Message becomes `done` only when row and exact file both exist;
* Task 006 remains manually invoked and does not add queue or worker behavior.

#### Task 006 file

After successful verification:

* change status from `planned` to `completed`;
* append concise completion evidence;
* do not rewrite the accepted requirements.

### Conditional update

#### `docs/ARCHITECTURE.md`

Update when live inspection confirms that it describes current processing data flow or component responsibility.

The expected architectural addition is:

```text
manual CLI
→ reusable processing function
→ locked Message
→ deterministic filesystem note
→ Artifact row
→ Message done
```

Document that:

* the application process currently invokes this manually;
* future workers may reuse the function;
* no worker or queue is implemented;
* filesystem and PostgreSQL have reconciliation rather than a distributed transaction.

If the architecture document deliberately excludes feature-level flows, report why it was left unchanged.

### Expected unchanged documents

Unless live evidence reveals a contradiction:

* `docs/TELEGRAM_INGESTION.md`;
* `docs/PROJECT_BRIEF.md`;
* `docs/WORKFLOW.md`;
* `AGENTS.md`;
* Task 004 and Task 005 implementation tooling documentation.

## Completion-report requirements

Codex must create `/tmp/task006-handoff.md` with exactly these sections.

### 1. Initial repository state

Report:

* branch;
* starting HEAD;
* starting working-tree status;
* recent relevant commits;
* confirmation that Task 005 was committed;
* confirmation that the Task 006 specification existed at `HEAD`;
* contradictions found between snapshots and the live repository.

### 2. Implementation plan followed

Summarize:

* planned model and migration;
* rendering modules;
* processing boundary;
* storage approach;
* CLI;
* tests;
* documentation;
* any justified deviation.

### 3. Repository inspection findings

Report:

* confirmed Task 006 filename;
* current Alembic head and selected revision;
* current model/session conventions;
* current test-cleanup behavior;
* current knowledge-base directory and Compose mount;
* container working directory and permissions;
* selected atomic no-replace primitive;
* next durable decision number;
* whether architecture documentation required an update.

### 4. Files changed

List every changed and new file with one sentence describing its purpose.

List important inspected files intentionally left unchanged, including Telegram ingestion documentation.

### 5. Data model and migration

Report:

* final Artifact fields and types;
* foreign key;
* constraint names and behavior;
* migration revision;
* upgrade behavior;
* downgrade behavior;
* isolated migration round-trip result;
* confirmation that users and messages survived rollback verification.

### 6. Rendering contract

Report:

* title algorithm;
* slug algorithm;
* path format;
* timestamp format;
* YAML quoting;
* key order;
* body normalization;
* final-newline rule;
* format version;
* golden-test coverage.

### 7. Processing and reconciliation

Report:

* final function signature and module;
* transaction ownership;
* source-message lock;
* duplicate-race handling;
* each reconciliation matrix outcome;
* Message status boundary;
* invalid metadata handling;
* exact-file recovery;
* missing-file recovery.

### 8. Filesystem safety and recovery

Report:

* root resolution and containment;
* existing-entry classification;
* temporary-file behavior;
* atomic no-replace publication;
* concurrent final-path handling;
* cleanup behavior;
* database-failure-after-publication behavior;
* filesystem limitations.

### 9. CLI and configuration

Report:

* final command;
* exact output;
* `KNOWLEDGE_BASE_PATH` behavior;
* Compose mount changes or confirmation that none were needed;
* isolated CLI verification command and result;
* confirmation that no Telegram request occurred.

### 10. Tests and verification results

For every required command, provide:

* exact command;
* passed, failed, or not run;
* relevant output.

Include:

* migration upgrade;
* migration downgrade and re-upgrade;
* focused rendering tests;
* focused processing tests;
* concurrency tests;
* failure-injection tests;
* CLI tests;
* complete pytest result;
* development database counts before and after pytest;
* knowledge-base cleanliness;
* `/health`;
* `/ready`;
* `git diff --check`;
* candidate and final review-bundle generation.

### 11. Documentation updates

State:

* what changed in the data model;
* the new Markdown contract document;
* whether architecture changed;
* README changes;
* `.env.example` change;
* D-025 or the live-confirmed decision;
* current-state update;
* Task 006 completion evidence;
* documents intentionally left unchanged.

### 12. Acceptance-criteria assessment

Evaluate these groups as:

```text
passed
failed
not verified
```

Groups:

* schema;
* deterministic rendering;
* path and storage safety;
* processing behavior;
* status behavior;
* failure recovery;
* CLI;
* configuration and infrastructure;
* documentation;
* regression and scope protection.

Explain every failed or unverified item.

### 13. Scope, deviations, and remaining risks

Report:

* all out-of-scope functionality avoided;
* any unavoidable deviation;
* source-message mutability limitation;
* atomic-publication filesystem assumptions;
* anything not verified;
* future queue/worker work explicitly not implemented.

### 14. Final Git boundary

Report:

* final branch;
* final HEAD;
* final `git status --short`;
* final `git diff --stat`;
* all changed and untracked paths;
* whether a commit was created;
* recommended implementation commit message;
* final review-bundle path.

Unless explicitly instructed otherwise, state:

```text
No implementation commit was created.
```

The report must distinguish:

* requirements from the committed Task 006 contract;
* Git evidence captured by the review bundle;
* verification claims supplied by Codex.

## Expected commit boundary

The accepted Task 006 specification must be committed separately before implementation.

After implementation review and bounded corrections, the Task 006 implementation commit should include only:

* minimal Artifact model changes;
* one Artifact migration;
* knowledge-base setting;
* the smallest required Compose mount or environment change;
* deterministic rendering code;
* safe storage code;
* one-message processing function;
* one-message CLI;
* focused and integration tests;
* test fixture cleanup changes;
* data-model documentation;
* Markdown-artifact contract documentation;
* architecture update when applicable;
* README and `.env.example`;
* durable decision;
* current-state update;
* Task 006 completion status and evidence.

It must not include:

* generated note files from tests or verification;
* temporary files;
* completion reports;
* review bundles;
* development database dumps;
* Telegram changes;
* queue or worker code;
* AI code;
* Git artifact automation;
* unrelated refactoring;
* Task 007 planning.

Suggested implementation commit message:

```text
feat: generate deterministic Markdown notes
```

Codex must not create the implementation commit unless explicitly instructed.

## Amendment — Task 005 review packaging correction

Accepted on 2026-07-02 after the review-packaging conflict was confirmed.
Task 006 retains its requirement to document `KNOWLEDGE_BASE_PATH` in the
committed root `.env.example` template. The user explicitly authorized a
separate, narrowly scoped Task 005 tooling correction so that this exact
tracked-at-HEAD template can be captured without making `.env.example`
generally non-secret-like.

The correction is limited to `scripts/review_bundle.py`,
`tests/test_review_bundle.py`, the appended Task 005 amendment, and the D-024
clarification. Application, database, migration, Telegram, Markdown rendering,
storage, processing, and CLI behavior remain outside the correction boundary.
