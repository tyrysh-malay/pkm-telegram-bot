# Task 004: Establish repository-driven workflow and context reporting

**Status:** completed
**Depends on:** Tasks 000–003
**Target file:** `tasks/004-repository-workflow-context.md`
**Expected implementation boundary:** one small documentation-and-tooling change after the task specification itself has been committed

## Goal

Establish a repeatable repository-local workflow that:

1. tells Codex which project documents to read;
2. defines when each project document must be updated;
3. standardizes how tasks are planned, implemented, reviewed, documented, and committed;
4. provides a compact, read-only repository context report suitable for supplying to Web Chat;
5. reduces the need to upload the complete documentation set for every planning or review conversation.

This task changes project-development workflow only. It must not change application runtime behavior.

## Confirmed current boundary

The following are accepted starting facts for this task:

* Tasks 000–003 are completed.
* Task 003 is closed and committed.
* The repository is the authoritative source of truth.
* Uploaded files in Web Chat may be stale snapshots.
* Codex can inspect the live local working tree, including uncommitted changes.
* Web Chat currently depends on uploaded files, supplied diffs, command output, and Codex reports.
* Direct GitHub repository access from Web Chat is not part of this task.

Before editing, Codex must verify from the live repository:

* current branch;
* current HEAD commit;
* working-tree status;
* recent commits;
* exact locations of project documentation;
* exact task filenames and current task conventions;
* whether `docs/ARCHITECTURE.md` and all other referenced documents exist;
* whether a `scripts/` directory or another established tooling location already exists;
* existing test-file and CLI conventions;
* whether the development image includes repository scripts and related tests;
* the next available identifier in `docs/DECISIONS.md`.

Documentation and this task specification must not override contradictory live repository evidence. Any contradiction must be reported before implementation proceeds.

## Problem and motivation

Project context currently exists across several places:

* the live repository;
* committed Git history;
* repository documentation;
* uncommitted local changes;
* Codex reports;
* uploaded Web Chat snapshots;
* separate architecture, planning, review, and future-scope conversations.

This creates several recurring problems:

* Web Chat snapshots become stale after repository changes.
* Git branch, commit, and working-tree information can become obsolete when maintained manually.
* Codex must repeatedly be told which files to inspect.
* task requirements, implementation reports, architectural decisions, and current-state documentation can overlap;
* it is not always clear which document should be updated after a change;
* copying the entire documentation set into Web Chat is inefficient;
* a generated report may accidentally be treated as authoritative after the repository changes again.

The project needs a small repository-owned workflow and reporting utility, not a general project-management or synchronization framework.

## Scope

### 1. Add `docs/WORKFLOW.md`

Create a concise but complete workflow document covering:

1. architecture discussion;
2. bounded task planning;
3. committing the accepted task specification;
4. Codex inspection of the live repository;
5. Codex implementation;
6. tests and acceptance verification;
7. implementation review against the task specification;
8. corrective implementation and review loops;
9. documentation updates based on verified behavior;
10. the implementation commit boundary;
11. selection of the next task.

The workflow must distinguish:

* committed repository state;
* uncommitted local working state;
* generated context-report snapshots;
* uploaded Web Chat snapshots;
* possible future GitHub-backed committed context.

The document must make clear that:

* the live local repository is authoritative for Codex;
* uncommitted local changes exist only in the local working tree;
* GitHub, if integrated later, would represent the pushed committed baseline rather than uncommitted local work;
* a generated context report is a point-in-time aid, not a new source of truth;
* Web Chat must continue labeling confirmed facts, assumptions, proposals, and items requiring repository verification.

### 2. Define conversation responsibilities

`docs/WORKFLOW.md` must define these responsibilities.

#### Architecture chat

Responsible for:

* discussing durable architectural boundaries;
* comparing architectural alternatives;
* identifying decisions that belong in `docs/DECISIONS.md` or `docs/ARCHITECTURE.md`;
* separating accepted decisions from tentative directions.

It must not:

* implement code;
* review an uncommitted implementation line by line;
* silently redefine an active task;
* treat future ideas as implemented behavior.

#### Active Task Planning chat

Responsible for:

* defining one bounded task;
* narrowing scope;
* writing acceptance criteria;
* defining non-goals and expected failure modes;
* identifying repository checks;
* producing a bounded Codex handoff.

It must not:

* combine unrelated milestones;
* rewrite architecture without escalation;
* review implementation details before evidence is supplied;
* silently change completed-task requirements to match implementation.

#### Codex

Responsible for:

* inspecting the live repository and Git state;
* reading the active task and required documentation;
* presenting an implementation plan before editing;
* making the smallest in-scope change;
* adding or updating tests;
* running required verification;
* updating affected documentation only after behavior is verified;
* reporting changed files, commands, results, limitations, and Git status.

Codex must not:

* trust stale documentation over the working tree;
* implement postponed functionality;
* introduce speculative abstractions;
* expose secrets;
* commit changes unless explicitly instructed.

#### Handoff Review chat

Responsible for:

* reviewing the supplied Git diff, command output, and Codex completion report;
* comparing implementation against the committed task specification;
* identifying missing acceptance criteria, regressions, scope expansion, and documentation mismatches;
* defining a bounded corrective loop when needed;
* confirming when the implementation is ready for its commit boundary.

It must not:

* invent repository facts that were not supplied;
* broaden the active task without returning to task planning;
* rewrite task requirements after implementation to hide a mismatch.

#### Future Scope chat

Responsible for:

* collecting product ideas;
* exploring possible future workflows;
* comparing possible later features;
* identifying questions that may require future architecture or planning work.

It must not:

* make an idea part of the active task;
* describe tentative features as implemented;
* add dependencies or runtime behavior to current work;
* record a durable architecture decision without the appropriate architecture process.

### 3. Define documentation update rules

`docs/WORKFLOW.md` must explicitly define the update responsibility for each document.

#### `docs/CURRENT_STATE.md`

Update after a task has been implemented and verified when the task changes the current semantic state of the project.

Rules:

* describe what currently works, what does not work, current operational boundaries, and the currently active task;

* replace or remove stale state rather than accumulating a chronological task history;

* do not use it as a changelog;

* do not manually maintain branch, HEAD commit, recent commits, or working-tree status when those facts can be generated;

* include a stable active-task field, preferably:

  ```text
  **Active task:** `tasks/<task-file>.md`
  ```

  or:

  ```text
  **Active task:** none selected
  ```

* do not claim behavior is implemented without verification;

* after Task 004 completion, record the established workflow and final context-report command;

* do not select or invent Task 005.

#### `docs/DECISIONS.md`

Update only for durable accepted architectural or development decisions.

Use it for decisions that:

* constrain future tasks;
* explain why one meaningful alternative was chosen;
* establish a lasting project rule.

Do not use it for:

* every changed filename;
* temporary implementation details;
* test output;
* routine completion notes;
* facts that belong only in `CURRENT_STATE.md`.

A decision may be marked tentative or unresolved when appropriate, but implementation must not be described as accepted merely because it was proposed.

#### `docs/ARCHITECTURE.md`

Update when a verified change affects:

* process or service boundaries;
* ownership of responsibilities;
* major data flow;
* runtime topology;
* integration boundaries;
* cross-component failure or recovery behavior.

Do not update it for routine internal refactoring that does not change an architectural boundary.

#### `docs/DATA_MODEL.md`

Update when a verified task changes:

* entities;
* fields;
* constraints;
* relationships;
* statuses;
* state-transition meaning;
* persistence ownership.

Do not update it for test fixtures or implementation-only query changes.

#### Domain documents

Domain documents such as `docs/TELEGRAM_INGESTION.md` must be updated when verified behavior in that domain changes.

Examples include:

* supported inputs;
* user-visible responses;
* idempotency behavior;
* transaction boundaries;
* runtime mode;
* known domain-specific failure handling.

Do not update a domain document for unrelated workflow or tooling changes.

#### `PROJECT_BRIEF.md`

Use the repository’s canonical project-brief path discovered during inspection.

Update only when the accepted product definition, MVP boundary, product value, or major non-goal changes.

Do not update it for routine implementation progress.

#### `README.md`

Update when a developer or user needs new operating instructions, including:

* setup commands;
* migration commands;
* test commands;
* configuration steps;
* supported command-line utilities;
* externally visible behavior.

Task 004 should add a short discoverability section for the final context-report command.

Do not duplicate the full workflow document in the README.

#### `.env.example`

Update whenever a task introduces, removes, or changes a configuration variable.

Use placeholders and safe example values only.

Task 004 is not expected to add configuration variables, so `.env.example` should remain unchanged unless repository inspection reveals a concrete need.

#### Task files

