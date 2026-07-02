# Task 005: Generate self-contained implementation review bundles

**Status:** completed
**Depends on:** Task 004
**Target file:** `tasks/005-implementation-review-bundles.md`
**Expected commit boundary:** one reviewable documentation-and-tooling implementation commit; the accepted task specification must be committed before implementation, and Codex must not commit implementation changes unless explicitly instructed

## Goal

Add a small, read-only repository command that generates one self-contained Markdown bundle containing the complete safe evidence needed to review an uncommitted task implementation against its committed task specification.

The bundle must let Handoff Review evaluate the implementation without requiring a manually assembled collection of task files, diffs, untracked files, and completion-report uploads.

This task does not replace the compact metadata-oriented context report introduced in Task 004.

## Confirmed current boundary

The supplied repository evidence confirms the following Task 004 outcomes:

* the repository-driven workflow is established;
* `docs/WORKFLOW.md` defines the task lifecycle and review responsibilities;
* `tasks/TEMPLATE.md` defines the standard task structure;
* `scripts/project_context.py` produces a compact metadata-oriented repository snapshot;
* the context report intentionally does not include complete diffs or complete untracked-file contents;
* D-023 establishes repository-local workflow and read-only context reporting;
* Task 004 is completed;
* `docs/CURRENT_STATE.md` recorded no active task after Task 004;
* Git is available in the authoritative development image;
* the authoritative test suite passed after Task 004.

The supplied task sequence contains Tasks 000–004, making `005` the expected next number.

Codex must still verify the live repository before editing. In particular, it must verify that no Task 005 file or later conflicting decision has already been added.

## Repository verification requirements

Before editing, Codex must inspect and report:

* current branch;
* current HEAD;
* staged, unstaged, and untracked state;
* recent commits;
* whether the working tree is clean before Task 005 implementation;
* whether `tasks/005-implementation-review-bundles.md` exists at `HEAD`;
* whether the accepted Task 005 specification has been committed before implementation begins;
* whether any other Task 005 filename already exists;
* the current contents and conventions of:

  * `AGENTS.md`;
  * `docs/WORKFLOW.md`;
  * `docs/CURRENT_STATE.md`;
  * `docs/DECISIONS.md`;
  * `README.md`;
  * `tasks/TEMPLATE.md`;
  * `scripts/project_context.py`;
  * `tests/test_project_context.py`;
  * `Dockerfile`;
  * `.dockerignore`;
  * `.gitignore`;
* whether D-023 exists and the next available decision identifier;
* how scripts and tests are copied into the development image;
* whether `scripts/` is a Python package or uses direct sibling imports;
* whether small helpers from `scripts/project_context.py` can be reused without changing its public behavior;
* the installed Git version and the supported forms of the required read-only Git commands;
* whether repository-local ignore rules include `.gitignore`, `.git/info/exclude`, or global excludes relevant to test fixtures;
* whether any live repository fact contradicts this task specification.

Contradictory live repository evidence must be reported before editing. It must not be silently resolved by rewriting this task.

## Problem or motivation

Task 004 reduced routine context handoff to one compact metadata report, but implementation review requires a different evidence boundary.

A complete review currently may require manually supplying:

* the accepted task specification;
* a Codex completion report;
* tracked staged and unstaged changes;
* newly created untracked files;
* a changed-file list;
* command results;
* repository metadata.

This manual process has already shown several weaknesses:

* ordinary `git diff` excludes untracked files;
* changed files can be forgotten during upload;
* a working-tree task file can differ from the committed review contract;
* ignored local files can accidentally become part of an ad hoc handoff;
* separately uploaded files may represent different repository moments;
* completion-report claims can be mistaken for verified Git evidence;
* a reviewer may not know whether evidence was truncated or omitted;
* unsafe files must not be uploaded merely because they are untracked.

The project needs a separate review-packaging command that captures one safe, internally consistent, point-in-time evidence bundle.

## Scope

### 1. Add the review-bundle command

Add the preferred command:

```bash
python3 scripts/review_bundle.py \
  --task tasks/005-implementation-review-bundles.md \
  --report /tmp/task005-handoff.md \
  > /tmp/task005-review-bundle.md
```

The command must:

* require `--task`;
* require `--report`;
* accept no option for including ignored files;
* print one Markdown bundle to standard output;
* write no repository or output file itself;
* use no network access;
* run from the repository root;
* discover and verify the Git repository before collecting evidence;
* return non-zero with a clear error when required evidence cannot be captured safely and completely.

A different script path or interface is permitted only when live repository inspection shows a stronger existing convention. Any deviation must be explained before editing and documented after verification.

### 2. Keep the Task 004 context report separate

`scripts/project_context.py` must remain the compact metadata-oriented context command.

Task 005 must not turn it into a full review bundle or add review-specific default output to it.

Small existing helpers may be reused or extracted where this reduces duplication, provided that:

* the helper remains narrowly scoped;
* no general Git framework is introduced;
* `scripts/project_context.py` retains its existing command, output boundary, safety behavior, and tests;
* any shared-helper change is covered by both context-report and review-bundle tests.

### 3. Add focused automated tests

Add focused tests, preferably:

```text
tests/test_review_bundle.py
```

Use temporary Git repositories and real Git commands where practical.

Do not depend on the developer’s real working tree for behavioral tests.

### 4. Update workflow documentation

