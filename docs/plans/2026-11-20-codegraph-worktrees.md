# Codegraph in worktrees Implementation Plan

> **For agentic workers:** Execute with the foreman loop (`foreman:orchestrating`). Tasks are sequential (0, 1, 2, 3). Task 0 is DONE (do not redo it). The verifier runs after tasks 1 and 2 and read-only after task 3. Task 0 and task 3 are `Mode: git`.

**Goal:** Keep codegraph correct inside worktrees: index a new worktree when the project already uses codegraph, query and sync that index through the codegraph CLI only (never the MCP `projectPath` on a worktree), uninit before removing the worktree, and keep `.worktrees/` out of the main index. Also fix the merge cleanup order so the remote branch is always deleted. Ship through a PR with no release cut and no tags.

**Spec:** `docs/specs/2026-11-20-codegraph-worktrees-design.md`

## Global Constraints

- **Worktree:** `.worktrees/codegraph-worktrees` (relative to the main checkout root; resolve it to an absolute path in briefs). **Branch:** `feat/codegraph-worktrees`. Tasks 1 to 3 carry `Worktree:` and `Branch:` lines; agents edit, test and run git only inside that path (task 1 uses its own scratch worktree, see there). Briefs for tasks 1 to 3 also carry `Plan: docs/plans/2026-11-20-codegraph-worktrees.md`.
- This plan file lives untracked in the main checkout (`docs/plans/`); the plan gate reads it from there. Task 0 copied it and the spec into the worktree; both changed afterwards (spec change after the task 1 probe), so the builder re-copies the current spec and plan from the main checkout into the worktree before task 3 (and before task 2 if it has not started), checks with `git diff --no-index` that both pairs are identical, then task 3 commits them.
- Follow `skills/releasing/SKILL.md` (Conventional Commits, named-file staging, no `--tags` / `--follow-tags`, GitHub Flow, worktree-first). No release cut, no version bump, no tags. The `[Unreleased]` → Added entry is written in task 2.
- Untracked files in the main checkout that are not part of this work (`.codegraph/`, `TODO.md`, `problems/`) are never copied, staged or deleted. The main checkout's `.codegraph/` is never uninit-ed and never re-indexed from scratch.
- Never edit the tracked `.gitignore` (spec rule 4). If the main index turns out to list `.worktrees/`, use `.git/info/exclude` if codegraph honours it, else codegraph's own config under `.codegraph/` (untracked); record which in Evidence.
- `ORCHESTRATOR_RULES` is capped at 15 lines and is at 15: this plan does not touch it.
- Agent files keep: `BLOCKED: plan`, `DISPUTE`, `docs/plans/`, the verdict strings, `## Evidence` / `## Unverified`, the MVC sentences, the changelog sentence, `Worktree:` lines, frontmatter (values containing `: ` stay quoted; `test_frontmatter_values_with_colon_space_are_quoted`).
- Cleanup order everywhere it is written (decision, one choice, no alternatives in the text): merge with `gh pr merge --merge` **without** `--delete-branch` (gh leaves the remote branch when a worktree has the local branch checked out); then `codegraph uninit -f <worktree>`; `git worktree remove <path>` without `--force`; `git branch -d <branch>`; then `git push origin --delete <branch>` (branch ref only, allowed; never a tag ref, never `--force`); then delete the untracked copies after the identical-content check, then `--ff-only`. If `uninit` or `git worktree remove` fails, report it and do not use `--force`. No daemon-stop step: `codegraph daemon` has no non-interactive stop and no per-worktree daemon is started (task 1 probe, 2026-11-20).
- **Codegraph in worktrees (spec rule 2):** inside a worktree use the codegraph CLI only (`codegraph explore`, `node`, `callers`, `sync`), with the worktree as the working directory. Never pass a worktree as the MCP `projectPath`: the long-running `codegraph serve --mcp` process keeps the DB open and locked, so `uninit` and `git worktree remove` fail with EPERM until that process exits. The MCP tool stays for the main checkout. The generalist (no Bash) uses Read only inside worktrees.
- Full suite: `python -m pytest -q` (inside the worktree) passes after task 2.

## Review Focus

