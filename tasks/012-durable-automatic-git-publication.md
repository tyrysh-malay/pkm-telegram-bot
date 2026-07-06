# Task 012: Add durable automatic Git publication for generated artifacts

**Status:** planned
**Depends on:** Tasks 000–011 and completion of the standalone Task 011 status correction
**Target file:** `tasks/012-durable-automatic-git-publication.md`
**Expected branch:** `task/012-durable-automatic-git-publication`
**Expected pull-request title:** `Task 012: Add durable automatic Git publication for generated artifacts`
**Expected contract commit:** `docs: define task 012 durable automatic Git publication`
**Expected implementation commit:** `feat: add durable automatic Git publication`
**Expected correction commit:** `fix: address Task 012 review findings`
**Expected merge method:** normal merge commit, performed only after separate explicit user authorization

## Pre-task baseline correction

Before creating the Task 012 branch, correct the confirmed Task 011 documentation inconsistency:

```text
tasks/011-manual-git-artifact-publication.md

Status: ready for review
→
Status: completed
```

This correction:

* does not consume a task number;

* is not part of Task 012;

* must be completed on synchronized `main`;

* must change only the Task 011 status line;

* must use the commit message:

  ```text
  docs: mark task 011 completed
  ```

* must be pushed before Task 012 branch creation;

* must receive a successful `CI / Test` result;

* must be absent from the Task 012 PR diff because it belongs to the corrected base.

The accepted Task 012 planning instruction explicitly authorizes this one-path standalone correction on the synchronized default branch.

It does not authorize another direct change to `main`.

Before applying the correction:

```bash
git switch main
git fetch origin --prune
git status --short
git rev-list --left-right --count main...origin/main
git rev-parse HEAD
grep -n '^\*\*Status:\*\*' tasks/011-manual-git-artifact-publication.md
```

Expected starting evidence:

```text
main
408bfc5318f0bf81ee67214b4eefbc89d25fdb70
0	0
clean working tree
Task 011 status = ready for review
```

After editing, verify:

```bash
git diff --check
git diff --name-only
git diff -- tasks/011-manual-git-artifact-publication.md
```

The diff must contain exactly one status-line change.

Then:

```bash
git add tasks/011-manual-git-artifact-publication.md
git diff --cached --check
git diff --cached --name-only
git commit -m "docs: mark task 011 completed"
git push origin main
```

Inspect the resulting default-branch CI run:

```bash
gh run list --branch main --workflow ci.yml --limit 10
```

Task 012 must not begin until that correction is present on `origin/main` and its `CI / Test` run has succeeded.

If repository rules reject the direct documentation push, use one standalone documentation-only branch and PR without assigning a task number. Task 012 still branches only after that correction is merged and green.

## Git and pull-request authorization

After the pre-task correction, this task authorizes Codex to perform only the following actions on:

```text
task/012-durable-automatic-git-publication
```

1. create or switch to the Task 012 branch from the corrected synchronized default branch;
2. create the distinct Task 012 contract commit;
3. push the Task 012 branch;
4. open or update one draft pull request targeting the verified default branch;
5. create one coherent Task 012 implementation commit;
6. push that implementation commit to the same branch;
7. inspect the `CI / Test` result for the exact pushed head;
8. update the PR description with implementation and verification evidence;
9. mark the PR ready only after local verification and CI succeed for the exact current head;
10. create and push bounded correction commits when review or CI findings require them.

This task does **not** authorize Codex to:

* push Task 012 implementation directly to `main`;
* merge the Task 012 pull request;
* delete the task branch;
* force-push;
* amend or rebase already pushed reviewed commits;
* configure branch protection;
* change repository visibility or Actions permissions;
* execute remote Git operations from the PKM application;
* initialize, clone, fetch, pull, push, merge, rebase, or switch branches in the knowledge-base repository;
* add deployment, release, or remote synchronization behavior.

The Task 012 pull request may be merged only after approval of the exact current green head and a separate explicit user authorization.

## Goal

Add one durable automatic local Git-publication stage after successful deterministic note generation:

```text
generate_note ProcessingTask
→ Task 006 establishes exact Artifact + Markdown
→ successful generate_note finalization atomically:
     mark generate_note succeeded
     establish pending publish_artifact task
→ existing dispatcher
→ Redis/Dramatiq
→ generic worker
→ existing publish_artifact_to_git(...)
→ one exact local Git commit or idempotent reconciliation
→ publish_artifact ProcessingTask succeeded
```

The task must preserve these independent outcomes:

```text
Message.status = done
generate_note = succeeded
```

means:

```text
the deterministic Artifact and Markdown file are valid
```

It must not mean:

```text
Git publication also succeeded
```

A blocked, retrying, or failed `publish_artifact` task must not invalidate, delete, rerender, or roll back the valid note.

## Confirmed current boundary

Live repository inspection confirms:

* Tasks 000–011 are user-confirmed complete.

* The current confirmed Task 011 merge baseline is:

  ```text
  main
  408bfc5318f0bf81ee67214b4eefbc89d25fdb70
  ```

* The merged Task 011 task file still has the stale status `ready for review`.

* Task 011 added nullable:

  ```text
  Artifact.git_commit_sha
  ```

* Task 011 added:

  ```python
  async def publish_artifact_to_git(
      session: AsyncSession,
      artifact_id: uuid.UUID,
      knowledge_base_root: Path,
  ) -> GitPublicationResult:
      ...
  ```

* `GitPublicationResult.outcome` is one of:

  ```text
  created
  reconciled
  existing
  ```

* `publish_artifact_to_git(...)`:

  * requires a fresh session without an active transaction;
  * validates the exact knowledge-base Git root;
  * acquires the repository publication lock;
  * requires an empty Git index;
  * locks and validates the selected Artifact;
  * validates exact Task 006 bytes;
  * accepts a valid stored publication SHA;
  * reconciles one exact trailer-bearing retained commit;
  * creates one selected-path commit when necessary;
  * persists `Artifact.git_commit_sha`;
  * owns commit and rollback;
  * retains a created Git commit when PostgreSQL commit fails.

* Task 011 performs no remote operation and no automatic invocation.

* The current ProcessingTask model already has:

  ```text
  message_id
  task_type
  status
  attempts
  max_attempts
  available_at
  lease_expires_at
  last_error
  ```

* Existing uniqueness is:

  ```text
  UNIQUE(message_id, task_type)
  ```

* Existing statuses are:

  ```text
  pending
  queued
  running
  retrying
  succeeded
  failed
  ```

* The current dispatcher selects due tasks by status and availability without examining task type.

* The current Dramatiq actor payload contains only the ProcessingTask UUID.

* The current worker claim boundary accepts only `generate_note`; unsupported types fail closed.

* The current worker:

  * claims a task through PostgreSQL;
  * increments attempts exactly once;
  * calls `process_text_message(...)`;
  * classifies permanent and retryable failures;
  * conditionally finalizes the claimed attempt;
  * retries through PostgreSQL state and fixed backoff.

* The current successful finalizer only changes the claimed task to `succeeded`.

* The current Task 006 processor remains the sole owner of:

  * Markdown rendering;
  * deterministic path and bytes;
  * filesystem publication;
  * Artifact creation and reconciliation;
  * source-Message locking;
  * `Message.status = "done"`.

