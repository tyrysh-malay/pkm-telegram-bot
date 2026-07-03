# Task 008: Restrict Telegram ingestion to the configured personal owner

**Status:** completed
**Depends on:** Tasks 000–007
**Target file:** `tasks/008-restrict-telegram-ingestion-owner.md`
**Expected commit boundary:** one reviewable implementation commit containing the minimal Telegram-owner configuration, early authorization boundary, focused tests, and verified documentation changes required by this task; the accepted task specification must be committed before implementation, and Codex must not commit implementation changes unless explicitly instructed

## Goal

Restrict all currently supported Telegram command and ordinary-text behavior to explicitly configured Telegram sender user IDs operating in private chats.

The accepted authorization boundary is:

```text
private Telegram message update
+ usable sender metadata
+ sender Telegram user ID in configured allowlist
→ existing handler behavior

anything else
→ silently reject before persistence or response
```

This task establishes the bot as a controlled personal-ingestion boundary without introducing database-backed permissions, administration features, or broader authentication infrastructure.

## Confirmed current boundary

The user has confirmed:

* Tasks 000–007 are complete.

* Task 007 established the automatic text-processing flow:

  ```text
  Telegram text
  → User + Message + ProcessingTask committed atomically
  → app dispatcher
  → Redis/Dramatiq
  → worker
  → existing process_text_message(...)
  → exact Markdown note + Artifact
  → Message done
  → ProcessingTask succeeded
  ```

* PostgreSQL owns operational and orchestration state.

* Redis is delivery transport only.

* Task 006 remains the sole implementation of:

  * deterministic Markdown rendering;
  * filesystem publication;
  * Artifact reconciliation;
  * source-Message locking;
  * successful `Message.status = "done"` behavior.

* Task 007 added one durable `generate_note` ProcessingTask for each newly inserted Telegram text Message.

* User, Message, and ProcessingTask creation occur in one PostgreSQL transaction.

* Telegram acknowledgement remains exactly:

  ```text
  Saved for processing.
  ```

* Duplicate Telegram delivery remains idempotent and establishes one Message and one ProcessingTask.

* The bot is intended to be personal.

* No confirmed Telegram sender allowlist currently protects the Telegram handlers.

* Until Task 008 is implemented, live Telegram operation remains suitable only for controlled use.

* Telegram sender identity, chat identity, and message identity are distinct concepts.

* User authorization must use the sender’s Telegram user ID rather than the Telegram chat ID or mutable profile fields.

* Completion reports, context reports, committed-contract copies, and review bundles must use a user-owned repository-external directory such as:

  ```text
  ~/pkm-handoffs/
  ```

* `/tmp` must not be used for project workflow artifacts.

Uploaded documents and bundles are point-in-time evidence. Codex must verify all repository-specific facts against the live repository before editing.

## Repository verification requirements

Before editing, Codex must inspect the live repository and report the results.

### Fresh repository context and Git state

Create the external workflow directory and generate a fresh context report:

```bash
mkdir -p "$HOME/pkm-handoffs"

python3 scripts/project_context.py \
  > "$HOME/pkm-handoffs/task008-context.md"
```

Then run:

```bash
git branch --show-current
git rev-parse HEAD
git status --short
git log --oneline --decorate -10
git diff --stat
git diff --check
```

Verify:

* the Task 007 implementation and any review corrections are committed;
* the working tree is clean before Task 008 implementation;
* Task 007 is marked completed according to repository conventions;
* no Task 008 file or later conflicting task already exists;
* `tasks/008-restrict-telegram-ingestion-owner.md` is the next repository-consistent filename;
* no later architecture or durable decision conflicts with this task;
* the accepted Task 008 specification is committed at `HEAD` before implementation begins.

After the accepted specification has been committed, capture the committed review contract outside the repository:

```bash
git show HEAD:tasks/008-restrict-telegram-ingestion-owner.md \
  > "$HOME/pkm-handoffs/task008-contract-from-head.md"
```

If the live repository uses another Task 008 filename or contains a conflicting Task 008 contract, Codex must report the contradiction before editing. It must not silently rename or rewrite the accepted specification.

### Settings and configuration

Inspect:

* `app/settings.py`;

* the existing Pydantic settings conventions;

* current cross-field or runtime validation for:

  * `TELEGRAM_BOT_ENABLED`;
  * `TELEGRAM_BOT_TOKEN`;

* how empty environment values are represented;

* how settings are cached;

* when settings are loaded during application import and lifespan startup;

* `.env.example`;

* the app service environment in Docker Compose;

* whether the worker process imports the shared application settings;

* existing configuration tests, if any.

Determine:

* the exact current token-validation boundary;
* whether Telegram configuration failure currently occurs during settings creation or Telegram runtime construction;
* the smallest consistent place to validate the relationship among Telegram enablement, token, and allowed user IDs;
* how a collection of numeric IDs can be represented without a custom general-purpose configuration framework.

Configuration validation must not contact Telegram, Redis, PostgreSQL, or another external service.

### Telegram runtime and routing

Inspect:

* Telegram Bot construction;
* Dispatcher construction;
* Router construction;
* router inclusion order;
* handler registration order;
* any router-level filters or middlewares;
* application lifespan startup and shutdown;
* polling enablement and disabled-mode behavior.

Identify the earliest small aiogram boundary that can reject a message update before any existing command or ordinary-text handler runs.

Codex must determine whether the strongest repository-consistent implementation is:

* a router-level message filter;
* an outer router middleware;
* a dispatcher-level middleware;
* another equivalently small aiogram routing boundary.

The implementation must cover every currently registered Telegram message handler. A guard duplicated separately inside each handler is not preferred unless live repository structure makes one shared routing boundary impossible.

### Existing handlers

Inspect:

* `/start` handler;
* ordinary text handler;
* any fallback or other command handlers;
* current handler filters;
* acknowledgement code;
* error handling;
* logging;
* all calls made before persistence;
* all current response paths.

Confirm:

* the exact current `/start` response;
* whether `/start` currently touches the database;
* where sender metadata is read;
* where chat metadata and chat type are available;
* whether ordinary text persistence begins directly in the handler or in an ingestion function;
* that authorization can occur before the ingestion input object is persisted;
* that rejected updates can finish without an API reply.

### Ingestion and Task 007 boundary

Inspect:

* the Telegram ingestion input structure;
* User create/update logic;
* Message insertion;
* ProcessingTask insertion;
* transaction ownership;
* duplicate handling;
* acknowledgement timing;
* Redis/Dramatiq separation;
* Task 007 ingestion tests.

Confirm:

* authorization can happen before the ingestion function is called;
* rejected updates cannot create or mutate a User;
* rejected updates cannot insert a Message;
* rejected updates cannot insert a ProcessingTask;
* no handler directly contacts Redis;
* only committed ProcessingTask rows become eligible for dispatch;
* allowed ordinary text retains the existing atomic transaction and exact acknowledgement.