1. Rule 1 is conditional: nothing is indexed unless the main checkout has `.codegraph/`.
2. `uninit` targets the worktree path only; the main `.codegraph/` survives the whole run.
3. The cleanup order in `skills/releasing/SKILL.md` is consistent in every line that mentions merge, delete branch or remove, and matches task 3.
4. The generalist is never told to run `codegraph sync` or to use MCP on a worktree; no text passes a worktree as `projectPath`.
5. No tracked ignore file changed.

---

### Task 0: Create the worktree and index it (DONE, PASSED; do not redo)

Status: done. `.worktrees/codegraph-worktrees` exists on `feat/codegraph-worktrees`; `codegraph init` took 2.45 s. The steps and acceptance below are kept as the record.

**Agent:** implementer
**Files:** none tracked. Creates `.worktrees/codegraph-worktrees` (branch `feat/codegraph-worktrees`); copies `docs/specs/2026-11-20-codegraph-worktrees-design.md` and `docs/plans/2026-11-20-codegraph-worktrees.md` into the worktree at the same paths; creates the worktree's own untracked `.codegraph/` via `codegraph init`.

Brief carries `Mode: git` and `Plan: docs/plans/2026-11-20-codegraph-worktrees.md`.

- [ ] **Step 1:** In the main checkout: `git fetch`, then `git merge --ff-only origin/main` (only untracked files exist, so this must succeed; if it refuses, stop and report, never reset).
- [ ] **Step 2:** If `.worktrees/` is not already a line in the file `git rev-parse --git-path info/exclude` names, append it. Do not touch the tracked `.gitignore`.
- [ ] **Step 3:** `git worktree add .worktrees/codegraph-worktrees -b feat/codegraph-worktrees main`.
- [ ] **Step 4:** Copy the spec and this plan from the main checkout into the worktree at the same relative paths.
- [ ] **Step 5 (first use of the new rule):** The main checkout has `.codegraph/`, so run `codegraph init -y <absolute worktree path>` and time it (for example `time codegraph init -y <path>` in Git Bash, or `Measure-Command` in PowerShell). Then `codegraph status <path>` and `git -C <path> status --short`. Record the duration and the file/symbol counts.

**Acceptance:**
- `git worktree list` shows `.worktrees/codegraph-worktrees` on `[feat/codegraph-worktrees]`; its `HEAD` equals `git rev-parse main`.
- `git status --short` in the main checkout does not list `.worktrees/` and still lists the untracked spec, plan, `.codegraph/`, `TODO.md`, `problems/`.
- `git diff --no-index` between each main-checkout copy and its worktree copy prints nothing.
- `<worktree>/.codegraph/` exists; `codegraph status <worktree>` reports an index with files; the init duration in seconds is stated under Evidence.
- The main checkout's `.codegraph/` was not touched (its `codegraph.db` mtime is unchanged by task 0, or state it was not re-indexed).
- Security: `git diff -- .gitignore` is empty and `git ls-files .gitignore` unchanged; no codegraph command targeted the main checkout with `uninit` or `index`.
- No commit, push or tag was made.

---

### Task 1: CLI-only lock check in a fresh scratch worktree (the one unproven check)

**Agent:** implementer
**Files:** none tracked. Creates and removes the scratch worktree `.worktrees/codegraph-lockcheck` (branch `probe/codegraph-lockcheck`, created from `main`, deleted with `git branch -d` at the end). Edits one function there and reverts it before removal.

Brief carries `Worktree:` (the task 0 worktree, for the report), `Branch:`, `Plan:` and the line `Mode: probe`. It must not depend on the earlier `.worktrees/codegraph-probe` (a separate cleanup dispatch removes it). **Never call the MCP `codegraph_explore` tool with this worktree as `projectPath`**; every codegraph command here is the CLI with the scratch worktree as the working directory (`cd` into it, or `git -C` for git).

Already proven, do not repeat (reuse as evidence in the report): probe init 1.73 s; after `codegraph sync`, CLI `codegraph explore` in the probe returned `raise ValueError("PROBE-EDIT unterminated quote")` while main returned the unedited line; `codegraph files` on main lists 0 `.worktrees` paths; `codegraph daemon` has no non-interactive stop and no per-worktree daemon was started.

