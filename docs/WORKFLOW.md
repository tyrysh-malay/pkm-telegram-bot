# Repository Workflow

This repository owns the project workflow. The live local repository is the
authority for Codex; documentation describes it but cannot override contrary
files, Git state, tests, or observed behavior.

## Sources and snapshots

Keep these forms of context distinct:

* **Committed repository state** is the history at `HEAD`.
* **Uncommitted local state** is the staged, unstaged, and untracked work in one
  local working tree. It is not represented by `HEAD` or a remote repository.
* **Generated context reports** are point-in-time, read-only snapshots of safe
  repository facts. They are handoff aids, not a source of truth.
* **Uploaded Web Chat files** are snapshots and may be stale as soon as the
  repository changes.
* **Possible future GitHub context** would show only the committed, pushed
  baseline. It would not show uncommitted local work.

Web Chat must label confirmed facts, assumptions, proposals, and claims that
still require live-repository verification. Codex must verify supplied context
against the local repository before acting on it.

## Task lifecycle

1. **Discuss architecture.** Compare durable boundaries and record accepted
   decisions separately from tentative directions.
2. **Plan one bounded task.** Define its goal, verified starting boundary,
   scope, non-goals, failure behavior, tests, acceptance criteria, and exact
   repository checks.
3. **Commit the accepted task specification.** The committed specification is
   the review contract and should normally precede implementation.
4. **Inspect the live repository.** Codex reads Git state, the active task,
   `CURRENT_STATE.md`, this workflow, referenced documents, relevant code,
   tests, and configuration. Contradictions are reported before editing.
5. **Implement the smallest useful change.** Avoid postponed behavior,
   speculative abstractions, unrelated refactoring, and secret exposure.
6. **Test and verify acceptance.** Run focused checks first, then every suite
   and manual check required by the task.
7. **Review against the specification.** The handoff review uses the diff,
   command output, and completion report to evaluate the committed contract.
8. **Correct and review again when needed.** Keep corrections bounded by the
   same task. Material scope changes return to task planning.
9. **Update documentation from verified behavior.** Remove stale semantic state
   and record durable decisions only after verification supports them.
10. **Reach the implementation commit boundary.** Confirm the diff contains
    only the task outcome. Codex commits only when explicitly instructed.
11. **Select the next task separately.** Completing a task does not invent or
    activate its successor.

Task requirements must not be silently rewritten after implementation to match
the code. Status or completion evidence may be appended without replacing the
contract. A changed requirement needs an explicit amendment and reason;
material scope changes require a new planning decision.

## Conversation responsibilities

### Architecture chat

Responsible for durable boundaries, architectural alternatives, candidates for
`DECISIONS.md` or `ARCHITECTURE.md`, and separating accepted decisions from
tentative directions.

It does not implement code, review an uncommitted implementation line by line,
silently redefine an active task, or present future ideas as current behavior.

### Active Task Planning chat

Responsible for one bounded task: narrowing scope, writing acceptance criteria,
defining non-goals and failure modes, identifying repository checks, and
producing a precise Codex handoff.

It does not combine unrelated milestones, rewrite architecture without
escalation, review implementation before evidence exists, or change completed
requirements to conceal an implementation mismatch.

### Codex

Responsible for inspecting live Git and repository state, reading required
documents, presenting a plan before editing, making the smallest in-scope
change, maintaining tests, running acceptance checks, updating affected docs
after verification, and reporting files, commands, results, limitations, and
final Git status.

Codex does not trust stale documentation over the working tree, implement
postponed functionality, add speculative abstractions, expose secrets, or
commit without explicit instruction.

### Handoff Review chat

Responsible for reviewing the supplied diff, command evidence, and completion
report against the accepted specification; finding missed criteria,
regressions, scope expansion, and documentation mismatches; defining bounded
corrections; and confirming readiness for the commit boundary.

It does not invent unsupplied repository facts, broaden the active task without
returning to planning, or rewrite requirements to hide a mismatch.

### Future Scope chat

Responsible for collecting product ideas, exploring later workflows and
features, comparing alternatives, and identifying future architecture or
planning questions.