### Telegram identity and aiogram test fixtures

Inspect:

* existing constructed aiogram `Message`, `User`, `Chat`, and `Update` fixtures;
* current chat-type values and enum usage;
* current handler tests;
* Telegram identity tests;
* tests that distinguish sender ID from chat ID;
* tests for missing `from_user`;
* tests for group or channel messages;
* whether the test suite currently feeds updates through the real Dispatcher/Router boundary or invokes handlers directly.

Determine the smallest fixture extension that proves authorization occurs at the routing boundary rather than only inside persistence code.

### Current runtime and downstream flow

Inspect:

* TaskDispatcher runtime;
* ProcessingTask dispatcher tests;
* Dramatiq actor and worker tests;
* Task 006 artifact-processing tests;
* the existing end-to-end Task 007 test or smoke path;
* `docker-compose.yml`;
* `/health` and `/ready`.

Confirm:

* Task 008 requires no dispatcher change;
* Task 008 requires no worker change;
* Task 008 requires no migration;
* existing pending, queued, running, retrying, succeeded, and failed ProcessingTask rows remain governed solely by Task 007;
* already persisted messages and tasks are not retrospectively authorized or removed;
* authorization is evaluated only when a Telegram update attempts to enter the ingestion boundary.

### Documentation and durable decisions

Read:

* `AGENTS.md`;
* `docs/WORKFLOW.md`;
* `tasks/TEMPLATE.md`;
* `docs/CURRENT_STATE.md`;
* `docs/DECISIONS.md`;
* `docs/ARCHITECTURE.md`;
* `docs/DATA_MODEL.md`;
* `docs/TELEGRAM_INGESTION.md`;
* `docs/MARKDOWN_ARTIFACTS.md`;
* `docs/PROJECT_BRIEF.md`;
* `README.md`;
* `.env.example`;
* `tasks/007-durable-background-processing.md`.

Verify:

* the next available durable decision identifier, expected to be D-027 after live confirmation;
* whether the architecture document explicitly shows the Telegram trust boundary;
* whether older documentation still says user allowlisting is postponed;
* whether any documentation still recommends controlled-only operation because no allowlist exists;
* whether Task 007 documentation requires only wording adjustments and no orchestration changes.

Any material contradiction must be reported before implementation. It must not be concealed by rewriting this task after implementation exists.

## Problem or motivation

The current Telegram boundary accepts supported messages based on their content and handler routing, but does not establish that the sender is the intended personal owner.

This creates several risks:

* an unknown Telegram user may create a User row;
* an unknown user may create a Message;
* an unknown user may create a durable ProcessingTask;
* the dispatcher and worker may process unauthorized content;
* the bot may acknowledge storage to an unauthorized sender;
* a group member may cause knowledge ingestion even when the intended owner is present in the group;
* username or profile changes could be mistaken for stable identity if authorization is implemented incorrectly;
* a public or accidentally discovered bot username could expose the ingestion path.

The smallest security boundary is a configuration-backed allowlist of immutable Telegram sender user IDs combined with a strict private-chat requirement.

Authorization must occur before operational state is created. A post-persistence check would still allow unauthorized content into PostgreSQL and the processing pipeline and therefore would not satisfy the task.

## Scope

Implement the following bounded outcome:

1. add `TELEGRAM_ALLOWED_USER_IDS` through the existing settings mechanism;

2. define one exact environment representation for the allowlist;

3. validate that enabled Telegram polling has:

   * a usable bot token;
   * at least one valid allowed sender user ID;

4. preserve disabled-mode startup with an empty allowlist;

5. add one small shared Telegram authorization boundary;

6. require a usable `from_user.id`;

7. require `chat.type` to be private;

8. authorize only when the sender Telegram user ID is configured;

9. apply the authorization boundary before all current Telegram message handlers;

10. silently reject unauthorized or non-private updates;

11. preserve the existing `/start` behavior for an allowed private sender;

12. preserve the complete Task 007 ordinary-text flow for an allowed private sender;

13. add explicit identity, settings, routing, state-safety, and regression tests;

14. update configuration and relevant documentation;

15. add one durable authorization decision after behavior is verified;

16. produce the completion report and review bundle under `~/pkm-handoffs/` or another user-owned repository-external directory.

## Out of scope

Do not add:

* database tables;
* database columns;
* Alembic migrations;
* database-backed permissions;
* database-backed allowlists;
* user roles;
* capabilities;
* administrators;
* owner-management commands;
* allowlist-management commands;
* an HTTP administration endpoint;
* an HTTP authentication system;
* runtime allowlist editing;
* runtime configuration reload;
* filesystem-based dynamic configuration;
* Redis-backed authorization;
* chat-ID authorization;
* username authorization;
* first-name or last-name authorization;
* Message-ID authorization;
* authorization through existing mutable User rows;
* group-chat ingestion;
* supergroup ingestion;
* channel ingestion;
* sender-chat authorization;
* membership or administrator checks;
* Telegram completion or failure notifications;
* unauthorized or access-denied replies;
* rate limiting;
* webhook deployment;
* multiple polling replicas;
* changes to Message or ProcessingTask state machines;
* changes to Task 007 dispatching;
* changes to Task 007 leases;
* changes to Task 007 retries;
* changes to Task 007 worker claims or finalization;
* changes to Task 006 deterministic rendering;
* changes to Task 006 storage or reconciliation;
* AI processing;
* link extraction;
* voice, image, file, document, or PDF processing;
* Git commits or pushes for generated notes;
* a generic authentication framework;
* a generic authorization framework;
* an external identity provider;
* unrelated Telegram refactoring.

## Affected components

### Settings

Expected changes:

* add a typed `telegram_allowed_user_ids` setting;
* add cross-field validation with Telegram enablement and token configuration;
* document the environment representation.

No external connection may occur during validation.

### Telegram routing

Expected changes:

* add one narrowly scoped authorization filter, middleware, or equivalent;
* attach it early enough to protect `/start` and ordinary-text handlers;
* ensure no current message handler bypasses it.

### Telegram handlers

Expected behavior changes:

* allowed private senders retain existing behavior;
* unknown senders and non-private chats never enter handler behavior.

Handler business logic should otherwise remain unchanged.

### Persistence and processing

No persistence, dispatcher, broker, worker, Artifact, or knowledge-base implementation change is expected.

### Docker Compose

Expected change:

* forward `TELEGRAM_ALLOWED_USER_IDS` to the app service when Telegram polling is enabled.

The worker does not need the allowlist for task processing. If the shared Settings model is imported by the worker, its disabled Telegram defaults must permit the worker to start with an empty allowlist.

