# Task 010: Add GitHub Actions CI for pull requests

**Status:** completed
**Depends on:** Tasks 000–009
**Target file:** `tasks/010-github-actions-ci.md`
**Expected branch:** `task/010-github-actions-ci`
**Expected pull-request title:** `Task 010: Add GitHub Actions CI for pull requests`
**Expected contract commit:** `docs: define task 010 GitHub Actions CI`
**Expected implementation commit:** `ci: add pull-request verification`
**Expected correction commit:** `fix: address Task 010 CI findings`
**Expected merge method:** normal merge commit, performed only after separate explicit user authorization

## Git and pull-request authorization

This accepted task explicitly authorizes Codex to perform only the following actions on:

```text
task/010-github-actions-ci
```

1. create or switch to the Task 010 branch from the synchronized pushed default branch;
2. create the distinct Task 010 contract commit;
3. push the task branch;
4. open or update one draft pull request targeting the verified default branch;
5. create one coherent Task 010 implementation commit;
6. push the implementation commit to the same task branch;
7. inspect the resulting GitHub Actions workflow and job runs;
8. update the pull-request description with local and CI verification evidence;
9. mark the pull request ready only after the exact current pushed head has a successful required CI result;
10. create and push bounded Task 010 correction commits when implementation or CI findings require them.

This task does **not** authorize Codex to:

* push directly to the default branch;
* merge the pull request;
* delete the local or remote task branch;
* force-push;
* amend or rebase already pushed reviewed commits;
* enable auto-merge;
* configure branch protection or repository rulesets;
* change repository visibility;
* change general GitHub Actions repository permissions;
* create deployment, release, publishing, or production workflows;
* commit unrelated local work.

A merge requires separate explicit user authorization after final review of the exact current pushed head.

## Goal

Add one minimal GitHub Actions continuous-integration workflow that automatically verifies:

```text
pull requests targeting main
and
pushes to main
```

The workflow must provide an independently executed green or red check for the exact pushed source commit being reviewed.

The intended CI boundary is:

```text
pushed commit
→ GitHub Actions
→ patch-integrity check
→ Docker Compose validation
→ development-image build
→ isolated PostgreSQL startup
→ isolated test database creation through Alembic
→ authoritative pytest suite
→ visible pass or fail result
→ unconditional cleanup
```

Task completion requires a real successful GitHub Actions run on the Task 010 implementation pull request. A valid-looking workflow file or successful local execution alone is insufficient.

## Confirmed current boundary

Live repository inspection confirms:

* Tasks 000–009 are complete.

* The pushed default branch is the accepted shared baseline.

* Each bounded task uses a dedicated branch and pull request.

* Handoff Review reviews the exact pushed PR head.

* The repository is public, and connected Web Chat can inspect pushed pull requests.

* No active task is currently selected.

* No `.github/workflows/ci.yml` exists on the default branch.

* GitHub Actions does not currently provide independent verification.

* Docker Compose is the authoritative local runtime and test environment.

* The Compose topology contains:

  ```text
  app
  worker
  redis
  postgres
  ```

* The app and worker use the same development image.

* The development image installs the `dev` dependency group and contains the application, migrations, and tests.

* PostgreSQL has a committed health check.

* Redis has a committed health check.

* The app service depends only on healthy PostgreSQL.

* The worker depends on PostgreSQL and Redis.

* Pytest requires `TEST_DATABASE_URL`.

* Pytest rejects a test database with the same database name as `DATABASE_URL`.

* Pytest creates the configured test database when it is absent.

* Pytest sets the application database URL to the isolated test database before importing database state.

* Pytest initializes the test schema from committed Alembic migrations.

* The suite contains explicit migration downgrade and re-upgrade tests.

* Current worker and dispatcher tests do not require a separately running Dramatiq worker.

* Current Redis-related test coverage does not require a live Redis service.

* Artifact-processing tests use pytest temporary paths where filesystem publication is exercised.

* Telegram polling is disabled for normal automated tests.

* No real Telegram token or AI-provider key is required.

* D-028 is the latest confirmed durable decision.

* D-029 is the expected next decision identifier, subject to live verification.

* The existing pull-request template still treats missing CI as a possible normal condition and must be updated after CI is verified.

Uploaded files and prior reports are not sufficient proof of current repository state. Codex must repeat the relevant live inspection before implementation.

## Repository verification requirements

Before editing, Codex must inspect and report the live local and GitHub state.

### Local Git state

Run:

```bash
git branch --show-current
git rev-parse HEAD
git status --short
git log --oneline --decorate -10
git diff --stat
git diff --check
```

Verify:

* Task 009 is committed and present on the pushed default branch;
* the local default branch is clean;
* the local default branch is synchronized with its remote counterpart;
* no Task 010 implementation already exists locally;
* no unrelated staged, unstaged, or untracked work would enter Task 010;
* no conflicting Task 010 branch exists;
* no later active task has already selected another CI design.

Do not stash, discard, move, or commit unrelated local changes automatically.

### Remote and pull-request state

Inspect:

```bash
git remote -v
git fetch origin --prune
git remote show origin
gh auth status
gh repo view --json nameWithOwner,visibility,defaultBranchRef
gh pr list --state all \
  --head task/010-github-actions-ci \
  --json number,title,state,isDraft,baseRefName,headRefName,headRefOid,url
```

Determine the real default branch rather than assuming it is `main`.

For a confirmed `main` default branch, verify:

```bash
git rev-parse main
git rev-parse origin/main
git rev-list --left-right --count main...origin/main
```

Expected synchronization before branch creation:

```text
0	0
```

### Existing Actions state

Inspect:

```bash
find .github -maxdepth 3 -type f -print | sort
gh workflow list --all
gh run list --limit 20
```

Verify:

* no existing workflow already supplies the required check;
* no conflicting workflow or check name exists;
* GitHub Actions is available for the repository;
* the implementation PR can trigger workflows without repository-setting changes;
* no existing repository rule requires a different check name or event.

If Actions is disabled or the repository refuses to run the workflow, record an external blocker. Do not silently change repository settings under this task.

### Runtime and test inspection

Read at minimum:

```text
docker-compose.yml
Dockerfile
pyproject.toml
.env.example
alembic.ini
alembic/env.py
tests/conftest.py
tests/test_migrations.py
tests/test_database.py
tests/test_task_dispatcher.py
tests/test_task_worker.py
app/settings.py
app/main.py
README.md
AGENTS.md
docs/WORKFLOW.md
docs/CURRENT_STATE.md
docs/DECISIONS.md
.github/pull_request_template.md
tasks/TEMPLATE.md
```

Search the current test suite for:

```text
redis
dramatiq
worker
knowledge_base_path
KNOWLEDGE_BASE_PATH
tmp_path
TELEGRAM_BOT_ENABLED
OPENAI_API_KEY
DATABASE_URL
TEST_DATABASE_URL
alembic
```

Confirm before implementation that:

* PostgreSQL is the only live Compose service required by pytest;
* Redis and the worker may remain stopped;
* no test performs a live Telegram or AI-provider call;
* no test must write into the checked-out `knowledge-base/`;
* the full suite still performs all required migration verification;
* the development image still contains all test dependencies and test sources.

A contradiction must be reported before changing the selected CI design.

## Problem or motivation

The pull-request workflow established by Task 009 distinguishes:

```text
Codex-supplied local verification claims
from
independently executed CI evidence
```

At present, only the first category exists.

This leaves several risks:

* local environment state can differ from a clean GitHub runner;
* a verification command may be omitted or reported incorrectly;
* a pushed correction may not receive the same verification as the previous head;
* reviewers cannot rely on a repository-owned green or red status;
* future branch protection has no stable check to require;
* Docker build or clean-database failures may be discovered only after review.

A small Docker Compose-backed GitHub Actions job closes this gap without introducing deployment or a parallel non-Docker test environment.

## Scope

Implement the following bounded outcome:

1. add one workflow at:

   ```text
   .github/workflows/ci.yml
   ```

2. trigger it for:

   * pull requests targeting the default branch;
   * pushes to the default branch;

3. run one job on one GitHub-hosted Linux runner;

4. give the workflow and job stable explicit names;

5. use read-only repository permissions;

6. check out the exact source commit intended for verification;

7. verify that the checked-out commit equals the selected CI head SHA;

8. run a patch-integrity check over the event’s relevant base-to-head range;

9. validate the committed Docker Compose configuration;

10. build the Compose development app image;

11. start only PostgreSQL and wait for its committed health check;

12. run the authoritative pytest suite in a one-off app-service container;

13. disable Telegram polling and the task dispatcher explicitly;

14. use only safe placeholder PostgreSQL configuration;

15. use a separate test database name;

16. isolate any knowledge-base output from the checked-out repository;

17. show useful PostgreSQL and Compose diagnostics when the test path fails;

18. remove containers, networks, and CI database volumes unconditionally;

19. verify one real successful workflow result on the exact current Task 010 PR head;

20. update repository workflow documentation and durable CI state.

## Out of scope

Do not add:

* application deployment;
* continuous delivery;
* production hosting;
* Docker registry authentication or publication;
* GitHub Releases;
* semantic versioning;
* GitHub Pages;
* production environments;
* production secrets;
* live Telegram API calls;
* live OpenAI or other AI-provider calls;
* automatic merging;
* auto-merge configuration;
* branch protection;
* repository rulesets;
* merge queues;
* Dependabot;
* CodeQL;
* dependency-review workflows;
* coverage collection or thresholds;
* test-result upload services;
* linting or formatting policy;
* static typing;
* matrix testing;
* multiple Python versions;
* multiple operating systems;
* ARM runners;
* self-hosted runners;
* Kubernetes;
* Terraform;
* Helm;
* cloud-provider configuration;
* Docker image caching beyond the runner’s normal behavior;
* custom reusable Actions;
* deployment credentials;
* a general CI abstraction;
* unrelated application refactoring.

These remain separate possible tasks.

## Affected components

Expected changes:

```text
.github/workflows/ci.yml
.github/pull_request_template.md
AGENTS.md
README.md
docs/CURRENT_STATE.md
docs/WORKFLOW.md
docs/DECISIONS.md
tasks/010-github-actions-ci.md
```

Conditionally allowed only when live verification proves a minimal CI-specific adjustment is necessary:

```text
docker-compose.yml
Dockerfile
tests/conftest.py
tests/test_migrations.py
tests/<directly affected CI-support test>
.env.example
.gitignore
.dockerignore
```

Any conditional change must be:

* justified in the PR description;
* smaller than introducing a separate CI runtime;
* verified locally and by the resulting workflow;
* unrelated to product behavior.

Expected unchanged:

```text
app/
alembic/versions/
knowledge-base/
docs/ARCHITECTURE.md
docs/DATA_MODEL.md
docs/TELEGRAM_INGESTION.md
docs/MARKDOWN_ARTIFACTS.md
docs/PROJECT_BRIEF.md
tasks/000-009
```

Updating Task 010’s own branch-head status or completion evidence does not alter the immutable contract at the recorded contract SHA.

## Data, state, migration, and configuration impact

### Product data and schema

No product database schema change is expected.

Do not add an Alembic revision.

Do not alter:

```text
users
messages
artifacts
processing_tasks
```

or their production state transitions.

### CI database state

CI must use ephemeral PostgreSQL state owned by the workflow run.

Use distinct safe database names:

```text
development database: pkm
test database: pkm_test
```

`DATABASE_URL` and `TEST_DATABASE_URL` must never resolve to the same database name.

The PostgreSQL credentials used in CI are disposable placeholders, not secrets.

The CI database volume must be removed during unconditional cleanup.

### Application configuration

CI must set safe values explicitly rather than reading real local credentials.

Required CI values include equivalents of:

```text
ENVIRONMENT=ci
POSTGRES_USER=pkm_ci
POSTGRES_PASSWORD=pkm_ci_password
POSTGRES_DB=pkm
DATABASE_URL=postgresql+asyncpg://pkm_ci:pkm_ci_password@postgres:5432/pkm
TEST_DATABASE_URL=postgresql+asyncpg://pkm_ci:pkm_ci_password@postgres:5432/pkm_test
TELEGRAM_BOT_ENABLED=false
TELEGRAM_BOT_TOKEN=
TELEGRAM_ALLOWED_USER_IDS=[]
TASK_DISPATCHER_ENABLED=false
REDIS_URL=redis://redis:6379/0
KNOWLEDGE_BASE_PATH=/var/tmp/pkm-ci-knowledge-base
OPENAI_API_KEY=
```

The exact placeholder strings may differ, but they must remain:

* non-secret;
* internally consistent;
* visibly CI-specific;
* unable to contact Telegram or an AI provider.

No committed `.env` or secret-bearing CI file is required.

## Behavioral requirements

### Workflow triggers

The workflow must trigger on:

```yaml
pull_request:
  branches:
    - main

push:
  branches:
    - main
```

Adapt `main` only when the live default branch has a different name.

Do not use:

```text
pull_request_target
schedule
workflow_dispatch
workflow_run
merge_group
```

in this task.

Do not add `paths-ignore`. Every future bounded pull request should receive the same baseline check, including documentation-only changes, until a separate task deliberately changes that policy.

### Workflow and check identity

Declare:

```text
workflow name: CI
job name: Test
```

The intended displayed check is:

```text
CI / Test
```

GitHub’s actual check context must be observed from the first real run and recorded in:

```text
README.md
docs/CURRENT_STATE.md
the Task 010 PR description
```

Future branch-protection work must use the observed context, not an assumed string.

Changing the workflow or job display name after Task 010 would change the future required-check identity and must be treated as a deliberate workflow change.

### Runner

Use:

```yaml
runs-on: ubuntu-24.04
```

Use one job only.

Set a bounded job timeout, expected:

```yaml
timeout-minutes: 30
```

Do not add a matrix.

### Permissions and public-repository safety

Set workflow-level permissions to:

```yaml
permissions:
  contents: read
```

The workflow must:

* use `pull_request`, not `pull_request_target`;
* require no repository secrets;
* use no write-capable token permission;
* not comment on PRs;
* not modify labels;
* not push commits;
* not upload packages or images;
* not create releases;
* not persist checkout credentials.

Use only the official checkout action. The expected current action is:

```yaml
actions/checkout@v6
```

Configure checkout with:

```yaml
persist-credentials: false
fetch-depth: 0
```

If the current supported official major differs during implementation, verify it from official GitHub documentation and record the chosen version.

### Exact source-head identity

For pull-request events, the source under test must be:

```text
github.event.pull_request.head.sha
```

For pushes to the default branch, the source under test must be:

```text
github.sha
```

The workflow must check out that selected SHA explicitly.

It must then fail if:

```bash
git rev-parse HEAD
```

does not equal the selected CI head SHA.

This requirement prevents the workflow from silently testing only GitHub’s synthetic pull-request merge commit while Handoff Review identifies a different pushed task-branch head.

The run and PR description must make the tested source SHA discoverable.

### Patch-integrity check

Run `git diff --check` against the event’s relevant change range.

For pull requests, the base must come from the pull-request base SHA and the head from the pull-request head SHA.

For pushes, the base must come from the event’s pre-push SHA and the head from the pushed SHA.

Handle GitHub’s all-zero “no previous commit” value safely, even though creation of the existing default branch is not an expected normal event.

Do not run bare:

```bash
git diff --check
```

against a clean checkout, because that would inspect only local working-tree changes and would not validate the committed PR patch.

### Compose validation and image build

Run:

```bash
docker compose config --quiet
docker compose build app
```

The build must use the committed development image boundary with development dependencies installed.

Do not install a second host-side Python environment in CI.

Do not add `actions/setup-python` for this task.

### Required live services

Start only:

```text
postgres
```

Do not start:

```text
app as a long-running Uvicorn service
worker
redis
```

The expected readiness command is equivalent to:

```bash
docker compose up -d --wait --wait-timeout 90 postgres
```

The committed PostgreSQL health check is the readiness authority.

If the available Compose version does not support the chosen bounded wait option, use a bounded `pg_isready` polling loop instead. Do not use an unbounded sleep.

### Authoritative pytest execution

Run pytest through a one-off app-service container, not through a separately installed host Python.

The expected command is equivalent to:

```bash
docker compose run --rm -T --no-deps \
  -e TASK_DISPATCHER_ENABLED=false \
  -e TELEGRAM_BOT_ENABLED=false \
  -e TELEGRAM_BOT_TOKEN= \
  -e TELEGRAM_ALLOWED_USER_IDS='[]' \
  -e OPENAI_API_KEY= \
  -e KNOWLEDGE_BASE_PATH=/var/tmp/pkm-ci-knowledge-base \
  app python -m pytest
```

Use `docker compose run`, rather than `exec`, because CI does not need to keep the Uvicorn app service running.

Use `--no-deps` only after PostgreSQL has already passed readiness.

Redis and the worker must remain absent unless live re-inspection proves that the authoritative suite now requires them. Such a discovery is a material task-contract contradiction and must be reported before broadening the workflow.

### Migration verification

The pytest session bootstrap must remain responsible for:

1. validating that the development and test database names differ;
2. creating the test database when absent;
3. selecting the test database for application database modules;
4. applying committed Alembic migrations to head.

The complete suite must continue to include explicit migration tests that exercise supported downgrade and re-upgrade paths.

Do not run `alembic upgrade head` separately against the CI development database merely to duplicate the pytest fixture.

A separate migration command is allowed only when live inspection proves the full suite no longer provides clean-database migration coverage.

### Knowledge-base isolation

CI must set:

```text
KNOWLEDGE_BASE_PATH=/var/tmp/pkm-ci-knowledge-base
```

or an equivalent container-local disposable path outside the checked-out bind-mounted knowledge base.

The workflow must not create or modify tracked files under:

```text
knowledge-base/
```

No generated Markdown artifact may be uploaded or committed.

### Failure visibility

The normal failing command output must remain visible in the Actions log.

When the test or readiness path fails, collect at least:

```bash
docker compose ps -a
docker compose logs --no-color postgres
```

Diagnostic steps must use an `if: failure()` boundary and must not hide the original failing exit status.

Do not print the complete process environment.

### Cleanup

Run cleanup with an unconditional Actions condition equivalent to:

```yaml
if: always()
```

Cleanup must execute:

```bash
docker compose down -v --remove-orphans
```

It must remove:

* the PostgreSQL container;
* one-off test containers;
* the Compose network;
* the CI PostgreSQL volume;
* orphaned Compose resources belonging to the CI project.

Use a CI-specific Compose project name derived from the workflow run or another non-secret unique value.

Cleanup failure should be visible but must not conceal the primary test failure.

### Caching

Do not add custom Docker layer caching in Task 010.

The first goal is a correct and observable check. Cache optimization remains a separate task after real run duration and failure patterns are known.

## Expected failure modes and recovery behavior

### Invalid workflow syntax

If GitHub does not register or start the workflow:

* Task 010 is not complete;
* inspect the Actions UI and workflow file;
* correct the same task branch;
* push a bounded correction commit;
* do not claim that CI exists based only on local YAML parsing.

### Docker or image-build failure

If the development image cannot build on the GitHub runner:

* preserve full build output;
* determine whether the failure is deterministic repository behavior or temporary external registry/network failure;
* apply only the smallest repository correction when the cause is in scope;
* do not add deployment credentials, alternative registries, or broad cache infrastructure.

### PostgreSQL readiness failure

On readiness failure:

* show Compose state and PostgreSQL logs;
* fail the job;
* clean up unconditionally;
* do not continue to pytest.

### Migration or test failure

Any failing migration or pytest result must make the job red.

Do not use:

```text
continue-on-error
pytest ... || true
allow-failure
```

for required verification.

### GitHub service or registry outage

A transient GitHub or public image-registry outage may be classified as an external environment failure only when the logs support that classification.

The task still requires a later successful run on the exact current head before completion.

### Changed PR head

Every pushed correction creates a new review head.

A green run for an older head does not satisfy completion for a newer head.

After each correction:

1. wait for or inspect the new workflow run;
2. require success for the new head;
3. update the PR description;
4. request review of the new head.

### Actions unavailable

If Actions is disabled, restricted, or cannot run without a repository-setting change:

* keep the PR in draft;
* record the exact blocker;
* do not change repository settings under this task;
* do not mark Task 010 completed.

## Tests

No new application test is required merely because a workflow file is added.

The implementation must preserve and execute the complete current suite.

Add or modify application or tooling tests only when a minimal CI-specific code/configuration change introduces behavior that is not already covered.

Required verification layers are:

1. repository and workflow structural inspection;
2. local CI-parity execution through Docker Compose;
3. complete authoritative pytest suite;
4. real GitHub Actions execution on the pushed implementation PR head;
5. exact-head and check-result inspection through GitHub;
6. Handoff Review of the workflow, documentation, PR patch, and successful run.

Do not add a test that merely searches the workflow YAML for strings when the real GitHub Actions run already verifies execution semantics.

A small structural test is allowed only when it protects a durable security or trigger invariant that GitHub execution does not make sufficiently reviewable.

## Acceptance criteria

Task 010 is accepted only when all of the following are true:

1. Task 010 exists at `tasks/010-github-actions-ci.md`.
2. The exact contract path and full contract SHA are recorded in the PR.
3. The implementation is on `task/010-github-actions-ci`.
4. No Task 010 change was pushed directly to the default branch.
5. One workflow exists at `.github/workflows/ci.yml`.
6. The workflow triggers for pull requests targeting the verified default branch.
7. The workflow triggers for pushes to the verified default branch.
8. The workflow does not use `pull_request_target`.
9. The workflow grants only `contents: read`.
10. Checkout credentials are not persisted.
11. The pull-request source checkout uses the exact PR head SHA.
12. The workflow verifies the checked-out SHA.
13. Patch integrity is checked over the committed event range.
14. Docker Compose configuration is validated.
15. The development app image is built successfully.
16. Only PostgreSQL is started as a long-running service.
17. PostgreSQL readiness uses a bounded health-based wait.
18. Redis and the worker are not started.
19. Pytest runs in a one-off app-service container.
20. Telegram polling is explicitly disabled.
21. The task dispatcher is explicitly disabled.
22. No real Telegram or AI-provider secret is required.
23. `DATABASE_URL` and `TEST_DATABASE_URL` target distinct database names.
24. The test database is created and initialized from committed Alembic migrations.
25. Existing migration downgrade/re-upgrade tests run as part of the full suite.
26. Knowledge-base output uses a disposable container-local path.
27. No tracked knowledge-base file is changed.
28. Failures produce useful Compose/PostgreSQL diagnostics.
29. Cleanup runs unconditionally and removes the CI database volume.
30. No custom Docker caching is introduced.
31. One job supplies one stable check.
32. The actual GitHub check context is observed and documented.
33. The complete local suite passes through the CI-parity command.
34. A real GitHub Actions pull-request run succeeds.
35. That successful run tested the exact current pushed PR head.
36. The successful run ID or URL, head SHA, workflow name, job name, and conclusion are recorded in the PR description.
37. Any correction commit receives a new successful run.
38. `README.md` documents CI and local parity.
39. `docs/WORKFLOW.md` distinguishes local claims from required CI evidence.
40. `docs/CURRENT_STATE.md` records the verified CI boundary without becoming a run log.
41. `docs/DECISIONS.md` records the durable CI choice as the next available decision.
42. `AGENTS.md` requires available CI to pass before readiness and final review.
43. The pull-request template no longer treats missing CI as a normal condition.
44. No database migration, runtime behavior, Telegram behavior, worker behavior, or artifact format changed.
45. No branch protection or deployment work was added.
46. The final local working tree is clean.
47. The local task branch matches its pushed remote head.
48. The PR remains unmerged pending separate authorization.
49. Handoff Review approves the exact head that owns the successful CI result.

