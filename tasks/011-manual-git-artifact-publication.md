# Task 011: Add a manual Git commit boundary for generated artifacts

**Status:** completed
**Depends on:** Tasks 000–010 and completion of the standalone Task 010 status correction
**Target file:** `tasks/011-manual-git-artifact-publication.md`
**Expected branch:** `task/011-manual-git-artifact-publication`
**Expected pull-request title:** `Task 011: Add a manual Git commit boundary for generated artifacts`
**Expected contract commit:** `docs: define task 011 manual Git artifact publication`
**Expected implementation commit:** `feat: add manual Git artifact publication`
**Expected correction commit:** `fix: address Task 011 review findings`
**Expected merge method:** normal merge commit, performed only after separate explicit user authorization

## Pre-task baseline correction

Before creating the Task 011 branch, correct the confirmed Task 010 documentation inconsistency:

```text
tasks/010-github-actions-ci.md

Status: ready for review
→
Status: completed
```

This correction:

* does not consume a task number;

* is not part of Task 011;

* must precede the Task 011 branch;

* must change only the Task 010 status line;

* must use the commit message:

  ```text
  docs: mark task 010 completed
  ```

* must receive a successful `CI / Test` result;

* must be present on the pushed default branch before Task 011 branches from it.

The user’s accepted Task 011 planning instruction authorizes exactly this one-path standalone documentation correction on the synchronized default branch.

It does not authorize any other direct default-branch change.

Before applying it, verify:

```bash
git switch main
git fetch origin --prune
git status --short
git rev-list --left-right --count main...origin/main
git rev-parse HEAD
```

Expected before the correction:

```text
current main:
1a26c73aa8a8801f753ffca314421beb5be9dac5

ahead/behind:
0	0

working tree:
clean
```

Then verify the correction diff contains only:

```text
tasks/010-github-actions-ci.md
```

After pushing the correction:

```bash
git fetch origin --prune
git rev-parse main
git rev-parse origin/main
git rev-list --left-right --count main...origin/main
gh run list --branch main --workflow ci.yml --limit 10
```

The resulting corrected `origin/main` SHA becomes the required Task 011 branch base.

If repository rules reject the direct documentation push, use one standalone documentation-only branch and pull request without a task number. Do not create Task 011 until that correction is merged and green.

## Git and pull-request authorization

After the pre-task correction is complete, this task authorizes Codex to perform only the following actions on:

```text
task/011-manual-git-artifact-publication
```

1. create or switch to the Task 011 branch from the corrected synchronized default branch;
2. create the distinct Task 011 contract commit;
3. push the task branch;
4. open or update one draft pull request targeting the verified default branch;
5. create one coherent Task 011 implementation commit;
6. push the implementation commit to the same task branch;
7. inspect the `CI / Test` result for the exact pushed head;
8. update the pull-request description;
9. mark the PR ready only after all local checks and `CI / Test` pass for the exact head;
10. create and push bounded correction commits when review or CI findings require them.

This task does **not** authorize Codex to:

* push Task 011 work directly to the default branch;
* merge the Task 011 pull request;
* delete the task branch;
* force-push;
* amend or rebase pushed reviewed commits;
* change repository visibility;
* configure branch protection;
* perform Git remote operations from the application;
* create, fetch, pull, push, merge, rebase, or switch branches in the knowledge-base repository;
* automatically initialize the knowledge-base repository;
* automatically invoke Git publication from the application or worker runtime.

A Task 011 merge requires separate explicit user authorization after approval of the exact current pushed head.

## Goal

Add one explicit, manually invoked local Git-publication boundary:

```text
existing valid Artifact
+ exact established Markdown file
+ initialized local knowledge-base Git repository
→ one local publication commit
→ commit SHA persisted on the Artifact
```

The reusable boundary and developer CLI must prove:

* exact repository-root selection;
* exact artifact-byte validation;
* selected-path-only commit behavior;
* idempotency;
* PostgreSQL/Git reconciliation;
* database-failure recovery;
* same-repository concurrency safety;
* preservation of unrelated working-tree state.

The resulting product flow remains two separate stages:

```text
Task 006 / Task 007:
Message
→ deterministic Markdown file
→ Artifact
→ Message done
→ ProcessingTask succeeded

Task 011 manual publication:
existing valid Artifact + exact file
→ local Git commit
→ Artifact.git_commit_sha
```

Task 011 must not connect these stages automatically.

## Confirmed current boundary

Live repository inspection confirms:

* Tasks 000–010 are user-confirmed complete.

* Task 010 was merged to `main`.

* The current confirmed Task 010 merge SHA is:

  ```text
  1a26c73aa8a8801f753ffca314421beb5be9dac5
  ```

* `tasks/010-github-actions-ci.md` still has the stale status `ready for review`.

* The repository has one GitHub Actions workflow named `CI`.

* The workflow has one job named `Test`.

* The observed pull-request check context is:

  ```text
  CI / Test
  ```

* CI builds the development app image, starts only PostgreSQL, and runs the complete pytest suite in a one-off app container.

* The current Dockerfile does not install the system Git executable.

* Docker Compose bind-mounts:

  ```text
  ./knowledge-base
  →
  /app/knowledge-base
  ```

  into both app and worker containers.

* `KNOWLEDGE_BASE_PATH` currently defaults to:

  ```text
  knowledge-base
  ```

* The configured knowledge-base root currently contains generated notes under:

  ```text
  inbox/
  ```

* Generated files are not committed by application code.

* Task 006 remains the sole deterministic Markdown-generation and filesystem-reconciliation boundary.

* `process_text_message(...)`:

  * owns its transaction;
  * locks the source Message;
  * validates persisted source fields;
  * renders deterministic Markdown;
  * validates or creates the Artifact;
  * establishes the exact file;
  * sets `Message.status = "done"`.

* The Artifact model currently contains:

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

* Artifact uniqueness is enforced by:

  * `(message_id, artifact_type)`;
  * `file_path`.

* No Git commit SHA, publication table, version table, branch field, remote field, or publication status exists.

* The latest current migration is `0003`.

* The expected Task 011 migration is therefore `0004`, subject to live verification.

* D-029 is the latest current durable decision.

* The expected next durable decision is D-030, subject to live verification.