### Tests

Expected additions or changes:

* focused settings validation tests;
* authorization-boundary tests;
* `/start` routing tests;
* ordinary-text routing tests;
* state-absence tests for rejected updates;
* allowed-flow regression coverage;
* Task 007 and Task 006 regression coverage.

### Documentation

Expected verified updates:

* `.env.example`;
* `README.md`;
* `docs/TELEGRAM_INGESTION.md`;
* `docs/CURRENT_STATE.md`;
* `docs/DECISIONS.md`;
* `docs/ARCHITECTURE.md`;
* this task file.

### Components expected to remain unchanged

Unless live repository inspection proves a direct requirement, do not modify:

* database models;
* Alembic migrations;
* `docs/DATA_MODEL.md`;
* Task 006 knowledge modules;
* `docs/MARKDOWN_ARTIFACTS.md`;
* Task 007 dispatcher or worker modules;
* Task 007 ProcessingTask state transitions;
* Redis configuration or broker behavior;
* worker process configuration;
* `/health`;
* `/ready`;
* `docs/PROJECT_BRIEF.md`;
* `docs/WORKFLOW.md`;
* `AGENTS.md`;
* Task 004/005 workflow tooling;
* completed Task 007 requirements.

## Data, state, migration, and configuration impact

### Database and operational state

Expected database impact:

```text
none
```

Requirements:

* add no migration;
* add no table;
* add no column;
* add no constraint;
* modify no existing User, Message, Artifact, or ProcessingTask row during deployment;
* perform no backfill;
* delete no historical unauthorized-looking data;
* do not reevaluate existing ProcessingTasks;
* allow existing pending or leased tasks to continue through Task 007 normally.

Task 008 governs only whether a new Telegram update may enter the current handler and persistence boundary.

### Configuration variable

Add:

```text
TELEGRAM_ALLOWED_USER_IDS
```

Use the existing settings naming convention so that the environment variable maps to a setting equivalent to:

```python
telegram_allowed_user_ids: frozenset[int]
```

The exact internal collection type may follow stronger live conventions, but authorization must use immutable set semantics during runtime.

### Environment representation

Use a JSON array of numeric Telegram user IDs.

Examples:

```text
TELEGRAM_ALLOWED_USER_IDS=[]
```

```text
TELEGRAM_ALLOWED_USER_IDS=[123456789]
```

```text
TELEGRAM_ALLOWED_USER_IDS=[123456789,987654321]
```

Requirements:

* values are numeric JSON integers;
* quoted numeric strings are invalid;
* booleans are invalid;
* null is invalid;
* floats are invalid;
* zero is invalid;
* negative values are invalid;
* values larger than the positive signed 64-bit integer range are invalid;
* surrounding JSON whitespace is acceptable;
* duplicate IDs may be normalized to one set member and must not create duplicate behavior;
* ordering has no authorization meaning;
* an omitted variable behaves as an empty allowlist;
* an empty array is valid only when Telegram polling is disabled;
* malformed JSON fails configuration validation clearly.

Do not add a comma-splitting mini-language or support multiple environment syntaxes in this task.

### Enablement matrix

Required configuration semantics:

```text
TELEGRAM_BOT_ENABLED=false
TELEGRAM_ALLOWED_USER_IDS omitted or []
→ valid
```

```text
TELEGRAM_BOT_ENABLED=false
TELEGRAM_ALLOWED_USER_IDS contains valid IDs
→ valid, but no polling starts
```

```text
TELEGRAM_BOT_ENABLED=true
TELEGRAM_BOT_TOKEN missing or blank
→ invalid configuration
```

```text
TELEGRAM_BOT_ENABLED=true
TELEGRAM_ALLOWED_USER_IDS omitted or []
→ invalid configuration
```

```text
TELEGRAM_BOT_ENABLED=true
TELEGRAM_BOT_TOKEN usable
TELEGRAM_ALLOWED_USER_IDS contains at least one valid ID
→ valid
```

If both token and allowlist requirements are violated, the configuration failure may report both issues or one clear combined Telegram configuration error. It must not proceed to network startup.

### `.env.example`

The committed `.env.example` must include a safe empty value:

```text
TELEGRAM_ALLOWED_USER_IDS=[]
```

It may include a concise comment explaining that the value is a JSON array of numeric Telegram user IDs and is required when Telegram is enabled.

It must not contain:

* the owner’s real Telegram user ID;
* another real user’s ID;
* a real bot token;
* machine-specific secrets.

### Runtime immutability

The allowlist is loaded during normal application settings initialization.

Requirements:

* the running polling process uses the loaded allowlist for its lifetime;
* changing the environment or `.env` file has no effect until application restart;
* add no file watcher;
* add no signal-based reload;
* add no database refresh;
* add no Redis refresh;
* add no runtime mutation API.

## Behavioral requirements

### Authorization identity

Authorize only with:

```text
message.from_user.id
```

The ID must be compared numerically to the configured allowed user IDs.

Do not authorize with:

```text
message.chat.id
message.message_id
message.from_user.username
message.from_user.first_name
message.from_user.last_name
persisted User.username
persisted User.first_name
persisted User.last_name
persisted User.id
```

A previously persisted User row is not authorization evidence.

A sender whose mutable profile fields match an allowed user’s profile is not authorized unless their Telegram user ID is explicitly allowed.

An allowlisted user remains authorized after changing username, first name, or last name.

### Private-chat requirement

Require the incoming message’s chat type to be exactly Telegram private chat according to the installed aiogram version.

Reject:

```text
group
supergroup
channel
sender-chat or channel-post forms
missing chat type
unknown chat type
```

An allowlisted sender in a group or supergroup is rejected.

The presence of the owner in a group does not authorize another group member.

The use of a private-chat requirement is independent of sender-ID membership: both conditions must pass.

### Missing or malformed sender metadata

Reject when:

* `from_user` is absent;
* sender ID is absent;
* sender ID is not a usable integer;
* the update form does not represent a normal user-authored message suitable for the current handlers.

Rejection must fail closed.

Do not derive a sender ID from the chat ID when `from_user` is absent.

### Routing placement

Authorization must execute before:

* `/start` response generation;
* ordinary-text handler behavior;
* construction or use of persistence input that triggers database work;
* User lookup;
* User insertion;
* User profile update;
* Message lookup or insertion;
* ProcessingTask lookup or insertion;
* acknowledgement;
* Redis publication;
* Dramatiq actor delivery;
* Task 006 processing.

The authorization decision must not query PostgreSQL, Redis, or Telegram.

Preferred shape:

```text
aiogram message routing
→ private-owner authorization boundary
→ existing command/text filters and handlers
```

An equivalent ordering is acceptable when required by live aiogram conventions, but no unauthorized update may reach a side-effecting handler.