## Required verification commands

### Repository bootstrap

Run and record:

```bash
git branch --show-current
git rev-parse HEAD
git status --short
git log --oneline --decorate -10
git remote -v
git fetch origin --prune
git remote show origin
git diff --stat
git diff --check
gh auth status
gh repo view --json nameWithOwner,visibility,defaultBranchRef
gh workflow list --all
gh run list --limit 20
```

### Contract and branch identity

After the contract commit:

```bash
git rev-parse HEAD
git show --stat --oneline HEAD
git status --short
git branch -vv
gh pr view --json number,title,state,isDraft,baseRefName,baseRefOid,headRefName,headRefOid,url,body
```

Record:

```text
repository
default branch
task branch
task path
contract SHA
PR number
base SHA
current head SHA
```

### Local CI-parity verification

Use a dedicated Compose project so cleanup cannot remove the normal development database volume:

```bash
export COMPOSE_PROJECT_NAME=pkm-task010-ci
export ENVIRONMENT=ci
export POSTGRES_USER=pkm_ci
export POSTGRES_PASSWORD=pkm_ci_password
export POSTGRES_DB=pkm
export DATABASE_URL=postgresql+asyncpg://pkm_ci:pkm_ci_password@postgres:5432/pkm
export TEST_DATABASE_URL=postgresql+asyncpg://pkm_ci:pkm_ci_password@postgres:5432/pkm_test
export TELEGRAM_BOT_ENABLED=false
export TELEGRAM_BOT_TOKEN=
export TELEGRAM_ALLOWED_USER_IDS='[]'
export TASK_DISPATCHER_ENABLED=false
export REDIS_URL=redis://redis:6379/0
export KNOWLEDGE_BASE_PATH=/var/tmp/pkm-ci-knowledge-base
export OPENAI_API_KEY=

docker compose down -v --remove-orphans || true
docker compose config --quiet
docker compose build app
docker compose up -d --wait --wait-timeout 90 postgres

docker compose run --rm -T --no-deps \
  -e TASK_DISPATCHER_ENABLED=false \
  -e TELEGRAM_BOT_ENABLED=false \
  -e TELEGRAM_BOT_TOKEN= \
  -e TELEGRAM_ALLOWED_USER_IDS='[]' \
  -e OPENAI_API_KEY= \
  -e KNOWLEDGE_BASE_PATH=/var/tmp/pkm-ci-knowledge-base \
  app python -m pytest

docker compose ps -a
docker compose down -v --remove-orphans
```

After cleanup:

```bash
docker compose ps -a
git status --short
git diff --check
git diff --name-status "$(git merge-base HEAD origin/main)"...HEAD
```

Expected:

* pytest passes;
* no CI Compose resources remain;
* no tracked knowledge-base file changed;
* no unrelated path changed.

### Workflow inspection after push

Run:

```bash
gh workflow list --all
gh pr view --json number,state,isDraft,baseRefOid,headRefOid,url
gh run list \
  --workflow ci.yml \
  --branch task/010-github-actions-ci \
  --event pull_request \
  --limit 10
```

For the selected workflow run:

```bash
gh run view <run-id> \
  --json databaseId,event,headBranch,headSha,status,conclusion,jobs,url
```

Require:

```text
event = pull_request
headSha = exact current PR head or the workflow’s explicitly recorded tested head
status = completed
conclusion = success
```

Inspect the PR check:

```bash
gh pr checks <pr-number> --watch
```

If a command exposes GitHub’s synthetic merge SHA as the workflow-run head, inspect the workflow logs and checkout-verification step to confirm that the tested repository checkout equals:

```text
github.event.pull_request.head.sha
```