* The current test suite uses isolated PostgreSQL state and committed Alembic migrations.

* Artifact and worker tests already use pytest temporary directories for filesystem behavior.

* Task 011 is the next unused task number in the current repository evidence.

* No Task 011 branch or task file was found during connected repository inspection.

Local-only facts such as the current contents of the developer’s `knowledge-base/`, its Git status, Git version, ownership, and Git author configuration must be reverified by Codex before implementation.

## Repository verification requirements

Before editing, Codex must inspect and report the corrected live repository state.

### Application repository

Run:

```bash
git branch --show-current
git rev-parse HEAD
git status --short
git log --oneline --decorate -12
git remote -v
git fetch origin --prune
git remote show origin
git diff --stat
git diff --check
git rev-list --left-right --count main...origin/main
gh auth status
gh repo view --json nameWithOwner,visibility,defaultBranchRef
gh pr list --state all \
  --head task/011-manual-git-artifact-publication \
  --json number,title,state,isDraft,baseRefName,headRefName,headRefOid,url
```

Verify:

* the Task 010 status correction is present on `origin/main`;
* its CI result passed;
* the default branch is clean and synchronized;
* no Task 011 branch or PR conflicts with this task;
* no unrelated work would enter either Task 011 commit;
* `tasks/011-manual-git-artifact-publication.md` is the next repository-consistent task file;
* D-030 and migration `0004` are the next available identifiers.

If unrelated local work exists, do not stash, discard, move, commit, or overwrite it automatically.

### Knowledge-base layout

Inspect:

```bash
find knowledge-base -maxdepth 3 -mindepth 1 -print | sort
git status --short -- knowledge-base
git check-ignore -v knowledge-base knowledge-base/* 2>/dev/null || true
```

When `knowledge-base/` is already a Git repository, inspect it directly:

```bash
git -C knowledge-base --version
git -C knowledge-base rev-parse --is-inside-work-tree
git -C knowledge-base rev-parse --show-toplevel
git -C knowledge-base rev-parse --is-bare-repository
git -C knowledge-base symbolic-ref --quiet --short HEAD
git -C knowledge-base status --porcelain=v1 --untracked-files=all
git -C knowledge-base diff --cached --name-only
git -C knowledge-base config --local --get user.name
git -C knowledge-base config --local --get user.email
```

Classify:

* whether `knowledge-base/` is already initialized;
* whether its exact top-level is the configured root;
* whether Git is instead discovering the application repository;
* whether it is a normal working tree;
* whether HEAD is attached to a named branch;
* whether that branch is unborn;
* whether the index is empty;
* whether unrelated unstaged or untracked files exist;
* whether repository-local author identity is configured;
* whether the selected generated path is ignored;
* whether the repository is rejected as unsafe because of bind-mount ownership.

The application repository and knowledge-base repository may be physically nested, but they must be distinct Git boundaries.

Task 011 must never accept the application repository as the knowledge-base Git root.

### Container and Git environment

Inspect:

```bash
docker compose config --quiet
docker compose build app
docker compose run --rm -T app git --version
docker compose run --rm -T app id
docker compose run --rm -T app \
  sh -c 'stat -c "%u:%g %n" /app/knowledge-base || true'
```

Before the Dockerfile change, absence of `git` is an expected finding.

Determine and report:

* the exact Git version after installation;
* the base image package manager;
* the smallest package-installation change;
* the container UID/GID;
* bind-mount ownership;
* whether command-scoped `safe.directory` is required;
* whether the knowledge-base `.git` directory is visible inside the app container;
* whether repository-local `user.name` and `user.email` are readable inside the container.

Do not modify global or system Git configuration as part of repository implementation.

### Relevant implementation

Read:

```text
app/db/models.py
app/db/session.py
app/knowledge/processing.py
app/knowledge/storage.py
app/knowledge/errors.py
app/knowledge/cli.py
app/knowledge/markdown.py
app/worker/processing.py
Dockerfile
docker-compose.yml
alembic/versions/
tests/conftest.py
tests/test_models.py
tests/test_migrations.py
tests/test_artifact_processing.py
tests/test_knowledge_cli.py
tests/test_task_worker.py
```

Verify that no later repository change already introduces:

* Git publication;
* a Git SHA column;
* a publication task;
* an automatic commit hook;
* a competing Artifact-validation boundary.

Any contradiction must be reported before implementation and must not be hidden by rewriting the task after work begins.

## Problem or motivation

Generated Markdown is currently durable on the filesystem and represented by an Artifact row, but it has no local repository-history boundary.

The project eventually intends to use Git-backed Markdown, but directly adding automatic worker commits would combine several unresolved concerns:

* Git and PostgreSQL cannot commit atomically;
* duplicate worker delivery is expected;
* the knowledge-base path may be nested inside the application repository;
* unrelated working-tree state may exist;
* the Git index may already contain user work;
* author configuration and ownership differ between host and container;
* a successful Git commit can outlive a failed database update;
* local Git and future remote synchronization are separate responsibilities.

Task 011 isolates these concerns behind one manual operation before introducing automatic scheduling or remote synchronization.

## Scope

Implement the following bounded outcome:

1. correct Task 010’s stale status before Task 011 branch creation;
2. add nullable `Artifact.git_commit_sha`;
3. add migration `0004`;
4. add one read-only existing-Artifact validation boundary that reuses Task 006 logic;
5. add one narrowly scoped local Git-publication module;
6. add one manual CLI accepting an Artifact UUID;
7. require the configured knowledge-base root itself to be the Git top-level;
8. reject parent-repository discovery;
9. require an existing initialized non-bare repository;
10. require an attached named branch while allowing its first commit;
11. require repository-local author name and email;
12. require an empty Git index;
13. allow unrelated unstaged and untracked paths;
14. stage and commit only the selected Artifact path;
15. verify staged and committed bytes;
16. record stable Artifact metadata in the commit message;
17. reconcile an existing exact publication commit;
18. validate a previously stored commit SHA;
19. preserve a Git commit when the PostgreSQL update fails;
20. serialize publication operations within one knowledge-base repository;
21. add Git to the authoritative application image;
22. add focused Git/PostgreSQL integration tests;
23. update current architecture, data-model, domain, CLI, and operational documentation;
24. require a successful `CI / Test` result on the exact implementation head.