Task specifications must normally be committed before implementation begins.

Rules:

* the accepted requirements, scope, non-goals, and acceptance criteria form the review contract;
* requirements must not be silently rewritten after implementation to match the code;
* task status or completion metadata may be updated after verification;
* completion evidence may be appended without replacing the original requirements;
* a discovered requirement change must be recorded explicitly as an amendment with its reason;
* material scope changes require returning to Active Task Planning;
* implementation commits and task-specification commits should remain distinguishable where practical.

### 4. Add `tasks/TEMPLATE.md`

Create a reusable template for future bounded tasks.

It must contain at least:

* task title and number;
* status;
* goal;
* confirmed current boundary;
* repository verification requirements;
* problem or motivation;
* scope;
* out of scope;
* affected components;
* data, state, migration, and configuration impact;
* behavioral requirements;
* investigation requirements where relevant;
* expected failure modes and recovery behavior;
* tests;
* acceptance criteria;
* required verification commands;
* documentation impact;
* completion-report requirements;
* expected commit boundary.

The template must reinforce that:

* one task should produce one reviewable outcome;
* confirmed facts must be separated from assumptions and proposals;
* the active task must not introduce future abstractions without a present requirement;
* verification commands should be exact when known;
* Codex must not commit unless explicitly instructed.

The template may include optional sections, but it must remain usable without deleting a large amount of irrelevant boilerplate.

### 5. Update root `AGENTS.md`

Keep the root file concise.

It must direct Codex to:

1. inspect Git branch, HEAD, status, recent commits, and current diff;
2. read the active task;
3. read `docs/CURRENT_STATE.md`;
4. read `docs/WORKFLOW.md`;
5. read every document referenced by the active task;
6. inspect the live repository before trusting documentation;
7. distinguish verified repository facts from stale or aspirational documentation;
8. present a concise plan before editing;
9. make the smallest in-scope change;
10. avoid postponed functionality and unrelated refactoring;
11. run the task’s acceptance verification;
12. update affected documentation after verification;
13. avoid exposing secrets;
14. avoid committing without explicit instruction;
15. produce the completion report required by the task.

Detailed lifecycle descriptions, conversation-role definitions, and the documentation-update matrix must live in `docs/WORKFLOW.md`, not be duplicated in `AGENTS.md`.

Existing high-level project and engineering guardrails may remain when concise and still accurate.

### 6. Add a read-only project context report

Introduce a small repository-owned Python utility.

Preferred interface:

```bash
python scripts/project_context.py
```

Codex must first inspect existing repository conventions. A different path may be selected only when it is clearly more consistent with the existing repository. Any deviation from the preferred interface must be:

* explained in the implementation plan;
* documented in `docs/WORKFLOW.md`;
* documented briefly in `README.md`;
* reported in the completion report.

#### Output format

The required output format is Markdown written to standard output.

JSON, YAML, HTML, persistent report files, and multiple output modes are out of scope.

The generated Markdown must be suitable for:

```bash
python scripts/project_context.py > /tmp/pkm-project-context.md
```

The command itself must not create or modify repository files.

#### Required report content

The report must contain compact sections for:

* generation timestamp in UTC;
* current branch, or explicit detached-HEAD state;
* current HEAD commit hash and subject;
* clean or dirty working-tree status;
* staged, unstaged, and untracked changed paths, using concise Git status output;
* a bounded recent-commit list, preferably the latest ten commits;
* task files under `tasks/`, sorted deterministically;
* explicit task status when present;
* the active task recorded in `docs/CURRENT_STATE.md`;
* relevant project documentation paths and whether each exists;
* deterministic document titles, such as the first Markdown heading, where simple;
* a reminder that the report is a point-in-time snapshot and that the live repository remains authoritative.

The report must not include:

* Git diff contents;
* file contents from `.env`, secret files, credentials, tokens, or local configuration;
* arbitrary environment variables;
* database contents;
* Telegram message contents;
* inferred implementation claims;
* generated AI summaries;
* absolute local paths unless a clear repository convention requires them.

#### Task-status behavior

Task status must be conservative.

The utility may use:

* an explicit `Status:` field in a task file;
* the active-task field in `docs/CURRENT_STATE.md`;
* other deterministic metadata explicitly standardized by `tasks/TEMPLATE.md`.

It must not infer that a task is complete only because:

* its filename has a lower number;
* a similarly named commit exists;
* a later task file exists;
* implementation files appear to be present.