### Final scope and synchronization

Run:

```bash
git fetch origin --prune
git status --short
git rev-parse HEAD
git rev-parse origin/task/010-github-actions-ci
git diff --check
git diff --name-status origin/main...HEAD
git log --oneline --decorate origin/main..HEAD
```

Expected:

```text
local HEAD = pushed task-branch HEAD = reviewed PR head
```

## Documentation impact

### `README.md`

Add a concise CI section covering:

* PR and `main` push triggers;
* stable workflow/job or observed check name;
* Docker Compose-backed execution;
* PostgreSQL-only service boundary;
* isolated test database;
* absence of Telegram and AI secrets;
* local CI-parity command or link to its documented sequence;
* branch protection as future work, not current behavior.

Do not duplicate the entire workflow file.

### `docs/WORKFLOW.md`

Update the evidence and lifecycle rules so that:

* local verification remains required;
* CI is independent evidence;
* an available required CI job must succeed for the exact current head before readiness and final approval;
* a green result for an older head is invalid after correction;
* CI failure diagnostics do not replace implementation review;
* CI success does not authorize merge;
* a push-to-main run occurs only after a separately authorized merge.

Preserve the conversation responsibilities and documentation-update matrix.

### `docs/CURRENT_STATE.md`

Record current semantic state only:

* GitHub Actions CI exists;
* its triggers;
* the observed check name;
* PostgreSQL-only CI topology;
* isolated test database and migration ownership;
* no live secrets;
* branch protection remains unimplemented.

Set:

```text
**Active task:** none selected
```

only after Task 010 is implemented, locally verified, pushed, and green on the exact current PR head.

Do not turn this file into a workflow-run chronology.

### `docs/DECISIONS.md`

Add the next available durable decision, expected:

```text
D-029 — Verify pull requests with one Docker Compose-backed GitHub Actions check
```

The decision should capture:

* one workflow and one job;
* PR and default-branch push triggers;
* exact-source-head checkout;
* PostgreSQL-only live service;
* one-off app test container;
* pytest/Alembic ownership of test-schema initialization;
* safe secret-free environment;
* unconditional cleanup;
* no caching, branch protection, deployment, or matrix in this task.

### `AGENTS.md`

Add a concise instruction that, once available:

* Codex must inspect the CI result for the exact pushed head;
* CI must pass before marking a task ready or presenting final implementation readiness;
* a correction invalidates the earlier green result;
* CI success does not authorize merge.

### `.github/pull_request_template.md`

Update the verification and risk sections to request:

```text
local verification commands and results
CI workflow/job name
CI run ID or URL
tested head SHA
CI conclusion
unverified items
```

Remove wording that treats “missing CI” as the normal expected state.

### Documents expected unchanged

Do not update:

```text
docs/ARCHITECTURE.md
docs/DATA_MODEL.md
docs/TELEGRAM_INGESTION.md
docs/MARKDOWN_ARTIFACTS.md
docs/PROJECT_BRIEF.md
```

unless live inspection reveals a direct contradiction caused by the CI implementation.

## Pull-request description requirements

The Task 010 PR description must include:

### Task contract

```text
task path
exact full contract SHA
base branch and base SHA
task branch
current pushed head SHA
```

### Outcome

Summarize:

* the workflow path;
* triggers;
* workflow and job names;
* exact source-checkout rule;
* PostgreSQL-only service boundary;
* pytest execution command;
* migration boundary;
* cleanup behavior.

### Local verification

List every exact local command and mark it:

```text
pass
fail
not run
```

Local results remain Codex-supplied claims.

### GitHub Actions verification

Record:

```text
workflow name
job name
observed check context
run ID
run URL
event
tested source head SHA
PR current head SHA
status
conclusion
```

State explicitly whether the CI run independently executed:

```text
git diff --check
docker compose config --quiet
docker compose build app
PostgreSQL readiness
python -m pytest
cleanup
```

### Documentation

List updated and intentionally unchanged documents.

### Risks and unverified items

Include:

* push-to-main execution cannot be observed before merge;
* branch protection is not configured;
* no custom Docker caching exists;
* private-repository Actions behavior is not part of this public-repository task;
* any transient registry or GitHub limitation encountered.

### Scope protection

Confirm:

* no real secret was used;
* no deployment or publishing was added;
* no product database migration was added;
* no runtime behavior changed;
* no worker or Redis service was required by CI;
* no branch-protection setting changed;
* no prohibited Git operation occurred.

## Completion reporting

No external completion-report file is required.

The pull-request description is the Task 010 completion report.

Task 010 may be described as complete only when:

1. local verification passes;
2. the implementation and documentation are pushed;
3. the exact current pushed head has a successful real CI result;
4. the PR description records that result;
5. Handoff Review approves that exact head.

A workflow run on an earlier head is historical evidence only.

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
workflow name
job/check name
successful run ID
tested source SHA
run conclusion
```

Approval applies only to the identified head and its successful CI result.

Review must inspect:

* the exact contract at the contract SHA;
* the full PR patch;
* workflow triggers;
* permissions;
* checkout SHA behavior;
* event-range patch check;
* Compose commands;
* safe environment;
* service readiness;
* migration boundary;
* cleanup;
* documentation;
* the real successful Actions run.

CI success does not replace implementation review.

## Correction behavior

Bounded corrections are authorized on the same task branch.

Use the expected message:

```text
fix: address Task 010 CI findings
```

A correction may change only:

* the CI workflow;
* directly affected CI-support configuration or tests;
* Task 010 documentation;
* PR-description evidence.

After every correction:

1. run relevant local verification;
2. push normally without force;
3. wait for the new workflow run;
4. require success on the new head;
5. update the PR description;
6. request review of the new exact head.

Do not amend or rebase reviewed commits to conceal a failed workflow or changed head.

Do not rewrite the contract to match an implementation deviation.

Material expansion—such as adding Redis, a worker, caching, multiple jobs, or host-side Python—returns to Active Task Planning unless live evidence proves it is the smallest necessary correction within the accepted goal.

## Merge boundary

The accepted merge method is a normal merge commit.

Merge requires:

1. successful local verification;
2. a successful CI result for the exact current pushed head;
3. final Handoff Review approval of that head;
4. separate explicit user authorization.

Task 010 does not authorize the merge.

The eventual merge push to the default branch should trigger the same workflow through the configured `push` event. That post-merge run cannot be required before merge and does not alter the pre-merge approval boundary.

Branch deletion is not authorized by this task.

## Prohibited committed artifacts

Do not commit:

```text
.env
.env.ci containing secrets
real Telegram tokens
real Telegram user IDs
OpenAI or other provider keys
database credentials with real operational value
credential-bearing URLs
GitHub tokens
Docker registry credentials
database dumps
PostgreSQL volume data
pytest cache
coverage output
generated Markdown notes
knowledge-base test output
GitHub Actions log copies
workflow-run JSON dumps
screenshots used as evidence
generated handoff files
review bundles
external completion reports
deployment configuration
release configuration
branch-protection configuration
unrelated changes
```

Safe literal CI placeholder values inside the workflow are allowed.

## Expected commit boundaries

### Contract commit

Expected message:

```text
docs: define task 010 GitHub Actions CI
```

Expected paths:

```text
tasks/010-github-actions-ci.md
docs/CURRENT_STATE.md
```

`docs/CURRENT_STATE.md` may change only to select Task 010 as the active task.

No workflow or implementation change belongs in the contract commit.

### Implementation commit

Expected message:

```text
ci: add pull-request verification
```

Expected paths:

```text
.github/workflows/ci.yml
.github/pull_request_template.md
AGENTS.md
README.md
docs/CURRENT_STATE.md
docs/WORKFLOW.md
docs/DECISIONS.md
tasks/010-github-actions-ci.md
```

Conditionally permitted only with direct justification:

```text
docker-compose.yml
Dockerfile
tests/conftest.py
tests/test_migrations.py
tests/<directly affected CI-support test>
.env.example
.gitignore
.dockerignore
```

The implementation commit must not include:

```text
application behavior changes
new database migrations
Telegram changes
worker logic changes
queue changes
artifact-format changes
deployment
publishing
branch protection
unrelated cleanup
```

### Correction commits

Expected message:

```text
fix: address Task 010 CI findings
```

Corrections remain on:

```text
task/010-github-actions-ci
```

They may modify only paths directly necessary to make the accepted CI boundary correct, safe, documented, and green.

Every correction must receive a new successful CI result before final approval.

## Authorized Git operations

Authorized only on the Task 010 branch:

```text
branch creation or switch
contract commit
task-branch push
draft PR creation
PR-description updates
implementation commit
implementation push
ready-for-review transition after green CI
bounded correction commits
bounded correction pushes
GitHub Actions run and check inspection
```

## Unauthorized Git and GitHub operations

This task does not authorize:

```text
git push origin main
git push --force
git push --force-with-lease
git rebase of reviewed commits
git commit --amend of pushed reviewed commits
gh pr merge
automatic merge
branch deletion
repository visibility changes
Actions permission changes
branch protection
ruleset changes
secret creation
environment creation
deployment
release publication
container publication
```

The final Task 010 outcome is a reviewed, green, unmerged pull request awaiting separate merge authorization.