## Out of scope

Do not add:

* automatic publication from Telegram ingestion;
* automatic publication from `process_text_message(...)`;
* automatic publication from TaskDispatcher;
* automatic publication from Dramatiq;
* a new ProcessingTask type;
* publication states on ProcessingTask;
* publication attempts, leases, or retries;
* a publication queue;
* a publication scheduler;
* bulk publication;
* committing multiple pending Artifacts;
* remote creation;
* remote validation;
* clone;
* fetch;
* pull;
* push;
* GitHub API use;
* GitHub authentication;
* branch creation or switching in the knowledge-base repository;
* merge;
* rebase;
* cherry-pick;
* revert;
* reset of Git history;
* force operations;
* automatic repository initialization;
* submodule creation;
* worktree creation;
* automatic Git configuration;
* GitPython, Dulwich, or another Git library;
* a generic source-control abstraction;
* a publication-history table;
* a publication-event table;
* branch, remote, or repository models;
* artifact revisions;
* content-addressed storage;
* Git history UI;
* deployment;
* release automation;
* AI processing;
* voice, image, link, file, or PDF ingestion;
* unrelated Telegram, Redis, worker, CI, branch-protection, or workflow refactoring.

## Affected components

Expected changes:

```text
app/db/models.py
app/knowledge/processing.py
app/knowledge/errors.py
app/knowledge/git_publication.py
app/knowledge/git_cli.py
alembic/versions/0004_add_artifact_git_commit_sha.py
tests/test_models.py
tests/test_migrations.py
tests/test_git_publication.py
tests/test_git_cli.py
Dockerfile
README.md
docs/ARCHITECTURE.md
docs/DATA_MODEL.md
docs/MARKDOWN_ARTIFACTS.md
docs/GIT_PUBLICATION.md
docs/CURRENT_STATE.md
docs/DECISIONS.md
tasks/011-manual-git-artifact-publication.md
```

Conditionally allowed only when live inspection proves a direct minimal need:

```text
app/settings.py
docker-compose.yml
.env.example
.gitignore
.dockerignore
tests/conftest.py
.github/workflows/ci.yml
```

Expected unchanged:

```text
app/bot/
app/worker/
app/knowledge/markdown.py
Telegram responses
Telegram authorization
Message ingestion transaction
ProcessingTask model and migrations
ProcessingTask lifecycle
Redis topology
deterministic Markdown format
deterministic artifact paths
Task 006 file-publication semantics
/health
/ready
GitHub collaboration workflow
branch protection
```

## Data, state, migration, and configuration impact

### Artifact model

Add exactly:

```text
git_commit_sha    TEXT nullable
```

to `Artifact`.

Use:

```python
git_commit_sha: Mapped[str | None] = mapped_column(Text)
```

Do not add:

* an index;
* a uniqueness constraint;
* a foreign key;
* a database-level Git-object-format constraint;
* a publication status;
* a publication timestamp;
* a branch or remote field.

The application stores only a canonical full hexadecimal object ID returned by Git.

The `TEXT` type is intentional:

* existing string metadata uses `TEXT`;
* the field is application-validated;
* it avoids hard-coding SHA-1 length;
* it permits a future repository object format without a schema migration.

### Migration

Create:

```text
0004_add_artifact_git_commit_sha.py
```

with:

```text
revision = "0004"
down_revision = "0003"
```

Upgrade:

```text
add nullable artifacts.git_commit_sha
```

Downgrade:

```text
drop artifacts.git_commit_sha
```

Existing Artifact rows must receive `NULL`.

The migration must not backfill by inspecting the filesystem or Git.

### Application settings

Do not add a separate Git-root setting.

The existing:

```text
KNOWLEDGE_BASE_PATH
```

is both:

* the Markdown artifact root;
* the required Git working-tree top-level.

The publisher must reject any repository whose reported top-level differs from the resolved configured root.

### Repository initialization

Repository initialization is documentation-only.

The implementation must never call:

```text
git init
```

Developers initialize and configure the repository explicitly, for example:

```bash
git -C <knowledge-base-root> init
git -C <knowledge-base-root> config --local user.name "<desired commit author>"
git -C <knowledge-base-root> config --local user.email "<desired commit email>"
```

These values remain in the knowledge-base repository’s local `.git/config` and are not committed to the application repository.

### Docker image

Install the system `git` package in the shared application image using the smallest base-image-consistent package operation.

Remove package-manager cache files in the same image layer.

Do not add GitPython or another Python Git dependency.

The worker receives the same image because app and worker already share it, but Task 011 must not invoke Git from the worker.

## Behavioral requirements

### Public function

Add:

```python
@dataclass(frozen=True)
class GitPublicationResult:
    artifact_id: uuid.UUID
    file_path: str
    git_commit_sha: str
    outcome: Literal["created", "reconciled", "existing"]


async def publish_artifact_to_git(
    session: AsyncSession,
    artifact_id: uuid.UUID,
    knowledge_base_root: Path,
) -> GitPublicationResult:
    ...
```

The function:

* requires a session without an active transaction;
* owns commit and rollback of the Artifact update;
* performs no remote operation;
* does not initialize or switch the repository;
* does not create or modify the Markdown file;
* does not create an Artifact;
* does not modify the Message;
* does not modify a ProcessingTask.

### Existing-Artifact validation

Add or expose one read-only validation helper under the Task 006 knowledge boundary.

It must:

1. load the Artifact by Artifact UUID;
2. lock that Artifact row with PostgreSQL `FOR UPDATE` when used for publication;
3. load its source Message;
4. reuse Task 006 source and metadata validation;
5. reuse the existing deterministic renderer only to calculate expected validation bytes;
6. resolve the persisted Artifact path through existing path-safety logic;
7. require the existing file to be a regular file with exact expected bytes;
8. fail if the file is absent, conflicting, unsupported, or escapes the root;
9. perform no file publication or repair;
10. perform no Artifact creation or metadata correction;
11. perform no Message status change.

This is read-only validation of the established Task 006 contract.

It is not a second Markdown-processing implementation.

### CLI

Add:

```bash
python -m app.knowledge.git_cli --artifact-id <artifact-uuid>
```

The documented Compose invocation is:

```bash
docker compose exec app \
  python -m app.knowledge.git_cli --artifact-id <artifact-uuid>
```

The CLI accepts an Artifact UUID, not a Message UUID.

Success prints exactly:

```text
artifact_id: <artifact-uuid>
file_path: <repository-relative-path>
git_commit_sha: <full-commit-sha>
outcome: created|reconciled|existing
```

Expected failures print one concise line to stderr:

```text
artifact Git publication failed: <reason>
```

and return exit status `1`.

Invalid CLI syntax remains argparse exit status `2`.

The command must not start:

* FastAPI;
* Telegram polling;
* the dispatcher;
* Redis;
* a worker.

### Git subprocess boundary

Use the local system `git` executable through explicit argument arrays.

Requirements:

* never use `shell=True`;

* never interpolate a command string;

* always pass paths after `--`;

* use the validated repository-relative Artifact path;

* use a bounded subprocess timeout;

* capture stdout and stderr;

* sanitize failure messages;

* do not expose arbitrary environment values;

* set `GIT_TERMINAL_PROMPT=0`;

* remove inherited repository-redirection variables such as:

  ```text
  GIT_DIR
  GIT_WORK_TREE
  GIT_INDEX_FILE
  GIT_OBJECT_DIRECTORY
  GIT_ALTERNATE_OBJECT_DIRECTORIES
  ```

* apply command-scoped:

  ```text
  safe.directory=<resolved knowledge-base root>
  ```

  to the Git subprocesses;

* do not write global or system Git configuration.

Only local inspection and commit commands are allowed.

No Git command may contact a remote.

### Repository-root validation

Before reading or changing Git state, require:

```text
git executable available
inside a working tree = true
bare repository = false
reported Git top-level = resolved KNOWLEDGE_BASE_PATH
HEAD attached to a named branch
no merge, rebase, cherry-pick, or revert operation in progress
```

Reject when:

* the root is not a Git repository;
* Git discovers only a parent repository;
* the top-level is the application repository;
* the repository is bare;
* HEAD is detached;
* repository metadata is unreadable;
* the repository is in an in-progress history operation.

An attached unborn branch is supported.

The publisher must not create or switch the branch.

### Git author identity

Require nonblank repository-local values for:

```text
user.name
user.email
```

Read them with local Git configuration scope.

Do not silently fall back to:

* committed application settings;
* a hard-coded production identity;
* Telegram identity;
* Artifact title;
* global host configuration alone.

Tests must configure deterministic test-only values such as:

```text
PKM Test
pkm-test@example.invalid
```

### Repository-wide publication lock

Serialize all publication operations for one knowledge-base repository.

Use an exclusive non-blocking filesystem lock at a Git-private path derived through:

```text
git rev-parse --git-path pkm-artifact-publication.lock
```

The lock:

* is inside Git metadata;
* is never tracked;
* protects HEAD and index mutations across different Artifacts;
* is held through Git inspection, commit creation, and PostgreSQL finalization;
* causes a clear busy failure when already held;
* is released on every success and failure path.

Do not wait indefinitely.

Artifact row locking remains required in addition to this repository-wide lock.

The repository lock protects Git-wide state.

The Artifact row lock protects the selected Artifact’s PostgreSQL publication state.

### Index and working-tree policy

Require the real Git index to be empty before publication.

Fail when:

* any unrelated path is staged;
* the selected Artifact path is staged;
* an unmerged index entry exists.

Do not modify or clear pre-existing staged state.

Unrelated unstaged and untracked files are allowed.

They must remain byte-for-byte and status-for-status unchanged after success or failure.

The selected Artifact path may currently be:

* untracked;
* tracked and modified;
* tracked and already equal to HEAD.

It must always contain the exact Task 006 bytes.

If the selected path is ignored, fail.

Do not use forced staging.

### Selected-path staging

Stage only:

```text
Artifact.file_path
```

After staging, verify:

* the staged path set is either:

  * exactly the selected path; or
  * empty because HEAD already contains the exact selected bytes;

* no second path is staged;

* the staged or existing HEAD blob equals the exact Task 006 bytes.

Git filters, line-ending conversion, attributes, or other configuration must not silently change the committed bytes.

If staged bytes differ from the expected bytes, fail and restore only the selected index entry.

### Commit behavior

Use this stable subject:

```text
Publish artifact <artifact-uuid>
```

Use this trailer block:

```text
PKM-Artifact-ID: <artifact-uuid>
PKM-Artifact-Path: <repository-relative-path>
```

Do not include:

* source text;
* title;
* Telegram identity;
* Telegram chat ID;
* usernames;
* secrets;
* absolute filesystem paths.

Create the commit with:

* no editor;
* no GPG signing;
* an explicit message supplied through stdin or a temporary file;
* all repository hooks disabled through an empty temporary hooks directory;
* `--allow-empty`.

An empty publication commit is allowed only when:

* HEAD already contains the exact expected bytes at the exact path;
* no existing matching publication trailer exists;
* a dedicated publication identity commit is still required.

The resulting commit tree must contain the exact expected bytes at the exact Artifact path.

### Hook isolation

Repository hooks must not execute.

The commit command must use an empty temporary `core.hooksPath`.

This prevents a local pre-commit, prepare-commit-msg, commit-msg, post-commit, or other hook from:

* modifying unrelated files;
* staging additional files;
* changing the commit message;
* performing remote operations;
* introducing hidden side effects.

Tests must prove that a configured sentinel hook does not execute.

### Existing publication lookup

When `Artifact.git_commit_sha` is `NULL`, search local commit history for the exact trailer:

```text
PKM-Artifact-ID: <artifact-uuid>
```

Search only existing local commit objects reachable from local branch or tag refs and the current HEAD.

Do not fetch.

For every candidate with that Artifact ID, validate:

* the Artifact-path trailer occurs exactly once;
* its value equals `Artifact.file_path`;
* the commit contains the path;
* the path’s blob bytes equal the expected Task 006 bytes;
* the object is a commit.

Outcomes:

```text
no candidate
→ create one publication commit

exactly one valid candidate
→ persist its SHA
→ outcome = reconciled

multiple candidates
→ fail closed

candidate with mismatching path or bytes
→ fail closed

candidate with malformed or duplicate required trailers
→ fail closed
```