### Shared handler protection

The implementation must protect every currently registered Telegram message handler through one shared boundary where practical.

Requirements:

* `/start` cannot bypass authorization;
* ordinary text cannot bypass authorization;
* a current fallback message handler, if one exists, cannot bypass authorization;
* direct handler calls used only by tests must not be mistaken for proof that production routing is protected;
* tests must exercise the actual configured filter or middleware boundary.

Do not add unrelated command handlers merely to test the boundary.

### Rejected-update behavior

For an unknown sender, non-private chat, or missing sender metadata:

```text
no User creation
no User update
no Message creation
no ProcessingTask creation
no acknowledgement
no unauthorized response
no access-denied response
no Redis publication caused by the update
no worker processing caused by the update
```

Silent rejection means no Telegram API response is sent by the bot for that update.

The update may be dropped by returning from middleware, returning a false filter result, or another normal aiogram routing outcome.

Do not raise an expected authorization exception into the polling loop.

### Rejection logging

Logging rejected updates is optional but permitted.

When logging is implemented, use only concise sanitized fields such as:

```text
telegram_user_id
telegram_chat_id
chat_type
reason
```

Permitted stable reasons include equivalents of:

```text
missing_sender
non_private_chat
sender_not_allowed
```

Do not log:

* message text;
* command arguments;
* captions;
* bot token;
* database URL;
* Redis URL credentials;
* full settings;
* real allowlist contents as a startup dump.

The polling loop must remain alive after a rejected update.

### Allowed `/start` behavior

For an allowlisted sender in a private chat:

* `/start` reaches the existing handler;
* the exact existing response remains unchanged;
* `/start` is not persisted unless live current behavior already does so;
* no ProcessingTask is created for `/start` unless live current behavior already does so.

Task 008 must not redefine `/start`.

### Allowed ordinary-text behavior

For an allowlisted sender in a private chat, preserve the current Task 007 sequence:

```text
authorize
→ create or update User
→ insert Message when new
→ insert one pending generate_note ProcessingTask when new
→ commit atomically
→ send Saved for processing.
→ dispatcher publishes task UUID
→ worker calls unchanged Task 006 processing
→ exact Artifact and Markdown note
→ Message done
→ ProcessingTask succeeded
```

Requirements:

* User profile updates continue after authorization;

* Message fields remain unchanged;

* ProcessingTask initial values remain unchanged;

* transaction boundaries remain unchanged;

* duplicate behavior remains unchanged;

* acknowledgement remains exactly:

  ```text
  Saved for processing.
  ```

* acknowledgement still occurs only after durable PostgreSQL commit;

* Redis unavailability still does not roll back accepted ingestion;

* Task 006 remains the sole owner of artifact generation and `Message.status = "done"`.

### Duplicate allowed delivery

Repeated delivery of the same allowed private Telegram message must still produce:

```text
one User identity
one Message
one generate_note ProcessingTask
one Artifact after processing
one deterministic Markdown file
```

Authorization must run for every delivery before existing duplicate handling.

Removing an ID from configuration after the first accepted delivery means a later replay is rejected after restart. It must not acknowledge, mutate, or reprocess the existing row through the Telegram handler.

### Mutable profile fields

For an allowlisted sender:

* changed username, first name, or last name must not revoke access;
* existing User profile-update behavior remains active after authorization.

For an unknown sender:

* copying the owner’s username or names must not grant access;
* no User row may be created merely to evaluate authorization.

### Existing operational state

Task 008 does not retroactively apply authorization to existing state.

Requirements:

* already persisted Messages remain;
* already created ProcessingTasks remain;
* existing due tasks remain dispatchable;
* queued and running leases remain valid;
* retries remain valid;
* terminal tasks remain terminal;
* existing Artifacts and Markdown files remain unchanged;
* the worker does not read the allowlist before processing a durable task;
* changing the allowlist does not cancel or fail existing tasks.

## Investigation requirements

Before selecting implementation details, Codex must determine:

* how the installed aiogram version represents private chat type;
* whether router-level global message filters run before command and text filters;
* whether an outer middleware is clearer than a custom filter in the current router structure;
* how settings are passed into Telegram runtime construction;
* whether the router is a module-level singleton or built at runtime;
* how to avoid reading global settings inside every authorization call;
* whether settings validation already uses Pydantic model validators or runtime checks;
* whether complex environment values are already parsed through JSON;
* whether test fixtures currently exercise Dispatcher routing;
* how `Message.answer` or Bot API calls are mocked;
* how to prove no persistence function is called on rejection;
* how to prove no response is sent;
* how to test a message with absent `from_user`;
* how to represent channel or sender-chat update forms without creating a large Telegram fixture framework;
* how existing tests distinguish `telegram_user_id` from `telegram_chat_id`;
* whether the app and worker import Settings in a way that requires disabled-mode defaults for the worker;
* whether architecture documentation needs a concise trust-boundary update.

Do not introduce a general authorization abstraction merely to hide these findings.

## Expected failure modes and recovery behavior

### Telegram enabled with empty allowlist

Behavior:

* configuration validation fails clearly;
* polling does not start;
* no Telegram network request occurs;
* no dispatcher or worker contract is changed.

Recovery:

* configure at least one valid sender user ID and restart the app, or disable Telegram polling.

### Telegram enabled with missing token

Behavior:

* preserve the existing clear configuration failure;
* polling does not start;
* no authorization boundary is exercised.

Recovery:

* configure a valid token and restart, or disable Telegram polling.

### Malformed allowlist syntax

Examples:

```text
123456789
123,456
["123456789"]
[true]
[0]
[-1]
[12.5]
```

Behavior:

* settings validation fails;
* no silent coercion to a valid allowlist;
* no polling startup;
* no network access.

Recovery:

* use a JSON array of positive numeric Telegram user IDs.

### Unknown sender

Behavior:

* silently reject;
* no response;
* no User, Message, or ProcessingTask mutation;
* polling remains alive.

Recovery:

* add the sender’s numeric Telegram user ID to configuration and restart.

### Allowlisted sender in non-private chat

Behavior:

* silently reject;
* no response;
* no operational state;
* no processing.

Recovery:

* send the supported command or text in a private chat with the bot.

### Missing sender metadata

Behavior:

* fail closed;
* silently reject;
* do not infer sender identity from chat identity;
* no operational state;
* polling remains alive.

Recovery:

* none inside the bot; only ordinary user-authored private messages are supported.

### Profile changes

Behavior:

* authorization remains based on sender ID;
* an allowlisted sender remains accepted;
* normal persisted profile fields may update after authorization.

Recovery:

* none required.

### Authorization implementation error

A malformed or unexpected update must not accidentally become authorized.

Behavior:

* fail closed where practical;
* log a concise sanitized error;
* do not persist or respond;
* do not terminate polling for subsequent updates.

Do not catch broad exceptions in a way that hides unrelated handler failures after authorization has succeeded.

### Configuration changed while running

Behavior:

* running process continues using its startup allowlist;
* no partial reload;
* no synchronization with other processes.

Recovery:

* restart the app.

### Existing tasks from a now-disallowed sender

Behavior:

* continue under Task 007;
* no cancellation or authorization recheck;
* no state rewrite.

Recovery:

* administrative cancellation is outside this task.

## Tests

Automated tests must not contact the real Telegram API.

Use existing aiogram object construction and mocking conventions. Do not add a large fake Telegram framework.

### Settings tests

Test at least:

1. Telegram disabled with omitted allowlist succeeds.
2. Telegram disabled with `[]` succeeds.
3. Telegram disabled with a valid non-empty allowlist succeeds.
4. Telegram enabled with a token and one valid ID succeeds.
5. Telegram enabled with a token and multiple valid IDs succeeds.
6. Telegram enabled with an empty allowlist fails.
7. Telegram enabled with an omitted allowlist fails.
8. Telegram enabled without a token still fails.
9. Malformed JSON fails.
10. A quoted numeric string fails.
11. A boolean fails.
12. Null fails.
13. A float fails.
14. Zero fails.
15. A negative integer fails.
16. An out-of-range integer fails.
17. Duplicate IDs normalize without changing authorization semantics.
18. Settings validation performs no external connection.

### Authorization-boundary unit tests

Test at least:

1. allowlisted sender plus private chat is authorized;
2. unknown sender plus private chat is rejected;
3. allowlisted sender plus group chat is rejected;
4. unknown sender plus group chat is rejected;
5. allowlisted sender plus supergroup is rejected;
6. allowlisted sender plus channel-style update is rejected;
7. missing `from_user` is rejected;
8. unusable sender ID is rejected;
9. chat ID does not grant authorization;
10. username does not grant authorization;
11. first or last name does not grant authorization;
12. allowlisted sender remains authorized after profile changes.

### Routing and `/start` tests

Test through the actual router, middleware, filter, or Dispatcher boundary:

1. allowlisted private `/start` receives the existing exact response;
2. unknown private `/start` receives no response;
3. allowlisted group `/start` receives no response;
4. missing-sender `/start` receives no response;
5. rejected `/start` performs no persistence call;
6. authorization runs before the `/start` handler.

### Ordinary-text handler tests

Test:

1. allowlisted private text reaches existing ingestion;

2. unknown private text does not call ingestion;

3. allowlisted group text does not call ingestion;

4. unknown group text does not call ingestion;

5. missing-sender text does not call ingestion;

6. rejected text sends no acknowledgement;

7. accepted text sends exactly:

   ```text
   Saved for processing.
   ```

8. authorization happens before User-profile mutation;

9. allowed profile changes still update the persisted User;

10. an unknown sender copying the owner’s username creates no User.

### Required identity fixtures

Include explicit fixtures for:

* private chat with an allowlisted sender;
* private chat with an unknown sender;
* group chat with an allowlisted sender;
* group chat with an unknown sender;
* two distinct senders in the same group chat;
* repeated delivery of one allowed message;
* two different message IDs with identical text;
* missing sender metadata;
* changed username and names for the same allowed sender ID;
* an unknown sender using matching profile fields.

Where private-chat fixtures naturally use matching chat and user IDs, add a lower-level authorization test proving that the implementation reads the sender field and does not consult the chat ID for allowlist membership.

### Rejected-state integration tests

For each rejected category, assert that the relevant unique fixture values create or modify none of:

```text
User
Message
ProcessingTask
```

At minimum cover:

* unknown private sender;
* allowlisted group sender;
* unknown group sender;
* missing sender metadata.

Also assert:

* no acknowledgement call;
* no direct broker or actor call;
* no generated Artifact;
* no generated Markdown file.

The dispatcher may remain disabled in rejection tests because the primary invariant is that no ProcessingTask exists.

### Allowed persistence and duplicate tests

Test:

1. one allowed private text creates one User, one Message, and one pending ProcessingTask atomically;
2. an injected ProcessingTask insert failure rolls back the accepted Message and sends no acknowledgement;
3. duplicate allowed delivery produces one Message and one ProcessingTask;
4. concurrent duplicate allowed delivery preserves the same result if current test conventions already cover concurrency;
5. rejected delivery using the same text but another sender creates no second state;
6. username changes do not create another User.

### End-to-end allowed-flow regression

Add or extend one deterministic integration test beginning at the Telegram authorization/routing boundary with a constructed allowlisted private message.

The test must establish:

```text
authorized private Telegram text
→ one Message
→ one ProcessingTask
→ dispatcher/worker processing
→ ProcessingTask succeeded
→ Message done
→ one Artifact
→ one exact deterministic Markdown file
```

Requirements:

* use an isolated test database;
* use an isolated temporary knowledge-base root;
* use the existing Task 007 dispatcher/worker test seams;
* use Task 006 expected bytes;
* contact no real Telegram API;
* do not require a real bot token;
* do not leave rows or files behind.

### Task 007 regression tests

Existing Task 007 tests must continue to prove:

* atomic Message and ProcessingTask insertion;
* duplicate idempotency;
* PostgreSQL-owned task states;
* dispatcher publication;
* lease recovery;
* worker claims;
* retry behavior;
* attempt ownership;
* Task 006 reuse;
* Redis-unavailable app behavior;
* one-process/one-thread worker configuration.

No existing Task 007 test should be weakened merely because authorization now exists before ingestion.

### Task 006 regression tests

Existing Task 006 tests must continue to prove:

* exact Markdown rendering;
* path stability;
* storage safety;
* reconciliation;
* concurrency behavior;
* manual CLI behavior;
* Message `done` ownership.

Task 008 must not change Task 006 code to make authorization tests pass.

### Application lifecycle tests

Test:

1. Telegram disabled plus empty allowlist permits app startup.
2. Telegram disabled starts no polling.
3. Telegram enabled plus empty allowlist fails before polling.
4. Telegram enabled plus a valid token and allowlist reaches normal runtime construction without contacting Telegram during settings validation.
5. dispatcher enablement remains independent of Telegram enablement.
6. worker startup is not made dependent on a non-empty Telegram allowlist.
7. `/health` and `/ready` semantics remain unchanged.

### Development-data isolation

Before the authoritative full test suite, record development database counts for:

```text
users
messages
processing_tasks
artifacts
```

After the suite:

* the same counts remain;
* existing row identities remain;
* Task 008 fixture users are absent;
* Task 008 fixture messages are absent;
* Task 008 fixture ProcessingTasks are absent;
* generated test notes are absent from the repository knowledge base.