* `Settings` currently contains:

  * Telegram configuration;
  * database URLs;
  * Redis URL;
  * dispatcher enablement;
  * knowledge-base path.

* No automatic Git-publication setting currently exists.

* No schema change is required merely to add a second accepted `task_type`.

* The current CI check is:

  ```text
  CI / Test
  ```

* D-030 is expected to describe Task 011’s manual publication decision.

* D-031 is the expected next durable decision identifier, subject to live verification.

* No Task 012 branch, task file, or conflicting automatic-publication implementation was found in the supplied evidence.

Codex must repeat all local-only and mutable checks before editing.

## Repository verification requirements

### Default branch and pre-task correction

Run:

```bash
git branch --show-current
git rev-parse HEAD
git status --short
git log --oneline --decorate -15
git remote -v
git fetch origin --prune
git remote show origin
git rev-list --left-right --count main...origin/main
git diff --stat
git diff --check
gh auth status
gh repo view --json nameWithOwner,visibility,defaultBranchRef
```

Verify:

* the Task 011 status correction exists on `origin/main`;
* its commit changed only the Task 011 status line;
* the correction’s default-branch CI run succeeded;
* local `main` equals `origin/main`;
* the working tree is clean;
* no Task 012 branch or PR conflicts with the accepted task;
* `tasks/012-durable-automatic-git-publication.md` is the next repository-consistent task path;
* migration `0004` remains the current Alembic head;
* D-031 is the next available durable decision number.

Inspect existing Task 012 state:

```bash
gh pr list --state all \
  --head task/012-durable-automatic-git-publication \
  --json number,title,state,isDraft,baseRefName,headRefName,headRefOid,url
```

Do not stash, discard, overwrite, move, or commit unrelated local work.

### Current task contract and workflow

Read:

```text
AGENTS.md
docs/WORKFLOW.md
docs/CURRENT_STATE.md
docs/DECISIONS.md
tasks/TEMPLATE.md
tasks/011-manual-git-artifact-publication.md
.github/pull_request_template.md
.github/workflows/ci.yml
```

Verify:

* the contract commit must precede implementation;
* the contract path and full SHA must be recorded in the PR;
* each pushed correction invalidates earlier review and CI evidence;
* merge remains separately authorized;
* the exact check context remains `CI / Test`.

### ProcessingTask model and persistence

Inspect:

```text
app/db/models.py
alembic/versions/0003_create_processing_tasks.py
alembic/versions/0004_add_artifact_git_commit_sha.py
tests/test_models.py
tests/test_migrations.py
tests/conftest.py
```

Confirm:

* `task_type` remains unrestricted text;
* `(message_id, task_type)` remains unique;
* no Artifact target column exists;
* no migration is needed for `publish_artifact`;
* test cleanup already handles multiple ProcessingTasks per Message;
* the next task can use the current table without schema or data backfill.

If live evidence proves that a schema migration is required, report the contradiction before implementation. Do not silently add one.

### Dispatcher

Inspect:

```text
app/worker/dispatcher.py
tests/test_task_dispatcher.py
```

Confirm:

* due-task selection does not filter by task type;
* the actor payload remains one canonical ProcessingTask UUID;
* queued-lease marking is task-type agnostic;
* queued and running lease recovery already applies to all ProcessingTask rows;
* no Git-specific dispatcher branch is required.

The dispatcher should remain behaviorally unchanged.

### Worker claim, execution, and finalization

Inspect:

```text
app/worker/constants.py
app/worker/processing.py
app/worker/tasks.py
app/worker/broker.py
tests/test_task_worker.py
```

Report:

* current accepted task-type constants;
* current `ClaimedTask` fields;
* unsupported-type behavior;
* claim transaction and row locking;
* attempt increment behavior;
* running lease;
* successful and failed finalization;
* stale finalizer protection;
* retry backoff;
* error sanitization;
* behavior when finalization raises after processing succeeded;
* current test injection seams.

Determine the smallest refactor needed to:

1. include `task_type` in the claim result;
2. accept both supported task types;
3. dispatch to the correct existing processor;
4. atomically establish the downstream task only after successful `generate_note`;
5. keep `publish_artifact` finalization terminal without another downstream task.

### Task 011 publication boundary

Inspect completely:

```text
app/knowledge/git_publication.py
app/knowledge/git_cli.py
app/knowledge/errors.py
app/knowledge/processing.py
tests/test_git_publication.py
tests/test_git_cli.py
docs/GIT_PUBLICATION.md
```

Confirm:

* the exact public function signature;
* transaction ownership;
* Artifact row locking;
* repository locking;
* retained-commit recovery;
* current exception hierarchy;
* current externally visible manual CLI messages;
* which current `GitPublicationError` causes are invariant failures;
* which causes are operational failures;
* whether exception subclasses can be introduced without changing CLI output.

Task 012 must not duplicate Git subprocess, commit, staging, trailer, lock, SHA-validation, or reconciliation logic.

### Artifact resolution from `message_id`

Inspect:

```text
app/db/models.py
app/knowledge/markdown.py
app/knowledge/processing.py
```

Confirm the current deterministic note identity:

```text
Artifact.message_id = ProcessingTask.message_id
Artifact.artifact_type = "note"
```

Determine a narrow resolver that returns the existing note Artifact UUID without:

* creating an Artifact;
* rendering Markdown;
* repairing metadata;
* changing Message status;
* invoking Git.

The resolver must fail clearly when:

* no note Artifact exists;
* more than one matching row somehow exists despite constraints;
* the Artifact type is unsupported or inconsistent.

### Settings and runtime

Inspect:

```text
app/settings.py
.env.example
docker-compose.yml
app/main.py
```

Confirm:

* settings are immutable for one process lifetime;
* app and worker share the settings model;
* worker receives the knowledge-base bind mount;
* worker can access the nested `.git` directory;
* the new setting can default to false without startup validation;
* no app lifespan or readiness dependency is needed.

### CI

Inspect:

```text
.github/workflows/ci.yml
Dockerfile
```

Confirm:

* Git remains installed in the shared image;
* current tests can create temporary Git repositories;
* CI requires no real Git author identity or knowledge-base repository;
* deterministic test-only repository configuration is sufficient;
* no CI workflow change is necessary unless a focused test proves otherwise.

## Problem or motivation

Task 011 proved safe publication only when a developer explicitly invokes the CLI for an Artifact UUID.

Without Task 012:

* automatically generated notes remain uncommitted until manually selected;
* PostgreSQL has no durable record that automatic Git publication is pending, retrying, failed, or complete;
* a temporary knowledge-base lock or Git command failure cannot be recovered through the existing dispatcher;
* a worker restart cannot resume publication automatically;
* manual publication and automatic generation remain operationally disconnected;
* future processing stages cannot rely on a proven durable downstream-task chaining boundary.

Adding the Git commit directly inside Task 006 or `generate_note` execution would create the wrong coupling:

* note generation would depend on Git repository health;
* a Git failure could incorrectly make a valid deterministic note look failed;
* Task 006 would acquire a second cross-resource responsibility;
* retry state would be ambiguous between note generation and publication;
* manual Task 011 semantics would be duplicated.