Do not reconcile an arbitrary commit that lacks the stable Artifact-ID trailer.

### Stored commit validation

When `Artifact.git_commit_sha` is non-null:

1. require a canonical full hexadecimal Git object ID;
2. require the object to exist locally;
3. require it to be a commit;
4. require exactly one matching Artifact-ID trailer;
5. require exactly one matching Artifact-path trailer;
6. require the commit to contain the exact path;
7. require the committed blob to equal the expected Task 006 bytes.

When all checks pass:

```text
outcome = existing
no new commit
no database mutation except normal transaction completion
```

Any missing object, wrong object type, malformed trailer, wrong Artifact ID, wrong path, missing blob, or different bytes fails closed.

Do not rewrite `git_commit_sha` to another commit automatically.

### Create-and-persist sequence

For a new publication:

```text
validate repository
→ acquire repository lock
→ require clean index
→ lock Artifact row
→ validate Artifact + Message + exact file
→ search for existing publication commit
→ stage selected path only
→ verify staged bytes
→ create commit
→ inspect commit and exact blob
→ set Artifact.git_commit_sha
→ commit PostgreSQL
→ return created
```

If an existing exact commit is found:

```text
validate repository
→ acquire repository lock
→ require clean index
→ lock Artifact row
→ validate Artifact + exact file
→ validate matching commit
→ set Artifact.git_commit_sha
→ commit PostgreSQL
→ return reconciled
```

### Git/PostgreSQL failure boundary

Git and PostgreSQL do not share a transaction.

If Git fails before creating a commit:

```text
rollback PostgreSQL
→ restore only the selected path’s index entry when this invocation staged it
→ preserve working-tree bytes
→ preserve unrelated state
→ no git_commit_sha
```

If Git creates the commit but PostgreSQL flush or commit fails:

```text
retain Git commit
→ rollback PostgreSQL
→ retain git_commit_sha = null
→ do not reset HEAD
→ do not revert the commit
→ do not delete the commit
```

A later invocation must find the exact trailer-bearing commit and reconcile it.

### Index cleanup after failed Git commit

The index is required to be clean before publication.

If this invocation stages the selected path but fails before commit creation:

* restore only that path’s index entry;
* never alter its working-tree bytes;
* never touch another path;
* use an index-only, path-specific operation;
* support both existing HEAD and an unborn branch;
* test both tracked and untracked selected paths.

A targeted:

```text
git restore --staged --source=HEAD -- <path>
```

or unborn-branch equivalent is permitted only for this narrowly tested cleanup boundary.

Do not use:

```text
git reset --hard
git checkout
git clean
git stash
```

If path-specific index cleanup also fails, report both failures and state clearly that manual index inspection is required.

### Remote prohibition

The implementation must never execute:

```text
clone
fetch
pull
push
remote
ls-remote
submodule
worktree
branch
switch
checkout
merge
rebase
cherry-pick
revert
reset
clean
stash
```

except for the narrowly approved path-specific index restoration described above.

No network credential is required.

## Expected failure modes and recovery behavior

### Git executable missing

Fail before database mutation:

```text
Git executable is unavailable
```

The Dockerfile and CI tests must prevent this in the authoritative environment.

### Root is not the exact repository

Fail when `rev-parse --show-toplevel` differs from the configured root.

Do not fall back to the parent application repository.

### Repository not initialized

Fail with a clear instruction to initialize it manually.

Do not call `git init`.

### Detached HEAD

Fail before staging.

Do not create a detached publication commit.

### Unborn named branch

Allow the first publication commit.

Recovery and index-cleanup tests must cover this case.

### Missing author configuration

Fail before staging or database mutation.

Do not invent an identity.

### Dirty index

Fail without changing either repository or PostgreSQL.

Report that staged or unmerged state must be resolved manually.

### Unrelated unstaged state

Allow it.

Verify it is preserved.

### Ignored selected path

Fail without forced staging.

### Artifact or file inconsistency

Fail when:

* Artifact does not exist;
* source Message does not exist;
* Artifact metadata differs from Task 006 expectations;
* file is absent;
* file bytes differ;
* path is unsafe;
* path is a symlink or another unsupported entry.

Do not recreate or repair anything.

### Repository lock busy

Fail clearly and leave Git and PostgreSQL unchanged.

### Commit-command failure

Rollback PostgreSQL and restore only the selected index entry.

Preserve all working-tree files.

### Database failure after Git commit

Retain the Git commit and rollback PostgreSQL.

The next invocation must reconcile it without creating another commit.

### Stored SHA inconsistency

Fail closed.

Do not clear or replace the stored SHA automatically.

### Ambiguous publication history

Multiple matching Artifact-ID commits fail closed and require manual investigation.

### New pushed application commit

Any Task 011 correction changes the PR head and requires a new successful `CI / Test` result and review.

## Tests

Add focused tests covering at least:

### Model and migration

1. new Artifact defaults to `git_commit_sha = NULL`;
2. full canonical SHA can be persisted;
3. migration `0004` upgrades existing Artifact rows with null SHA;
4. downgrade to `0003` removes only the SHA column;
5. downgrade preserves User, Message, Artifact, ProcessingTask, and Message-status state;
6. re-upgrade restores the nullable column without inventing values.

### Repository validation

7. exact repository top-level succeeds;
8. parent-only repository is rejected;
9. application repository is never used accidentally;
10. missing repository fails;
11. bare repository fails;
12. detached HEAD fails;
13. unborn named branch succeeds;
14. merge or rebase in progress fails;
15. missing local author name fails;
16. missing local author email fails;
17. bind-mount-style ownership is handled only through exact command-scoped safe-directory configuration.

### Artifact validation

18. missing Artifact fails;
19. invalid Artifact metadata fails;
20. absent file fails;
21. conflicting file fails;
22. symlink or unsupported file fails;
23. exact Task 006 file succeeds;
24. validation does not recreate the file;
25. validation does not alter Message status;
26. validation does not create a new Artifact.

### Selected-path isolation

27. unrelated staged path causes failure and remains staged;
28. selected path already staged causes failure and remains staged;
29. unrelated unstaged tracked change is allowed and preserved;
30. unrelated untracked file is allowed and preserved;
31. only the selected path enters the new commit;
32. selected untracked file can be committed;
33. selected tracked modification can be committed;
34. selected path already exact in HEAD produces a dedicated empty publication commit;
35. ignored selected path fails;
36. a Git filter or attribute that changes staged bytes fails before commit;
37. commit hooks do not execute.