When explicit status is unavailable, report:

```text
unspecified
```

or an equivalent neutral value.

#### Documentation summary behavior

To keep the implementation small, Task 004 requires only a deterministic documentation index containing paths, existence, and document titles.

Semantic document summarization is not required.

#### Implementation constraints

The utility must:

* use the Python standard library unless repository inspection proves an existing dependency is already appropriate;
* call Git through explicit read-only commands;
* avoid `shell=True`;
* avoid destructive Git operations;
* avoid network access;
* avoid reading secret-bearing configuration files;
* produce deterministic ordering;
* succeed when run from the repository root;
* return a clear non-zero exit code when it cannot establish that it is operating in a Git repository;
* handle a dirty working tree without failing;
* report detached HEAD explicitly;
* report missing optional documentation as missing rather than inventing content;
* avoid modifying timestamps or repository files.

### 7. Add automated tests for the context report

Add focused tests using the repository’s existing test conventions.

Preferred test path:

```text
tests/test_project_context.py
```

Tests should use temporary Git repositories or testable pure functions where practical.

At minimum, verify:

1. Markdown output includes branch and HEAD information.
2. Dirty or untracked files are reported by path.
3. recent commits are bounded and ordered.
4. task files are listed deterministically.
5. explicit task status is reported.
6. missing task status is reported conservatively.
7. the active task can be read from `docs/CURRENT_STATE.md`.
8. missing optional documentation is reported without an implementation claim.
9. detached HEAD is handled.
10. invoking the report does not change repository status or create repository files.
11. secret-file contents are never included in output.
12. running outside a Git repository produces a clear failure.

Do not build a general Git abstraction framework solely for these tests.

### 8. Add a durable decision

Add the next available decision entry to `docs/DECISIONS.md`.

The decision must establish that:

* repository-local task files and documentation define the development workflow;
* accepted task specifications are normally committed before implementation;
* Codex inspects the live local working tree and does not treat documentation as stronger evidence than repository state;
* implementation is reviewed against the accepted task specification;
* documentation is updated after verification;
* a read-only generated context report is the standard compact handoff to Web Chat;
* the report is a snapshot rather than a source of truth;
* uploaded snapshots may be stale;
* possible future GitHub retrieval would describe only the committed and pushed baseline;
* automatic commits and automatic rewriting of `CURRENT_STATE.md` are not part of this decision.

Do not hardcode a decision number until the live file has been inspected.

### 9. Update `docs/CURRENT_STATE.md`

After implementation and verification:

* remove stale Task 003 active-work wording;
* describe Task 004 as completed;
* record the final workflow and context-report paths;
* record the final context-report command;
* describe the report as read-only and point-in-time;
* retain the actual current application capabilities and known limitations;
* remove manually maintained branch, HEAD, recent-commit, and working-tree values;
* set the active task to `none selected` unless the user has explicitly selected another task;
* do not invent Task 005;
* include only facts verified from the live repository and test results.

### 10. Update `README.md`

Add a short developer-facing section that:

* shows the final context-report command;
* states that it prints Markdown to standard output;
* gives an example redirect to a file outside the repository;
* states that it is read-only;
* points to `docs/WORKFLOW.md` for the full project workflow.

Do not duplicate the complete workflow or conversation-role definitions in the README.

## Affected components

### Application

No application runtime behavior changes.

### Database

No model, migration, schema, fixture, or database-runtime changes.

### Telegram bot

No handlers, polling, message ingestion, acknowledgement, or configuration changes.

### Worker and queue

No worker, Redis, Dramatiq, task queue, retry, or scheduling changes.

### Documentation

Expected changes:

* `tasks/004-repository-workflow-context.md`;
* `docs/WORKFLOW.md`;
* `tasks/TEMPLATE.md`;
* root `AGENTS.md`;
* `docs/DECISIONS.md`;
* `docs/CURRENT_STATE.md`;
* `README.md`.

### Tooling

Expected addition:

* `scripts/project_context.py`, unless repository inspection identifies a more appropriate existing location.

### Tests

Expected addition:

* focused automated tests for the context-report utility.

### Infrastructure

No Compose, CI/CD, deployment, or infrastructure behavior changes are expected.

A Dockerfile or packaging adjustment is permitted only if the existing authoritative test setup cannot see the new script or tests. Any such adjustment must be minimal and explicitly justified.