Update `docs/WORKFLOW.md` to define:

* when the compact project-context report is appropriate;
* when a full implementation-review bundle is required;
* how Codex produces the completion report;
* how the review bundle is generated;
* the evidence-precedence rule;
* the requirement to regenerate the bundle after any implementation, documentation, task, or completion-report change;
* the prohibition against silently combining bundle evidence with conflicting separately uploaded files.

### 5. Update contributor documentation

Update `README.md` with concise usage instructions:

```bash
python3 scripts/review_bundle.py \
  --task tasks/<active-task>.md \
  --report /tmp/<task>-handoff.md \
  > /tmp/<task>-review-bundle.md
```

The README must state that:

* the report file should normally be stored outside the repository;
* the bundle output should be redirected outside the repository;
* the command is read-only;
* ignored files are never included;
* unsafe or oversized evidence causes failure rather than truncation;
* the compact context report and the review bundle serve different purposes.

Do not duplicate the complete safety or workflow specification in the README.

### 6. Add a durable decision

Add the next repository-confirmed decision, expected to be D-024, specializing D-023 for implementation-review packaging.

The decision must establish that:

* the committed task specification is the review contract;
* the captured Git evidence is the implementation state;
* the explicit completion report contains explanations and verification claims;
* implementation review should normally receive one generated, self-contained bundle;
* the bundle is point-in-time evidence, not a new source of truth;
* a repository or report change invalidates the previous bundle;
* conflicting separately uploaded files do not override the bundle;
* a conflict requires generating a fresh bundle;
* ignored, unsafe, binary, symlinked, or oversized evidence is rejected rather than omitted or included;
* review packaging remains separate from the compact Task 004 context report;
* no upload, commit, push, or repository-writing automation is introduced.

Codex must verify the decision number before using it.

### 7. Update current state and task completion evidence

After implementation and verification:

* update `docs/CURRENT_STATE.md` with the verified review-bundle command and boundary;
* preserve current application capabilities and limitations;
* describe the context report and review bundle as separate commands;
* set the active task to `none selected` unless the user has explicitly selected another task;
* update this task’s status to `completed`;
* append concise completion evidence without rewriting the accepted requirements.

Do not invent Task 006.

## Out of scope

Do not add:

* GitHub API integration;
* GitHub repository downloads;
* GitHub OAuth;
* private-repository credentials;
* automatic uploads to Web Chat;
* automatic file attachments;
* automatic commits;
* automatic pushes;
* automatic pull requests;
* CI/CD changes;
* issue-tracker integration;
* background monitoring;
* automatic completion-report generation;
* automatic verification-command execution by the bundle tool;
* semantic relevance classification for untracked files;
* AI-generated review summaries;
* automatic documentation rewriting;
* a general Git abstraction framework;
* a general archive format;
* ZIP, tar, JSON, YAML, or HTML output;
* binary-file packaging;
* symlink traversal;
* ignored-file inclusion overrides;
* application behavior changes;
* database models or migrations;
* Telegram behavior changes;
* Redis;
* Dramatiq;
* worker behavior;
* AI processing;
* Markdown knowledge-artifact generation;
* unrelated refactoring.

## Affected components

### Tooling

Expected changes:

* add `scripts/review_bundle.py`;
* optionally make a narrowly bounded helper adjustment for code shared with `scripts/project_context.py`.

### Tests

Expected changes:

* add `tests/test_review_bundle.py`;
* update `tests/test_project_context.py` only when a small helper extraction requires regression coverage.

### Documentation

Expected changes:

* this task file;
* `docs/WORKFLOW.md`;
* `README.md`;
* `docs/DECISIONS.md`;
* `docs/CURRENT_STATE.md`;
* `AGENTS.md` only if one concise instruction is necessary and not already implied by the workflow.

### Development image

No Dockerfile change is expected because Task 004 already made Git and repository scripts available in the development image.

A minimal Dockerfile or copy-list adjustment is permitted only if live inspection proves the new script or tests would otherwise be absent from the authoritative environment.

### Components that must not change

Do not modify:

* `app/` runtime behavior;
* database schema or migrations;
* Telegram ingestion;
* worker or queue behavior;
* knowledge-artifact generation;
* application configuration;
* `.env.example`, unless live inspection reveals an unexpected direct configuration requirement.

## Data, state, migration, and configuration impact

Expected impact:

* no database migration;
* no operational database state change;
* no application state change;
* no new environment variable;
* no secret configuration;
* no persistent bundle file written by the command;
* no generated file committed to the repository;
* no network state;
* no queue state;
* no runtime process change.

The command reads repository evidence and one explicit completion-report file, constructs the complete bundle in memory, and writes it only to standard output after successful validation.

## Behavioral requirements

## Command-line interface

The command must require exactly these operational inputs:

```text
--task <repository-relative task path>
--report <completion-report file path>
```

Normal `--help` behavior is allowed.

No option may weaken ignored-file, secret, binary, symlink, or size protections.

Argument or validation errors must:

* produce no bundle on standard output;
* print a concise error to standard error;
* exit non-zero.

## Repository discovery

The command must establish the repository root through Git.

It must fail when:

* Git cannot be executed;
* the current directory is not inside a Git work tree;
* `HEAD` cannot be resolved;
* required Git evidence cannot be collected.

Detached HEAD is valid and must be reported explicitly.

The output must not expose the absolute repository path.