- [ ] **Step 1:** In the main checkout: `git worktree add .worktrees/codegraph-lockcheck -b probe/codegraph-lockcheck main`; from inside it, `codegraph init -y`.
- [ ] **Step 2:** In the scratch worktree edit one string literal inside a function in `scripts/memory.py` (uncommitted). From inside it run `codegraph sync`, then CLI `codegraph explore "<that function name>"`. Quote the output (it must contain the edited line).
- [ ] **Step 3:** Revert the edit (`git -C <scratch> checkout -- scripts/memory.py`). From the main checkout run `codegraph uninit -f <abs scratch path>`; it must succeed (exit 0, no EPERM). Then `git worktree remove .worktrees/codegraph-lockcheck` without `--force`; it must succeed. Then `git branch -d probe/codegraph-lockcheck`. Quote each command's output and exit code.
- [ ] **Step 4:** If the CLI alone also leaves a lock (`uninit` or `worktree remove` fails with EPERM or similar), stop, do not use `--force`, and report `FAIL: spec` with the quoted error and the processes holding the DB if findable. Do not continue to task 2.
- [ ] **Step 5:** Check the main `.codegraph/` still exists and `codegraph status` works on it; `git worktree list` shows no `codegraph-lockcheck` entry.

**Acceptance:**
- Evidence quotes: the CLI `codegraph explore` output from the scratch worktree containing the edited line; the `codegraph uninit -f` output and exit code (0); the `git worktree remove` output and exit code (0, without `--force`); `git branch -d` output; `git worktree list` afterwards with no scratch entry.
- The MCP tool was never called with the scratch worktree as `projectPath` (state it).
- Security (no destructive cleanup): every `codegraph uninit` named the scratch path, none named the main checkout; the main `.codegraph/` still exists after the run.
- Security (no tracked-file changes for exclusion): `git diff -- .gitignore` is empty in the main checkout and both worktrees.
- `git status --short` in the task 0 worktree shows no tracked change from this task; the edit was reverted and never committed.
- Failure path: if the CLI leaves a lock, the report says `FAIL: spec` with the quoted error, and no `--force` was used.

---

### Task 2: Releasing rules, agent text, README, CHANGELOG, text tests (tests first)

**Agent:** implementer
**Files:** Modify `skills/releasing/SKILL.md`, `skills/orchestrating/SKILL.md`, `agents/builder.md`, `agents/implementer.md`, `agents/ui.md`, `agents/generalist.md`, `agents/verifier.md`, `README.md`, `CHANGELOG.md`; Test `tests/test_components.py`

Brief carries `Worktree:`, `Branch:` and `Plan:` lines. Rule text follows the updated spec (rule 2: CLI only; no daemon-stop step). Rule 4: the probe showed `codegraph files` on main lists 0 `.worktrees` paths, so no exclusion beyond task 0's `.git/info/exclude` line is needed; say the main index must not contain `.worktrees/` and the tracked `.gitignore` is never edited.

- [ ] **Step 1 (tests first):** In `tests/test_components.py` (which already has `_read` and the worktree tests) add:
  - `test_releasing_codegraph_rules`: `skills/releasing/SKILL.md` contains `codegraph init`, `codegraph sync`, `codegraph uninit`, `git push origin --delete`, a sentence that a worktree is never passed as `projectPath` (assert the exact phrase you write, for example ``never pass a worktree as `projectPath` ``), `codegraph explore` as the CLI run with the worktree as working directory, and a sentence that indexing happens only if the main checkout has `.codegraph/` (assert the exact phrase you write, for example `only if the main checkout has `.codegraph/``); it says a project without `.codegraph/` gets nothing; it says the main index must not contain `.worktrees/` and never edits the tracked `.gitignore` for it (reuse the existing phrase `tracked `.gitignore` is never edited`).
  - `test_releasing_cleanup_order`: in the cleanup rule, `gh pr merge --merge` appears and `--delete-branch` is not part of the cleanup command (assert the text states merge without `--delete-branch` and why: remote branch left while a worktree holds the local one); `daemon` does not appear in the cleanup rule; positions in the file text satisfy `codegraph uninit` < `git worktree remove` < `branch -d` < `git push origin --delete`; `--force` still never used and `never -D` still present; the line with the rule on the main-checkout `--ff-only` and the untracked-copy identical check is still there. Also assert the old contradictory sentence is gone: no remaining text says to `delete the branch after merge` in the PR rule without naming the order (match the exact new text you write).
  - `test_agents_codegraph_cli_only_in_worktrees`: `implementer`, `ui` and `verifier` contain `codegraph explore` and the never-`projectPath`-on-a-worktree rule (assert the exact phrase you write); `implementer` and `ui` contain `codegraph sync`; `generalist` states it uses Read only inside worktrees and never passes a worktree as `projectPath` (assert your phrase) and does not instruct `codegraph sync` (the substring may appear only inside a "does not run" sentence); `builder` and `implementer` contain `codegraph init`. Also assert the forbidden direction for every agent file and `skills/releasing/SKILL.md`: `projectPath` is forbidden for worktrees, so no line tells an agent to pass a worktree path as `projectPath` (every line containing `projectPath` and a worktree reference also contains `never`).
  - Keep the existing worktree and invariants tests green.