### Commit semantics

38. commit subject matches the exact convention;
39. Artifact-ID trailer occurs exactly once;
40. Artifact-path trailer occurs exactly once;
41. committed path is exact;
42. committed bytes equal Task 006 bytes;
43. no unrelated file enters the commit;
44. returned SHA equals the created commit;
45. PostgreSQL stores the same SHA;
46. outcome is `created`.

### Idempotency and reconciliation

47. repeated invocation with valid stored SHA creates no commit;
48. stored SHA returns outcome `existing`;
49. null SHA plus one exact matching commit stores that SHA;
50. reconciliation creates no second commit;
51. reconciliation returns outcome `reconciled`;
52. database failure after Git commit leaves SHA null;
53. the later invocation reconciles the retained commit;
54. missing stored object fails;
55. stored non-commit object fails;
56. stored commit missing the path fails;
57. stored commit with wrong bytes fails;
58. stored commit with wrong trailers fails;
59. multiple matching publication commits fail.

### Concurrency

60. same-repository lock prevents concurrent commits for the same Artifact;
61. same-repository lock prevents concurrent commits for different Artifacts;
62. lock failure changes neither Git nor PostgreSQL;
63. Artifact row is selected with `FOR UPDATE`;
64. repeated same-Artifact publication produces at most one commit.

### Failure cleanup

65. failure after staging restores the selected index state;
66. tracked selected-path cleanup preserves working bytes;
67. untracked selected-path cleanup preserves the file;
68. unborn-branch cleanup leaves the index clean;
69. unrelated working-tree state remains unchanged;
70. cleanup failure reports both the primary and cleanup failure.

### CLI

71. Artifact UUID is required;
72. invalid UUID is rejected by argparse;
73. success output is exact;
74. created, reconciled, and existing outcomes print correctly;
75. expected publication errors return `1`;
76. SQLAlchemy and Git command errors return `1`;
77. CLI starts no Telegram, dispatcher, Redis, worker, or FastAPI runtime.

### Regression

78. Task 006 artifact-processing tests pass unchanged;
79. Task 007 worker and ProcessingTask tests pass unchanged;
80. complete authoritative pytest suite passes;
81. `CI / Test` passes on the exact pushed Task 011 head.

## Acceptance criteria

Task 011 is accepted only when:

1. the standalone Task 010 status correction is on `main`;
2. that correction changes only the Task 010 status;
3. the corrected `main` received a green CI result;
4. Task 011 branches from the corrected pushed `main`;
5. the Task 011 contract is committed before implementation;
6. the contract path and full SHA are recorded in the PR;
7. migration `0004` adds only nullable `Artifact.git_commit_sha`;
8. no generic publication table or status framework is added;
9. `KNOWLEDGE_BASE_PATH` remains the single root setting;
10. the configured root must equal Git’s exact top-level;
11. parent-repository discovery is rejected;
12. implicit `git init` is absent;
13. detached HEAD is rejected;
14. an unborn named branch is supported;
15. local Git author name and email are required;
16. the real Git index must be empty;
17. unrelated staged state is never modified;
18. unrelated unstaged and untracked state is preserved;
19. ignored selected paths fail;
20. only the selected Artifact path may enter a commit;
21. committed bytes equal the exact Task 006 bytes;
22. Task 006 rendering and publication behavior remain unchanged;
23. the publisher never creates or repairs an Artifact or file;
24. the publisher never changes Message status;
25. the publisher never changes ProcessingTask state;
26. commit subject and trailers follow the exact convention;
27. a Git commit SHA is persisted only after commit validation;
28. a valid stored SHA is idempotent;
29. one exact retained commit is reconciled;
30. duplicate or inconsistent matching commits fail closed;
31. a Git commit retained after database failure is recoverable;
32. no compensating Git history rewrite occurs;
33. repository-wide locking protects index and HEAD;
34. Artifact row locking protects the selected database row;
35. hooks cannot run;
36. no remote Git command exists;
37. system Git is present in the authoritative image;
38. no Git Python library is added;
39. focused tests pass;
40. migration downgrade/re-upgrade tests pass;
41. Task 006 and Task 007 regressions pass;
42. the complete suite passes;
43. `CI / Test` succeeds for the exact current PR head;
44. architecture, data-model, domain, current-state, decision, README, and CLI documentation are current;
45. no automatic worker publication is added;
46. no branch protection, deployment, or remote synchronization is added;
47. the final working tree is clean;
48. local and remote task-branch heads match;
49. the PR remains unmerged pending separate authorization;
50. Handoff Review approves the exact green head.

## Required verification commands

### Pre-task status correction

```bash
git switch main
git fetch origin --prune
git status --short
git rev-list --left-right --count main...origin/main
git rev-parse HEAD
grep -n '^\*\*Status:\*\*' tasks/010-github-actions-ci.md

# Make only the one-line correction.

git diff --check
git diff -- tasks/010-github-actions-ci.md
git diff --name-only
git add tasks/010-github-actions-ci.md
git diff --cached --check
git diff --cached --name-only
git commit -m "docs: mark task 010 completed"
git push origin main
gh run list --branch main --workflow ci.yml --limit 10
```

Require a successful run for the correction commit before Task 011 branch creation.

### Task branch bootstrap

```bash
git fetch origin --prune
git switch main
git pull --ff-only
git status --short
git rev-list --left-right --count main...origin/main
git switch -c task/011-manual-git-artifact-publication
```

After the contract commit:

```bash
git rev-parse HEAD
git show --stat --oneline HEAD
git status --short
git push -u origin task/011-manual-git-artifact-publication
gh pr create \
  --draft \
  --base main \
  --head task/011-manual-git-artifact-publication \
  --title "Task 011: Add a manual Git commit boundary for generated artifacts"
```

### Static and focused verification