## Task contract requirements

`--task` must identify:

* a normalized repository-relative path;
* under `tasks/`;
* ending in `.md`;
* with no absolute path or `..` traversal;
* present at `HEAD`;
* stored at `HEAD` as a regular blob, not a symlink or submodule;
* valid UTF-8 text;
* within the configured per-file size limit.

The bundle must read the task specification from:

```text
HEAD:<task-path>
```

It must not use the working-tree version as the review contract.

If the working-tree task file has changed after the task-specification commit, that change must appear only through the captured Git status and tracked diff.

The bundle must record:

* task repository path;
* source commit;
* byte size;
* SHA-256 hash of the exact committed task bytes.

The command must fail if the supplied task is not committed at `HEAD`.

## Completion-report requirements

`--report` must identify an explicit existing file.

The report must be:

* a regular file;
* not a symlink;
* valid UTF-8 text;
* free of NUL bytes;
* within the configured per-file size limit;
* not suspicious under the secret-evidence rules.

The report may be outside the repository and should normally be placed under `/tmp`.

When the report resolves inside the repository:

* it must not be ignored;
* it must not be a symlink;
* it remains subject to all changed-evidence safety rules;
* if it is also an untracked file, its content must appear once in the bundle and its manifest entry must identify both roles rather than duplicating the payload.

The bundle must include the report in full.

The report section must state clearly:

* the report contains Codex explanations and verification claims;
* the bundler does not independently execute or validate those claims.

The output must not display an absolute external report path. A safe basename or role label is sufficient.

## Git status requirements

The bundle must include complete non-ignored staged, unstaged, and untracked status for the captured working tree.

The implementation must use a machine-readable Git status form and render a canonical deterministic status section.

Requirements:

* include every staged path;
* include every unstaged path;
* include every non-ignored untracked path;
* preserve combined staged and unstaged state;
* use repository-relative paths;
* represent paths safely in Markdown;
* use deterministic path ordering;
* disable rename inference or normalize renames consistently as delete/add records;
* exclude ignored files;
* reject unmerged or conflicted index states rather than presenting incomplete ordinary-diff evidence.

The rendered status is evidence and must have its own byte size and SHA-256 hash in the evidence manifest.

## Tracked diff requirements

The bundle must include the complete tracked working-tree diff against `HEAD`.

The diff must represent the final tracked working-tree state relative to `HEAD`, including:

* staged changes;
* unstaged changes;
* files with both staged and unstaged changes;
* tracked additions;
* tracked deletions;
* mode changes.

The preferred Git boundary is equivalent to:

```bash
git diff \
  --no-ext-diff \
  --no-textconv \
  --no-renames \
  --full-index \
  HEAD --
```

Codex may adjust flags only when required by the installed Git version and must preserve the same safety and completeness semantics.

The implementation must not:

* use an external diff driver;
* use text-conversion filters;
* omit a tracked path silently;
* include binary patches;
* truncate the diff.

Before including the diff, the command must reject changed tracked evidence that is:

* binary;
* not strict UTF-8 text where file content is present;
* a symlink;
* a submodule;
* an unsupported special file;
* suspicious under the secret-evidence rules;
* over the per-file/blob limit;
* part of an unmerged conflict.

The complete diff must have:

* byte size;
* SHA-256 hash;
* one evidence-manifest entry.

An empty tracked diff is valid and must be represented explicitly with size zero and the SHA-256 hash of empty bytes.

## Untracked-file requirements

Discover untracked files through Git using semantics equivalent to:

```bash
git ls-files --others --exclude-standard -z
```

Do not use a manually maintained file list.

For every discovered untracked path, the command must:

1. confirm that the path remains inside the repository;
2. confirm that it is not ignored;
3. use `lstat`-style behavior rather than following symlinks;
4. require a regular file;
5. reject symlinks and special files;
6. require a safe UTF-8 path;
7. reject control characters in paths;
8. apply secret-path safety checks;
9. enforce the per-file size limit;
10. read the file as strict UTF-8;
11. reject NUL bytes;
12. apply the high-confidence secret-content checks;
13. include the complete content;
14. calculate byte size and SHA-256;
15. list it deterministically by repository-relative path.

Directories are not evidence items. Git-discovered files inside untracked directories must be expanded and handled individually.

Ignored files must never be included and there must be no override.

## Ignored-file behavior

Ignored untracked files are absent from discovery and must not appear in:

* status evidence;
* changed-file manifest;
* evidence manifest;
* content sections.

If an explicitly supplied report resolves inside the repository and is ignored, the command must fail.

If a tracked changed path also matches a repository ignore rule, the command must fail rather than either:

* including an ignored path;
* silently removing the path from the required tracked diff.

This preserves both the no-ignored-files rule and the completeness rule.

## Supported evidence types

The first version supports only regular UTF-8 text evidence.

Unsupported evidence includes:

* binary files;
* invalid UTF-8;
* files containing NUL bytes;
* symlinks;
* submodules;
* sockets;
* devices;
* FIFOs;
* other special files.

The command must reject the complete bundle when unsupported changed evidence is encountered.

It must not replace unsupported evidence with:

* a placeholder;
* a summary;
* a hash-only record;
* a truncated section;
* a “binary files differ” line.

## Secret-evidence safety

Because implementation review requires complete evidence, unsafe evidence must cause the whole command to fail. Redacting or silently omitting a changed file would make the bundle incomplete.

