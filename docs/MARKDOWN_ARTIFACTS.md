# Deterministic Markdown Artifacts

## Processing boundary

The manual command processes exactly one existing message UUID:

```text
persisted text Message
→ deterministic Markdown note
→ Artifact row
→ Message status done
```

The source must have `input_type = "text"`, non-null NUL-free `raw_text`, a
timezone-aware `created_at`, and integer Telegram chat and message identifiers.
The accepted starting statuses are `received` and `done`; status alone never
proves consistency.

## Deterministic metadata

Source newlines are normalized from CRLF and CR to LF.

The title is the first line with a non-whitespace Unicode character, stripped
at both ends, with each internal Unicode-whitespace run replaced by one ASCII
space, then truncated to 80 Unicode code points. There is no ellipsis. A
whitespace-only source produces `Untitled note`.

The slug applies Unicode NFKC and casefold to the final title, retains Unicode
alphanumeric characters, converts every other run to one hyphen, trims
hyphens, truncates to 80 code points, and removes a trailing truncation hyphen.
An empty result becomes `note`. It is not transliterated and is not unique.

The relative path is independent of title and slug:

```text
inbox/YYYY-MM-DD--<canonical-full-message-uuid>.md
```

The date comes from `Message.created_at` converted to UTC. `captured_at` is also
source-derived UTC and always uses `YYYY-MM-DDTHH:MM:SS.ffffffZ`.

## Format version 1

Frontmatter fields have this exact order:

```yaml
---
format_version: 1
artifact_type: "note"
source: "telegram"
source_message_id: "<application-message-uuid>"
telegram_chat_id: 123
telegram_message_id: 456
captured_at: "<UTC timestamp>"
title: "<derived title>"
slug: "<derived slug>"
tags: []
topics: []
---
```

Every string scalar uses standard-library JSON-compatible double quoting with
non-ASCII text preserved. Telegram IDs and format version are unquoted base-10
integers. Tags and topics are fixed empty arrays and are not persisted in
PostgreSQL.

The body is:

```markdown
# <derived title>

<newline-normalized original text>
```

Leading whitespace and ordinary trailing spaces are preserved. Only source
newlines are normalized; all trailing LF characters are removed before the
complete UTF-8 file receives exactly one final LF. No current clock, Artifact
UUID, profile field, summary, or AI-generated value affects the bytes.

## Filesystem safety and publication

The configured root is resolved to an absolute normalized path. The processor
derives the relative path only from trusted source date and UUID values,
rejects unsafe components, confirms the destination parent is a real directory
inside the root, and inspects the final entry without following a symlink.

The expected path is classified as:

* `absent` — no entry;
* `exact` — regular file with byte-identical content;
* `conflicting` — regular file with different bytes;
* `unsupported` — symlink, directory, FIFO, socket, device, or other entry.

Conflicting and unsupported entries are preserved and cause failure. For an
absent path, the code exclusively creates a unique same-directory temporary
file, writes and fsyncs all bytes, and hard-links it to the final name. The
hard link is atomic and cannot replace an existing name on the supported
Linux/Docker filesystems. A concurrently appearing final entry is accepted
only if its bytes are exact. Handled paths clean the temporary name; an abrupt
process termination is outside that `finally` guarantee.

## Reconciliation matrix

| Artifact row | Expected file | Result |
|---|---|---|
| absent | absent | publish file, insert row, set `done` |
| absent | exact | retain file, insert row, set `done` |
| absent | conflicting/unsupported | fail without changes |
| valid | absent | recreate file, retain row identity, set `done` if needed |
| valid | exact | retain both; set `done` only if needed |
| valid | conflicting/unsupported | fail without changes |
| inconsistent | any | fail before file publication |
| expected path owned by another row | any | fail before file publication |

A valid row must match source message ID, type `note`, derived title and slug,
and expected relative path. Inconsistent metadata is never silently updated.

The processor locks only the source Message with PostgreSQL `FOR UPDATE`.
Database uniqueness on `(message_id, artifact_type)` and `file_path` is the
final duplicate protection. An expected uniqueness race gets at most one fresh
transaction reconciliation attempt; unrelated integrity failures propagate.

## PostgreSQL/filesystem recovery

There is no distributed transaction. The exact file is established before a
new Artifact transaction commits. If database flush or commit then fails, the
database rolls back, the previous Message status remains, and the exact orphan
file stays. A later explicit invocation recognizes it and creates the missing
row. The same rule preserves a recreated file if a later status commit fails.

Filesystem failure rolls back pending database changes. Exact files are never
deleted as compensation. Conflicts require manual investigation outside the
command.

Task 006 renders the current persisted source fields. It does not add source
versioning or immutability; manual source mutation after generation can produce
a metadata or byte conflict and is not repaired automatically.

## Manual command

```bash
python3 -m app.knowledge.cli --message-id <uuid>
```

Success prints the stable Artifact ID and relative path. The command loads the
normal database and `KNOWLEDGE_BASE_PATH` settings but does not start Telegram,
FastAPI, polling, a queue, or a worker. Processing is not automatic, and no Git
commit is created.

## Separate Git publication

Task 011 consumes an already valid Artifact and its exact established file.
It reruns the Task 006 renderer only to calculate validation bytes; it does not
rerender, recreate, repair, or change the Markdown file, Artifact metadata, or
Message status. Task 006 paths and format-version-1 bytes remain unchanged.

Publication is manually invoked by Artifact UUID after Task 006 processing and
is never called automatically by ingestion or the worker. Its repository,
index, commit, idempotency, and PostgreSQL/Git recovery rules are documented in
`docs/GIT_PUBLICATION.md`.
