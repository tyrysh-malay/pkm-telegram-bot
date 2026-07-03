# Task 009: Migrate project collaboration to GitHub-backed pull-request reviews

**Status:** planned
**Depends on:** Tasks 000–008
**Target file:** `tasks/009-github-backed-collaboration.md`
**Expected branch:** `task/009-github-backed-collaboration`
**Expected pull-request title:** `Task 009: Migrate project collaboration to GitHub-backed pull-request reviews`
**Expected contract commit:** `docs: define task 009 GitHub-backed collaboration`
**Expected implementation commit:** `chore: migrate collaboration to GitHub pull requests`
**Expected correction commit:** `fix: address Task 009 review findings`
**Expected merge method:** normal merge commit, performed only after separate explicit user authorization

## Commit, push, and pull-request authorization

This accepted task explicitly authorizes Codex to perform only the following repository-writing and GitHub actions:

1. create or switch to the branch:

   ```text
   task/009-github-backed-collaboration
   ```

2. create the distinct Task 009 contract commit on that branch;

3. push that task branch to the verified project remote;

4. open one draft pull request from that task branch to the verified default branch;

5. update the pull-request title and description;

6. create one coherent Task 009 implementation commit;

7. push that implementation commit to the same task branch;

8. mark the pull request ready for review after all readiness conditions pass;

9. create and push bounded Task 009 correction commits on the same branch when review findings require them.

This task does **not** authorize Codex to:

* push directly to the default branch;
* merge the pull request;
* delete the remote or local task branch;
* force-push after the pull request has been opened;
* amend or rebase already pushed reviewed commits without explicit agreement;
* create another product-task branch;
* commit unrelated local changes;
* change repository settings or branch-protection rules.

The user must provide separate explicit authorization before any merge.

## Goal

Replace the upload-heavy context-report and implementation-review-bundle workflow with a repository-owned GitHub task-branch and pull-request workflow.

The accepted normal lifecycle is:

```text
clean synchronized default branch
→ create bounded task branch
→ commit accepted task specification
→ push task branch
→ open draft pull request
→ confirm connected Web Chat access
→ implement and verify locally
→ commit and push reviewable implementation
→ update PR description
→ mark PR ready
→ Handoff Review inspects exact pushed PR head
→ bounded correction commits when required
→ final approval
→ separately authorized merge commit
```

Task 009 must be the first complete pilot of this workflow.

The migration must preserve the distinction between local uncommitted work and GitHub-visible committed work:

```text
Codex local working tree
→ may contain uncommitted work
→ authoritative for Codex while editing
→ not visible through GitHub
→ not reviewable by connected Web Chat

GitHub branch and pull request
→ contain committed and pushed work only
→ visible to connected Web Chat
→ define the shared implementation-review boundary
```

GitHub must never be described as exposing uncommitted local state.

## Confirmed current boundary

The user has confirmed:

* Tasks 000–008 are complete.

* Task 008 established private-owner Telegram authorization while leaving repository workflow tooling unchanged.

* The current collaboration workflow uses:

  ```text
  scripts/project_context.py
  scripts/review_bundle.py
  external completion-report files
  manually uploaded Web Chat files
  ```

* The existing workflow was created because Web Chat could not directly inspect the private GitHub repository.

* The project now has a connected private GitHub repository that is intended to provide committed context and pull-request evidence to Web Chat.

* The local working tree remains authoritative to Codex for uncommitted editing and local verification.

* GitHub represents only committed and pushed repository state.

* A repository-owned task specification remains the implementation-review contract.

* The exact contract must be pinned to a task path at a full commit SHA rather than inferred from the later branch head.

* A pull request must replace the generated implementation-review bundle only after connected Web Chat access has been explicitly verified.

* The pull-request description must replace the external completion report after the access gate passes.

* Verification results in a PR description remain claims supplied by Codex unless independently executed by CI.

* CI is not implemented by this task.

* Task 009 must not alter application, Telegram, persistence, queue, worker, artifact, or knowledge-base behavior.

* Historical task files and completion evidence must remain intact.

* Task 009 may supersede active workflow instructions without rewriting historical Tasks 004–008.

* D-027 is expected to be the latest existing durable decision, making D-028 the expected next identifier, subject to live verification.

Uploaded documents are point-in-time evidence. Codex must verify all repository, remote, branch, decision, and GitHub facts against the live local repository and connected GitHub repository before editing.

## Transitional bootstrap

Task 009 cannot assume that the new workflow has already replaced the old one.

Implementation must proceed in two phases.

### Phase A: establish the task branch and draft pull request

Before changing workflow documentation or removing reporting tools:

1. verify that completed Task 008 is committed;

2. verify that Task 008 is present on the pushed remote default branch;

3. verify that the local default branch is synchronized with the remote default branch;

4. verify that the working tree is clean;

5. create:

   ```text
   task/009-github-backed-collaboration
   ```

6. add the accepted Task 009 specification;

7. update only the smallest necessary active-task pointer when repository convention requires it;

8. create the distinct contract commit;

9. push the task branch;

10. open one draft pull request;

11. record in its description:

    ```text
    task path
    exact full contract commit SHA
    base branch
    task branch
    concise goal
    access-gate status
    ```

No implementation change may precede the contract commit.

### Phase B: connected-access gate

After the draft pull request exists, Codex must provide the user with:

```text
repository name
pull-request number or URL
base branch
task branch
task path
full contract commit SHA
current PR head SHA
```

Do not expose credentials or a credential-bearing remote URL.

Before deleting, disabling, or superseding the current reporting workflow, obtain explicit confirmation that connected Web Chat can inspect all of:

```text
the private repository
the draft pull request
the task file at the exact contract commit
the pull-request commit list
the pull-request patch or changed files
the current pull-request head SHA
```

The access gate is a human-confirmed transition boundary. Codex must not infer that the gate passed merely because:

* `git push` succeeded;
* `gh pr view` succeeded locally;
* the repository exists;
* the PR URL can be opened in a browser;
* GitHub CLI is authenticated.

### Gate failure

If connected Web Chat cannot inspect any required evidence:

* stop the workflow migration;
* do not remove either reporting script;
* do not remove either focused reporting test;
* do not mark D-023 or D-024 superseded;
* do not replace the active workflow instructions;
* do not mark Task 009 completed;
* keep the pull request in draft state;
* record the exact blocker in the PR description;
* preserve the current context-report and review-bundle fallback.

A failed gate is an external collaboration blocker, not an application defect.

The user may later resolve access and resume the same Task 009 branch and draft PR.

### Gate success

Only after explicit confirmation may Codex:

* migrate active workflow documentation;
* remove obsolete reporting scripts and their focused tests;
* update D-023 and D-024 as superseded;
* treat the PR description as the normal completion summary;
* complete Task 009 review without generating a new review bundle.

## Repository verification requirements

Before editing, Codex must inspect and report the live repository and GitHub state.

## Local Git state

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

* Task 008 implementation and any review corrections are committed;
* the current working tree is clean;
* no staged, unstaged, or untracked Task 009 implementation exists;
* no unrelated local work would be included;
* no Task 009 or later conflicting task file exists;
* `tasks/009-github-backed-collaboration.md` is the next repository-consistent task filename;
* the active-task field follows current repository convention.

If unrelated local changes exist, do not stash, discard, commit, or move them automatically. Report the blocker.

## Remote and default branch

Inspect:

```bash
git remote -v
git remote get-url origin
git fetch origin --prune
git remote show origin
```