A separate `publish_artifact` ProcessingTask preserves independent durable outcomes while reusing the existing PostgreSQL orchestration lifecycle and existing local Git publisher.

## Scope

Implement the following bounded outcome:

1. add `TASK_TYPE_PUBLISH_ARTIFACT = "publish_artifact"`;
2. accept `generate_note` and `publish_artifact` as supported worker task types;
3. include task type in the claimed-task value;
4. keep the actor payload as ProcessingTask UUID only;
5. keep the dispatcher task-type agnostic;
6. add `GIT_PUBLICATION_ENABLED` with default false;
7. forward the setting through normal app and worker configuration;
8. use the setting only when finalizing successful `generate_note`;
9. atomically mark the claimed `generate_note` task succeeded and establish one pending `publish_artifact` task when enabled;
10. preserve a pre-existing publication task without resetting its state;
11. create no downstream task when disabled;
12. create no automatic backfill;
13. resolve the deterministic note Artifact from the publication task’s `message_id`;
14. call the unchanged `publish_artifact_to_git(...)` with a fresh session;
15. classify publication failures through explicit exception types;
16. retry operational publication failures through the existing ProcessingTask lifecycle;
17. fail deterministic publication invariant violations permanently;
18. preserve Task 011 manual CLI behavior;
19. preserve note-generation and Message-status behavior;
20. add focused chaining, worker, recovery, configuration, and end-to-end tests;
21. update architecture, state, data-flow, configuration, and durable-decision documentation;
22. require a successful `CI / Test` run for the exact Task 012 head.

## Out of scope

Do not add:

* a database migration;
* `artifact_id` on ProcessingTask;
* a publication-task table;
* a generic task-target model;
* a workflow graph or DAG;
* ProcessingEvent;
* a second dispatcher;
* a second queue;
* a second Dramatiq actor payload;
* a Redis result backend;
* Dramatiq automatic retries;
* new ProcessingTask states;
* new lease types;
* running-lease heartbeat;
* unlimited retries;
* manual retry administration;
* automatic backfill;
* bulk publication;
* publishing existing Artifacts on startup;
* automatic task creation for already-succeeded historical `generate_note` rows;
* changes to Telegram ingestion;
* changes to the original Message plus `generate_note` transaction;
* changes to Telegram acknowledgements;
* changes to Task 006 Markdown rendering;
* changes to Task 006 filesystem publication;
* changes to Task 006 Artifact reconciliation;
* changes to Task 011 Git staging;
* changes to Task 011 commit metadata;
* changes to Task 011 repository validation;
* changes to Task 011 index policy;
* weakening Task 011 locks;
* remote Git operations;
* clone, fetch, pull, push, or authentication;
* GitHub API integration;
* automatic repository initialization;
* branch creation or switching;
* merging or rebasing inside the knowledge base;
* worker-to-Telegram notifications;
* deployment;
* webhook ingestion;
* AI processing;
* summaries, tags, topics, or embeddings;
* voice, image, link, file, or PDF handling;
* vector databases;
* RAG;
* LangChain or LangGraph;
* unrelated CI, branch-protection, Telegram, Redis, schema, or workflow refactoring.

## Affected components

Expected changes:

```text
app/settings.py
app/worker/constants.py
app/worker/processing.py
app/knowledge/errors.py
app/knowledge/git_publication.py
tests/test_task_worker.py
tests/test_git_publication.py
tests/test_settings.py or existing settings-focused test module
.env.example
docker-compose.yml
README.md
docs/ARCHITECTURE.md
docs/DATA_MODEL.md
docs/GIT_PUBLICATION.md
docs/CURRENT_STATE.md
docs/DECISIONS.md
tasks/012-durable-automatic-git-publication.md
```

A narrowly scoped new helper module is permitted when it makes the Artifact-resolution or worker processor boundary clearer, for example:

```text
app/worker/processors.py
```

or:

```text
app/knowledge/artifact_lookup.py
```

Add one only when it avoids placing unrelated lookup behavior inside the Git subprocess module.

Conditionally allowed:

```text
tests/conftest.py
tests/test_task_dispatcher.py
app/db/models.py
.github/workflows/ci.yml
Dockerfile
```

These paths may change only when live inspection proves a direct minimal need.

Expected unchanged in behavior:

```text
app/bot/
app/bot/ingestion.py
app/worker/dispatcher.py
app/worker/tasks.py
app/worker/broker.py
app/knowledge/markdown.py
app/knowledge/storage.py
app/knowledge/processing.py
app/knowledge/git_cli.py
alembic/versions/
Telegram responses
Message ingestion transaction
ProcessingTask schema
Redis topology
Dramatiq payload
Task 006 deterministic bytes
Task 011 commit subject and trailers
/health
/ready
GitHub workflow architecture
```

A file listed as expected unchanged may receive a minimal import or test seam only when strictly required, but its established semantics must remain unchanged and the deviation must be justified in the PR.

## Data, state, migration, and configuration impact

### Database schema

Expected schema impact:

```text
none
```

Do not add an Alembic migration.

Do not alter:

```text
users
messages
artifacts
processing_tasks
```

The current ProcessingTask schema is sufficient because:

```text
task_type = unrestricted TEXT
UNIQUE(message_id, task_type)
```

supports:

```text
one generate_note task
one publish_artifact task
```

for the same Message.

### New task type

Add exactly:

```text
publish_artifact
```

The complete accepted first-version task types become:

```text
generate_note
publish_artifact
```

No database enum or check constraint is added.

### Publication-task initial state

A newly established publication task has:

```text
task_type = "publish_artifact"
status = "pending"
attempts = 0
max_attempts = 3
available_at = downstream-task creation time
lease_expires_at = null
last_error = null
```

Use existing ProcessingTask defaults and conventions rather than duplicating literal values where those defaults are authoritative.

### Configuration

Add:

```text
GIT_PUBLICATION_ENABLED
```

Internal setting:

```python
git_publication_enabled: bool = False
```

Required semantics:

```text
false
→ successful generate_note finalization does not create publish_artifact
```

```text
true
→ successful generate_note finalization atomically establishes publish_artifact
```

The setting gates **new downstream-task creation only**.

It must not gate:

* claiming an existing `publish_artifact` task;
* executing an existing publication task;
* retrying an existing publication task;
* lease recovery;
* manual Git publication;
* Task 006 note generation.

A process started with:

```text
GIT_PUBLICATION_ENABLED=false
```

must still execute any already durable `publish_artifact` task it receives.

### `.env.example`

Add a safe default:

```text
GIT_PUBLICATION_ENABLED=false
```

Do not include:

* author identity;
* repository credentials;
* remote URL;
* branch name;
* GitHub token.

### Compose

Forward the setting to both app and worker services using the repository’s existing environment convention.

Although downstream creation occurs in the worker finalization path, forwarding one consistent immutable value to both processes avoids unexplained process-specific settings behavior.

The default remains false.

No new service, volume, network, queue, or secret is introduced.

### Existing data

Do not backfill:

* existing Artifacts;
* existing null `git_commit_sha` values;
* existing succeeded `generate_note` tasks;
* Messages created before Task 012;
* manually generated legacy Artifacts.

Task 012 affects only future successful `generate_note` finalizations that occur while automatic task creation is enabled.