## Acceptance criteria

### Configuration

* `TELEGRAM_ALLOWED_USER_IDS` exists through the current settings mechanism.
* The documented format is one JSON array of positive numeric Telegram user IDs.
* The disabled application accepts an omitted or empty allowlist.
* Enabling Telegram with an empty allowlist fails clearly.
* Enabling Telegram without a token still fails clearly.
* Enabling Telegram with a usable token and non-empty valid allowlist succeeds.
* Invalid IDs and malformed syntax fail without silent coercion.
* `.env.example` contains no real Telegram user ID.
* configuration changes require restart.

### Authorization identity

* Only `message.from_user.id` determines sender allowlist membership.
* `telegram_chat_id` does not authorize.
* username and names do not authorize.
* persisted mutable User fields do not authorize.
* profile changes do not affect an allowed sender whose ID is unchanged.
* missing sender metadata fails closed.

### Chat boundary

* Only private chats are accepted.
* An allowlisted sender in a group, supergroup, or channel context is rejected.
* An unknown sender in a private chat is rejected.
* Both private-chat and allowlist conditions are required.

### Routing boundary

* Authorization occurs before `/start`.
* Authorization occurs before ordinary-text ingestion.
* Every current Telegram message handler is protected by the shared boundary.
* Rejected updates do not reach side-effecting handler behavior.

### Rejected behavior

For every rejected update:

* no User is created or updated;
* no Message is inserted;
* no ProcessingTask is inserted;
* no acknowledgement is sent;
* no unauthorized response is sent;
* no downstream processing is caused;
* polling remains operational for later updates.

### Accepted behavior

For an allowlisted sender in a private chat:

* `/start` retains its exact current response;
* ordinary text retains its current persistence fields;
* User, Message, and ProcessingTask remain atomic;
* duplicate delivery remains idempotent;
* acknowledgement remains exactly `Saved for processing.`;
* Redis unavailability remains independent from ingestion commit;
* Task 007 still reaches `ProcessingTask.status = "succeeded"`;
* Task 006 still establishes one exact Markdown note, one Artifact, and `Message.status = "done"`.

### Existing state

* No migration is added.
* Existing rows are not modified by deployment.
* Existing ProcessingTasks are not reauthorized.
* Pending and leased tasks continue normally.
* Existing Artifacts and Markdown notes remain unchanged.

### Regression and isolation

* focused authorization and settings tests pass;
* Telegram ingestion tests pass;
* Task 007 dispatcher and worker tests pass;
* Task 006 tests pass unchanged;
* the complete authoritative Docker test suite passes;
* development database counts and identities remain unchanged;
* no test-generated note or workflow artifact is left inside the repository.

### Documentation and scope

* README documents the required allowlist format and restart behavior;
* Telegram-ingestion documentation describes the private-owner boundary and silent rejection;
* current-state documentation reflects verified protected ingestion;
* architecture documentation shows the owner/private trust boundary without changing runtime topology;
* the next live-confirmed durable decision records the authorization choice;
* no queue, worker, artifact, AI, Git, webhook, database-permission, or multimodal contract is broadened.

## Required verification commands

Adapt individual test filenames only when live repository conventions require it. Record every actual command and result in the completion report.

### Initial context and Git checks

```bash
mkdir -p "$HOME/pkm-handoffs"

python3 scripts/project_context.py \
  > "$HOME/pkm-handoffs/task008-context.md"

test -s "$HOME/pkm-handoffs/task008-context.md"

git branch --show-current
git rev-parse HEAD
git status --short
git log --oneline --decorate -10
git diff --stat
git diff --check
```

After the task specification commit:

```bash
git show HEAD:tasks/008-restrict-telegram-ingestion-owner.md \
  > "$HOME/pkm-handoffs/task008-contract-from-head.md"

test -s "$HOME/pkm-handoffs/task008-contract-from-head.md"
```

### Repository inspection

```bash
find app/bot -maxdepth 3 -type f -print | sort
find app/worker -maxdepth 3 -type f -print | sort
find tests -maxdepth 2 -type f -print | sort

sed -n '1,240p' app/settings.py
sed -n '1,320p' app/bot/runtime.py
sed -n '1,320p' app/bot/handlers.py
sed -n '1,360p' app/bot/ingestion.py
sed -n '1,260p' app/main.py
sed -n '1,280p' docker-compose.yml
sed -n '1,240p' .env.example
```

If the live repository uses different paths, report and use the discovered equivalents.

Inspect identity-related decisions and documentation:

```bash
grep -nE \
  'allowlist|authorization|telegram_user_id|telegram_chat_id|private chat|controlled use|D-0(12|13|26|27)' \
  docs/DECISIONS.md \
  docs/TELEGRAM_INGESTION.md \
  docs/ARCHITECTURE.md \
  docs/CURRENT_STATE.md \
  README.md
```

### Compose configuration

```bash
docker compose config --quiet
docker compose config
```

Confirm from resolved output:

* the app receives `TELEGRAM_ALLOWED_USER_IDS`;
* the worker does not require a non-empty allowlist;
* no new service or migration exists;
* app, worker, PostgreSQL, and Redis topology remains unchanged.

### Focused settings and authorization tests

Preferred command:

```bash
docker compose exec app python -m pytest \
  tests/test_telegram_authorization.py \
  tests/test_telegram_ingestion.py
```

If settings tests are placed in a separate existing settings-test module, include that module explicitly.

### Focused downstream regression tests

```bash
docker compose exec app python -m pytest \
  tests/test_processing_tasks.py \
  tests/test_task_dispatcher.py \
  tests/test_task_worker.py \
  tests/test_artifact_processing.py \
  tests/test_markdown_artifacts.py \
  tests/test_knowledge_cli.py
```

Adapt only for actual live test filenames. Do not silently omit the equivalent coverage.

### Disabled configuration smoke

Verify that empty allowlist remains valid while Telegram is disabled:

```bash
docker compose run --rm --no-deps \
  -e TELEGRAM_BOT_ENABLED=false \
  -e TELEGRAM_BOT_TOKEN= \
  -e 'TELEGRAM_ALLOWED_USER_IDS=[]' \
  app \
  python -c 'from app.settings import Settings; Settings()'
```

Expected result:

```text
exit 0
```

### Enabled empty-allowlist rejection

```bash
if docker compose run --rm --no-deps \
  -e TELEGRAM_BOT_ENABLED=true \
  -e TELEGRAM_BOT_TOKEN=test-token \
  -e 'TELEGRAM_ALLOWED_USER_IDS=[]' \
  app \
  python -c 'from app.settings import Settings; Settings()'
then
  echo "ERROR: enabled Telegram accepted an empty allowlist" >&2
  exit 1
fi
```

Expected result:

```text
non-zero configuration-validation exit
```

