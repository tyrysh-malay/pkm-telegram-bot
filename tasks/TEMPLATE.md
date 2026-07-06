# Task NNN: Short bounded outcome

**Status:** template
**Depends on:** verified prerequisite tasks or none
**Expected branch:** `task/NNN-short-slug`
**Expected pull-request title:** `Task NNN: Short bounded outcome`
**Expected contract commit:** `docs: define task NNN ...`
**Expected implementation commit:** `type: bounded outcome`
**Expected correction commit:** `fix: address Task NNN review findings`
**Expected merge method:** define explicitly; merge always requires separate authorization

## Git and pull-request authorization

State exactly whether this task authorizes each of the following:

* task-branch creation or switching;
* the contract commit;
* task-branch push;
* draft pull-request creation and description updates;
* the implementation commit and push;
* ready-for-review transition;
* bounded correction commits and pushes.

Define the exact branch and commit boundary for every authorized action. The
template does not authorize any action by itself.

Codex may commit or push only when the active task or user explicitly authorizes
the exact branch and commit boundary. Codex must never merge or push directly
to the default branch without separate explicit authorization. State whether
force-push, rebase, amend, branch deletion, and repository-setting changes are
prohibited; reviewed history should normally remain stable.

## Goal

State one observable, reviewable outcome. One task should produce one bounded
result rather than combine unrelated milestones.

## Confirmed current boundary

List only facts confirmed from the live repository and GitHub. Keep assumptions
and proposals out of this section.

## Repository verification requirements

Require inspection of local branch, HEAD, status, remotes, default-branch
synchronization, branch ancestry, existing task branches and pull requests,
relevant paths, behavior, tests, configuration, and documentation.
Contradictory live evidence overrides stale documentation and must be reported.

Record the repository, default branch, task branch, task path, and exact full
contract commit SHA. The contract is the task file at that SHA, not a later
branch-head version.

## Problem or motivation

Explain the present problem and why this task is worth doing now.

## Scope

List the smallest changes required for the goal.

## Out of scope

List adjacent and future work explicitly. Do not introduce future abstractions
without a present requirement.

## Affected components

Name application, tooling, documentation, infrastructure, or test boundaries
that may change, and explicitly identify important components that must not.

## Data, state, migration, and configuration impact

Describe persistence, migrations, operational state, secrets, and configuration
impact, including "none" where verified.

## Behavioral requirements

Define inputs, outputs, invariants, user-visible behavior, and compatibility
requirements.

## Investigation requirements (optional)

Record unknowns that must be resolved from repository evidence before choosing
an implementation. Separate assumptions and proposals from confirmed facts.

## Expected failure modes and recovery behavior

Define expected failures, visible errors, retry or recovery boundaries,
idempotency needs, logging, and safety behavior where relevant. Include push,
PR-head divergence, and review invalidation where applicable.

## Tests

Specify focused tests, regression coverage, and manual checks. Prefer exact
test cases over broad aspirations.

## Acceptance criteria

List independently verifiable pass conditions for behavior, safety,
documentation, scope protection, pushed-head identity, and PR readiness.

## Required verification commands

Give exact commands when known. Include focused tests first, the authoritative
suite when required, `git diff --check`, scope comparisons against the PR base,
and relevant manual checks.

## Documentation impact

List documents that must change after behavior is verified and documents that
should remain unchanged.

## Pull-request description requirements

Require the PR description to include:

* task path, exact full contract SHA, base branch, and task branch;
* initial repository state and access-gate result when applicable;
* bounded outcome and changed paths;
* exact verification commands with pass, fail, or not-run results;
* documentation changes;
* risks, environment limitations, absent CI, and unverified items;
* exact base SHA, current pushed head SHA, and included commits;
* final local/remote boundary and confirmation that prohibited actions did not occur.

Verification in the description is a supplied claim unless an available CI
check independently executed it.

## Review-head identity

Require Handoff Review to identify the repository, PR number, task path,
contract SHA, base SHA, and exact pushed head SHA. Approval applies only to that
head. Any correction commit changes the review boundary and requires review of
the new head.

## Correction behavior

Define whether bounded corrections are authorized on the same task branch,
their expected commit boundary and message, required verification, and PR
description updates. Do not rewrite the contract to conceal a mismatch and do
not force-push reviewed commits without explicit agreement.

## Merge boundary

Define the accepted merge method. Require final approval of the exact current
head and separate explicit authorization before merge. State whether branch
deletion requires another authorization or normal user action.

## Prohibited committed artifacts

At minimum prohibit secrets, local-environment files, database dumps, generated
knowledge artifacts, generated handoff files, review bundles, credential-bearing
URLs, and unrelated work. Add task-specific exclusions.

## Expected commit boundaries

### Contract commit

List the exact task-contract paths and expected message. No implementation
change belongs in this commit.

### Implementation commit

List the exact permitted paths and behavior, expected message, and excluded
paths. The implementation commit must follow the contract commit.

### Correction commits

Define the bounded correction paths or rule and expected message. Corrections
stay on the same task branch and do not silently rewrite reviewed history.