## Behavioral requirements

### Supported task types

Add constants:

```python
TASK_TYPE_GENERATE_NOTE = "generate_note"
TASK_TYPE_PUBLISH_ARTIFACT = "publish_artifact"

SUPPORTED_TASK_TYPES = (
    TASK_TYPE_GENERATE_NOTE,
    TASK_TYPE_PUBLISH_ARTIFACT,
)
```

The exact collection type may follow live style.

Unknown task types must continue to fail closed without invoking either processor.

### Claimed task identity

Extend the immutable claim result to include:

```python
task_type: str
```

Equivalent boundary:

```python
@dataclass(frozen=True)
class ClaimedTask:
    id: uuid.UUID
    message_id: uuid.UUID
    task_type: str
    attempt: int
    max_attempts: int
```

Claim behavior remains:

* one PostgreSQL row lock;
* no claim for terminal, future, or currently running tasks;
* attempts increment once;
* running lease established once;
* unsupported task types become failed without consuming a processing attempt;
* no Artifact or Git work occurs during claim.

### Processor dispatch

`run_processing_task(...)` must dispatch by the claimed task type.

Required behavior:

```text
generate_note
→ fresh session
→ process_text_message(session, message_id, knowledge_base_root)
```

```text
publish_artifact
→ resolve existing deterministic note Artifact ID from message_id
→ fresh session
→ publish_artifact_to_git(session, artifact_id, knowledge_base_root)
```

Do not alter the Dramatiq actor interface.

Do not pass `artifact_id`, task type, paths, or configuration through Redis.

PostgreSQL remains the authority reloaded after delivery.

### Artifact resolution

Add one narrow async resolver equivalent to:

```python
async def resolve_note_artifact_id(
    session: AsyncSession,
    message_id: uuid.UUID,
) -> uuid.UUID:
    ...
```

Requirements:

* query only the existing note Artifact for the Message;
* use the existing accepted note artifact type constant;
* return its UUID;
* perform no rendering;
* perform no file IO;
* perform no Git operation;
* perform no row creation;
* perform no repair;
* perform no Message or ProcessingTask mutation;
* require a fresh read transaction or a session owned by the resolver call;
* close or roll back that read transaction before calling `publish_artifact_to_git(...)`.

Failure semantics:

```text
no note Artifact
→ permanent publication invariant failure
```

```text
more than one note Artifact
→ permanent publication invariant failure
```

```text
database unavailable
→ retryable operational failure
```

The existing database uniqueness constraint remains the final duplicate protection.

### Successful `generate_note` finalization

When processing succeeds and the claimed task type is `generate_note`, finalization must execute one transaction that:

1. conditionally verifies that the row still has:

   * the claimed task ID;
   * `status = running`;
   * the claimed attempt number;
   * `task_type = generate_note`;

2. marks that row:

   ```text
   status = succeeded
   lease_expires_at = null
   last_error = null
   updated_at = finalization time
   ```

3. when automatic publication creation is enabled, establishes:

   ```text
   ProcessingTask(
       message_id = claimed.message_id,
       task_type = publish_artifact
   )
   ```

4. commits both outcomes atomically.

If the claimed row is stale:

* do not update it;
* do not create a downstream task;
* return the existing stale-finalizer result.

If downstream insertion or transaction commit fails:

* the `generate_note` success update must roll back;
* the task remains recoverable as running until lease recovery;
* later processing may re-run idempotent Task 006 behavior;
* later finalization retries downstream creation.

Do not mark `generate_note` succeeded in a separate transaction before creating the downstream task.

### Existing publication task

The downstream establishment operation must be idempotent.

When no publication task exists:

```text
insert one pending publish_artifact task
```

When one already exists:

```text
retain it exactly
```

Do not reset:

* status;
* attempts;
* max attempts;
* availability;
* lease;
* last error;
* timestamps.

A pre-existing:

```text
pending
queued
running
retrying
succeeded
failed
```

publication task remains in that state.

Use the existing uniqueness constraint as final protection.

A repository-consistent implementation may use PostgreSQL `INSERT ... ON CONFLICT DO NOTHING` on `(message_id, task_type)`.

Do not catch a broad `IntegrityError` and assume every constraint failure is the expected duplicate.

### Disabled downstream creation

When:

```text
GIT_PUBLICATION_ENABLED=false
```

successful `generate_note` finalization must preserve current Task 007 behavior:

```text
generate_note → succeeded
no publish_artifact task
```

No later configuration change automatically creates the omitted task.

The manual Task 011 CLI remains available.

### Existing durable publication tasks

Claiming and running `publish_artifact` must not consult `GIT_PUBLICATION_ENABLED`.

This invariant prevents durable work from being abandoned when:

* configuration is later disabled;
* app and worker restart under different historical settings;
* a task was created before a deployment change.

### Successful `publish_artifact` finalization

When `publish_artifact_to_git(...)` returns:

```text
created
reconciled
existing
```

the ProcessingTask succeeds through the normal finalization boundary.

No downstream task is created.

The result outcome does not need a new database column.

The Artifact’s `git_commit_sha` remains the durable publication result.

### Manual publication before automatic execution

When the Artifact was already published manually:

```text
Artifact.git_commit_sha is valid
```

the automatic task must:

1. resolve the Artifact;
2. invoke existing Task 011 publication;
3. receive `outcome = existing`;
4. finalize `publish_artifact` as succeeded;
5. create no new Git commit.

### Retained commit after database failure

When Task 011 creates a commit but its Artifact SHA database update fails:

```text
publish_artifact attempt
→ operational error
→ ProcessingTask retrying unless attempts exhausted
```

A later attempt must reuse Task 011’s existing reconciliation:

```text
find exact trailer-bearing commit
→ persist SHA
→ no duplicate commit
→ ProcessingTask succeeded
```

Task 012 must not implement a second retained-commit search.

### Duplicate delivery

At-least-once delivery may invoke the same publication task more than once.

Required outcome:

```text
one Artifact
one exact selected-path Git publication identity
one stored git_commit_sha
one terminal publish_artifact result
```

A duplicate delivery after task success is a no-op at claim time.

A duplicate delivery during an active attempt must not increment attempts or create a second commit.

### Publication error taxonomy

Extend the existing Task 011 exception hierarchy without changing the manual CLI’s public prefix.

Use a boundary equivalent to:

```python
class GitPublicationError(KnowledgeArtifactError):
    ...

class GitPublicationInvariantError(GitPublicationError):
    ...

class GitPublicationOperationalError(GitPublicationError):
    ...

class GitPublicationBusyError(GitPublicationOperationalError):
    ...

class GitPublicationTransactionError(GitPublicationInvariantError):
    ...
```

Exact subclass names may differ when live code supports a clearer small hierarchy, but worker classification must use exception types rather than message matching.

#### Permanent publication failures

Treat as permanent:

* Artifact missing;
* deterministic note Artifact missing for the Message;
* Artifact metadata inconsistency;
* absent, conflicting, or unsupported deterministic file;
* unsafe Artifact path;
* stored Git SHA malformed;
* stored object absent or not a commit;
* stored commit path or bytes inconsistent;
* malformed, duplicate, wrong, or ambiguous publication trailers;
* multiple matching publication commits;
* wrong Git top-level;
* application repository selected as knowledge base;
* bare repository;
* detached HEAD;
* missing repository-local author identity;
* dirty or unmerged index;
* history operation in progress;
* ignored selected path;
* Git filters changing staged bytes;
* transaction-contract misuse by caller.

