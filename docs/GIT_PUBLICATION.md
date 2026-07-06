# Manual Git Artifact Publication

## Boundary

Publication is an explicit local operation on one existing Artifact UUID:

```text
valid Artifact + exact Task 006 file + initialized local Git repository
→ one selected-path commit
→ Artifact.git_commit_sha
```

It does not create or repair notes, initialize Git, change branches, contact a
remote, enqueue work, or run from Telegram ingestion or the worker.

## Repository setup and validation

`KNOWLEDGE_BASE_PATH` is both the Markdown root and required exact Git
top-level. Initialize and configure it manually:

```bash
git -C knowledge-base init
git -C knowledge-base config --local user.name "<desired commit author>"
git -C knowledge-base config --local user.email "<desired commit email>"
```

The publisher rejects parent-repository discovery, bare repositories, detached
HEAD, merge/rebase/cherry-pick/revert state, missing repository-local author
values, and a nonempty or unmerged index. An attached unborn branch is valid.
Every Git command applies `safe.directory` only for that command, disables
terminal prompting, strips inherited Git repository-redirection variables by
using a minimal environment, has a timeout, and uses argument arrays rather
than a shell.

## CLI

```bash
docker compose exec app \
  python -m app.knowledge.git_cli --artifact-id <artifact-uuid>
```

Success output is:

```text
artifact_id: <artifact-uuid>
file_path: <repository-relative-path>
git_commit_sha: <full-commit-sha>
outcome: created|reconciled|existing
```

Expected failures return status 1 with one `artifact Git publication failed:`
line. Argparse syntax failures return status 2.

## Commit and working-tree policy

The real index must be empty before publication. Unrelated unstaged tracked
changes and untracked files are allowed and preserved. Ignored selected paths
fail; forced staging is never used. The publisher stages only
`Artifact.file_path`, verifies the index contains no second path, and compares
the staged blob with the exact Task 006 bytes so attributes or clean filters
cannot silently change content.

Repository hooks are disabled with a temporary empty `core.hooksPath`, signing
and editors are disabled, and the stable commit message is:

```text
Publish artifact <artifact-uuid>

PKM-Artifact-ID: <artifact-uuid>
PKM-Artifact-Path: <repository-relative-path>
```

An empty identity commit is permitted when HEAD already contains the exact
blob but no matching publication commit exists. The completed commit tree,
trailers, path, and blob are validated before PostgreSQL stores its SHA.

## Locks, idempotency, and recovery

One nonblocking exclusive lock at Git-private
`pkm-artifact-publication.lock` serializes HEAD and index work for the whole
knowledge-base repository. A PostgreSQL `FOR UPDATE` lock separately protects
the selected Artifact row. Both remain held through database finalization.

| Database/history state | Result |
|---|---|
| null SHA, no matching commit | create commit; `created` |
| null SHA, one exact matching commit | store its SHA; `reconciled` |
| valid stored SHA | create nothing; `existing` |
| malformed stored commit or candidate | fail closed |
| multiple matching commits | fail closed |

Git and PostgreSQL do not share a transaction. Failure before a commit rolls
back PostgreSQL and restores only the selected index entry while preserving its
working bytes. Failure after Git creates the commit retains history and rolls
back PostgreSQL; the next invocation finds the exact local trailer-bearing
commit and reconciles it. Cleanup failure reports the primary failure and
requires manual index inspection. The publisher never resets, reverts, or
otherwise rewrites history as compensation.

## Local-only scope

The implementation performs no clone, fetch, pull, push, remote inspection or
configuration, branch creation or switching, merge, rebase, submodule, or
worktree operation. Remote synchronization and automatic publication remain
future tasks.