- [ ] **Step 2:** Run `python -m pytest tests/test_components.py -q` in the worktree; expected: the new tests FAIL (red). Paste the failure summary.
- [ ] **Step 3:** `skills/releasing/SKILL.md`, "Branches and PRs": add the codegraph rules next to the worktree rules, keeping the bullet style:
  1. **Index on creation, only if the project already uses codegraph:** only if the main checkout has `.codegraph/`, the agent that creates the worktree runs `codegraph init -y <worktree>` right after `git worktree add`; a project without `.codegraph/` gets nothing (indexing is the user's decision).
  2. **Query the worktree's index through the CLI only:** inside a worktree run `codegraph explore` (or `node`, `callers`) with the worktree as the working directory; never pass a worktree as `projectPath` to the MCP tool (the long-running MCP server keeps the DB locked and blocks `uninit` and `git worktree remove`; the MCP tool stays for the main checkout); after editing run `codegraph sync <worktree>` before the next query. Agents without Bash (the generalist) use Read only inside worktrees.
  3. **Keep the main index free of worktrees:** the main index must not list `.worktrees/` files (the probe found `codegraph files` on main lists none); if it ever does, exclude them via `.git/info/exclude` if codegraph honours it, else codegraph's own config; never the tracked `.gitignore`.
  4. **Cleanup order, replaces the existing "Cleanup after merge" bullet and the "delete the branch after merge" clause of the PR bullet so the text has one order:** in the `Mode: git` merge task: `gh pr merge --merge` without `--delete-branch` (never `--admin`; gh leaves the remote branch while a worktree holds the local one); `codegraph uninit -f <worktree>` (worktree path only, never the main checkout), only when the worktree has `.codegraph/`; `git worktree remove <path>` without --force; `git branch -d <branch>` (never -D); `git push origin --delete <branch>` (branch ref only; allowed, never a tag, never --force); then delete the main checkout's untracked spec and plan copies only if `git diff --no-index` shows them identical to the merged ones, and `--ff-only` the default branch there. If `uninit` or `git worktree remove` fails, report it and do not use `--force`.
  Keep: "Never force-push `main`. Ask the user first before `reset --hard`, `branch -D` or `clean -fdx`", the changelog and tag rules, "One PR per request. The full test suite passes before merge."
- [ ] **Step 4:** `skills/orchestrating/SKILL.md`: in the brief template, extend the `Worktree:` line comment to say it also tells the agent which directory to run the codegraph CLI from (`foreman:releasing`); never a worktree as MCP `projectPath`. Keep the main session on the main index. No other lane changes.
- [ ] **Step 5:** Agents. `builder.md`: when the main checkout has `.codegraph/`, the worktree creator also runs `codegraph init -y <worktree>` (through the plan's task 0 or itself). `implementer.md`: same for the quick-lane creator; use the CLI (`codegraph explore`) with the brief's `Worktree:` path as working directory, never as MCP `projectPath`; run `codegraph sync <worktree>` after edits before the next query; in a `Mode: git` merge brief follow the cleanup order (merge without `--delete-branch`, `codegraph uninit -f` on the worktree only, `git worktree remove` without `--force`, `branch -d`, then `git push origin --delete <branch>`). `ui.md`: CLI `codegraph explore` from the worktree plus `codegraph sync` after edits, never `projectPath` on a worktree. `generalist.md`: it has no Bash, so inside worktrees it uses Read only and never passes a worktree as `projectPath`; it does not run `codegraph sync`. `verifier.md`: query the worktree's index with the CLI from the worktree for read-only checks, never `projectPath`. Keep every invariant in Global Constraints; keep `generalist` free of Bash (the tools frontmatter is unchanged).
- [ ] **Step 6:** `README.md`: add one line to "Branch guard" (or its worktree sentence): when the main checkout has `.codegraph/`, each worktree gets its own codegraph index (`codegraph init`), queried through the codegraph CLI from the worktree (never the MCP `projectPath`) and removed with `uninit` before `git worktree remove`. No new section.
- [ ] **Step 7:** `CHANGELOG.md`: under `## [Unreleased]` → `### Added` add one behaviour line: worktrees get their own codegraph index when the project already uses codegraph, and cleanup uninits it before removing the worktree. Under `### Fixed` add one line: the merge cleanup deletes the remote branch when a worktree held the local one (merge without `--delete-branch`, then `git push origin --delete`). No secrets or private paths; no version bump.
- [ ] **Step 8:** Run `python -m pytest -q` in the worktree; expected: PASS.

**Acceptance:**
- `python -m pytest -q` passes; the three new tests were seen failing first (the third is `test_agents_codegraph_cli_only_in_worktrees`).
- `skills/releasing/SKILL.md` names `codegraph init` (with the "only if the main checkout has `.codegraph/`" condition), the never-`projectPath`-on-a-worktree rule, the CLI-only rule, `codegraph sync`, `codegraph uninit`, the main-index exclusion rule, and has exactly one cleanup order with `codegraph uninit` before `git worktree remove` and `git push origin --delete <branch>` after `branch -d`; no sentence in the file contradicts it (quote `grep -n "delete-branch\|origin --delete\|worktree remove\|uninit" skills/releasing/SKILL.md` under Evidence).
- Security (no destructive cleanup): the text restricts `codegraph uninit` to the worktree path, has no daemon-stop step, keeps `git worktree remove` without `--force` and `branch -d` never `-D`, and keeps the `reset --hard` / `branch -D` ask-first rule.
- Security (no tracked-file changes for exclusion): the text says the tracked `.gitignore` is never edited, and `git diff main..HEAD -- .gitignore` is empty.
- `implementer`, `ui`, `verifier` say CLI-only and never `projectPath` on a worktree; `generalist` says Read only inside worktrees; the generalist does not instruct `codegraph sync` and its frontmatter tools are unchanged; no file tells an agent to pass a worktree as `projectPath`; invariants intact in every agent file (`BLOCKED: plan`, `DISPUTE`, `docs/plans/`, verdict strings, `## Evidence`, `## Unverified`, MVC sentences, changelog sentence, frontmatter).
- `ORCHESTRATOR_RULES` unchanged and the 15-line cap test passes (`git diff main..HEAD -- scripts/foreman_hooks.py` is empty).
- README has the one codegraph line; `CHANGELOG.md` has one Added entry and one Fixed entry under `[Unreleased]`, no version bump.
- `git diff --name-only main..HEAD` (plus uncommitted changes) lists only the Files above plus the `docs/specs` and `docs/plans` copies from task 0.

---

### Task 3: Commit, push, PR, merge, cleanup in the new order

**Agent:** implementer
**Files:** none edited. Git only: commits of the worktree's changed files (`skills/releasing/SKILL.md`, `skills/orchestrating/SKILL.md`, `agents/builder.md`, `agents/implementer.md`, `agents/ui.md`, `agents/generalist.md`, `agents/verifier.md`, `README.md`, `CHANGELOG.md`, `tests/test_components.py`, `docs/specs/2026-11-20-codegraph-worktrees-design.md`, `docs/plans/2026-11-20-codegraph-worktrees.md`); deletes the main checkout's untracked spec and plan copies.

Brief carries `Mode: git`, `Worktree:`, `Branch:` and `Plan:` lines. Never use the MCP `codegraph_explore` with the worktree as `projectPath` (it would lock the DB again). Intent for the brief: stage the files above by name, commit, push the branch, open a PR, merge, clean up in the order below.

- [ ] **Step 0 (re-sync, before anything else):** the spec and this plan changed after task 0. Copy the current `docs/specs/2026-11-20-codegraph-worktrees-design.md` and `docs/plans/2026-11-20-codegraph-worktrees.md` from the main checkout over the worktree copies, then `git diff --no-index` each pair and confirm both print nothing. (If task 2 has not started, do this before task 2 instead.)
- [ ] **Step 1:** In the worktree run `python -m pytest -q`; it must pass before anything is committed. Stage by name only (never `git add -A` / `git add .`; the worktree's untracked `.codegraph/` stays unstaged). Conventional Commits, summary at most 72 chars, for example `docs(releasing): codegraph per worktree and cleanup order` (skills, agents, README, CHANGELOG, tests) and `docs(plans): add codegraph-worktrees spec and plan`. End each message with the attribution line from the session's system reminder.
- [ ] **Step 2:** `git push -u origin feat/codegraph-worktrees` (branch only; no `--tags`, no `--follow-tags`, no force). `gh pr create` (Conventional Commit title; body states what and why, test result, no release cut).
- [ ] **Step 3:** From the main checkout run `gh pr merge --merge` (never `--admin`, no `--delete-branch`; the branch is held by the worktree).
- [ ] **Step 4 (cleanup, in this order):** (a) `codegraph uninit -f <abs worktree path>` (CLI, never the main checkout); (b) `git worktree remove .worktrees/codegraph-worktrees` without `--force` (if it refuses, stop and report, never force); (c) `git branch -d feat/codegraph-worktrees` (never `-D`; if `-d` refuses only because the main checkout is not yet fast-forwarded, do step 5 and retry `-d`); (d) `git push origin --delete feat/codegraph-worktrees` (branch ref only). If (a) fails, report it and do not continue to (b).
- [ ] **Step 5:** `git fetch`. For each of the spec and plan, save the merged version (`git show origin/main:<path>` into a temp file outside the repo) and run `git diff --no-index <temp> <main-checkout copy>`. Only when both print nothing, delete the two untracked copies in the main checkout (nothing else), then `git merge --ff-only origin/main`. If any diff is non-empty, delete nothing and report.
- [ ] **Step 6:** Report the PR URL, merge commit SHA, the final `git status --short`, `git worktree list`, and `codegraph status` on the main checkout.

**Acceptance:**
- Every commit message follows Conventional Commits and files were staged by name; `git log --stat origin/main -5` shows only the Files above.
- `git ls-remote --tags origin` shows no new tag; `git tag --list` unchanged; the push used the branch ref only.
- PR merged with a merge commit (`gh pr view --json state,mergeCommit`), `--admin` and `--delete-branch` unused, remote branch gone (`git ls-remote --heads origin feat/codegraph-worktrees` empty after step (d)).
- Security (no destructive cleanup): the command log shows `codegraph uninit -f <worktree path>` before `git worktree remove`, which ran without `--force`; `git branch -d` without `-D`; `uninit` never named the main checkout; the two untracked copies were deleted only after `git diff --no-index` printed nothing for both.
- Security (tracked ignore files): `git log -1 -- .gitignore` is not in the merged PR's commit range.
- Main checkout: `git rev-parse main` equals `git rev-parse origin/main`; `git worktree list` shows only the main checkout; `git branch --list feat/codegraph-worktrees` is empty; `.codegraph/` (still indexed, `codegraph status` works), `TODO.md`, `problems/` exist untouched; `codegraph files` on main lists no `.worktrees/` path.
- The spec and plan are tracked in main (`git ls-files docs/specs/2026-11-20-codegraph-worktrees-design.md docs/plans/2026-11-20-codegraph-worktrees.md`).
- No release cut: `CHANGELOG.md` still has the entries under `[Unreleased]`, no version file changed.
- The verifier then runs read-only over the final state and quotes the above.