It does not add ideas to the active task, describe tentative features as
implemented, introduce current dependencies or behavior, or record a durable
decision without the architecture process.

## Documentation update rules

### `docs/CURRENT_STATE.md`

Update after an implemented and verified task changes the current semantic
state. Describe what works, what does not, operational boundaries, and one
stable field:

```text
**Active task:** `tasks/<task-file>.md`
```

or:

```text
**Active task:** none selected
```

Replace stale state instead of accumulating task history. This is not a
changelog. Do not manually maintain branch, HEAD, recent commits, or working
tree status, and do not claim unverified behavior.

### `docs/DECISIONS.md`

Update only for accepted durable architectural or development choices that
constrain later tasks or explain a meaningful alternative. Do not record every
file change, test output, temporary detail, or routine completion note. Mark
tentative and unresolved choices honestly.

### `docs/ARCHITECTURE.md`

Update when verified behavior changes process or service boundaries,
responsibility ownership, major data flow, runtime topology, integration
boundaries, or cross-component failure and recovery. Do not update it for a
routine internal refactor.

### `docs/DATA_MODEL.md`

Update when entities, fields, constraints, relationships, statuses,
state-transition meaning, or persistence ownership change. Test fixtures and
implementation-only query changes do not belong here.

### Domain documents

Update a domain document such as `docs/TELEGRAM_INGESTION.md` when verified
domain behavior changes: supported inputs, visible responses, idempotency,
transaction boundaries, runtime mode, or domain failure handling. Do not
update it for unrelated workflow or tooling work.

### `docs/PROJECT_BRIEF.md`

This is the canonical project brief. Update it only when the accepted product
definition, MVP boundary, product value, or a major non-goal changes—not for
routine progress.

### `README.md`

Update when developers or users need new setup, migration, test,
configuration, supported utility, or visible behavior instructions. Link to
this document instead of duplicating the workflow.

### `.env.example`

Update whenever configuration variables are added, removed, or changed. Use
placeholders and safe examples only.

### Task files

Normally commit an accepted task specification before implementation. Its
requirements, scope, non-goals, and criteria are the review contract. Status
and completion evidence may be added later, but requirements are not silently
rewritten. Record amendments with reasons and return material changes to task
planning. Keep specification and implementation commits distinguishable where
practical.

## Context and implementation-review reports

Use the compact project-context report for orientation, planning handoff, and
metadata checks that do not require implementation contents:

From the repository root, run:

```bash
python3 scripts/project_context.py
```

The command prints Markdown to standard output. It uses only explicit read-only
Git queries and whitelisted task/document metadata. It does not read diffs,
secrets, environment variables, databases, or Telegram content, and it writes
nothing. A dirty working tree and detached HEAD are valid report states; failure
to establish Git context exits non-zero rather than printing a partial report.

To hand off a snapshot without modifying the repository:

```bash
python3 scripts/project_context.py > /tmp/pkm-project-context.md
```

Always label the generated file as point-in-time context and re-run it when the
repository changes.

Implementation review requires the separate full bundle. After implementation,
verification, and documentation updates, Codex writes the task's explicit
completion report outside the repository, normally under `/tmp`, then runs:

```bash
python3 scripts/review_bundle.py \
  --task tasks/<active-task>.md \
  --report /tmp/<task>-handoff.md \
  > /tmp/<task>-review-bundle.md
```

The committed task specification is the review contract. Captured Git status,
the tracked diff, and complete safe untracked-file contents are the
implementation state. The completion report supplies Codex's explanations and
verification claims; bundle generation does not independently execute or
validate those claims.

The bundle command is read-only and emits Markdown only after complete evidence
passes its ignored-path, secret, text, file-type, size, and consistency checks.
It includes neither ignored files nor partial or truncated substitutes for
rejected evidence.

Regenerate the bundle after any implementation, documentation, task, or
completion-report change. Separately uploaded files must not silently override
or be combined with conflicting bundle evidence; a conflict requires a fresh
bundle from the current repository and report.