## Data, state, migration, and configuration impact

Expected impact:

* no database migration;
* no persistent application-state change;
* no new environment variables;
* no `.env.example` changes;
* no secrets;
* no generated repository artifact committed by the reporting utility;
* no application configuration changes.

## Expected failure modes and safety behavior

### Not a Git repository

The utility must:

* print a clear error to standard error;
* exit non-zero;
* create or modify nothing.

### Git command unavailable or fails

The utility must not emit a report that appears complete.

It must:

* identify the failed operation;
* exit non-zero;
* avoid partial claims that could be mistaken for verified state.

### Dirty working tree

A dirty working tree is normal input.

The utility must:

* succeed;
* label the tree as dirty;
* list changed paths concisely;
* avoid printing diff contents.

### Detached HEAD

The utility must:

* succeed;
* label the repository as detached;
* still report HEAD and recent commits.

### Missing optional documentation

The utility must:

* mark the path as missing;
* continue producing the report;
* not infer document content.

Missing required workflow files after Task 004 implementation should fail the relevant automated acceptance test, even if the report itself can describe them as missing.

### Missing or malformed task metadata

The utility must:

* report task status as `unspecified`;
* not infer completion from ordering or filenames;
* continue producing the report.

### Secret exposure risk

The utility must not read or print:

* `.env`;
* credentials;
* tokens;
* arbitrary environment values;
* database rows;
* file diffs.

Only safe repository metadata and whitelisted documentation metadata may be inspected.

### Partial or ambiguous documentation

The report must label unavailable or ambiguous information rather than treating it as implemented behavior.

## Out of scope

Do not add:

* direct GitHub API integration;
* GitHub OAuth;
* GitHub personal-access tokens;
* private-repository credentials;
* Web Chat repository write access;
* automatic Git commits;
* automatic pushes;
* automatic task selection;
* automatic rewriting of `docs/CURRENT_STATE.md`;
* automatic modification of any documentation;
* persistent report generation inside the repository;
* report upload automation;
* CI/CD changes;
* pull-request automation;
* issue-tracker integration;
* a general workflow engine;
* a plugin system;
* a CLI framework dependency;
* Redis;
* Dramatiq;
* background workers;
* AI processing;
* AI-generated documentation summaries;
* Markdown knowledge-artifact generation;
* changes to Telegram runtime behavior;
* Telegram identity redesign;
* unrelated application, persistence, or test refactoring.

GitHub-backed context retrieval may be mentioned only as a possible future improvement representing the pushed committed baseline.

## Tests

### Unit and focused utility tests

Test:

* Git metadata collection;
* task metadata parsing;
* active-task parsing;
* document indexing;
* Markdown rendering;
* missing-data behavior;
* safety and read-only behavior.

### Integration-style utility test

Run the actual command against a temporary Git repository and verify:

* successful Markdown output;
* expected Git facts;
* unchanged repository status before and after invocation.

### Existing regression suite

Run the complete existing pytest suite in the authoritative Docker environment.

No live Telegram test is required because Telegram runtime behavior is unchanged.

### Manual verification

Generate a report from the real repository and inspect it for:

* compactness;
* readability;
* correct branch and HEAD;
* correct dirty-state reporting;
* task list;
* active-task field;
* documentation index;
* absence of secrets and file contents;
* clear snapshot disclaimer.

## Acceptance criteria

Task 004 is complete only when all of the following are true.

### Workflow documentation

* `docs/WORKFLOW.md` exists.
* It documents the complete task lifecycle.
* It defines all five conversation responsibilities.
* It distinguishes committed state, uncommitted state, generated reports, uploaded snapshots, and possible future GitHub context.
* It includes explicit update rules for every required project document.
* It states that task requirements must not be silently rewritten after implementation.

### Task template

* `tasks/TEMPLATE.md` exists.
* It contains every required planning, verification, documentation, and completion-report section.
* It separates confirmed facts from repository-verification requirements.
* It supports one bounded, reviewable task.

### Codex instructions

* root `AGENTS.md` points Codex to the active task, `CURRENT_STATE.md`, `WORKFLOW.md`, and task-referenced documents;
* it requires live repository inspection before trusting documentation;
* it requires a pre-edit plan, minimal change, verification, documentation updates, and a completion report;
* it forbids out-of-scope work and commits without explicit instruction;
* it does not duplicate the full workflow document.

### Context report