At minimum, reject paths matching a conservative case-insensitive policy covering:

* `.env`;
* names beginning with `.env.`;
* private-key and keystore suffixes such as:

  * `.pem`;
  * `.key`;
  * `.p12`;
  * `.pfx`;
  * `.jks`;
* common private-key basenames such as:

  * `id_rsa`;
  * `id_ed25519`;
* path components named:

  * `secret`;
  * `secrets`;
  * `credential`;
  * `credentials`;
* delimiter-separated filename terms such as:

  * `secret`;
  * `credential`;
  * `token`;
  * `password`;
  * `api_key`.

The matching rule must avoid treating ordinary words such as `tokenizer` as a secret filename solely because they contain a shorter substring.

At minimum, reject content containing a private-key header such as:

```text
-----BEGIN ... PRIVATE KEY-----
```

Do not add probabilistic entropy scanning, provider-specific online validation, or a large secret-scanning dependency.

The completion report and task contract are subject to the same high-confidence content protection.

## Size limits

Use explicit byte limits:

```text
Maximum individual evidence file or blob: 1,048,576 bytes
Maximum complete tracked diff:            4,194,304 bytes
Maximum final Markdown bundle:            8,388,608 bytes
```

The individual limit applies to:

* the committed task blob;
* the completion-report file;
* each untracked file;
* each present `HEAD` blob for a changed tracked path;
* each present working-tree file for a changed tracked path.

The command must:

* measure bytes, not characters;
* fail before writing bundle output when a limit is exceeded;
* identify the evidence item and applicable limit;
* never truncate;
* never offer an override in this task.

Constants must be named and tested.

## Changed-file manifest

The bundle must contain a deterministic manifest sorted by repository-relative path.

For each changed path, include:

* repository-relative path;
* Git status;
* whether the path is staged, unstaged, untracked, deleted, or a combination;
* evidence representation:

  * tracked diff;
  * complete untracked content;
  * explicit completion report, when applicable;
* current-file byte size and SHA-256 when current content exists;
* `HEAD` blob byte size and SHA-256 when committed content exists;
* a clear marker when one side does not exist.

Rename detection should be disabled or normalized as delete/add to avoid ambiguous two-path evidence.

The manifest must not infer semantic relevance.

## Evidence manifest

The bundle must contain an evidence manifest with deterministic ordering.

Include one entry for:

* canonical Git status evidence;
* committed task contract;
* completion report;
* complete tracked diff;
* every included untracked-file payload.

Each entry must include:

* stable role;
* safe source label;
* byte size;
* SHA-256 hash.

Hashes must be calculated over the exact source evidence bytes represented by the entry, before Markdown framing is added.

The bundle itself does not need to contain a hash of itself.

## Markdown rendering

The bundle must be valid readable Markdown.

Required top-level order:

1. title and UTC generation timestamp;
2. point-in-time and source-of-truth disclaimer;
3. evidence-precedence rule;
4. branch and HEAD;
5. complete Git status;
6. deterministic changed-file manifest;
7. evidence manifest;
8. committed task specification;
9. completion report;
10. complete tracked diff;
11. complete safe untracked-file contents;
12. closing regeneration warning.

Evidence contents must be placed in Markdown code fences that cannot be broken by backticks contained in the evidence.

Use a dynamic fence length longer than the longest backtick run in the payload, with a sensible minimum.

The renderer must:

* preserve evidence text;
* not reinterpret Markdown inside evidence;
* safely escape path labels and headings;
* use deterministic section and file ordering;
* avoid absolute local paths;
* avoid generated semantic summaries.

## Review precedence and disclaimer

The generated bundle must state:

1. the committed task specification defines the requirements and review contract;
2. the captured Git status, tracked diff, and untracked-file contents define the implementation state;
3. the completion report provides Codex explanations and verification claims.

It must also state:

* the bundle is point-in-time evidence;
* the live repository remains authoritative;
* the bundler does not independently validate completion-report claims;
* separately uploaded files must not silently override bundle evidence;
* any conflict or repository change requires generating a fresh bundle.

## Point-in-time consistency

The command must avoid producing a bundle assembled from different repository states.

At minimum:

1. capture the starting HEAD;
2. capture canonical status;
3. capture the tracked diff;
4. discover and read untracked files;
5. capture all external and committed evidence;
6. recapture HEAD, status, tracked diff, and untracked path set before rendering;
7. fail if any recaptured repository evidence differs.

For regular files read directly, use before/after metadata and content checks sufficient to detect modification during capture.

The command must also fail if the completion report changes while being read.

No Markdown may be written to standard output until:

* all evidence is collected;
* all validation succeeds;
* consistency checks pass;
* the final bundle size is known to be within limits.

A failure must leave standard output empty.

## Read-only behavior

The utility may use only explicit read-only Git operations.

It must not invoke:

* `git add`;
* `git reset`;
* `git checkout`;
* `git restore`;
* `git clean`;
* `git commit`;
* `git stash`;
* `git apply`;
* `git update-index`;
* any mutating Git command.

It must:

* avoid `shell=True`;
* create no repository file;
* change no repository file;
* change no index entry;
* change no Git configuration;
* change no file timestamp intentionally;
* leave `git status` unchanged.

Creating the explicitly supplied completion report outside the repository is part of the Codex handoff workflow, not behavior performed by the bundling command.