These require configuration, repository, or data repair rather than blind repeated attempts.

#### Retryable publication failures

Treat as retryable, subject to existing attempt limits:

* publication lock busy;
* temporary lock-file open failure;
* Git executable temporarily unavailable;
* Git command timeout;
* Git subprocess execution OS failure;
* transient filesystem IO failure not classified as a deterministic file conflict;
* SQLAlchemy/database failure;
* database commit failure after Git commit;
* other explicitly typed operational publication failures.

Do not classify unknown exceptions as permanent merely because they derive from `GitPublicationError`.

Unexpected exceptions remain retryable until the existing maximum attempts are exhausted, while being sanitized as unexpected processing failures.

### Error sanitization

Extend `sanitize_processing_error(...)` with stable non-secret summaries.

At minimum:

```text
GitPublicationInvariantError: Git publication contract violation
GitPublicationOperationalError: Git publication operation failed
```

A busy-lock error may use:

```text
GitPublicationBusyError: Git publication already in progress
```

Requirements:

* no absolute repository path;
* no commit message body;
* no author identity;
* no Git stderr containing local paths;
* no environment contents;
* one line;
* existing maximum stored length.

Preserve existing Task 006 error summaries.

### Retry lifecycle

Publication tasks reuse:

```text
max_attempts = 3
PROCESSING_RETRY_BACKOFF = 5 seconds
running lease = 300 seconds
queued lease = 30 seconds
```

Do not add publication-specific retry counts or backoff constants.

An operational failure:

```text
running → retrying
```

unless the claimed attempt reaches the existing maximum.

A permanent failure:

```text
running → failed
```

immediately.

A worker crash:

```text
running lease expires
→ retrying or failed under existing recovery
```

### Runtime independence

Git publication must not affect:

* FastAPI startup;
* Telegram polling startup;
* app dispatcher startup;
* `/health`;
* database-only `/ready`;
* User/Message/`generate_note` persistence;
* Telegram acknowledgement;
* Task 006 deterministic processing;
* Redis-independent durable capture.

A missing or invalid knowledge-base Git repository affects only publication-task processing.

### No remote operations

Automatic publication must use only the existing local Task 011 boundary.

It must perform no:

```text
clone
fetch
pull
push
ls-remote
remote modification
GitHub API request
authentication
```

No remote URL or credential is required.

## Expected failure modes and recovery behavior

### Downstream insertion fails

Behavior:

```text
Task 006 processing may already have succeeded idempotently
generate_note finalization transaction rolls back
generate_note is not durably succeeded
no required downstream task is lost
```

Recovery:

```text
running lease expires
→ generate_note retries
→ Task 006 reconciles exact Artifact/file
→ finalization retries atomic downstream creation
```

### Downstream task already exists

Behavior:

```text
retain existing task unchanged
mark claimed generate_note succeeded
```

Do not create a duplicate or reset failed/retrying/succeeded state.

### Automatic creation disabled

Behavior:

```text
generate_note succeeds normally
no publication task created
```

Recovery or later enablement does not backfill that completed row.

### Existing publication task while setting disabled

Behavior:

```text
claim and process it normally
```

The setting is irrelevant after durable creation.

### Missing Artifact for publication task

Behavior:

```text
publish_artifact → failed permanently
```

Do not invoke Task 006 or recreate the Artifact.

### Publication repository lock busy

Behavior:

```text
publish_artifact → retrying
```

unless attempts are exhausted.

### Invalid knowledge-base repository

Wrong root, detached HEAD, missing author, dirty index, or invalid stored commit causes permanent task failure.

The valid note remains intact.

### Git commit succeeds but Artifact SHA update fails

Behavior:

```text
retain Git commit
rollback Artifact SHA update
publish_artifact → retrying
```

Later execution reconciles through Task 011.

### Worker crashes after Git and PostgreSQL publication commit but before task finalization

Behavior:

```text
Artifact.git_commit_sha is already valid
publish_artifact remains running
lease expires
later attempt calls Task 011
Task 011 returns existing
task succeeds
```

No duplicate commit is created.

### Worker crashes before publication completes

Existing running-lease recovery schedules another bounded attempt.

### Unsupported task type

Continue to fail closed without invoking Task 006 or Task 011.

### Stale finalizer

A late finalizer cannot:

* overwrite a newer attempt;
* create a downstream task;
* mark a changed task succeeded;
* reset an existing publication task.

### Redis unavailable

Durable pending or retrying tasks remain in PostgreSQL.

App startup, ingestion, `/health`, and `/ready` remain independent.

### Corrective pushed commit

Every pushed correction changes the PR head and requires:

* a new CI run;
* updated PR evidence;
* review of the new exact head.

## Tests

Add or update focused tests covering at least:

### Configuration

1. `git_publication_enabled` defaults to false.
2. `GIT_PUBLICATION_ENABLED=true` parses as true.
3. Disabled and enabled settings require no Git repository inspection.
4. Settings validation performs no Git, Redis, or database call.
5. Compose forwards the setting to app and worker.
6. CI default remains safe and secret-free.

### Task-type claim behavior

7. `generate_note` remains claimable.
8. `publish_artifact` becomes claimable.
9. ClaimedTask records the exact task type.
10. Unknown task type still becomes failed without consuming an attempt.
11. Terminal publication task is ignored.
12. Active running publication task is ignored.
13. Future retrying publication task is ignored.
14. Publication attempts increment exactly once.

### Disabled chaining

15. Successful `generate_note` with publication disabled becomes succeeded.
16. No `publish_artifact` task is created.
17. Existing Task 007 tests remain unchanged in outcome.

### Enabled chaining

18. Successful `generate_note` with publication enabled creates one pending publication task.
19. `generate_note` success and downstream insertion commit atomically.
20. Publication task has the same `message_id`.
21. Publication task uses `task_type = publish_artifact`.
22. Publication task starts with standard defaults.
23. Repeated finalization does not create a second publication task.
24. A stale finalizer creates no publication task.
25. An existing pending publication task is preserved.
26. Existing queued, running, retrying, succeeded, and failed publication tasks are preserved without reset.
27. Expected uniqueness conflict is handled without swallowing unrelated integrity failures.

### Finalization failure recovery

28. Injected downstream insertion failure rolls back `generate_note` success.
29. Injected finalization commit failure leaves no partial success/task pair.
30. Lease recovery makes the generate task retryable.
31. Repeated idempotent Task 006 processing can finalize successfully later.
32. Exactly one publication task exists after recovery.

### Artifact resolution

33. Existing note Artifact resolves by Message UUID.
34. Missing note Artifact is permanent.
35. Resolver creates no Artifact.
36. Resolver performs no rendering.
37. Resolver changes no Message or task state.
38. Database lookup failure is retryable.
39. The resolver’s transaction is closed before Task 011 receives its fresh session.

### Publication execution