```bash
git diff --check
docker compose config --quiet
docker compose build app
docker compose run --rm -T app git --version

docker compose up -d --wait --wait-timeout 90 postgres

docker compose run --rm -T --no-deps app \
  python -m pytest \
  tests/test_models.py \
  tests/test_migrations.py \
  tests/test_git_publication.py \
  tests/test_git_cli.py \
  tests/test_artifact_processing.py \
  tests/test_knowledge_cli.py \
  tests/test_task_worker.py
```

### Complete authoritative suite

```bash
docker compose run --rm -T --no-deps app python -m pytest
```

### Migration inspection

```bash
docker compose run --rm -T --no-deps app alembic current
docker compose run --rm -T --no-deps app alembic history
```

Migration tests must independently verify:

```text
0004 → 0003 → 0004
```

with preserved non-publication state.

### Application scope protection

```bash
git diff --name-status origin/main...HEAD
git diff --check origin/main...HEAD

git diff --exit-code origin/main...HEAD -- \
  app/bot \
  app/worker \
  app/knowledge/markdown.py \
  alembic/versions/0001_create_users_and_messages.py \
  alembic/versions/0002_create_artifacts.py \
  alembic/versions/0003_create_processing_tasks.py
```

Adjust only if the diff command syntax requires path separation for the live Git version.

Expected: no changes in those protected paths.

### Manual repository-boundary inspection

Using a disposable temporary directory, verify:

```bash
tmp_root="$(mktemp -d)"
git -C "$tmp_root" init
git -C "$tmp_root" config --local user.name "PKM Test"
git -C "$tmp_root" config --local user.email "pkm-test@example.invalid"
git -C "$tmp_root" status --porcelain=v1
git -C "$tmp_root" symbolic-ref --quiet --short HEAD
```

The focused integration suite must exercise the actual publisher against temporary repositories rather than the developer’s real knowledge base.

Do not commit test output into the application repository.

### CI verification

After pushing the implementation:

```bash
gh pr view \
  --json number,state,isDraft,baseRefOid,headRefOid,url

gh pr checks <pr-number> --watch

gh run list \
  --workflow ci.yml \
  --branch task/011-manual-git-artifact-publication \
  --event pull_request \
  --limit 10
```

For the selected run:

```bash
gh run view <run-id> \
  --json databaseId,event,headBranch,headSha,status,conclusion,jobs,url
```

Require:

```text
check = CI / Test
conclusion = success
tested source SHA = exact current PR head
```

### Final synchronization and scope