## Output-location behavior

Documentation must instruct users to redirect output outside the repository, normally under `/tmp`.

For example:

```bash
python3 scripts/review_bundle.py \
  --task tasks/005-implementation-review-bundles.md \
  --report /tmp/task005-handoff.md \
  > /tmp/task005-review-bundle.md
```

Redirecting output into the repository is unsupported because the shell creates or truncates the output file before the command starts, which would change the evidence being captured.

The command does not need to discover the shell’s output destination.

## Investigation requirements

Before choosing implementation details, Codex must determine:

* whether `run_git` and repository-root discovery from `project_context.py` can be reused cleanly;
* whether importing sibling script helpers works consistently:

  * when invoked directly;
  * when imported by pytest;
  * inside the development container;
* whether a tiny shared helper module is clearer than duplication;
* how Git reports:

  * mode changes;
  * staged additions;
  * staged deletion plus untracked recreation;
  * non-ASCII paths;
  * conflicted entries;
  * submodules;
  * binary paths;
* which installed Git flags provide deterministic no-rename, no-textconv behavior;
* whether `.gitattributes` or external diff configuration can influence output and how the chosen flags prevent that;
* whether ignored-path checks need `git check-ignore --no-index`;
* whether the Docker development image already includes every required script and test path.

A small shared helper extraction is a proposal, not a requirement. It must not become a general repository framework.

## Expected failure modes and recovery behavior

## Missing required arguments

Behavior:

* argparse-style usage error;
* non-zero exit;
* no bundle on standard output.

Recovery:

* provide both required arguments.

## Not inside a Git work tree

Behavior:

* clear standard-error message;
* non-zero exit;
* empty standard output;
* no writes.

Recovery:

* run from the repository.

## Missing or uncommitted task contract

Behavior:

* fail when the task is absent from `HEAD`;
* explain that the accepted task must be committed before implementation review;
* do not fall back to the working-tree file.

Recovery:

* commit the accepted task specification separately, then rerun.

## Missing or invalid completion report

Behavior:

* fail for missing, unreadable, symlinked, ignored in-repository, non-UTF-8, unsafe, or oversized report;
* identify the reason without printing report contents.

Recovery:

* create a safe regular UTF-8 report outside the repository.

## Binary, symlinked, special, unsafe, or oversized changed evidence

Behavior:

* fail the entire bundle;
* identify the path and rejection category;
* do not emit a partial bundle;
* do not silently omit the file.

Recovery:

* remove the unsafe file from the task working tree, replace it with safe reviewable evidence, or redesign the task boundary.

## Ignored evidence

Behavior:

* ignored untracked files are never discovered;
* an explicit ignored in-repository report is rejected;
* a changed tracked path matching ignore rules causes failure.

Recovery:

* move the report outside the repository or remove unsafe ignored content from the implementation boundary.

## Unmerged Git state

Behavior:

* fail clearly;
* no partial bundle.

Recovery:

* resolve or abort the merge/rebase conflict before review packaging.

## Repository mutation during capture

Behavior:

* fail consistency checks;
* standard output remains empty;
* message instructs the user to rerun.

Recovery:

* stop concurrent edits and regenerate the bundle.

## Bundle-size overflow

Behavior:

* fail before writing output;
* report calculated size and configured maximum;
* no truncation.

Recovery:

* split the implementation into a smaller task or remove unrelated evidence.

## Git command failure

Behavior:

* identify the failed read-only operation;
* exit non-zero;
* do not present partial evidence as complete.

Recovery:

* correct the repository or Git environment and rerun.

## Tests

Add focused tests covering at least the following.

### Command and contract behavior

1. Both `--task` and `--report` are required.
2. The task contract is read from `HEAD`.
3. An uncommitted working-tree rewrite of the task does not replace the contract.
4. A task absent from `HEAD` is rejected.
5. Absolute, escaping, non-task, symlink, and submodule task paths are rejected.

### Git evidence

6. Branch and HEAD are included.
7. Detached HEAD is represented.
8. Staged-only changes appear.
9. Unstaged-only changes appear.
10. A file with staged and unstaged changes is represented correctly.
11. Tracked additions and deletions appear in the complete diff.
12. Mode-only changes are preserved.
13. Unmerged states are rejected.
14. The tracked diff hash and size match the emitted diff source bytes.

### Untracked evidence

15. All safe non-ignored untracked files are discovered automatically.
16. Files in untracked directories are included individually.
17. Ordering is deterministic.
18. File contents are complete.
19. Ignored files are absent.
20. An explicit report that is also an untracked repository file is not duplicated.
21. Symlinked, binary, invalid-UTF-8, special, and oversized untracked evidence is rejected.

### Safety

22. Secret-like paths are rejected rather than redacted.
23. Ordinary names such as `tokenizer.py` are not rejected solely for containing `token`.
24. Private-key content is rejected.
25. Ignored in-repository reports are rejected.
26. Unsupported tracked binary, symlink, and submodule changes are rejected.
27. Per-file, diff, and total-bundle limits are enforced.
28. Errors produce empty standard output.
29. The command does not change Git status or create repository files.
30. External diff and textconv behavior cannot alter the captured diff.

### Bundle structure and integrity

