# Task NNN: Short bounded outcome

**Status:** template
**Depends on:** verified prerequisite tasks or none
**Expected commit boundary:** one reviewable implementation commit; Codex must
not commit unless explicitly instructed

## Goal

State one observable, reviewable outcome. One task should produce one bounded
result rather than combine unrelated milestones.

## Confirmed current boundary

List only facts confirmed from the live repository. Keep assumptions and
proposals out of this section.

## Repository verification requirements

List facts Codex must verify before editing: Git state, relevant paths,
behavior, tests, configuration, and documentation. Contradictory live evidence
overrides stale documentation and must be reported.

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
idempotency needs, logging, and safety behavior where relevant.

## Tests

Specify focused tests, regression coverage, and any manual checks. Prefer exact
test cases over broad aspirations.

## Acceptance criteria

List independently verifiable pass conditions for behavior, safety,
documentation, and scope protection.

## Required verification commands

Give exact commands when known. Include focused tests first, the authoritative
suite when required, `git diff --check`, and relevant manual checks.

## Documentation impact

List documents that must change after behavior is verified and documents that
should remain unchanged.

## Completion-report requirements

Require the starting Git state, implementation summary, changed files, an
acceptance matrix with evidence, exact command results, tests, documentation,
postponed work, risks, unverified items, final `git status --short`, and
`git diff --stat`.

## Expected commit boundary

Describe the files and behavior that belong in the implementation commit and
suggest a commit message. State explicitly that Codex must not commit unless
instructed.
