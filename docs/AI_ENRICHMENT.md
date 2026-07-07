# Manual AI Enrichment

Task 013 adds one explicit developer command for enriching an existing
completed text Message. It is not automatic orchestration.

## Source Boundary

The input must already have:

* `Message.input_type = "text"`;
* non-null `raw_text`;
* `Message.status = "done"`;
* one raw `artifact_type = "note"` Artifact for the Message;
* exact raw note metadata and exact raw note file bytes.

The provider input is exactly:

```python
normalize_newlines(message.raw_text).rstrip("\n")
```

The raw Markdown frontmatter, raw note heading, Telegram IDs, database IDs, and
Git metadata are not sent. The canonical source must contain non-whitespace
text and fit within 65,536 UTF-8 bytes. Its SHA-256 is persisted as
`source_content_sha256`.

## Schema And Prompt

Schema version 1 contains:

```text
title
summary
key_points
tags
action_items
```

The Pydantic model is strict, immutable after validation, and rejects extra
fields. Text fields normalize newlines and Unicode whitespace to one ASCII
space; required scalars and list items cannot be empty or contain NUL. Lists
are bounded to 12 items and deduplicated by Unicode NFKC plus casefold while
preserving first normalized display values. Tags preserve human-readable
Unicode after NFKC normalization, optional leading `#` removal, and whitespace
collapse.

Prompt version 1 is repository-owned and separates authority from source data:
OpenAI receives the instruction as `instructions` and the canonical source as
`input`.

## Provider Boundary

The domain depends on a provider-neutral protocol:

```text
source_text -> ProviderEnrichmentResult
```

The result contains only provider name, accepted model, optional response ID,
and the validated `EnrichmentResult`. Domain, persistence, and rendering code
do not import OpenAI SDK response objects.

The Task 013 adapter uses the official OpenAI Python SDK with
`AsyncOpenAI(max_retries=0, timeout=60.0)` and one Responses `parse(...)`
request:

```text
text_format = EnrichmentResult
store = false
max_output_tokens = 2000
```

It does not use streaming, background mode, conversations,
`previous_response_id`, tools, function calling, metadata, or user identifiers.
OpenAI SDK exceptions are translated by type into provider-neutral
authentication, permission, invalid-request, refusal, incomplete, rate-limit,
connection, timeout, server, response, or operational failures. Raw provider
messages, source text, and keys are not copied into local errors.

## Transactions And Concurrency

Enrichment has two phases.

Phase 1 validates the current source and checks for an existing accepted row. If
none exists, the database session is closed before the provider request. After
the provider returns, a new transaction locks the Message, revalidates the same
raw Artifact/file and source digest, and inserts at most one `AIEnrichment`.

Concurrent invocations may both call OpenAI. The post-provider lock and
`UNIQUE(message_id)` constraint ensure only one accepted row. Losing callers
discard their provider result and continue from the accepted winner.

Phase 2 never calls the provider. It locks the accepted enrichment, revalidates
the source and stored JSON, renders deterministic Markdown, and establishes one
`enriched_note` Artifact/file. If the enrichment was committed but local
materialization failed, rerunning uses the accepted row without credentials.

## Markdown Output

Enriched Markdown is format version 1 and is written under:

```text
processed/YYYY-MM-DD--<message-uuid>.md
```

The date is the source Message UTC date. The path does not depend on title,
model, response ID, enrichment ID, or current time. The renderer uses only
snapshotted Message and AIEnrichment fields plus the normalized result.

The raw note under `inbox/` is not modified. Enriched Artifacts are not
published to Git by Task 011 or Task 012.

## CLI

Run one manual enrichment from the app container:

```bash
docker compose exec app \
  python -m app.knowledge.ai_cli \
  --message-id <canonical-message-uuid>
```

For a new provider request, set both `OPENAI_API_KEY` and `OPENAI_MODEL` in the
app environment. Startup, `/health`, `/ready`, the worker, and existing-row
reconciliation do not require either value.

Success prints:

```text
message_id: <message-uuid>
source_artifact_id: <raw-artifact-uuid>
ai_enrichment_id: <ai-enrichment-uuid>
enriched_artifact_id: <enriched-artifact-uuid>
file_path: <processed-relative-path>
provider: <provider>
model: <accepted-model>
outcome: created|reconciled|existing
```

Expected domain failures print a bounded safe reason to stderr and exit `1`.
Invalid arguments remain argparse exit `2`.

## Limitations

Task 013 does not implement automatic ProcessingTasks, worker integration,
Telegram commands, regeneration, replacement, history, provider routing,
fallback providers, usage/cost tracking, embeddings, RAG, remote Git
synchronization, or enriched Git publication. Provider output is structurally
validated but not independently fact-checked.