31. UTC timestamp is included.
32. Review-precedence language is included.
33. Status, changed-file manifest, and evidence manifest are present.
34. Task, report, tracked diff, and untracked contents are included in the required order.
35. SHA-256 and byte sizes are correct.
36. Dynamic code fences safely contain evidence with triple or longer backtick runs.
37. Absolute repository and report paths are not exposed.
38. Completion-report claims are labeled as supplied claims rather than independently verified facts.
39. Empty tracked diff and empty untracked set are represented explicitly.
40. Mutation during capture causes failure where practical to simulate.

### Regression

41. Existing `tests/test_project_context.py` continues to pass.
42. `python3 scripts/project_context.py` retains its compact metadata-only behavior.
43. The complete authoritative pytest suite passes.

Do not build a large fake Git implementation.

## Acceptance criteria

Task 005 is complete only when all of the following are true.

### Command boundary

* `scripts/review_bundle.py` exists or a repository-justified equivalent is documented.
* `--task` and `--report` are mandatory.
* Markdown is written only to standard output.
* the utility writes nothing;
* the utility uses no network;
* the utility uses no third-party dependency without explicit repository justification.

### Contract and report

* the task specification is loaded from `HEAD`;
* an uncommitted task rewrite cannot replace the review contract;
* an uncommitted task is rejected;
* the completion report is included in full;
* report claims are labeled as claims supplied by Codex;
* both inputs have hashes and byte sizes.

### Git evidence completeness

* branch or detached-HEAD state is included;
* HEAD hash and subject are included;
* complete staged, unstaged, and non-ignored untracked status is included;
* the complete safe tracked working-tree diff against `HEAD` is included;
* all safe non-ignored untracked text-file contents are included;
* changed paths are discovered through Git;
* no manual upload list is required;
* no required safe evidence is silently omitted;
* no evidence is truncated.

### Manifest and integrity

* changed-file manifest ordering is deterministic;
* evidence manifest ordering is deterministic;
* each evidence payload has SHA-256 and byte size;
* tracked current and `HEAD` file hashes and sizes are represented where applicable;
* dynamic Markdown fencing preserves arbitrary backtick runs.

### Safety

* ignored files are never included;
* there is no ignored-file override;
* binary evidence is rejected;
* symlinked evidence is rejected;
* special files are rejected;
* invalid UTF-8 is rejected;
* secret-like paths are rejected;
* high-confidence private-key content is rejected;
* unmerged states are rejected;
* per-file limit is 1,048,576 bytes;
* tracked-diff limit is 4,194,304 bytes;
* final-bundle limit is 8,388,608 bytes;
* all failures occur before any bundle is written to standard output.

### Point-in-time consistency

* the bundle includes a UTC generation timestamp;
* starting and ending repository evidence is compared;
* repository mutation during capture causes failure;
* the output states that repository or report changes require regeneration;
* separately uploaded conflicting files cannot silently override bundle evidence.

### Separation from Task 004

* `scripts/project_context.py` remains a compact metadata report;
* no full diff or untracked-file packaging is added to its default output;
* existing context-report tests pass;
* review packaging remains a separate command.

### Documentation

* `docs/WORKFLOW.md` defines when and how to generate a review bundle;
* `README.md` contains concise usage;
* the next durable decision specializes D-023;
* `docs/CURRENT_STATE.md` records the verified command and boundary;
* this task contains completion evidence after verification;
* `AGENTS.md` is changed only if a concise instruction is genuinely necessary;
* architecture, data-model, Telegram, project-brief, and environment documentation remain unchanged unless repository evidence proves a direct Task 005 impact.

### Scope protection

* no application runtime behavior changes;
* no database or migration changes;
* no Telegram changes;
* no worker, Redis, AI, upload, commit, push, network, or CI automation;
* no semantic untracked-file relevance classifier;
* no general Git framework;
* no automatic documentation rewriting.

## Required verification commands

## Initial repository state

```bash
git branch --show-current
git rev-parse HEAD
git status --short
git log --oneline --decorate -10
git diff --check
```

Verify Task 005 is the next available task and that its accepted specification is committed:

```bash
find tasks -maxdepth 1 -type f -name '*.md' -print | sort
git ls-tree -r --name-only HEAD -- tasks/
git show HEAD:tasks/005-implementation-review-bundles.md \
  > /tmp/task005-contract-from-head.md
test -s /tmp/task005-contract-from-head.md
```

Inspect relevant implementation and documentation conventions:

```bash
sed -n '1,240p' AGENTS.md
sed -n '1,280p' docs/WORKFLOW.md
sed -n '1,220p' tasks/TEMPLATE.md
sed -n '1,360p' scripts/project_context.py
sed -n '1,320p' tests/test_project_context.py
grep -n '^## D-' docs/DECISIONS.md | tail -10
```

## Focused and authoritative tests

```bash
docker compose config --quiet
docker compose up -d --build
docker compose exec app python -m pytest tests/test_review_bundle.py
docker compose exec app python -m pytest tests/test_project_context.py
docker compose exec app python -m pytest
```

Verify the existing compact report remains operational:

```bash
python3 scripts/project_context.py > /tmp/task005-project-context.md
test -s /tmp/task005-project-context.md
```

## Completion-report and bundle finalization

After implementation, documentation updates, and final tests, create the Codex completion report outside the repository:

```text
/tmp/task005-handoff.md
```

Generate a candidate bundle:

```bash
python3 scripts/review_bundle.py \
  --task tasks/005-implementation-review-bundles.md \
  --report /tmp/task005-handoff.md \
  > /tmp/task005-review-bundle-candidate.md
```

Inspect the candidate and record bundle-generation verification in the completion report.

Then regenerate the final bundle from the finalized report:

```bash
python3 scripts/review_bundle.py \
  --task tasks/005-implementation-review-bundles.md \
  --report /tmp/task005-handoff.md \
  > /tmp/task005-review-bundle.md
```

After the final bundle is generated, do not modify:

* repository implementation files;
* documentation;
* the Task 005 file;
* `/tmp/task005-handoff.md`.

Any such change requires regeneration.

## Bundle checks

```bash
test -s /tmp/task005-review-bundle.md
test "$(wc -c < /tmp/task005-review-bundle.md)" -le 8388608
sed -n '1,260p' /tmp/task005-review-bundle.md
```

Confirm required sections:

```bash
grep -F '# Implementation Review Bundle' \
  /tmp/task005-review-bundle.md
grep -F '## Committed task specification' \
  /tmp/task005-review-bundle.md
grep -F '## Completion report' \
  /tmp/task005-review-bundle.md
grep -F '## Tracked working-tree diff against HEAD' \
  /tmp/task005-review-bundle.md
grep -F '## Untracked file contents' \
  /tmp/task005-review-bundle.md
grep -F '## Changed-file manifest' \
  /tmp/task005-review-bundle.md
grep -F '## Evidence manifest' \
  /tmp/task005-review-bundle.md
```

Confirm the current HEAD and task contract are represented:

```bash
head_sha="$(git rev-parse HEAD)"
grep -F "$head_sha" /tmp/task005-review-bundle.md

task_sha256="$(sha256sum /tmp/task005-contract-from-head.md | cut -d' ' -f1)"
grep -F "$task_sha256" /tmp/task005-review-bundle.md
```

Confirm the completion-report hash is represented:

```bash
report_sha256="$(sha256sum /tmp/task005-handoff.md | cut -d' ' -f1)"
grep -F "$report_sha256" /tmp/task005-review-bundle.md
```

Confirm the bundle is read-only:

```bash
before_status="$(git status --porcelain=v1 --untracked-files=all)"

python3 scripts/review_bundle.py \
  --task tasks/005-implementation-review-bundles.md \
  --report /tmp/task005-handoff.md \
  > /tmp/task005-review-bundle-readonly.md

after_status="$(git status --porcelain=v1 --untracked-files=all)"
test "$before_status" = "$after_status"
cmp /tmp/task005-review-bundle.md \
    /tmp/task005-review-bundle-readonly.md
```

Because timestamps differ between independent invocations, `cmp` may be replaced by a deterministic comparison that removes only the documented generation-timestamp line. Codex must explain the chosen check.

Confirm the task contract came from `HEAD`, not the working tree, through focused tests and manual inspection of the task section.

Confirm ignored files are absent through focused temporary-repository tests. Do not print or inspect real ignored secret files merely for manual verification.

## Existing service regression

```bash
curl --retry 5 --retry-all-errors --retry-delay 1 \
  http://localhost:8000/health

curl --retry 5 --retry-all-errors --retry-delay 1 \
  http://localhost:8000/ready
```

No live Telegram message is required because Telegram behavior is unchanged.

## Final Git checks

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
  tasks/005-implementation-review-bundles.md \
  scripts/project_context.py \
  scripts/review_bundle.py \
  tests/test_project_context.py \
  tests/test_review_bundle.py \
  Dockerfile