If live validation intentionally occurs in Telegram runtime construction rather than `Settings()`, invoke that repository-confirmed boundary instead and document the reason.

### Enabled valid-allowlist configuration

Use a synthetic non-secret ID:

```bash
docker compose run --rm --no-deps \
  -e TELEGRAM_BOT_ENABLED=true \
  -e TELEGRAM_BOT_TOKEN=test-token \
  -e 'TELEGRAM_ALLOWED_USER_IDS=[123456789]' \
  app \
  python -c 'from app.settings import Settings; Settings()'
```

Expected result:

```text
exit 0 without a Telegram network request
```

### Authoritative runtime and migration checks

Task 008 adds no migration, but existing migrations must still apply:

```bash
docker compose up -d --build
docker compose exec app alembic upgrade head
docker compose exec app alembic current
```

Verify services:

```bash
docker compose ps
```

### Development database isolation

Before pytest, record repository-confirmed development database counts and identifying marker rows for:

```text
users
messages
processing_tasks
artifacts
```

Use the live repository’s established safe count command.

Run the complete suite:

```bash
docker compose exec app python -m pytest
```

Then repeat the exact same development database count and identity queries.

Required result:

```text
all counts unchanged
all pre-existing identities unchanged
no Task 008 fixture rows present
```

### Health and readiness

```bash
curl --retry 5 --retry-all-errors --retry-delay 1 \
  http://localhost:8000/health

curl --retry 5 --retry-all-errors --retry-delay 1 \
  http://localhost:8000/ready
```

If the known local VPN/Docker bridge problem prevents host-port verification, run the repository-established in-container equivalents and report the host limitation separately. Do not change repository networking to conceal a local routing problem.

### Knowledge-base cleanliness

```bash
find knowledge-base -maxdepth 3 -type f -print | sort
git status --short -- knowledge-base
```

Confirm no authorization test or smoke note remains.

### Final Git checks

```bash
git diff --check
git status --short
git diff --stat

git diff -- \
  .env.example \
  README.md \
  app/settings.py \
  app/bot \
  docker-compose.yml \
  docs/ARCHITECTURE.md \
  docs/CURRENT_STATE.md \
  docs/DECISIONS.md \
  docs/TELEGRAM_INGESTION.md \
  tasks/008-restrict-telegram-ingestion-owner.md \
  tests
```

Adapt the file list only when live inspection justifies a narrowly scoped equivalent path.

### Completion report and review bundle

Create the completion report outside the repository:

```bash
mkdir -p "$HOME/pkm-handoffs"
```

Save it as:

```text
$HOME/pkm-handoffs/task008-handoff.md
```

Generate a candidate bundle:

```bash
python3 scripts/review_bundle.py \
  --task tasks/008-restrict-telegram-ingestion-owner.md \
  --report "$HOME/pkm-handoffs/task008-handoff.md" \
  > "$HOME/pkm-handoffs/task008-review-bundle-candidate.md"
```

Verify it is non-empty:

```bash
test -s "$HOME/pkm-handoffs/task008-review-bundle-candidate.md"
```

After every implementation, test, documentation, task-status, or completion-report correction, regenerate the final bundle:

```bash
python3 scripts/review_bundle.py \
  --task tasks/008-restrict-telegram-ingestion-owner.md \
  --report "$HOME/pkm-handoffs/task008-handoff.md" \
  > "$HOME/pkm-handoffs/task008-review-bundle.md"

test -s "$HOME/pkm-handoffs/task008-review-bundle.md"
```

Do not change repository files or the completion report after final bundle generation without regenerating the bundle again.

Confirm that no workflow artifact is inside the repository:

```bash
git status --short

find . -maxdepth 3 -type f \
  \( -name 'task008-context.md' \
     -o -name 'task008-contract-from-head.md' \
     -o -name 'task008-handoff.md' \
     -o -name 'task008-review-bundle*.md' \) \
  -print
```

The final `find` command must produce no repository-local Task 008 workflow artifact.

## Documentation impact

### Required updates

#### `.env.example`

Add:

```text
TELEGRAM_ALLOWED_USER_IDS=[]
```

Include a concise safe comment if consistent with the file.

Do not include a real user ID.

#### `README.md`

Document:

* the JSON-array format;
* that sender Telegram user IDs, not chat IDs or usernames, are authorized;
* that Telegram enablement requires a non-empty allowlist;
* that only private chats are accepted;
* that unknown and non-private updates are silently ignored;
* that changes require application restart;
* that the worker continues processing already durable tasks independently;
* that no administrative allowlist command exists.

Do not document a real owner ID.

#### `docs/TELEGRAM_INGESTION.md`

Replace stale “allowlisting postponed” or controlled-only wording with verified behavior.

Document:

```text
Telegram message
→ private-owner authorization
→ existing ingestion transaction
```

Explain:

* sender-ID identity;
* private-chat requirement;
* silent rejection;
* no state before authorization;
* allowed atomic Message and ProcessingTask behavior;
* unchanged acknowledgement;
* duplicate behavior;
* no database-backed permissions;
* restart-required configuration.

#### `docs/CURRENT_STATE.md`

After verification:

* record Task 008 as implemented;
* describe the protected Telegram boundary;
* retain the complete Task 007 processing flow;
* retain Task 006 deterministic ownership;
* state that group/channel ingestion remains unsupported;
* state that runtime allowlist management is not implemented;
* update the active-task field according to workflow conventions;
* use `~/pkm-handoffs/` examples and no `/tmp` examples.

Do not turn the document into a chronological changelog.

#### `docs/DECISIONS.md`

Add the next live-confirmed decision, expected to be D-027.

The decision must establish:

* the bot is protected as a personal ingestion boundary by configured Telegram sender user IDs;
* authorization uses `from_user.id`;
* authorization does not use chat ID, username, names, or database profile fields;
* only private chats are accepted;
* unauthorized and non-private updates are silently rejected before state mutation;
* the allowlist is configuration-backed and loaded at startup;
* enabled polling requires a non-empty allowlist;
* no database permission model or runtime administration is introduced;
* existing durable ProcessingTasks are not reauthorized;
* group ingestion and runtime owner management remain postponed.

#### `docs/ARCHITECTURE.md`

Add a concise trust-boundary representation, for example:

```text
Telegram update
→ private-chat + configured-sender gate
→ aiogram handlers
→ PostgreSQL Message + ProcessingTask
→ existing dispatcher/worker flow
```

Document that the authorization gate belongs to the app process before persistence and does not change worker behavior or runtime topology.

#### Task 008 file

After successful verification:

* change status from `planned` to `completed`;
* append concise completion evidence;
* do not rewrite accepted requirements;
* record any explicit amendment separately with its reason.

### Expected unchanged documentation