Do not reproduce a remote URL containing embedded credentials.

Determine the actual default branch from repository evidence rather than assuming `main`.

Where GitHub CLI is available, inspect:

```bash
gh auth status
gh repo view --json \
  nameWithOwner,isPrivate,defaultBranchRef,mergeCommitAllowed,rebaseMergeAllowed,squashMergeAllowed
```

Verify:

* `origin` points to the intended private project repository;
* the authenticated GitHub identity has access;
* the repository is private;
* the default branch is known;
* normal merge commits are allowed;
* Task 008 is present on the remote default branch;
* the local default branch is neither ahead of nor behind the remote default branch before branch creation.

For a default branch confirmed as `main`, use:

```bash
git rev-parse main
git rev-parse origin/main
git rev-list --left-right --count main...origin/main
```

Expected synchronization result:

```text
0	0
```

Adapt commands only when the live default branch has another name.

Task 009 must not silently enable merge commits through repository settings. If the repository disallows the accepted normal merge method, report the contradiction before implementation.

## Existing branches and pull requests

Inspect:

```bash
git branch --list
git branch -r
```

Where supported:

```bash
gh pr list --state all \
  --head task/009-github-backed-collaboration \
  --json number,title,state,isDraft,baseRefName,headRefName,headRefOid,url
```

Verify:

* no conflicting local branch exists;
* no conflicting remote branch exists;
* no duplicate Task 009 pull request exists.

If the exact branch or PR already exists:

* inspect it;
* compare its base, task path, contract SHA, commits, and patch to this task;
* resume it only when it is clearly the same authorized Task 009 effort;
* do not delete or replace it automatically;
* report any mismatch.

## Workflow files and active references

Inspect:

```text
AGENTS.md
docs/WORKFLOW.md
docs/CURRENT_STATE.md
docs/DECISIONS.md
README.md
tasks/TEMPLATE.md
tasks/PROMPT.md, when present
scripts/project_context.py
scripts/review_bundle.py
tests/test_project_context.py
tests/test_review_bundle.py
Dockerfile
.dockerignore
.gitignore
.github/
```

Search the active repository for:

```text
project_context.py
review_bundle.py
context report
project context report
review bundle
completion report
contract-from-head
pkm-handoffs
manual upload
Source folder
/tmp
```

Classify every match as:

* active current instruction;
* implementation support;
* historical task contract;
* historical completion evidence;
* unrelated use.

Historical references must not be removed merely because the active workflow changes.

## Docker and test support

Determine:

* whether Git installation in the development image is still used by any active application, test, development, or future repository function;
* whether the Dockerfile copies `scripts/` or reporting tests specifically or copies broader directories;
* whether deleting the scripts requires a Dockerfile or `.dockerignore` adjustment;
* whether `.gitignore` contains entries added solely for the old handoff workflow;
* whether any remaining test imports or invokes the removed utilities.

Do not remove Git from the image unless live evidence proves that it has no current repository purpose.

## Decisions and documentation

Read all durable decisions affecting repository workflow, especially the live equivalents of:

```text
D-023
D-024
D-027
```

Verify:

* the next available decision number;
* the exact current statuses of D-023 and D-024;
* the principles that must survive supersession;
* whether another later decision already selects a GitHub workflow.

Read the documentation-update matrix in `docs/WORKFLOW.md` and preserve it.

Any material contradiction must be reported before implementation. It must not be hidden by rewriting this task after implementation has started.

## Problem or motivation

The current reporting workflow was a reasonable compatibility solution when Web Chat could not inspect the private repository.

It now creates avoidable overhead:

* Codex must generate external context files;
* Codex must maintain separate completion-report files;
* implementation review requires one generated bundle;
* bundle generation must capture and validate every changed text file;
* files must be uploaded manually;
* a bundle becomes stale after every repository or report change;
* upload errors can separate evidence from the live project;
* reviewers must reconcile point-in-time artifacts with repository state;
* workflow output directories and report-file safety add process complexity;
* uncommitted local work still cannot be inspected directly by Web Chat.

A connected private GitHub repository provides a more natural committed-review boundary:

```text
task contract commit
+ task branch
+ pull request base/head
+ PR commits
+ PR patch
+ PR description
```

This does not eliminate the local/remote distinction. It makes that distinction explicit and moves review to committed, pushed work.

## Scope

Implement the following bounded outcome:

1. pilot Task 009 on one dedicated task branch;
2. commit its accepted specification before implementation;
3. push the contract commit;
4. open one draft pull request;
5. record the exact contract task path and SHA;
6. verify connected Web Chat access before workflow removal;
7. define the local/default-branch/task-branch/PR authority model;
8. replace the normal active workflow with task branches and PR review;
9. update Codex instructions with precise commit and push authority;
10. update the reusable task template with branch, commit, PR, correction, and merge boundaries;
11. add one concise pull-request template;
12. replace active README handoff commands with the contributor PR workflow;
13. replace current-state reporting instructions with the GitHub-backed collaboration model;
14. add the next durable GitHub collaboration decision;
15. mark D-023 and D-024 superseded after the access gate succeeds;
16. remove obsolete reporting utilities and focused tests after the gate succeeds;
17. remove only directly obsolete Docker or ignore support confirmed by inspection;
18. preserve historical tasks and evidence;
19. run structural verification and the complete authoritative application suite;
20. update the draft PR with the final completion summary;
21. push the reviewable implementation;
22. mark the PR ready only after readiness criteria pass;
23. conduct Handoff Review against the exact pushed PR head;
24. apply bounded correction commits on the same branch when required;
25. leave merge execution outside Task 009 authorization.

## Out of scope

Do not add:

* GitHub Actions;
* CI or CD;
* branch-protection automation;
* repository-ruleset changes;
* status-check requirements;
* release automation;
* automatic merge;
* merge queues;
* automatic dependency updates;
* Dependabot configuration;
* issue templates;
* issue forms;
* project boards;
* GitHub OAuth in the application;
* GitHub API integration in the PKM bot;
* automatic pull-request creation by application runtime code;
* a general Git or GitHub abstraction;
* automatic Git commits for generated notes;
* automatic knowledge-base pushes;
* automatic knowledge-base pull requests;
* deployment workflows;
* application runtime changes;
* Telegram behavior changes;
* authorization changes;
* database schema changes;
* Alembic migrations;
* ProcessingTask changes;
* Redis or Dramatiq changes;
* Markdown rendering changes;
* knowledge-base file changes;
* environment-variable changes;
* Docker Compose topology changes;
* health or readiness changes;
* another product task;
* broad repository cleanup;
* rewriting historical task contracts;
* deleting historical completion evidence;
* direct pushes to the default branch;
* task-branch merge execution.

CI should be considered as a separate future task after the branch and PR workflow has been established.

## Affected components

## Git and GitHub workflow

Expected changes:

* one Task 009 branch;
* one contract commit;
* one draft PR;
* one implementation commit;
* optional bounded correction commits;
* explicit PR metadata and review-head tracking.

## Repository documentation

Expected changes:

```text
docs/WORKFLOW.md
docs/CURRENT_STATE.md
docs/DECISIONS.md
README.md
AGENTS.md
tasks/TEMPLATE.md
tasks/009-github-backed-collaboration.md
```

Conditional change:

```text
tasks/PROMPT.md
```

when it actively instructs use of the superseded workflow.

## GitHub metadata

Expected addition:

```text
.github/pull_request_template.md
```

## Reporting tools

Expected removals after the connected-access gate succeeds:

```text
scripts/project_context.py
scripts/review_bundle.py
tests/test_project_context.py
tests/test_review_bundle.py
```

## Development image and ignore rules

Conditional changes after live inspection:

```text
Dockerfile
.dockerignore
.gitignore
```

Only directly obsolete support may be removed.

## Components expected to remain unchanged

Unless live inspection reveals an unavoidable active workflow reference, do not modify:

```text
app/
alembic/
docker-compose.yml
.env.example
knowledge-base/
docs/ARCHITECTURE.md
docs/DATA_MODEL.md
docs/TELEGRAM_INGESTION.md
docs/MARKDOWN_ARTIFACTS.md
docs/PROJECT_BRIEF.md
tasks/000-bootstrap.md
tasks/001-persistence-foundation.md
tasks/002-telegram-text-ingestion.md
tasks/003-isolate-database-tests.md
tasks/004-repository-workflow-context.md
tasks/005-implementation-review-bundles.md
tasks/006-deterministic-markdown-artifacts.md
tasks/007-durable-background-processing.md
tasks/008-restrict-telegram-ingestion-owner.md
```

Updating the status of D-023 and D-024 in `docs/DECISIONS.md` is required and is not a rewrite of the historical task files.

## Data, state, migration, and configuration impact

## Application data and runtime state

Expected impact:

```text
none
```

Requirements:

* no database migration;
* no schema change;
* no database backfill;
* no Message, User, Artifact, or ProcessingTask mutation;
* no Redis-state change caused by the implementation;
* no Telegram interaction change;
* no knowledge-base artifact change;
* no environment-variable addition or removal;
* no Docker Compose service change.

## Git state

Task 009 intentionally changes repository and GitHub collaboration state:

```text
one new task branch
one contract commit
one draft pull request
one implementation commit
zero or more bounded correction commits
```

The default branch remains unchanged until a separately authorized merge.

## GitHub state

Task 009 may create and update:

* one draft pull request;
* its title;
* its description;
* its draft/readiness state;
* pushed commits on the exact task branch.

Task 009 must not:

* merge;
* close the PR except when explicitly instructed after a proven bootstrap error;
* delete the branch;
* modify repository settings;
* modify branch protections;
* expose secrets.

## Local workflow artifacts

After a successful access gate, the normal workflow must not require:

```text
project-context Markdown files
contract-from-HEAD copies
external completion-report files
review-bundle files
manual Web Chat source uploads
```

Task 009 must not commit any existing external report or bundle.

The old external directory may continue to exist on the developer’s machine. This task does not delete user-owned files outside the repository.

## Behavioral requirements

## Source-of-truth and visibility model

The final workflow must define four distinct boundaries.

### Local working tree

The local working tree is authoritative to Codex while editing and running local verification.

Uncommitted changes:

* are visible only to Codex and local tools;
* may not be represented by the remote task branch;
* may not be described by Handoff Review as reviewed repository state;
* must be committed and pushed before review;
* must not be inferred from PR-description claims.

Codex must report when requested review evidence exists only locally.

### Pushed default branch

The pushed default branch represents the accepted shared baseline.

It contains:

* merged accepted implementations;
* verified merged documentation;
* completed task state;
* superseded workflow state after Task 009 is eventually merged.

Normal task implementation must not occur directly on this branch.

Updating the local default branch with a fast-forward from its remote counterpart is allowed. Creating implementation commits or pushing task work directly to it is not.

### Pushed task branch

One task branch represents one bounded active task.

Required name format:

```text
task/<three-digit-task-number>-<short-slug>
```

Examples:

```text
task/009-github-backed-collaboration
task/010-structured-ai-enrichment
```

Requirements:

* branch from the current remote default-branch baseline;
* do not combine unrelated tasks;
* do not reuse a completed task branch for a new task;
* do not force-push after review begins without explicit agreement;
* do not rebase reviewed commits silently;
* preserve contract and implementation commit identities.

### Pull request

The pull request is the shared review boundary.

It records:

* exact base branch;
* exact task branch;
* exact contract commit;
* current pushed head;
* commits;
* patch;
* changed files;
* supplied implementation and verification summary;
* available independent checks.

It does not record uncommitted local work.

## Contract commit

The accepted task specification must be committed before implementation.

For Task 009, the contract commit should contain only:

```text
tasks/009-github-backed-collaboration.md
docs/CURRENT_STATE.md
```

`docs/CURRENT_STATE.md` may change only to set:

```text
**Active task:** `tasks/009-github-backed-collaboration.md`
```

when that matches current repository convention.

No workflow migration, script deletion, PR template, decision supersession, or implementation evidence belongs in the contract commit.

The contract commit message must be equivalent to:

```text
docs: define task 009 GitHub-backed collaboration
```

After the commit, record:

```text
git rev-parse HEAD
```

as the full contract SHA.

The review contract is:

```text
<full-contract-sha>:tasks/009-github-backed-collaboration.md
```

The PR description must record that exact pair.

Later branch-head changes to the task file may only:

* set task status;
* append concise completion evidence;
* record an explicit amendment with its reason.

They must not silently replace accepted requirements.

## Draft pull request

Open the PR after the contract commit is pushed and before implementation begins.

Required properties:

```text
state: open
draft: true
base: verified default branch
head: task/009-github-backed-collaboration
title: Task 009: Migrate project collaboration to GitHub-backed pull-request reviews
```

The initial PR description must include:

```markdown
## Task contract

Task path: `tasks/009-github-backed-collaboration.md`
Contract commit: `<full SHA>`
Base branch: `<verified default branch>`
Task branch: `task/009-github-backed-collaboration`

## Outcome

Migrate active project collaboration from uploaded review bundles to an exact
GitHub task-branch and pull-request review boundary.

## Access gate

Status: pending

Connected Web Chat must confirm access to the private repository, contract
commit, PR commits, PR patch, and current PR head before the old reporting tools
are removed.
```

Do not claim the access gate has passed before receiving explicit confirmation.

## Connected-access gate evidence

After the draft PR is created, verify locally that GitHub contains the expected pushed state:

```text
PR number
PR URL
base branch
head branch
contract SHA
current head SHA
commit list
changed files
```

Then request confirmation through the project collaboration channel.

The confirmation must identify the same repository and pull request.

The gate passes only when connected Web Chat demonstrates or explicitly confirms that it can access:

1. repository metadata;
2. PR metadata;
3. the task file at the contract SHA;
4. the PR commit list;
5. the PR patch or changed-file contents;
6. the current PR head SHA.

Record the result in the PR description:

```text
Access gate: passed
Confirmed against PR head: <SHA>
Confirmation date: <date>
```

Do not store private conversation transcripts in the repository.

## Implementation commits

Implementation begins only after the access gate passes.

Prefer one coherent implementation commit containing the bounded workflow migration.

The implementation commit message must be equivalent to:

```text
chore: migrate collaboration to GitHub pull requests
```

The implementation commit may include only:

* active workflow migration;
* AGENTS instructions;
* task-template changes;
* PR template;
* README guidance;
* current-state update;
* durable-decision update;
* removal of old reporting utilities and focused tests;
* directly obsolete support;
* Task 009 completion state and evidence.

Do not commit generated reports or external handoff files.

## Pull-request description as completion summary

After implementation and verification, replace or extend the PR description using the repository template.

It must contain:

```markdown
## Task contract

Task path:
Contract commit:
Base branch:

## Outcome

## Verification

## Documentation

## Risks and unverified items

## Review scope
```

The description must also report:

* task branch;
* implementation commit SHA;
* current head SHA;
* access-gate result;
* exact commands run;
* pass, fail, or not-run result for each required command;
* full-suite pass count;
* Docker or environment limitations;
* deleted workflow tools;
* historical files intentionally preserved;
* confirmation that no application behavior changed;
* confirmation that no secret or local report was committed;
* final `git status --short`;
* final comparison against the PR base.

The PR description contains supplied claims. It must state:

```text
Verification results in this description are reported by Codex and are not
independently executed proof unless a corresponding CI check is present.
```

Task 009 must not add CI merely to change this statement.

## Evidence precedence

The migrated workflow must establish this precedence:

1. the task file at the exact contract commit defines requirements;
2. the PR base and current pushed head define the implementation comparison;
3. PR commits and the PR patch define pushed implementation state;
4. the PR description provides implementation explanations and verification claims;
5. CI checks, when introduced later, provide independently executed verification.

A later branch-head version of the task file does not replace the recorded contract.

The local working tree does not override GitHub review evidence until changes are committed and pushed.

## Review-head identity

Handoff Review must identify:

```text
repository
PR number
base SHA
head SHA
contract SHA
task path
```

The review result applies only to the identified PR head SHA.

After any correction commit:

* the PR head changes;
* prior approval applies only to the earlier head;
* Handoff Review must inspect the updated patch and identify the new head SHA;
* final approval must reference the latest pushed head.

## Correction loop

Review findings must be addressed on the same task branch.

Use a bounded commit message equivalent to:

```text
fix: address Task 009 review findings
```

Requirements:

* include only corrections within Task 009;
* do not begin Task 010;
* do not rewrite the contract to conceal a mismatch;
* do not force-push;
* push the correction commit normally;
* update the PR description when verification or risk information changes;
* request review of the new exact head.

A material scope change returns to Architecture Planning or Active Task Planning.

## Ready-for-review transition

Keep the PR in draft while any of these remain incomplete:

* access gate;
* workflow implementation;
* documentation;
* required verification;
* PR completion summary;
* scope check;
* branch cleanliness.

Codex is authorized to mark the PR ready only after:

* all implementation changes are committed and pushed;
* required local verification has completed;
* documentation reflects verified behavior;
* Task 009 is marked completed on the branch;
* `docs/CURRENT_STATE.md` records no active task unless another task was explicitly selected;
* PR description is complete;
* no unrelated file is present;
* the PR head equals the locally verified commit.

Marking ready is not approval and does not authorize merge.

## Merge boundary

Task 009 must document the accepted merge policy:

* use a normal merge commit;
* preserve the original contract and implementation commit identities;
* do not squash the branch into one commit;
* do not rebase-and-merge;
* merge only after Handoff Review approves the exact current head;
* merge only after the user separately authorizes it;
* task branch deletion occurs only after merge and separate authorization or normal user action.

Task 009 itself must not execute the merge.

## Pull-request template

Add:

```text
.github/pull_request_template.md
```

Keep it concise.

Required structure:

```markdown
## Task contract

Task path:
Contract commit:
Base branch:

## Outcome

## Verification

Verification results below are reported claims unless backed by an available CI check.

## Documentation

## Risks and unverified items

## Review scope
```

Include brief reminders that:

* the contract commit must be an exact full SHA;
* the contract is the task file at that SHA;
* unrelated changes do not belong in the PR;
* the reviewed state is the pushed PR head;
* no secret, generated handoff file, review bundle, database dump, generated knowledge artifact, or local-environment file may be committed.

Do not duplicate `docs/WORKFLOW.md`.

## Workflow-document requirements

Update `docs/WORKFLOW.md` so that its normal lifecycle becomes:

1. architecture planning;
2. bounded task planning;
3. synchronize the default branch;
4. create one task branch;
5. commit the accepted task contract;
6. push and open a draft PR;
7. inspect the live local repository;
8. implement locally;
9. verify;
10. update documentation from verified behavior;
11. commit and push;
12. complete the PR description;
13. mark ready;
14. review exact PR head;
15. apply bounded correction commits;
16. obtain final approval;
17. merge only after separate authorization;
18. select the next task separately.

The workflow must preserve the existing conversation responsibilities.

### Architecture Planning

Responsible for:

* durable architecture;
* meaningful alternatives;
* accepted boundaries;
* escalation of material scope changes.

It does not implement or review PR patches line by line.

### Active Task Planning

Responsible for:

* one bounded task;
* branch name;
* contract boundary;
* commit and push authorization;
* PR boundary;
* tests;
* acceptance criteria;
* merge boundary.

It does not merge, implement, or silently broaden the task.

### Codex

Responsible for:

* local repository and remote inspection;
* task-branch creation when authorized;
* contract commit and PR bootstrap when authorized;
* local implementation;
* local verification;
* coherent authorized commits;
* pushing only the task branch;
* PR-description updates;
* preserving unrelated local state.

It does not:

* push directly to the default branch;
* merge;
* expose secrets;
* claim GitHub contains local uncommitted state.

### Handoff Review

Responsible for reviewing:

```text
exact contract commit
task path
PR base SHA
PR head SHA
PR commits
PR patch
PR description
available checks
```

It cannot review uncommitted local changes.

It must identify the exact head SHA reviewed.

### Future Scope

Retain the current product-idea and future-boundary responsibility without making ideas part of active PR scope.

The workflow must preserve the documentation-update matrix for:

```text
CURRENT_STATE
DECISIONS
ARCHITECTURE
DATA_MODEL
domain documents
PROJECT_BRIEF
README
.env.example
task files
```

## AGENTS.md requirements

Update root `AGENTS.md` concisely.

It must instruct Codex to:

1. inspect local branch, HEAD, status, remotes, base relationship, and current diff;
2. confirm the active task branch is based on the expected pushed default branch;
3. read the task contract at its recorded exact commit;
4. read `docs/CURRENT_STATE.md`, `docs/WORKFLOW.md`, and referenced documents;
5. report contradictions before editing;
6. implement only the active task;
7. run required verification;
8. update documentation only from verified behavior;
9. create only commits explicitly authorized by the active task or user;
10. push only the explicitly authorized task branch;
11. never push directly to the default branch without separate authorization;
12. never merge a pull request without separate authorization;
13. never force-push reviewed work without explicit agreement;
14. never expose secrets;
15. update the PR description with supplied verification claims;
16. leave unrelated local changes untouched.

Keep detailed lifecycle rules in `docs/WORKFLOW.md`.

## Task-template requirements

Update `tasks/TEMPLATE.md`.

Future task specifications must contain fields or sections for:

```text
expected branch
expected PR title
contract commit boundary
implementation commit boundary
commit authorization
push authorization
PR creation authorization
correction-commit behavior
PR description requirements
review-head identity
merge boundary
prohibited committed artifacts
```

Replace unconditional wording equivalent to:

```text
Codex must not commit unless explicitly instructed.
```

with:

```text
Codex may commit or push only when the active task or user explicitly authorizes
the exact branch and commit boundary. Codex must never merge or push directly
to the default branch without separate explicit authorization.
```

The template must not automatically authorize commits, pushes, PR creation, readiness changes, force-pushes, or merges. Each active task must define its own exact authority.