```

Adapt the final file list only when live repository inspection justifies an additional narrowly scoped helper file.

## Documentation impact

### Required updates

* add and later complete `tasks/005-implementation-review-bundles.md`;
* update `docs/WORKFLOW.md`;
* update `README.md`;
* update `docs/DECISIONS.md` with the next decision specializing D-023;
* update `docs/CURRENT_STATE.md`.

### Conditional updates

* update `AGENTS.md` only when one concise review-bundle instruction is needed;
* update `scripts/project_context.py` and its tests only for a narrow shared-helper extraction that preserves existing behavior;
* update `Dockerfile` only when the authoritative development image otherwise lacks the new script or tests.

### Expected unchanged documents and components

Unless live evidence proves a direct impact, do not change:

* `docs/ARCHITECTURE.md`;
* `docs/DATA_MODEL.md`;
* `docs/TELEGRAM_INGESTION.md`;
* `docs/PROJECT_BRIEF.md`;
* `.env.example`;
* database migrations;
* application modules;
* Compose service behavior.

## Completion-report requirements

Codex must create a final completion report suitable for saving as:

```text
/tmp/task005-handoff.md
```

The report must contain exactly these sections.

### 1. Initial repository state

Report:

* branch;
* starting HEAD;
* starting status;
* recent relevant commits;
* confirmation that the Task 005 specification existed at `HEAD`;
* contradictions between supplied documentation and the live repository.

### 2. Implementation plan followed

Summarize:

* planned files;
* selected command interface;
* helper reuse or extraction decision;
* any justified deviation.

### 3. Repository inspection findings

Report:

* confirmed task number and filename;
* D-023 presence;
* selected next decision number;
* Git version and relevant supported flags;
* existing script/import/test conventions;
* Docker development-image behavior;
* ignore-rule findings relevant to implementation.

### 4. Files changed

List every changed file with its purpose.

Explicitly list files inspected but intentionally left unchanged when relevant.

### 5. Review-bundle design

Report:

* final command;
* bundle section order;
* task-contract source;
* completion-report handling;
* status collection;
* tracked-diff collection;
* untracked discovery;
* changed-file manifest;
* evidence manifest;
* SHA-256 and byte-size behavior;
* dynamic Markdown-fence behavior;
* point-in-time consistency checks.

### 6. Safety and failure behavior

Report:

* ignored-file policy;
* secret-path policy;
* private-key content policy;
* UTF-8 and NUL handling;
* binary detection;
* symlink and special-file handling;
* unmerged-state handling;
* per-file limit;
* tracked-diff limit;
* total-bundle limit;
* no-partial-output behavior.

### 7. Tests added or updated

List:

* focused test file;
* every behavioral category covered;
* any existing context-report tests changed;
* context-report regression result.

### 8. Verification results

For every required command, provide:

* exact command;
* success, failure, or not run;
* relevant output summary.

Include:

* focused review-bundle tests;
* context-report tests;
* complete pytest result;
* candidate bundle generation;
* final bundle generation;
* final bundle byte size;
* task, report, status, diff, and untracked evidence checks;
* read-only before/after status comparison;
* context-report command result;
* `/health`;
* `/ready`;
* `git diff --check`.

### 9. Documentation updates

State:

* what changed in `WORKFLOW.md`;
* what changed in README;
* the durable decision added;
* the current-state update;
* Task 005 status and completion evidence;
* whether `AGENTS.md` was changed;
* documents intentionally left unchanged.

### 10. Acceptance-criteria assessment

Evaluate each acceptance group as:

```text
passed
failed
not verified
```

Groups:

* command boundary;
* contract and report;
* Git evidence completeness;
* manifest and integrity;
* safety;
* point-in-time consistency;
* Task 004 separation;
* documentation;
* scope protection.

Explain every failure or unverified result.

### 11. Scope, deviations, and remaining risks

Report:

* out-of-scope work avoided;
* any unavoidable deviation;
* unsupported evidence types;
* anything not verified;
* any repository or report state that would require regenerating the final bundle.

### 12. Final Git boundary

Report:

* final branch;
* final HEAD;
* final `git status --short`;
* final `git diff --stat`;
* changed and untracked file list;
* whether a commit was created;
* recommended implementation commit message.

Unless explicitly instructed otherwise, state:

```text
No implementation commit was created.
```

The completion report must not claim that the bundler independently verified command results. It must distinguish:

* command results reported by Codex;
* Git evidence captured by the bundler;
* task requirements from the committed specification.

## Expected commit boundary

The accepted Task 005 specification should be committed separately before implementation.

After implementation review and any bounded corrections, the implementation commit should contain only:

* the review-bundle utility;
* focused review-bundle tests;
* narrowly necessary shared-helper changes;
* workflow documentation;
* README usage;
* the durable review-packaging decision;
* current-state update;
* Task 005 completion status and evidence;
* a minimal AGENTS or development-image adjustment only when justified.

It must not include:

* generated review bundles;
* `/tmp` completion reports;
* ignored local files;
* application changes;
* database changes;
* Telegram changes;
* future feature work;
* unrelated cleanup.

Suggested implementation commit message:

```text
chore: add implementation review bundles
```

Codex must not create the implementation commit unless explicitly instructed.

## Completion evidence

Completed on 2026-07-02 without creating an implementation commit.

* Added the standalone read-only `scripts/review_bundle.py` command and focused
  real-Git coverage in `tests/test_review_bundle.py` without changing the compact
  `scripts/project_context.py` command.
* Documented review generation and evidence precedence in `docs/WORKFLOW.md` and
  `README.md`, recorded D-024, and updated current semantic state.
* Verified 44 focused review-bundle tests, 10 project-context regression tests,
  and 69 tests in the complete authoritative Docker suite.
* Verified host-side compact-report generation, a complete review-bundle smoke
  generation, unchanged Git status across bundle generation, and successful
  `/health` and `/ready` checks.
* Kept application, database, migration, Telegram, worker, environment, and
  Dockerfile behavior unchanged.

## Amendment — tracked root environment template

Accepted on 2026-07-02 to resolve a conflict discovered while packaging Task
006. The repository establishes `.env.example` as its committed public
configuration template, and Task 006 requires updating it. The original broad
`.env.*` rejection therefore prevented a complete bundle of otherwise required
tracked evidence.

The bundler may capture the exact path `.env.example` only when it exists at
HEAD as a regular tracked Git blob and participates as tracked changed evidence.
It must not be ignored, and all ordinary tracked-evidence checks for Git type,
working-tree type, UTF-8, NUL bytes, private-key content, binary diff, size,
hashes, consistency, and repository mutation remain mandatory.

This is not a global secret-path allowlist. Root `.env`, every other root
`.env.*` name, nested `.env.example`, an untracked or newly staged
`.env.example` absent from HEAD, and a completion report named `.env.example`
remain rejected. No ignored-file override or command-line bypass is added.

The intended separate correction commit is:

```text
fix: allow tracked env example in review bundles
```

Correction verification passed 55 focused review-bundle tests and 146 tests in
the complete authoritative Docker suite. The corrected tool generated the
complete Task 006 implementation-review bundle without omitting or weakening
evidence checks.