Unless live evidence proves a direct contradiction, do not modify:

* `docs/DATA_MODEL.md`;
* `docs/MARKDOWN_ARTIFACTS.md`;
* `docs/PROJECT_BRIEF.md`;
* `docs/WORKFLOW.md`;
* `AGENTS.md`;
* completed Task 006 requirements;
* completed Task 007 requirements.

## Completion-report requirements

Codex must create:

```text
$HOME/pkm-handoffs/task008-handoff.md
```

The report must contain exactly these sections.

### 1. Initial repository state

Report:

* branch;
* starting HEAD;
* starting working-tree status;
* recent relevant commits;
* confirmation that Task 007 was committed;
* confirmation that Task 008 existed as a committed regular blob before implementation;
* fresh context-report path;
* committed-contract-copy path;
* contradictions between uploaded snapshots and live repository evidence.

### 2. Implementation plan followed

Summarize:

* selected settings representation;
* selected validation boundary;
* selected aiogram authorization boundary;
* handler and test changes;
* documentation plan;
* any justified deviation.

### 3. Repository inspection findings

Report:

* confirmed Task 008 filename;
* existing token-validation behavior;
* settings construction and caching;
* Bot, Dispatcher, Router, middleware, filter, and handler registration structure;
* exact `/start` and text handler locations;
* current chat-type representation;
* ingestion transaction boundary;
* Task 007 Message and ProcessingTask behavior;
* next durable decision number;
* why no migration is required.

### 4. Files changed

List every changed and new file with its purpose.

List important inspected files intentionally left unchanged, including:

* database models;
* migrations;
* Task 006 knowledge code;
* Task 007 dispatcher and worker code;
* data-model and Markdown-artifact documentation.

### 5. Configuration and validation

Report:

* final internal setting type;
* exact environment syntax;
* empty/disabled behavior;
* enabled/non-empty requirement;
* invalid-value handling;
* token interaction;
* Compose forwarding;
* restart behavior;
* confirmation that `.env.example` has no real ID.

### 6. Authorization and routing boundary

Report:

* chosen filter or middleware;
* where it is attached;
* evaluation order;
* sender-ID comparison;
* private-chat check;
* missing-sender behavior;
* proof that `/start` and text handlers are both protected;
* proof that authorization performs no external lookup.

### 7. Accepted and rejected behavior

Report:

* allowed `/start` result;
* allowed text result;
* exact acknowledgement;
* rejected update response count;
* User, Message, and ProcessingTask counts for rejection tests;
* mutable-profile behavior;
* duplicate allowed-delivery result;
* existing-task behavior.

### 8. Tests and verification results

For every required command, provide:

* exact command;
* pass, fail, or not run;
* exact or relevant pass counts;
* settings-test results;
* authorization tests;
* Telegram tests;
* Task 007 regression tests;
* Task 006 regression tests;
* full suite;
* Compose config;
* health/readiness;
* development-data counts before and after;
* knowledge-base cleanliness.

### 9. End-to-end allowed-flow evidence

Report:

* constructed authorized update setup;
* sender ID and chat type using synthetic test values;
* Message UUID;
* ProcessingTask UUID and final status;
* Message final status;
* Artifact UUID;
* relative Markdown path;
* exact-byte verification;
* cleanup results.

Do not report real user IDs, bot tokens, raw private message content, or credentials.

### 10. Documentation updates

Report:

* what changed in README;
* what changed in Telegram ingestion documentation;
* what changed in current state;
* what changed in architecture;
* selected durable decision;
* what intentionally remained unchanged.

### 11. Acceptance matrix and scope

Mark every acceptance criterion:

```text
pass
fail
unverified
```

Provide direct evidence.

Explicitly confirm that no:

* migration;
* database permission model;
* runtime allowlist command;
* group ingestion;
* Task 006 change;
* Task 007 state-machine change;
* AI or multimodal feature;
* Git artifact automation;
* unrelated refactor

was added.

### 12. Risks and unverified items

Report:

* local Telegram network limitations;
* local Docker/VPN limitations;
* commands not run;
* behavior inferred rather than directly verified;
* configuration limitations;
* the fact that allowlist changes require restart;
* the fact that existing tasks are not retroactively blocked.

### 13. Final repository boundary

Report:

* final `git diff --check`;
* final `git status --short`;
* final `git diff --stat`;
* completion-report path;
* candidate and final review-bundle paths;
* final bundle generation result;
* confirmation that no workflow artifact, test note, database dump, real Telegram ID, or secret is inside the repository;
* confirmation that no implementation commit was created unless explicitly instructed.

The completion report contains Codex claims for review. The review-bundle command does not independently execute or validate those claims.

## Expected commit boundary

The accepted Task 008 specification should be committed separately before implementation begins.

The implementation commit may include only the smallest verified Task 008 result:

* one typed allowed-user-ID setting;
* Telegram enablement/allowlist validation;
* one narrow aiogram authorization filter or middleware;
* minimal router/runtime wiring;
* focused settings and authorization tests;
* necessary Telegram handler and ingestion regression-test adjustments;
* `.env.example`;
* README;
* Telegram-ingestion documentation;
* current-state documentation;
* concise architecture trust-boundary documentation;
* one durable decision;
* Task 008 status and completion evidence.

It must not include:

* database migrations;
* database model changes;
* generated Markdown notes;
* Redis data;
* database dumps;
* context reports;
* committed-contract copies;
* completion reports;
* review bundles;
* real Telegram user IDs;
* real bot tokens;
* Task 006 code changes;
* Task 007 dispatcher or worker changes;
* runtime allowlist administration;
* group ingestion;
* webhook behavior;
* AI or multimodal work;
* Git artifact automation;
* local VPN or host-routing changes;
* Task 009 planning;
* unrelated refactoring.

Suggested implementation commit message:

```text
feat: restrict Telegram ingestion to configured owners
```

Codex must not create the implementation commit unless explicitly instructed.

## Completion evidence

Implemented and verified on 2026-07-03 without changing the accepted contract.
Enabled Telegram polling now requires a strict, non-empty JSON sender-ID
allowlist, and one Dispatcher-level message root filter permits only configured
senders in private chats before `/start`, text ingestion, response, or state
mutation.

Focused authorization and ingestion coverage passed 44 tests; focused Task
006/007 regressions passed 91 tests; and the complete suite passed 219 tests.
Configuration smokes, resolved Compose topology, migration head, health and
readiness, development-data isolation, exact-byte authorized end-to-end
processing, cleanup, and repository knowledge-base cleanliness were verified.
The normal Compose BuildKit rebuild encountered local DNS failure, so the same
Dockerfile was built successfully with host networking before the four-service
Compose runtime was recreated; the repository configuration was not changed.
Full evidence is in the repository-external Task 008 handoff and review bundle.