## Removal of obsolete reporting tools

After the access gate passes, remove:

```text
scripts/project_context.py
scripts/review_bundle.py
tests/test_project_context.py
tests/test_review_bundle.py
```

Remove active references that instruct normal use of:

```text
context-report generation
contract-from-HEAD copies
external completion-report files
review-bundle generation
manual source-file uploads
~/pkm-handoffs as review transport
/tmp as workflow-report transport
```

Do not modify historical references in:

```text
Tasks 004–008
historical completion evidence
historical review bundles outside the repository
```

Do not delete user-owned external files.

Inspect and conditionally remove directly obsolete support from:

```text
Dockerfile
.gitignore
.dockerignore
tasks/PROMPT.md
```

Rules:

* remove only support whose sole current purpose was the deleted tooling;
* keep Git in the development image when another current need exists;
* keep general ignore rules that remain useful;
* do not perform unrelated Docker cleanup;
* do not change application image behavior beyond removing proven-dead workflow-only support.

## Durable decision requirements

Add the next live-confirmed decision, expected to be D-028.

D-028 must establish:

* repository-owned task specifications remain review contracts;
* active tasks use one pushed task branch and one GitHub PR;
* the contract is pinned by exact task path and full contract SHA;
* GitHub shows committed and pushed state only;
* the local uncommitted working tree remains a distinct Codex authority;
* PR base/head, commits, and patch replace generated review bundles;
* the PR description replaces the external completion report;
* PR verification results remain claims unless backed by CI;
* Handoff Review reviews an exact PR head SHA;
* corrections use bounded commits on the same branch;
* normal task work does not occur directly on the default branch;
* direct default-branch push is prohibited;
* Codex never merges without separate authorization;
* normal merge commits preserve contract and implementation identities;
* Task 004/005 reporting mechanisms are superseded only after the access gate succeeds.

Mark D-023 and D-024:

```text
Status: superseded
Superseded by: D-028
```

Preserve their historical text.

D-028 must explicitly retain these principles:

```text
the repository owns the workflow
the task contract precedes implementation
requirements are not rewritten to match implementation
snapshots and summaries are not independent sources of truth
review evidence must identify one exact repository state
```

## Current-state requirements

Update `docs/CURRENT_STATE.md` after successful implementation verification.

Replace active context-report and review-bundle instructions with:

```text
pushed default branch = accepted shared baseline
pushed task branch + PR = active shared review state
local working tree = Codex-only uncommitted state
task contract = exact task path at recorded contract SHA
PR head SHA = exact implementation state under review
```

During the contract commit, set:

```text
**Active task:** `tasks/009-github-backed-collaboration.md`
```

After implementation is complete and pushed, set:

```text
**Active task:** none selected
```

unless another task was explicitly selected.

Do not record a chronological list of PRs, branch SHAs, or merges in current state.

## README requirements

Replace normal report-generation and upload instructions with a concise contributor workflow:

```text
synchronize default branch
create task branch
commit task contract
push and open draft PR
confirm connected review access
implement and verify
commit and push
review exact PR head
merge only after approval and separate authorization
```

Link to `docs/WORKFLOW.md`.

Do not duplicate the full workflow.

## Investigation requirements

Before selecting exact changes, Codex must determine:

* actual default branch;
* actual repository identity;
* whether the remote URL contains embedded credentials;
* authenticated GitHub identity;
* whether merge commits are permitted;
* whether the Task 009 branch or PR already exists;
* whether a PR template already exists;
* whether multiple PR templates or organization templates affect selection;
* whether connected Web Chat can resolve commit-specific file contents;
* whether connected Web Chat can inspect PR patches for a private repository;
* whether GitHub connector evidence includes exact head SHA;
* how the current Handoff Review chat will identify the PR;
* all active documentation references to old tooling;
* whether `tasks/PROMPT.md` contains old workflow instructions;
* whether Git in the development image has a remaining purpose;
* whether deleting the tests changes Docker copy assumptions;
* whether reporting scripts are imported elsewhere;
* whether D-028 is truly the next decision;
* whether historical Task 008 is committed and pushed;
* whether the complete test suite currently passes before workflow changes.

Do not introduce a general GitHub automation framework to answer these questions.

## Expected failure modes and recovery behavior

## Task 008 not on remote default branch

Behavior:

* stop before Task 009 branch creation;
* do not push Task 008 directly through Task 009 authority;
* do not create a PR from an outdated base;
* report local and remote SHAs.

Recovery:

* complete the separate Task 008 merge or synchronization process with proper authorization;
* restart Task 009 from a clean synchronized baseline.

## Dirty default branch

Behavior:

* stop;
* list changed paths without exposing secret content;
* do not stash, clean, reset, commit, or discard automatically.

Recovery:

* user or owning workflow resolves the unrelated local state.

## Local and remote default branches diverged

Behavior:

* stop;
* report ahead/behind counts;
* do not create the task branch;
* do not merge or rebase automatically.

Recovery:

* synchronize through an explicitly selected safe operation.

## Wrong or ambiguous remote repository

Behavior:

* stop;
* do not push;
* do not open a PR;
* do not print credentials.

Recovery:

* configure or identify the intended private repository.

## GitHub authentication unavailable

Behavior:

* preserve all local state;
* do not remove old tools;
* do not claim the migration is active;
* leave Task 009 unimplemented or blocked.

Recovery:

* authenticate the established GitHub publishing mechanism.

## Existing conflicting Task 009 branch or PR

Behavior:

* do not delete, overwrite, or force-push;
* inspect and report branch and PR metadata;
* reuse only when it matches the accepted contract and user intent.

Recovery:

* resolve the conflict explicitly.

## Contract commit contains implementation changes

Behavior:

* fail the contract-boundary check;
* do not push or open the PR as the accepted pilot;
* do not hide the violation in the PR description.

Recovery:

* recreate the branch from the synchronized base or create an explicit corrective contract boundary before implementation begins, with user agreement.

## Connected-access gate fails

Behavior:

* keep PR draft;
* preserve old scripts, tests, decisions, and active instructions;
* record blocker;
* generate no claim that GitHub has replaced review bundles.

Recovery:

* restore or configure connected access, then rerun the gate on the same PR.

## Push rejected

Behavior:

* preserve local commits;
* report rejection;
* do not force-push;
* do not push to another branch or remote silently.

Recovery:

* resolve authentication, permissions, or remote divergence.

## PR head changes after review

Behavior:

* invalidate approval for the earlier head;
* require review of the new head;
* record the exact replacement SHA.

Recovery:

* Handoff Review inspects the new patch and issues a new result.

## Local uncommitted change after push

Behavior:

* do not imply it is part of PR review;
* keep the PR description tied to the pushed head;
* commit and push only when in scope and authorized.

Recovery:

* commit and push a coherent correction or remove the local change without affecting reviewed state.

## Merge method unavailable

Behavior:

* do not silently squash or rebase;
* report repository setting contradiction;
* leave PR unmerged.

Recovery:

* user makes a separate workflow decision or repository-setting change outside Task 009.

## Secret or local artifact detected

Behavior:

* do not commit or push;
* remove it from the proposed commit boundary without deleting user data unnecessarily;
* rotate exposed credentials when actual exposure occurred;
* report the affected path safely.

Recovery:

* clean the task-branch commit boundary and rerun checks.

## Docker or network failure

Behavior:

* distinguish local environment failure from repository regression;
* use the established local VPN/Docker diagnosis when applicable;
* do not alter application code, mirrors, or networking merely to make Task 009 pass;
* report unverified commands honestly.

Recovery:

* repair the local environment and rerun authoritative checks.

## Tests

## Contract-boundary checks

Verify:

1. task branch is based on the synchronized remote default branch;

2. first task-branch commit is the contract commit;

3. contract commit contains only:

   ```text
   tasks/009-github-backed-collaboration.md
   docs/CURRENT_STATE.md, when required
   ```

4. task file is a regular committed blob;

5. PR description records the exact full contract SHA;

6. implementation commit is later than the contract commit.

## GitHub bootstrap checks

Verify:

1. branch is pushed;
2. one draft PR exists;
3. PR base is the default branch;
4. PR head is the Task 009 branch;
5. title matches the accepted task;
6. task path is present in the description;
7. contract SHA is present in the description;
8. PR-reported head SHA matches the pushed branch head;
9. no duplicate Task 009 PR exists.

## Connected-access gate checks

Connected Web Chat must verify:

1. private repository access;
2. PR metadata access;
3. task contents at the contract commit;
4. commit-list access;
5. patch or changed-file access;
6. exact current head SHA.

The result must be recorded without storing private conversation content.

## PR-template structural checks

Verify that `.github/pull_request_template.md` contains exactly one section for each required heading:

```text
Task contract
Outcome
Verification
Documentation
Risks and unverified items
Review scope
```

Verify that it mentions:

```text
exact contract commit
reported verification claims
unrelated-change prohibition
secret/local-artifact prohibition
pushed PR head review boundary
```

## Active-documentation checks

Search active documentation and confirm that normal instructions no longer direct users to:

```text
scripts/project_context.py
scripts/review_bundle.py
external completion reports
contract-from-head files
review-bundle generation
manual Web Chat source uploads
~/pkm-handoffs as the review transport
/tmp as a workflow-report location
```

Historical tasks and evidence may still contain these strings.

Limit the active scan to live workflow and contributor documents, including:

```text
AGENTS.md
docs/WORKFLOW.md
docs/CURRENT_STATE.md
README.md
tasks/TEMPLATE.md
tasks/PROMPT.md, when active
.github/pull_request_template.md
```

## Removal checks

After the access gate passes, verify these paths are absent:

```text
scripts/project_context.py
scripts/review_bundle.py
tests/test_project_context.py
tests/test_review_bundle.py
```

Verify no import, test, Docker copy rule, or active command references a removed path.

## Historical-preservation checks

Verify that historical task files remain present:

```text
tasks/004-repository-workflow-context.md
tasks/005-implementation-review-bundles.md
tasks/006-deterministic-markdown-artifacts.md
tasks/007-durable-background-processing.md
tasks/008-restrict-telegram-ingestion-owner.md
```

Compare them to the remote default-branch baseline and confirm Task 009 did not rewrite them.

## Scope checks

Confirm there is no change under:

```text
app/
alembic/
knowledge-base/
```

Confirm no change to:

```text
.env.example
docker-compose.yml
docs/ARCHITECTURE.md
docs/DATA_MODEL.md
docs/TELEGRAM_INGESTION.md
docs/MARKDOWN_ARTIFACTS.md
docs/PROJECT_BRIEF.md
```

unless a live contradiction was reported and explicitly accepted before editing.

## Application regression

Run the authoritative existing suite even though application behavior is unchanged.

No application test should require modification solely because collaboration changed.

## Acceptance criteria

Task 009 is complete only when all of the following are true:

1. Task 008 is completed, committed, and present on the pushed default branch.
2. The local default branch started clean and synchronized with its remote.
3. Task 009 uses exactly one dedicated pushed task branch.
4. The accepted Task 009 specification exists in a distinct contract commit.
5. The contract commit precedes every implementation commit.
6. One draft PR records the exact task path, contract SHA, base branch, and task branch.
7. Connected Web Chat can inspect the private repository.
8. Connected Web Chat can inspect the task file at the exact contract commit.
9. Connected Web Chat can inspect PR commits, patch, changed files, and current head SHA.
10. The access gate passed before old reporting tools or active instructions were removed.
11. `docs/WORKFLOW.md` defines the branch/PR lifecycle and evidence precedence.
12. `docs/WORKFLOW.md` states that Handoff Review cannot inspect uncommitted local work.
13. `AGENTS.md` defines precise task-branch commit and push authority.
14. `AGENTS.md` prohibits direct default-branch push and unauthorized merge.
15. `tasks/TEMPLATE.md` defines branch, contract, implementation, PR, correction, and merge boundaries.
16. `.github/pull_request_template.md` exists and is concise.
17. Active documentation no longer requires context files, external completion reports, source uploads, or review bundles.
18. D-028 records the GitHub-backed workflow.
19. D-023 and D-024 are marked superseded by D-028 without deleting their historical content.
20. Obsolete reporting scripts and focused tests are removed only after the gate passes.
21. Directly obsolete Docker or ignore support is removed only when live evidence proves it has no other use.
22. Historical Tasks 004–008 remain present and unmodified by Task 009.
23. No application, schema, queue, Telegram, authorization, artifact, environment, or Compose behavior changes.
24. The authoritative full test suite passes.
25. The PR description contains the final supplied completion summary and verification results.
26. The final pushed PR head matches the locally verified implementation commit.
27. Handoff Review identifies and reviews that exact head SHA.
28. Every correction is a bounded pushed commit on the same branch.
29. The PR is marked ready only after verification and documentation complete.
30. No secret, generated handoff artifact, database dump, or generated note is committed.
31. No force-push occurs after review begins.
32. No direct push to the default branch occurs.
33. No merge occurs without separate explicit user authorization.
34. The accepted merge method remains a normal merge commit.

## Required verification commands

Adapt commands only when live repository evidence establishes a different default branch, remote name, file path, or stronger existing convention.

Record every actual command and result in the PR description.

## Phase A: verify baseline

```bash
git branch --show-current
git rev-parse HEAD
git status --short
git log --oneline --decorate -10
git diff --stat
git diff --check
git remote -v
git fetch origin --prune
git remote show origin
```

Inspect repository metadata:

```bash
gh auth status

gh repo view --json \
  nameWithOwner,isPrivate,defaultBranchRef,mergeCommitAllowed,rebaseMergeAllowed,squashMergeAllowed
```

Resolve the default branch:

```bash
DEFAULT_BRANCH="$(
  gh repo view --json defaultBranchRef \
    --jq '.defaultBranchRef.name'
)"

test -n "$DEFAULT_BRANCH"
```

Verify local/remote synchronization:

```bash
git rev-parse "$DEFAULT_BRANCH"
git rev-parse "origin/$DEFAULT_BRANCH"
git rev-list --left-right --count \
  "$DEFAULT_BRANCH...origin/$DEFAULT_BRANCH"
```

Expected result:

```text
0	0
```

Confirm Task 008 is on the remote default branch using its live-confirmed implementation or completion commit.

Confirm the tree is clean:

```bash
test -z "$(git status --porcelain=v1 --untracked-files=all)"
```

## Phase A: create branch and contract commit

Update the local default branch only by fast-forward:

```bash
git switch "$DEFAULT_BRANCH"
git merge --ff-only "origin/$DEFAULT_BRANCH"
```

Create the task branch:

```bash
git switch -c task/009-github-backed-collaboration
```

Add only the contract boundary:

```bash
git add \
  tasks/009-github-backed-collaboration.md \
  docs/CURRENT_STATE.md

git diff --cached --check
git diff --cached --name-status
```

The staged paths must contain only the accepted contract boundary.

Create the contract commit:

```bash
git commit -m "docs: define task 009 GitHub-backed collaboration"
```

Capture:

```bash
CONTRACT_SHA="$(git rev-parse HEAD)"
printf '%s\n' "$CONTRACT_SHA"
```

Push only the task branch:

```bash
git push -u origin task/009-github-backed-collaboration
```

## Phase A: create draft PR

Before creating a duplicate, inspect:

```bash
gh pr list \
  --state all \
  --head task/009-github-backed-collaboration \
  --json number,title,state,isDraft,baseRefName,headRefName,headRefOid,url
```

Create the draft PR using the exact verified default branch:

```bash
gh pr create \
  --draft \
  --base "$DEFAULT_BRANCH" \
  --head task/009-github-backed-collaboration \
  --title "Task 009: Migrate project collaboration to GitHub-backed pull-request reviews" \
  --body "## Task contract

Task path: \`tasks/009-github-backed-collaboration.md\`
Contract commit: \`$CONTRACT_SHA\`
Base branch: \`$DEFAULT_BRANCH\`
Task branch: \`task/009-github-backed-collaboration\`

## Outcome

Migrate active project collaboration from uploaded review bundles to an exact GitHub task-branch and pull-request review boundary.

## Access gate

Status: pending

Connected Web Chat must confirm access to the private repository, contract commit, PR commits, PR patch, and current PR head before the old reporting tools are removed."
```

Inspect:

```bash
gh pr view --json \
  number,title,state,isDraft,baseRefName,headRefName,headRefOid,url,body,commits,files
```

## Phase B: connected-access gate

Provide the PR identity to the user and obtain explicit confirmation.

Do not continue to workflow removal until confirmation.

After confirmation, update the PR description to record:

```text
access gate passed
confirmation date
confirmed PR head SHA
```

Use `gh pr edit` or the connected GitHub action supported by the live environment.

## Implementation inspection

Search active references:

```bash
grep -RInE \
  'project_context\.py|review_bundle\.py|context report|review bundle|completion report|contract-from-head|pkm-handoffs|manual upload|Source folder|/tmp' \
  AGENTS.md \
  docs/WORKFLOW.md \
  docs/CURRENT_STATE.md \
  README.md \
  tasks/TEMPLATE.md \
  tasks/PROMPT.md \
  Dockerfile \
  .dockerignore \
  .gitignore \
  2>/dev/null || true
```

Inspect utility usage:

```bash
grep -RInE \
  'project_context|review_bundle' \
  . \
  --exclude-dir=.git \
  --exclude='*.pyc' \
  --exclude='task*-review-bundle.md' \
  2>/dev/null || true
```

Inspect historical task checksums or baseline diffs before editing:

```bash
git diff --name-only "origin/$DEFAULT_BRANCH...HEAD" -- \
  tasks/004-repository-workflow-context.md \
  tasks/005-implementation-review-bundles.md \
  tasks/006-deterministic-markdown-artifacts.md \
  tasks/007-durable-background-processing.md \
  tasks/008-restrict-telegram-ingestion-owner.md
```

Expected result before and after implementation:

```text
no output
```

## Structural checks

Verify PR template headings:

```bash
for heading in \
  "## Task contract" \
  "## Outcome" \
  "## Verification" \
  "## Documentation" \
  "## Risks and unverified items" \
  "## Review scope"
do
  grep -Fx "$heading" .github/pull_request_template.md
done
```

Verify deleted files are absent:

```bash
test ! -e scripts/project_context.py
test ! -e scripts/review_bundle.py
test ! -e tests/test_project_context.py
test ! -e tests/test_review_bundle.py
```

Verify historical task files remain:

```bash
test -f tasks/004-repository-workflow-context.md
test -f tasks/005-implementation-review-bundles.md
test -f tasks/006-deterministic-markdown-artifacts.md
test -f tasks/007-durable-background-processing.md
test -f tasks/008-restrict-telegram-ingestion-owner.md
```

Verify historical task files are unchanged relative to the PR base:

```bash
test -z "$(
  git diff --name-only "origin/$DEFAULT_BRANCH...HEAD" -- \
    tasks/004-repository-workflow-context.md \
    tasks/005-implementation-review-bundles.md \
    tasks/006-deterministic-markdown-artifacts.md \
    tasks/007-durable-background-processing.md \
    tasks/008-restrict-telegram-ingestion-owner.md
)"
```

Verify application boundaries are unchanged:

```bash
test -z "$(
  git diff --name-only "origin/$DEFAULT_BRANCH...HEAD" -- \
    app \
    alembic \
    knowledge-base \
    .env.example \
    docker-compose.yml \
    docs/ARCHITECTURE.md \
    docs/DATA_MODEL.md \
    docs/TELEGRAM_INGESTION.md \
    docs/MARKDOWN_ARTIFACTS.md \
    docs/PROJECT_BRIEF.md
)"
```

## Active-reference checks

After migration, this command must find no active normal-use instruction for the removed workflow:

```bash
grep -RInE \
  'scripts/project_context\.py|scripts/review_bundle\.py|contract-from-head|review-bundle generation|pkm-handoffs|manual Source-folder upload|/tmp/.+-handoff|external completion report' \
  AGENTS.md \
  docs/WORKFLOW.md \
  docs/CURRENT_STATE.md \
  README.md \
  tasks/TEMPLATE.md \
  tasks/PROMPT.md \
  .github/pull_request_template.md \
  2>/dev/null
```

Expected result:

```text
no active obsolete instruction
```

Permitted text may explain that the mechanisms are historical and superseded, but must not instruct their normal use.

## Authoritative regression

Run:

```bash
git diff --check
docker compose config --quiet
docker compose up -d --build
docker compose exec app python -m pytest
```

If the documented local VPN/Docker bridge fault blocks a normal image build, follow the existing local runbook without changing repository behavior. Report the exact deviation.

Verify health and readiness through the established repository commands:

```bash
curl --retry 5 --retry-all-errors --retry-delay 1 \
  http://localhost:8000/health

curl --retry 5 --retry-all-errors --retry-delay 1 \
  http://localhost:8000/ready
```

Use established in-container checks when the known host bridge problem prevents host-port checks, and report the limitation.

## Implementation commit

Before committing:

```bash
git status --short
git diff --check
git diff --stat
git diff --name-status
```

Stage only Task 009 implementation paths.

Inspect staged scope:

```bash
git diff --cached --check
git diff --cached --stat
git diff --cached --name-status
```

Create the implementation commit:

```bash
git commit -m "chore: migrate collaboration to GitHub pull requests"
```

Push only the task branch:

```bash
git push origin task/009-github-backed-collaboration
```

Capture:

```bash
IMPLEMENTATION_SHA="$(git rev-parse HEAD)"
printf '%s\n' "$IMPLEMENTATION_SHA"
```

## Final PR update and readiness

Inspect the PR after push:

```bash
gh pr view --json \
  number,title,state,isDraft,baseRefName,headRefName,headRefOid,url,body,commits,files
```

Verify:

```bash
test "$(
  gh pr view --json headRefOid --jq '.headRefOid'
)" = "$(git rev-parse HEAD)"
```

Update the PR description with final completion evidence.

Then mark ready:

```bash
gh pr ready
```

Reinspect:

```bash
gh pr view --json \
  number,title,state,isDraft,baseRefName,headRefName,headRefOid,url
```

Expected:

```text
isDraft = false
headRefOid = locally verified HEAD
```

## Final local and remote boundary

Run:

```bash
git status --short
git diff --check
git log --oneline --decorate "origin/$DEFAULT_BRANCH..HEAD"
git diff --stat "origin/$DEFAULT_BRANCH...HEAD"
git diff --name-status "origin/$DEFAULT_BRANCH...HEAD"
git rev-parse HEAD
git rev-parse "origin/task/009-github-backed-collaboration"
```

Expected:

```text
clean working tree
local HEAD = remote task-branch HEAD
contract commit preserved
implementation commit preserved
no unrelated paths
```

## Handoff Review evidence

Handoff Review must inspect through the connected GitHub repository:

```text
PR number
task path
contract SHA
base branch and base SHA
head branch and head SHA
commit list
changed files
complete patch
PR description
available checks
```

It must report the exact head SHA reviewed.

Do not generate a Task 009 review bundle after the access gate passes.

## Correction verification

For each correction:

```bash
git status --short
git diff --check
docker compose exec app python -m pytest
git add <bounded-correction-paths>
git diff --cached --check
git commit -m "fix: address Task 009 review findings"
git push origin task/009-github-backed-collaboration
git rev-parse HEAD
gh pr view --json headRefOid
```

Adapt verification to the actual correction while retaining the authoritative full suite when repository behavior or Docker support changes.

Do not force-push.

## Documentation impact

## Required changes

### `tasks/009-github-backed-collaboration.md`

* commit the accepted contract before implementation;
* retain the accepted requirements;
* set status to `completed` only after verification;
* append concise completion evidence;
* record explicit amendments separately when required.

### `docs/WORKFLOW.md`

Replace the normal report/upload lifecycle with the GitHub task-branch and PR lifecycle.

Preserve:

* conversation responsibilities;
* documentation update matrix;
* contract-before-implementation rule;
* source-of-truth distinctions;
* scope-change escalation;
* correction-loop discipline.

### `AGENTS.md`

Add concise branch, contract, push, PR, and merge authority.

Do not duplicate the complete workflow.

### `tasks/TEMPLATE.md`

Add future-task fields for:

* branch;
* contract commit;
* implementation commits;
* authorization;
* PR;
* corrections;
* review head;
* merge boundary;
* prohibited artifacts.

### `.github/pull_request_template.md`

Add the concise required template.

### `README.md`

Replace normal handoff-report commands with the short contributor PR lifecycle and link to the workflow.

### `docs/CURRENT_STATE.md`

During the contract commit, set Task 009 active.

After verified implementation, record the GitHub-backed collaboration model and set no active task unless another task was selected.

### `docs/DECISIONS.md`

Add D-028 and mark D-023/D-024 superseded without deleting their contents.

### Conditional files

Update only when inspection proves a live active reference or obsolete support:

```text
Dockerfile
.gitignore
.dockerignore
tasks/PROMPT.md
```

## Expected unchanged documentation and runtime

Do not modify:

```text
docs/ARCHITECTURE.md
docs/DATA_MODEL.md
docs/TELEGRAM_INGESTION.md
docs/MARKDOWN_ARTIFACTS.md
docs/PROJECT_BRIEF.md
.env.example
docker-compose.yml
```

No runtime or domain documentation change is needed because application behavior does not change.

## Pull-request completion-summary requirements

No external Task 009 completion-report file is required after the access gate passes.

The PR description becomes the completion summary and must include:

### Task contract

* task path;
* full contract SHA;
* base branch;
* task branch.

### Initial repository state

* starting default branch SHA;
* remote default branch SHA;
* synchronization result;
* clean working-tree confirmation;
* Task 008 remote-baseline confirmation;
* GitHub repository identity without credentials.

### Access gate

* result;
* confirmation date;
* PR head at confirmation;
* any limitation.

### Outcome

* concise implementation summary;
* migration result;
* deleted utilities;
* retained historical files;
* conditional Docker or ignore changes.

### Verification

For every required command:

```text
exact command
pass / fail / not run
relevant output or count
```

Include:

* structural checks;
* active-reference checks;
* historical-preservation checks;
* scope checks;
* Compose validation;
* image build;
* full pytest result;
* health/readiness;
* final Git boundary;
* PR-head match.

State that the results are supplied claims unless backed by CI.

### Documentation

List:

* workflow changes;
* AGENTS changes;
* template changes;
* PR template;
* README;
* current state;
* D-028;
* D-023/D-024 status changes;
* documents intentionally unchanged.

### Risks and unverified items

Report:

* local environment limitations;
* GitHub connector limitations;
* checks not run;
* lack of CI;
* merge not performed;
* branch not deleted;
* any retained legacy support;
* any assumption requiring post-merge verification.

### Review scope

List:

* exact base SHA;
* exact current head SHA;
* contract SHA;
* commits included;
* changed paths;
* explicit scope exclusions.

### Final repository state

Report:

* `git status --short`;
* `git diff --check`;
* branch name;
* local head;
* remote task-branch head;
* PR number and URL;
* draft/readiness state;
* confirmation that no merge occurred;
* confirmation that no default-branch push occurred;
* confirmation that no force-push occurred;
* confirmation that no secret or local workflow artifact was committed.

## Expected commit boundary

The Task 009 branch should contain distinguishable commits equivalent to:

```text
docs: define task 009 GitHub-backed collaboration
chore: migrate collaboration to GitHub pull requests
fix: address Task 009 review findings
```

The correction commit is included only when review identifies a bounded defect.

## Contract commit boundary

Expected paths:

```text
tasks/009-github-backed-collaboration.md
docs/CURRENT_STATE.md
```

No implementation change belongs in this commit.

## Implementation commit boundary

Permitted paths:

```text
tasks/009-github-backed-collaboration.md
docs/WORKFLOW.md
docs/CURRENT_STATE.md
docs/DECISIONS.md
AGENTS.md
tasks/TEMPLATE.md
README.md
.github/pull_request_template.md
scripts/project_context.py                 # deletion
scripts/review_bundle.py                   # deletion
tests/test_project_context.py              # deletion
tests/test_review_bundle.py                # deletion
Dockerfile                                 # only when directly justified
.gitignore                                 # only when directly justified
.dockerignore                              # only when directly justified
tasks/PROMPT.md                            # only when actively required
```

It must not contain:

```text
application changes
database changes
migration changes
Telegram changes
worker or queue changes
generated Markdown notes
knowledge-base files
environment configuration
Docker Compose topology changes
context-report files
contract-copy files
external completion-report files
review-bundle files
database dumps
credentials
real Telegram IDs
CI configuration
another product task
unrelated cleanup
```

## Authorized Git operations

This task authorizes only on:

```text
task/009-github-backed-collaboration
```

* branch creation;
* contract commit;
* branch push;
* draft PR creation;
* PR-description updates;
* implementation commit;
* implementation push;
* ready-for-review transition;
* bounded correction commits;
* bounded correction pushes.

## Unauthorized Git operations

This task does not authorize:

```text
git push origin <default-branch>
gh pr merge
git merge into the default branch
git push --force
git push --force-with-lease
interactive rebase of reviewed commits
amending pushed reviewed commits
branch deletion
repository-setting changes
```

The final Task 009 outcome is a reviewed, unmerged PR awaiting separate user authorization.