40. `publish_artifact` dispatches to `publish_artifact_to_git(...)`.
41. It passes the resolved Artifact UUID.
42. It passes the configured knowledge-base root.
43. It does not invoke `process_text_message(...)`.
44. `created` result succeeds the task.
45. `reconciled` result succeeds the task.
46. `existing` result succeeds the task.
47. No downstream task follows successful publication.

### Manual-before-automatic behavior

48. Manual publication establishes `git_commit_sha`.
49. Later automatic publication returns existing.
50. No second Git commit is created.
51. Publication task becomes succeeded.

### Git/database recovery

52. Git commit retained after Artifact database failure is not removed.
53. The first publication attempt becomes retrying.
54. A later attempt reconciles the retained commit.
55. The later attempt creates no duplicate commit.
56. Artifact stores the retained commit SHA.
57. Publication task succeeds.

### Crash and lease recovery

58. Simulated crash after publication commit but before task finalization leaves the task running.
59. Expired lease moves it to retrying.
60. Later Task 011 invocation returns existing.
61. Task succeeds without duplicate commit.

### Error classification

62. publication lock contention is retryable.
63. Git timeout is retryable.
64. Git executable/OS failure is retryable.
65. SQLAlchemy failure is retryable.
66. Artifact inconsistency is permanent.
67. deterministic file conflict is permanent.
68. invalid stored SHA or commit is permanent.
69. ambiguous publication history is permanent.
70. wrong repository root is permanent.
71. detached HEAD is permanent.
72. dirty index is permanent.
73. classification uses exception types, not message strings.
74. manual CLI still catches the common publication base class and preserves its documented prefix.

### Error sanitization

75. permanent publication summary is stable and secret-free.
76. operational publication summary is stable and secret-free.
77. local paths and Git stderr are not stored.
78. summaries remain one line and bounded.
79. existing Task 006 summaries remain unchanged.

### Existing-task independence from configuration

80. A publication task created while enabled is processed after settings become disabled.
81. Dispatcher still selects it.
82. Worker still claims it.
83. It can succeed normally.
84. No new publication task is created from unrelated historical state.

### Duplicate delivery and concurrency

85. duplicate actor delivery creates at most one commit.
86. duplicate delivery does not double-increment attempts.
87. repository lock behavior remains owned by Task 011.
88. two publication tasks encountering repository lock contention use retry state rather than corrupting Git.
89. no unrelated knowledge-base path is committed.

### Regression

90. Task 006 focused tests pass unchanged.
91. Task 007 dispatcher and lease-recovery tests pass.
92. Task 011 publication and CLI tests pass.
93. Telegram authorization and ingestion tests pass.
94. migration head remains `0004`.
95. full authoritative pytest suite passes.
96. `CI / Test` succeeds on the exact current Task 012 head.

## Acceptance criteria

Task 012 is accepted only when all of the following are true:

1. Task 011’s standalone status correction is on `main`.
2. That correction changes only the Task 011 status line.
3. The correction has a successful default-branch CI run.
4. Task 012 branches from the corrected synchronized `main`.
5. The Task 012 contract is committed before implementation.
6. The exact contract path and full SHA are recorded in the PR.
7. No database migration is added.
8. The existing ProcessingTask schema is reused.
9. `publish_artifact` is the only new task type.
10. The actor payload remains ProcessingTask UUID only.
11. The dispatcher remains task-type agnostic.
12. The worker accepts exactly the two supported task types.
13. Unsupported task types still fail closed.
14. Claim results include task type.
15. `GIT_PUBLICATION_ENABLED` defaults to false.
16. The setting gates downstream creation only.
17. Existing publication tasks run even when the setting is false.
18. Disabled generation finalization creates no publication task.
19. Enabled successful generation atomically creates one publication task.
20. Generation success and downstream insertion cannot partially commit.
21. Stale finalizers create no downstream task.
22. Existing publication tasks are preserved without reset.
23. No backfill is implemented.
24. Publication task resolves the existing note Artifact by Message UUID.
25. Missing Artifact fails permanently.
26. Task 006 is not invoked by the publication task.
27. Task 011 is invoked unchanged for Git publication.
28. Manual-before-automatic publication creates no duplicate commit.
29. Retained-commit recovery creates no duplicate commit.
30. Publication success does not change Message status.
31. Publication failure does not invalidate the Artifact or file.
32. `generate_note` remains succeeded after later publication failure.
33. Publication uses existing attempts, leases, retry backoff, and terminal states.
34. Operational publication errors retry.
35. Deterministic publication invariant errors fail permanently.
36. Error classification uses exception types.
37. Stored errors are sanitized and bounded.
38. Task 011 exact-root validation remains unchanged.
39. Task 011 empty-index protection remains unchanged.
40. Task 011 selected-path-only commit behavior remains unchanged.
41. Task 011 repository and Artifact locking remain unchanged.
42. No remote Git operation exists.
43. App startup does not inspect the Git repository.
44. `/health` remains process liveness.
45. `/ready` remains database-only readiness.
46. Telegram ingestion and acknowledgement remain unchanged.
47. Redis remains delivery transport only.
48. PostgreSQL remains task-state authority.
49. No new queue, service, task table, target abstraction, or workflow DAG is added.
50. Focused configuration tests pass.
51. Focused chaining and finalization tests pass.
52. Focused publication recovery tests pass.
53. Task 006 regressions pass.
54. Task 007 orchestration regressions pass.
55. Task 011 publication regressions pass.
56. The full suite passes.
57. Migration head remains `0004`.
58. Documentation reflects the new durable stage.
59. D-031 or the live-confirmed next decision records the architecture.
60. `CI / Test` succeeds for the exact current pushed head.
61. The final working tree is clean.
62. Local and remote task-branch heads match.
63. The PR remains unmerged pending separate authorization.
64. Handoff Review approves the exact green head.

## Required verification commands

### Pre-task correction

```bash
git switch main
git fetch origin --prune
git status --short
git rev-list --left-right --count main...origin/main
git rev-parse HEAD
grep -n '^\*\*Status:\*\*' tasks/011-manual-git-artifact-publication.md

# Change only the status line.

git diff --check
git diff --name-only
git diff -- tasks/011-manual-git-artifact-publication.md
git add tasks/011-manual-git-artifact-publication.md
git diff --cached --check
git diff --cached --name-only
git commit -m "docs: mark task 011 completed"
git push origin main
gh run list --branch main --workflow ci.yml --limit 10
```

Require successful `CI / Test` for the correction commit.

### Task branch and contract

```bash
git fetch origin --prune
git switch main
git pull --ff-only
git status --short
git rev-list --left-right --count main...origin/main
git switch -c task/012-durable-automatic-git-publication
```

After writing the contract:

```bash
git add \
  tasks/012-durable-automatic-git-publication.md \
  docs/CURRENT_STATE.md

git diff --cached --check

git commit \
  -m "docs: define task 012 durable automatic Git publication"

git push -u origin task/012-durable-automatic-git-publication
```

Open the draft PR:

```bash
gh pr create \
  --draft \
  --base main \
  --head task/012-durable-automatic-git-publication \
  --title "Task 012: Add durable automatic Git publication for generated artifacts"
```

Record:

```bash
git rev-parse HEAD
gh pr view \
  --json number,title,state,isDraft,baseRefName,baseRefOid,headRefName,headRefOid,url,body
```

### Static and configuration checks