```bash
git fetch origin --prune
git status --short
git rev-parse HEAD
git rev-parse origin/task/011-manual-git-artifact-publication
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

* system Git as a development-image dependency;
* explicit knowledge-base repository initialization;
* repository-local author configuration;
* exact repository-root requirement;
* the app-container CLI command;
* exact success output;
* clean-index requirement;
* permitted unrelated unstaged state;
* no remote operation;
* no automatic publication;
* database-failure reconciliation.

Do not include real author identity, email, credentials, or remote URLs.

### `docs/ARCHITECTURE.md`

Add the manual publication boundary:

```text
existing valid Artifact + exact file
→ manual Git publisher
→ local commit
→ Artifact.git_commit_sha
```

Preserve:

* Task 006 ownership;
* Task 007 worker flow;
* PostgreSQL orchestration ownership;
* Redis delivery role;
* two-process runtime;
* manual-only publication.

Explain that PostgreSQL and Git do not share a transaction.

### `docs/DATA_MODEL.md`

Add:

```text
Artifact.git_commit_sha    TEXT nullable
```

Document:

* null means no successfully recorded publication commit;
* non-null means one exact validated local commit;
* the SHA is not a branch, remote, synchronization, or retry state;
* no uniqueness or index exists;
* recovery may reconcile a retained commit after database failure.

Remove the statement that Artifact has no Git SHA.

### `docs/MARKDOWN_ARTIFACTS.md`

State clearly that:

* Task 006 bytes and paths remain unchanged;
* Task 011 consumes an already valid Artifact and file;
* Git publication never repairs or rerenders the note;
* Git publication is separate and manual.

Link to `docs/GIT_PUBLICATION.md`.

### `docs/GIT_PUBLICATION.md`

Add a focused domain document covering:

* repository-root validation;
* initialization and author setup;
* CLI interface;
* commit message and trailers;
* index policy;
* working-tree preservation;
* repository and row locks;
* idempotency matrix;
* PostgreSQL/Git recovery;
* failure behavior;
* absence of remotes and automation.

### `docs/CURRENT_STATE.md`

After implementation, verification, pushed green CI, and review readiness:

* record manual Git publication as implemented;
* record nullable Artifact SHA;
* record exact root requirement;
* record manual-only CLI;
* record no remote synchronization;
* retain automatic worker publication as not implemented;
* set:

  ```text
  **Active task:** none selected
  ```

Do not turn the file into a commit or run history.

### `docs/DECISIONS.md`

Add the next available decision, expected:

```text
D-030 — Publish one validated Artifact through an explicit local Git commit
```

Record:

* knowledge-base root is the exact Git root;
* manual Artifact-UUID CLI;
* nullable SHA on Artifact;
* Task 006 remains unchanged;
* clean-index policy;
* unrelated unstaged state is preserved;
* repository-wide lock plus Artifact row lock;
* stable commit trailers;
* retained-commit reconciliation;
* local-only Git;
* no initialization, remote, worker, or automatic publication.

### Task file

Set Task 011 status according to repository convention only after implementation and verification evidence exists.

The immutable review contract remains the Task 011 file at its recorded contract commit SHA.

### Expected unchanged documentation

Do not update:

```text
docs/TELEGRAM_INGESTION.md
docs/PROJECT_BRIEF.md
```

unless live implementation reveals a direct contradiction.

## Pull-request description requirements

The PR description must record:

### Contract and branch identity

```text
repository
task path
full contract commit SHA
base branch and base SHA
task branch
current pushed head SHA
```

### Pre-task correction

Record:

```text
Task 010 status-correction commit SHA
changed path
successful main-branch CI run
confirmation that it is not part of the Task 011 PR diff
```

### Outcome

Summarize:

* Artifact field and migration;
* publication function;
* CLI;
* exact root validation;
* Git version and Dockerfile change;
* index policy;
* commit format;
* lock behavior;
* recovery behavior;
* absence of remotes and automation.

### Verification

List exact commands and classify each:

```text
pass
fail
not run
```

Include:

* focused tests;
* migration tests;
* full suite;
* Docker image build;
* Git version;
* scope checks;
* CI run.

### GitHub Actions

Record:

```text
workflow: CI
check: CI / Test
run ID
run URL
event
tested source SHA
current PR head SHA
conclusion
```

### Documentation

List updated and intentionally unchanged documents.

### Risks and unverified items

Include:

* actual user knowledge-base initialization remains a manual operation;
* no remote synchronization exists;
* no worker integration exists;
* publication requires a clean index;
* filesystem locking is Linux/Docker-specific;
* external manual branch switching can create history requiring investigation;
* application and knowledge-base repositories remain separate operational boundaries.

### Scope protection

Confirm:

* no Task 006 rendering change;
* no Task 007 lifecycle change;
* no remote Git command;
* no implicit initialization;
* no generated knowledge artifact committed to the application PR;
* no real author identity or credentials committed;
* no prohibited GitHub operation occurred.

## Completion reporting

No external completion-report file is required.

The Task 011 PR description is the completion report.

Task 011 may be described as complete only when:

1. the Task 010 correction is independently complete;
2. Task 011 local verification passes;
3. migration verification passes;
4. the complete suite passes;
5. implementation and documentation are pushed;
6. `CI / Test` succeeds for the exact current PR head;
7. the PR description records that evidence;
8. Handoff Review approves the exact green head.

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

* the exact contract;
* the complete PR patch;
* migration;
* Artifact field;
* Task 006 validation reuse;
* repository-root validation;
* allowed Git command boundary;
* index isolation;
* hooks isolation;
* locking;
* commit metadata;
* stored-SHA validation;
* retained-commit recovery;
* CLI;
* tests;
* documentation;
* successful CI result.

Approval applies only to that exact head.

## Correction behavior

Bounded corrections are authorized on the same Task 011 branch.

Expected message:

```text
fix: address Task 011 review findings
```

A correction may change only:

* Task 011 publication code;
* migration or model details required by the contract;
* directly related focused tests;
* Docker Git availability;
* Task 011 documentation;
* PR-description evidence.

After every correction:

1. rerun relevant focused tests;
2. rerun the complete suite when behavior changed;
3. push normally without force;
4. require a new successful `CI / Test` result;
5. update the PR description;
6. review the new exact head.

Do not amend or rebase reviewed commits.

Do not rewrite the contract to hide an implementation mismatch.

Automatic worker publication, remote Git, bulk publication, or a broader state model requires a new task.

## Merge boundary

The accepted merge method is a normal merge commit.

Merge requires:

1. successful focused and full local verification;
2. successful migration verification;
3. a successful `CI / Test` result for the exact current head;
4. Handoff Review approval of that head;
5. separate explicit user authorization.

Task 011 does not authorize merge or branch deletion.

## Prohibited committed artifacts

Do not commit:

```text
knowledge-base/.git/
generated Markdown notes
temporary Git repositories
Git lock files
Git index files
Git object databases
database dumps
real Git author identity added only for testing
real email addresses added only for testing
Git credentials
remote URLs containing credentials
Telegram tokens
Telegram user IDs
OpenAI or other provider keys
.env
local application configuration
pytest caches
coverage output
Git command logs containing private paths
generated handoff files
review bundles
external completion reports
unrelated work
```

Test-only author identity must use reserved non-deliverable values.

## Expected commit boundaries

### Standalone pre-task correction

Expected message:

```text
docs: mark task 010 completed
```

Exact path:

```text
tasks/010-github-actions-ci.md
```

Exact change:

```text
Status: ready for review
→
Status: completed
```

This commit is on the corrected default-branch baseline and is not part of the Task 011 PR diff.

### Contract commit

Expected message:

```text
docs: define task 011 manual Git artifact publication
```

Expected paths:

```text
tasks/011-manual-git-artifact-publication.md
docs/CURRENT_STATE.md
```

`docs/CURRENT_STATE.md` may change only to select Task 011 as active.

No model, migration, code, Docker, test, or implementation documentation change belongs in the contract commit.

### Implementation commit

Expected message:

```text
feat: add manual Git artifact publication
```

Expected paths:

```text
app/db/models.py
app/knowledge/processing.py
app/knowledge/errors.py
app/knowledge/git_publication.py
app/knowledge/git_cli.py
alembic/versions/0004_add_artifact_git_commit_sha.py
tests/test_models.py
tests/test_migrations.py
tests/test_git_publication.py
tests/test_git_cli.py
Dockerfile
README.md
docs/ARCHITECTURE.md
docs/DATA_MODEL.md
docs/MARKDOWN_ARTIFACTS.md
docs/GIT_PUBLICATION.md
docs/CURRENT_STATE.md
docs/DECISIONS.md
tasks/011-manual-git-artifact-publication.md
```

Conditionally allowed with direct justification:

```text
app/settings.py
docker-compose.yml
.env.example
.gitignore
.dockerignore
tests/conftest.py
.github/workflows/ci.yml
```

The implementation commit must not include:

```text
Telegram behavior changes
worker behavior changes
ProcessingTask changes
Redis changes
Task 006 Markdown-format changes
automatic Git publication
remote Git operations
knowledge-base content
application-repository generated artifacts
branch protection
deployment
unrelated cleanup
```

### Correction commits

Expected message:

```text
fix: address Task 011 review findings
```

Corrections stay on:

```text
task/011-manual-git-artifact-publication
```

They may modify only paths directly required to make the accepted publication boundary correct, recoverable, isolated, tested, documented, and green.

## Authorized Task 011 Git operations

Authorized for the application repository only:

```text
Task 011 branch creation
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

Authorized inside the knowledge-base repository only through the implemented manual publisher:

```text
local repository inspection
selected-path staging
one local commit
commit and blob inspection
path-specific index restoration after publisher failure
```

## Unauthorized operations

Unauthorized in the application repository:

```text
Task 011 push directly to main
force-push
amend of reviewed commits
rebase of reviewed commits
PR merge
branch deletion
repository-setting changes
```

Unauthorized in the knowledge-base repository:

```text
implicit init
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
bulk commits
automatic publication
```

The final Task 011 outcome is a reviewed, green, unmerged application PR plus a reusable manual local publication boundary awaiting separate merge authorization.