* the final documented command succeeds from the repository root;
* it prints Markdown to standard output;
* it reports branch or detached-HEAD state;
* it reports HEAD;
* it reports clean or dirty status;
* it reports changed paths without diff contents;
* it reports bounded recent commits;
* it lists task files deterministically;
* it reports explicit task status and uses a neutral value when status is absent;
* it reports the active task from `CURRENT_STATE.md`;
* it indexes relevant documentation paths and titles;
* it contains a snapshot/source-of-truth disclaimer;
* it performs no writes;
* it does not expose secrets;
* it adds no third-party dependency unless explicitly justified by repository evidence.

### Tests and safety

* focused utility tests pass;
* the complete existing pytest suite passes;
* running the utility does not alter `git status`;
* running outside a Git repository fails clearly;
* missing optional documentation does not create false implementation claims;
* detached HEAD is covered;
* secret contents are not emitted.

### Durable documentation

* the next available durable decision records the repository-driven lifecycle and read-only context reporting;
* `docs/CURRENT_STATE.md` reflects verified post-Task-004 semantic state;
* manually maintained branch, commit, and working-tree values are removed from `CURRENT_STATE.md`;
* `README.md` contains concise context-report usage;
* `.env.example`, data-model documentation, architecture documentation, and Telegram behavior documentation remain unchanged unless live repository inspection finds a concrete Task 004 reason to change them.

### Scope protection

* no application runtime behavior changes;
* no database or migration changes;
* no Telegram behavior changes;
* no worker, Redis, AI, GitHub API, CI/CD, or automatic commit behavior;
* no automatic rewriting of repository documentation.

## Required verification

Codex must first record the initial state:

```bash
git branch --show-current
git rev-parse HEAD
git status --short
git log --oneline --decorate -10
git diff --check
```

Inspect relevant repository structure:

```bash
find docs tasks -maxdepth 2 -type f -print | sort
find scripts tests -maxdepth 2 -type f -print 2>/dev/null | sort
```

Use the final selected command below. The preferred command is shown:

```bash
python scripts/project_context.py
```

Generate a copy outside the repository:

```bash
python scripts/project_context.py > /tmp/pkm-project-context.md
test -s /tmp/pkm-project-context.md
sed -n '1,240p' /tmp/pkm-project-context.md
```

Verify read-only behavior:

```bash
before_status="$(git status --porcelain=v1 --untracked-files=all)"
python scripts/project_context.py > /tmp/pkm-project-context-readonly.md
after_status="$(git status --porcelain=v1 --untracked-files=all)"
test "$before_status" = "$after_status"
```

Verify that obvious secret values or file contents are not emitted. Adapt patterns to safe test fixtures; do not print actual secrets:

```bash
! grep -E 'TELEGRAM_BOT_TOKEN=|DATABASE_URL=|OPENAI_API_KEY=' \
  /tmp/pkm-project-context.md
```

Run focused tests using the repository’s authoritative environment. The exact focused path may be adapted after inspection:

```bash
docker compose config --quiet
docker compose up -d --build
docker compose exec app python -m pytest tests/test_project_context.py
docker compose exec app python -m pytest
```

Verify existing application health after the full suite:

```bash
curl --retry 5 --retry-all-errors --retry-delay 1 \
  http://localhost:8000/health

curl --retry 5 --retry-all-errors --retry-delay 1 \
  http://localhost:8000/ready
```

Run final repository checks:

```bash
git diff --check
git status --short
git diff --stat
git diff -- \
  AGENTS.md \
  README.md \
  docs/WORKFLOW.md \
  docs/CURRENT_STATE.md \
  docs/DECISIONS.md \
  tasks/TEMPLATE.md \
  tasks/004-repository-workflow-context.md \
  scripts/project_context.py \
  tests/test_project_context.py
```

When the final utility path differs from the preferred path, replace the affected commands and paths with the documented final interface.

No live Telegram message is required for Task 004.

## Documentation impact

### Required updates

* add `docs/WORKFLOW.md`;
* add `tasks/TEMPLATE.md`;
* update root `AGENTS.md`;
* add the context-report utility;
* add its tests;
* add the next available entry to `docs/DECISIONS.md`;
* update `docs/CURRENT_STATE.md`;
* update `README.md`;
* retain this task file as the accepted implementation contract.

### Not expected to change

Unless repository inspection identifies a direct and documented reason:

* `docs/ARCHITECTURE.md`;
* `docs/DATA_MODEL.md`;
* `docs/TELEGRAM_INGESTION.md`;
* the canonical project brief;
* `.env.example`;
* database migrations;
* Docker Compose;
* application modules.

## Codex execution requirements

Before editing, Codex must:

1. inspect Git state;
2. read root `AGENTS.md`;
3. read this task file;
4. read `docs/CURRENT_STATE.md`;
5. read `docs/DECISIONS.md`;
6. read `docs/ARCHITECTURE.md`;
7. read the canonical project brief;
8. inspect task, documentation, script, test, Docker, and packaging conventions;
9. explain the proposed file changes and selected context-report interface;
10. identify contradictions between repository facts and documentation.

During implementation, Codex must:

1. make the smallest change satisfying this task;
2. keep workflow detail in `docs/WORKFLOW.md`;
3. keep `AGENTS.md` concise;
4. use the standard library for the reporting utility unless clearly insufficient;
5. avoid application-runtime changes;
6. avoid silently rewriting task requirements;
7. avoid automatic commits;
8. avoid exposing secrets.

After implementation, Codex must:

1. run the focused tests;
2. run the complete authoritative test suite;
3. run the context-report command against the real repository;
4. verify that the command is read-only;
5. inspect the report for false claims and secret exposure;
6. update documentation from verified facts;
7. run `git diff --check`;
8. report the final working tree and clean commit boundary;
9. not commit unless explicitly instructed.

## Required completion-report format

Codex must return a completion report with exactly these sections.

### 1. Initial repository state

Report:

* branch;
* starting HEAD;
* starting working-tree status;
* recent relevant commits;
* contradictions found between documentation and the live repository.

### 2. Implementation plan followed

Summarize the approved plan and note any justified deviation.

### 3. Repository inspection findings

Report:

* canonical documentation paths;
* existing script and test conventions;
* selected context-report path and interface;
* selected output format;
* next decision identifier;
* any missing or stale documentation found.

### 4. Files changed

List every changed file with one sentence explaining its purpose.

### 5. Workflow and documentation design

Summarize:

* lifecycle established;
* role boundaries;
* documentation-update rules;
* task-file immutability and amendment rules;
* source-of-truth hierarchy.

### 6. Context-report design

Report:

* final command;
* output format;
* Git commands used;
* task-status rules;
* missing-document behavior;
* detached-HEAD behavior;
* secret-protection measures;
* why the utility is read-only.

### 7. Tests added or updated

List the tested behaviors and final test files.

### 8. Verification results

For every required command, report:

* exact command;
* success or failure;
* relevant output summary.

Include:

* focused test result;
* complete pytest result;
* context-report execution result;
* read-only before/after status comparison;
* `/health` result;
* `/ready` result;
* `git diff --check` result.

### 9. Documentation updates

State which documents were updated and why.

Explicitly identify documents intentionally left unchanged.

### 10. Acceptance-criteria assessment

Evaluate every acceptance-criteria group as:

```text
passed
failed
not verified
```

Explain every failure or unverified item.

### 11. Scope and limitations

Report:

* any out-of-scope change that was avoided;
* any unavoidable deviation;
* anything not verified;
* any possible future GitHub-context improvement without implementing it.

### 12. Final Git boundary

Report:

* final branch;
* final HEAD;
* final `git status --short`;
* changed-file summary;
* whether a commit was created;
* recommended commit message.

Unless explicitly instructed otherwise, the report must state:

```text
No commit was created.
```

## Expected commit boundary

The accepted task specification should be committed before Codex implementation.

After implementation review and corrections, Task 004 should form one reviewable implementation commit containing only:

* workflow documentation;
* task template;
* concise Codex instructions;
* read-only context-report utility;
* focused tests;
* durable decision;
* current-state update;
* concise README usage.

Suggested implementation commit message:

```text
docs: establish repository-driven workflow
```

A separate tooling-oriented message is also acceptable when repository conventions favor it:

```text
chore: add project context reporting
```

Do not include unrelated application changes in the same commit.

## Completion evidence

Implemented in the working tree with repository-local workflow documentation,
task template, read-only context-reporting utility, automated utility tests, and
the durable decision D-023.

The authoritative development image rebuilt successfully. The focused context
suite passed 10 tests, the complete suite passed 25 tests, and the host-published
`/health` and `/ready` checks returned successful JSON responses.