```bash
git diff --check
docker compose config --quiet
docker compose build app
docker compose run --rm -T app git --version
```

Inspect the rendered setting:

```bash
docker compose config | grep -n "GIT_PUBLICATION_ENABLED"
```

### Focused tests

Adapt exact filenames to live test organization:

```bash
docker compose up -d --wait --wait-timeout 90 postgres

docker compose run --rm -T --no-deps app \
  python -m pytest \
  tests/test_task_worker.py \
  tests/test_task_dispatcher.py \
  tests/test_git_publication.py \
  tests/test_git_cli.py \
  tests/test_artifact_processing.py \
  tests/test_processing_tasks.py \
  tests/test_settings.py
```

When the settings tests live in another existing module, use that path instead of creating a redundant file.

### Full suite

```bash
docker compose run --rm -T --no-deps app python -m pytest
```

### Migration boundary

```bash
docker compose run --rm -T --no-deps app alembic current
docker compose run --rm -T --no-deps app alembic heads
docker compose run --rm -T --no-deps app alembic history
```

Expected:

```text
current head = 0004
no Task 012 migration
```

### Focused manual chaining smoke

Use a disposable PostgreSQL row set and a disposable temporary knowledge-base Git repository.

The smoke must establish:

```text
one Message
one generate_note ProcessingTask
GIT_PUBLICATION_ENABLED=true
```

Then run the real processing path until:

```text
Message.status = done
generate_note.status = succeeded
publish_artifact.status = succeeded
Artifact.git_commit_sha is non-null
```

Verify:

```bash
git -C <temporary-knowledge-base> log --oneline --decorate
git -C <temporary-knowledge-base> show \
  <artifact-git-commit-sha>:<artifact-file-path>
```

The shown bytes must equal the deterministic file bytes.

Repeat or redeliver the publication task and verify the commit count does not increase.

Clean up every smoke row and temporary repository.

Do not use the developer’s real knowledge-base history as test state.

### Disabled-creation smoke

With:

```text
GIT_PUBLICATION_ENABLED=false
```

process one new `generate_note` task and verify:

```text
generate_note = succeeded
publish_artifact row count for message = 0
Artifact remains manually publishable
```

Clean up all smoke state.

### Existing-task-after-disable smoke

1. create a durable publication task while enabled;
2. restart or invoke the worker with creation disabled;
3. process the existing task;
4. verify it succeeds.

### Scope protection

```bash
git diff --check origin/main...HEAD
git diff --name-status origin/main...HEAD
```

Verify no Task 012 diff under:

```text
app/bot/
alembic/versions/
app/knowledge/markdown.py
app/knowledge/storage.py
```

unless a direct contract-approved contradiction was documented before editing.

Search for prohibited Git commands in automatic publication changes:

```bash
git diff origin/main...HEAD -- app \
  | grep -E '(^|[^a-z])(clone|fetch|pull|push|ls-remote)([^a-z]|$)' \
  && exit 1 || true
```

This search is only a supplemental review check; tests and code review remain authoritative.

### CI verification

After pushing implementation:

```bash
gh pr view \
  --json number,state,isDraft,baseRefOid,headRefOid,url

gh pr checks <pr-number> --watch

gh run list \
  --workflow ci.yml \
  --branch task/012-durable-automatic-git-publication \
  --event pull_request \
  --limit 10
```

Inspect the selected run:

```bash
gh run view <run-id> \
  --json databaseId,event,headBranch,headSha,status,conclusion,jobs,url
```

Require:

```text
check context = CI / Test
conclusion = success
tested source SHA = exact current PR head
```

### Final synchronization

```bash
git fetch origin --prune
git status --short
git rev-parse HEAD
git rev-parse origin/task/012-durable-automatic-git-publication
git diff --check
git diff --name-status origin/main...HEAD
git log --oneline --decorate origin/main..HEAD
```

Expected:

```text
local HEAD
=
remote task-branch HEAD
=
current PR head
=
head with successful CI / Test
```

## Documentation impact

### `README.md`

Document:

* `GIT_PUBLICATION_ENABLED`;
* default false behavior;
* automatic chaining when enabled;
* manual Task 011 CLI remains available;
* existing durable publication tasks continue when creation is disabled;
* no backfill;
* no remote Git operation;
* publication failure does not invalidate the note;
* required initialized local knowledge-base repository remains unchanged.

Do not duplicate the full Task 011 Git safety document.

### `docs/ARCHITECTURE.md`

Extend the runtime flow:

```text
generate_note succeeds
→ atomically establish publish_artifact
→ dispatcher
→ Redis
→ worker
→ Task 011 local Git publisher
→ publish_artifact succeeds
```

Document:

* Task 006 and Task 011 remain separate ownership boundaries;
* PostgreSQL owns both task states;
* publication failure is independent of note validity;
* the configuration gate affects downstream creation only;
* dispatcher and actor payload remain generic;
* no remote synchronization exists.

### `docs/DATA_MODEL.md`

No schema field is added.

Update ProcessingTask semantics to document two accepted task types:

```text
generate_note
publish_artifact
```

Document:

* one of each may exist for a Message;
* existing uniqueness enforces this;
* publication task points to the current note indirectly through `message_id`;
* no generic target or Artifact foreign key exists;
* `Artifact.git_commit_sha` remains the publication result.

### `docs/GIT_PUBLICATION.md`

Add the automatic execution section:

* manual and automatic callers share `publish_artifact_to_git(...)`;
* automatic worker resolution from Message to Artifact;
* error classification;
* ProcessingTask retries;
* retained-commit recovery;
* manual-before-automatic behavior;
* task-creation configuration gate;
* no remote operations.

Do not weaken or replace Task 011 repository rules.

### `docs/CURRENT_STATE.md`

After implementation and verified green CI:

* record automatic durable publication as implemented;
* show the complete two-stage processing flow;
* state that the feature defaults to disabled;
* state no backfill;
* distinguish Message done, generate success, and publication success;
* retain remote synchronization as not implemented;
* set:

  ```text
  **Active task:** none selected
  ```

Do not turn the file into a chronological run log.

### `docs/DECISIONS.md`

Add the next live-confirmed decision, expected:

```text
D-031 — Chain local Git publication through a second durable ProcessingTask
```

Record:

* separate `publish_artifact` stage;
* atomic success/downstream creation;
* setting gates creation only;
* existing tasks are configuration-independent;
* current message-scoped ProcessingTask model is reused;
* generic actor payload is unchanged;
* Task 006 and Task 011 remain sole implementation boundaries;
* publication errors are typed permanent or retryable;
* PostgreSQL owns retries;
* no backfill, remote synchronization, or generic DAG.

### `.env.example`

Add:

```text
GIT_PUBLICATION_ENABLED=false
```

with a concise safe comment where consistent.

### `docker-compose.yml`

Forward the safe value to app and worker.

Do not change service topology.

### Task file

After implementation, verification, push, and CI, update only status/completion evidence according to repository convention.

The immutable review contract remains the Task 012 file at its recorded contract commit SHA.

### Expected unchanged documentation

Do not update:

```text
docs/TELEGRAM_INGESTION.md
docs/MARKDOWN_ARTIFACTS.md
docs/PROJECT_BRIEF.md
docs/WORKFLOW.md
```

