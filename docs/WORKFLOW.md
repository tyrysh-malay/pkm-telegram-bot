# Repository Workflow

This repository owns the project workflow. The live local repository is the
authority for Codex while editing; documentation describes it but cannot
override contrary files, Git state, tests, or observed behavior.

## Sources of truth and visibility

Keep these boundaries distinct:

* **Local working tree:** authoritative to Codex for current editing and local
  verification. Uncommitted changes are visible only to local tools and cannot
  be reviewed through GitHub.
* **Pushed default branch:** the accepted shared baseline. Normal task work is
  not committed or pushed directly here.
* **Pushed task branch and pull request:** the shared implementation-review
  state. They contain committed and pushed work only.
* **Task contract:** the task file at the exact full contract commit SHA
  recorded in the pull-request description. A later task-file version at the
  branch head does not replace it.
* **Pull-request description:** Codex's implementation explanation and supplied
  verification claims. These claims are not independently executed proof
  unless a corresponding CI check exists.

GitHub never exposes local uncommitted state. If requested review evidence
exists only locally, Codex must say so and must not describe it as reviewed.

## Evidence precedence

Review evidence has this order:

1. the task file at the exact contract commit defines requirements;
2. the pull-request base and exact pushed head define the comparison;
3. pull-request commits and patch define pushed implementation state;
4. the pull-request description explains the implementation and reports local
   verification claims;
5. available CI checks provide independently executed verification.

Snapshots, summaries, comments, and separately supplied files are handoff aids,
not independent sources of truth. Conflicting evidence requires inspection of
the current repository and pull request.

## Task lifecycle

1. **Discuss architecture.** Compare durable boundaries and record accepted
   decisions separately from tentative directions.
2. **Plan one bounded task.** Define its goal, verified starting boundary,
   branch, contract and implementation commits, Git authorization, PR boundary,
   tests, acceptance criteria, correction behavior, and merge boundary.
3. **Synchronize the default branch.** Fetch the verified remote and require a
   clean local default branch with no ahead/behind difference.
4. **Create one task branch.** Use the task's authorized branch from the pushed
   default baseline and preserve unrelated local state.
5. **Commit the accepted task contract.** The repository-owned task
   specification precedes implementation and receives an exact full SHA.
6. **Push and open a draft PR.** Record task path, contract SHA, base branch,
   task branch, goal, and any required connected-access gate.
7. **Inspect the live repository.** Read local and remote Git state, the exact
   contract, current state, this workflow, referenced documents, relevant code,
   tests, configuration, and PR metadata. Report contradictions before editing.
8. **Implement locally.** Make the smallest useful change without postponed
   functionality, speculative abstraction, or unrelated cleanup.
9. **Test and verify acceptance.** Run focused checks first, then every suite
   and manual check required by the task.
10. **Update documentation from verified behavior.** Remove stale semantic
    state and record durable decisions only after verification supports them.
11. **Commit and push the implementation.** Use only an explicitly authorized
    task-branch boundary. Never mix unrelated changes or push the default branch.
12. **Complete the PR description.** Record exact commands and results,
    documentation, risks, exclusions, contract SHA, base SHA, and current head.
13. **Mark ready.** Do this only when the task authorizes it and implementation,
    verification, documentation, description, scope, and branch cleanliness pass.
14. **Review the exact PR head.** Handoff Review identifies the repository, PR,
    contract SHA, base SHA, and exact pushed head SHA.
15. **Apply bounded corrections.** Keep them on the same task branch, preserve
    history, rerun relevant checks, push normally, and review the new exact head.
16. **Obtain final approval.** Approval applies only to the identified head.
17. **Merge only after separate authorization.** Use the task's accepted merge
    method; readiness or approval alone never authorizes merge.
18. **Select the next task separately.** Completion does not invent or activate
    a successor.

Task requirements must not be silently rewritten after implementation to match
the code. Status and concise evidence may be appended without replacing the
contract. Material scope changes return to task planning.

## Git and GitHub authority

Each task must explicitly authorize the exact branch and each permitted action:
branch creation, contract commit, push, draft PR creation, implementation
commit, readiness transition, and correction commits. Without that authority,
Codex stops at the relevant boundary.

Codex must never, without separate explicit authorization:

* push task work directly to the default branch;
* merge a pull request;
* force-push or silently rebase reviewed commits;
* amend already pushed reviewed commits;
* delete task branches;
* change repository settings or protection rules;
* commit secrets, local configuration, generated knowledge artifacts, database
  dumps, credential-bearing URLs, or unrelated work.

Fast-forwarding a clean local default branch to its remote counterpart is
allowed when the task authorizes branch bootstrap. Normal accepted merges use a
merge commit when the task specifies that policy, preserving contract and
implementation commit identities.

## Pull-request review boundary

The PR must identify:

```text
repository
PR number
task path
full contract commit SHA
base branch and base SHA
task branch and current head SHA
commits and changed paths
```

The description must summarize outcome, exact verification commands and
results, documentation, risks and unverified items, and review scope. It must
state that reported verification is a Codex claim unless backed by an
available CI check.

When connected access is a task prerequisite, the gate passes only after the
collaboration channel explicitly confirms repository and PR metadata, the task
at the contract SHA, commit list, changed files or patch, and current head SHA.
Record visibility limitations honestly. A successful local push or CLI query is
not evidence that another review surface has access.

After any pushed correction, the old review result applies only to the earlier
head. Update the description when evidence changes and require review of the new
head. Do not force-push to make the head appear unchanged.

## Conversation responsibilities

### Architecture Planning

Responsible for durable architecture, meaningful alternatives, accepted
boundaries, and escalation of material scope changes. It does not implement or
review PR patches line by line.

### Active Task Planning

Responsible for one bounded task: branch name, contract boundary, commit and
push authorization, PR boundary, tests, acceptance criteria, correction
behavior, and merge boundary. It does not implement, merge, or silently broaden
the task.

### Codex

Responsible for local and remote inspection, authorized task-branch and PR
bootstrap, local implementation, verification, documentation, coherent
authorized commits, pushing only the task branch, PR-description updates, and
preserving unrelated state.

Codex does not push the default branch, merge without separate authorization,
expose secrets, or claim GitHub contains local uncommitted work.

### Handoff Review

Responsible for reviewing the exact contract commit and task path, PR base and
head SHAs, commits, complete patch, description, and available checks. It cannot
review uncommitted local changes and must identify the exact head SHA reviewed.

### Future Scope

Responsible for collecting product ideas, exploring later workflows and
features, and identifying future planning questions. It does not add ideas to
the active task, describe tentative features as implemented, or record a
durable decision without the architecture process.

## Documentation update rules

### `docs/CURRENT_STATE.md`

Update after an implemented and verified task changes current semantic state.
Describe what works, what does not, and operational boundaries. Maintain one
stable field:

```text
**Active task:** `tasks/<task-file>.md`
```

or:

```text
**Active task:** none selected
```

Replace stale state instead of accumulating task history. Do not maintain
branch, commit, PR, or working-tree chronology here.

### `docs/DECISIONS.md`

Update only for accepted durable architectural or development choices that
constrain later tasks or explain a meaningful alternative. Do not record every
file change, test result, or temporary detail.

### `docs/ARCHITECTURE.md`

Update when verified behavior changes process or service boundaries,
responsibility ownership, major data flow, runtime topology, integration
boundaries, or cross-component failure and recovery.

### `docs/DATA_MODEL.md`

Update when entities, fields, constraints, relationships, statuses,
state-transition meaning, or persistence ownership change.

### Domain documents

Update a domain document when verified behavior changes supported inputs,
visible responses, idempotency, transaction boundaries, runtime mode, or domain
failure handling. Do not update it for unrelated workflow work.

### `docs/PROJECT_BRIEF.md`

Update only when the accepted product definition, MVP boundary, product value,
or a major non-goal changes.

### `README.md`

Update when developers or users need new setup, migration, test,
configuration, contributor workflow, supported utility, or visible behavior
instructions. Link to this workflow instead of duplicating it.

### `.env.example`

Update whenever configuration variables are added, removed, or changed. Use
placeholders and safe examples only.

### Task files

Commit the accepted specification before implementation. Its requirements,
scope, non-goals, and criteria are the review contract. Later changes may set
status, append concise completion evidence, or record an explicit amendment and
reason; they must not silently replace accepted requirements.