unless live implementation reveals a direct contradiction.

## Pull-request description requirements

The Task 012 PR description must include:

### Contract identity

```text
repository
task path
exact full contract SHA
base branch
base SHA
task branch
current pushed head SHA
```

### Pre-task correction

Record:

```text
Task 011 status-correction commit SHA
changed path
successful main-branch CI run
confirmation that it is absent from the Task 012 PR diff
```

### Outcome

Summarize:

* new task type;
* configuration gate;
* atomic downstream creation;
* processor dispatch;
* Artifact resolution;
* error classification;
* retry behavior;
* existing-task independence from the setting;
* absence of schema and remote changes.

### Changed paths

List every changed path and its responsibility.

Identify conditionally changed paths and explain why they were necessary.

### Verification

List every exact command as:

```text
pass
fail
not run
```

Include:

* Compose validation;
* image build;
* focused tests;
* full suite;
* migration-head verification;
* enabled chaining smoke;
* disabled creation smoke;
* existing-task-after-disable smoke;
* duplicate-delivery/idempotency verification;
* scope checks;
* CI.

### CI

Record:

```text
workflow: CI
check: CI / Test
run ID
run URL
event
tested head SHA
current PR head SHA
conclusion
```

### Documentation

List updated and intentionally unchanged documents.

### Risks and unverified items

Include:

* automatic creation defaults to false;
* no historical backfill;
* local Git repository must already satisfy Task 011;
* publication can fail independently of note generation;
* no remote synchronization;
* fixed retries may exhaust before an operator repairs a deterministic repository condition;
* no administrative retry command exists.

### Scope protection

Confirm:

* no migration;
* no Task 006 behavior change;
* no Task 011 Git-semantic weakening;
* no Telegram behavior change;
* no Redis payload change;
* no remote Git operation;
* no generated note or knowledge-base `.git` data committed to the application PR;
* no prohibited GitHub operation occurred.

## Review-head identity

Handoff Review must identify:

```text
repository
PR number
task path
contract SHA
base SHA
task branch
exact pushed head SHA
CI workflow
CI check
successful run ID
tested source SHA
```

Review must inspect:

* exact contract;
* complete PR patch;
* Task 011 status correction exclusion;
* task-type constants;
* claim behavior;
* processor dispatch;
* atomic finalization and downstream insertion;
* setting semantics;
* Artifact resolver;
* error taxonomy;
* retry and permanent-failure classification;
* Task 006 and Task 011 reuse;
* tests;
* documentation;
* successful CI result.

Approval applies only to the identified head.

## Correction behavior

Bounded corrections are authorized on the same Task 012 branch.

Expected message:

```text
fix: address Task 012 review findings
```

Corrections may change only:

* Task 012 task-type and worker orchestration code;
* publication exception classification;
* settings/Compose configuration;
* directly related tests;
* Task 012 documentation;
* PR-description evidence.

After every correction:

1. run relevant focused tests;
2. run the full suite when behavior changed;
3. push normally without force;
4. require a new successful `CI / Test`;
5. update the PR description;
6. review the new exact head.

Do not amend or rebase reviewed commits.

Do not rewrite the contract to hide a mismatch.

A migration, generic workflow graph, remote synchronization, or Task 006/011 redesign returns to Active Task Planning.

## Merge boundary

The accepted merge method is a normal merge commit.

Merge requires:

1. successful focused local verification;
2. successful full suite;
3. successful smoke verification;
4. successful `CI / Test` for the exact current head;
5. Handoff Review approval of that head;
6. separate explicit user authorization.

Task 012 does not authorize merge or branch deletion.

## Prohibited committed artifacts

Do not commit:

```text
knowledge-base/.git/
generated Markdown notes
temporary Git repositories
Git object databases
Git index or lock files
real author identity added for tests
real email added for tests
Git credentials
remote URLs containing credentials
Telegram tokens
Telegram user IDs
OpenAI or other provider keys
.env
local application configuration
database dumps
Redis dumps
pytest caches
coverage output
workflow logs
generated handoff files
review bundles
external completion reports
unrelated work
```

Use reserved test-only identities such as:

```text
PKM Test
pkm-test@example.invalid
```

## Expected commit boundaries

### Standalone pre-task correction

Expected message:

```text
docs: mark task 011 completed
```

Exact path:

```text
tasks/011-manual-git-artifact-publication.md
```

Exact change:

```text
Status: ready for review
→
Status: completed
```

This belongs to the corrected default-branch baseline and must not appear in the Task 012 PR diff.

### Contract commit

Expected message:

```text
docs: define task 012 durable automatic Git publication
```

Expected paths:

```text
tasks/012-durable-automatic-git-publication.md
docs/CURRENT_STATE.md
```

`docs/CURRENT_STATE.md` may change only to select Task 012 as active.

No code, configuration, test, migration, or implementation documentation belongs in this commit.

### Implementation commit

Expected message:

```text
feat: add durable automatic Git publication
```

Expected paths:

```text
app/settings.py
app/worker/constants.py
app/worker/processing.py
app/knowledge/errors.py
app/knowledge/git_publication.py
tests/test_task_worker.py
tests/test_git_publication.py
.env.example
docker-compose.yml
README.md
docs/ARCHITECTURE.md
docs/DATA_MODEL.md
docs/GIT_PUBLICATION.md
docs/CURRENT_STATE.md
docs/DECISIONS.md
tasks/012-durable-automatic-git-publication.md
```

One narrow new helper and its test are permitted when justified:

```text
app/worker/processors.py
tests/test_worker_processors.py
```

or an equivalently scoped path.

Conditionally permitted:

```text
tests/test_task_dispatcher.py
tests/conftest.py
app/db/models.py
Dockerfile
.github/workflows/ci.yml
```

The implementation commit must not include:

```text
Alembic migration
Telegram behavior change
Task 006 rendering/storage change
Task 011 Git commit-format change
remote Git behavior
new queue or service
generic DAG
AI work
deployment
branch protection
unrelated cleanup
```

### Correction commits

Expected message:

```text
fix: address Task 012 review findings
```

Corrections remain on:

```text
task/012-durable-automatic-git-publication
```

They may modify only paths directly required to make the accepted durable publication stage correct, recoverable, tested, documented, and green.

## Authorized application-repository operations

Authorized only for Task 012:

```text
task-branch creation
contract commit
task-branch push
draft PR creation
PR-description updates
implementation commit
implementation push
ready-for-review transition after green CI
bounded correction commits
bounded correction pushes
CI inspection
```

## Unauthorized operations

Unauthorized in the application repository:

```text
Task 012 push directly to main
force-push
amend of pushed reviewed commits
rebase of pushed reviewed commits
PR merge
branch deletion
repository-setting changes
```

Unauthorized in the knowledge-base repository:

```text
implicit initialization
clone
fetch
pull
push
remote modification
branch creation
branch switching
checkout
merge
rebase
cherry-pick
revert
history reset
clean
stash
force operations
submodule operations
worktree operations
bulk publication
```

The final Task 012 outcome is a reviewed, green, unmerged application pull request that adds one durable, independently retryable automatic local Git-publication stage while preserving Task 006 and Task 011 as the sole note-generation and Git-publication implementations.
