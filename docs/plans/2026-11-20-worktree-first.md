# Worktree first Implementation Plan

> **For agentic workers:** Execute with the foreman loop (`foreman:orchestrating`). Tasks are sequential (0, 1, 2, 3). The verifier runs after tasks 0, 1 and 2 (changed files) and read-only after task 3. Task 0 and task 3 are `Mode: git`.

**Goal:** Every request gets its own git worktree and branch before the first edit, and a `branch-guard` hook denies subagent edits on the default branch. Add the rules to the `releasing` skill, wire the agents, make `trap_inject` resolve repo-relative paths per worktree, document it, and ship it through a PR with no release cut and no tags.

**Spec:** `docs/specs/2026-11-20-worktree-first-design.md`

## Global Constraints

- **Worktree:** `.worktrees/worktree-first` (relative to the main checkout root; resolve it to an absolute path in briefs). **Branch:** `feat/worktree-first`. Tasks 1 to 3 carry `Worktree:` and `Branch:` lines; agents edit, test and run git only inside that path. Briefs for tasks 1 to 3 also carry `Plan: docs/plans/2026-11-20-worktree-first.md`.
- This plan file lives untracked in the main checkout (`docs/plans/`); the plan gate reads it from there. Task 0 copies it and the spec into the worktree; task 3 commits them.
- Follow `skills/releasing/SKILL.md` for this work (Conventional Commits, named-file staging, no `--tags` / `--follow-tags`, GitHub Flow). No release cut, no version bump, no tags. The `[Unreleased]` → Added entry is written in task 1.
- Untracked files in the main checkout that are not part of this work (`.codegraph/`, `TODO.md`, `problems/`) are never copied, staged or deleted.
- `ORCHESTRATOR_RULES` is capped at 15 lines (`test_orchestrator_rules_cover_bugs_within_line_cap`) and is at 15 now: fold the new text into an existing line, add no line.
- Agent files keep: `BLOCKED: plan`, `DISPUTE`, `docs/plans/`, the verdict strings, `## Evidence` / `## Unverified`, the MVC sentences, the changelog sentence, frontmatter (values containing `: ` stay quoted; `test_frontmatter_values_with_colon_space_are_quoted`).
- The hook fails open: every git error or timeout allows the edit.
- Plan revisions after task 0 (FAIL: plan) are written to the main-checkout copy, which the plan gate reads. Before task 3 the builder copies the current spec and plan into the worktree again, so the identical-content check in task 3 step 5 can pass.
- Full suite: `python -m pytest -q` (run inside the worktree) passes after tasks 1 and 2.
- Hook tests use `tests/conftest.py::run_hook` and real `git` repos in `tmp_path`. Make an initial commit with `git -c user.name=t -c user.email=t@t commit --allow-empty -q -m init` (an unborn branch has no default branch to match). Create the default branch explicitly with `git init -q -b main`.
- Do not claim a new hook-latency measurement in the README; the branch-guard adds one more `uv run` launch on Edit/Write and that is stated as unmeasured, or left out.

## Review Focus

1. The hook denies only in subagents, only when the edited file's own checkout is on the default branch, and never blocks on its own failure.
2. `trap_inject` uses the edited file's own toplevel, so a memory `paths:` glob matches `src/a.py` for `.worktrees/<slug>/src/a.py`.
3. Cleanup never uses `--force` or `-D`, and the main checkout's untracked spec and plan copies are deleted only after an identical-content check.
4. `.worktrees/` is excluded through `.git/info/exclude` only; tracked `.gitignore` is untouched.

---

### Task 0: Create the worktree

**Agent:** implementer
**Files:** none tracked. Creates `.worktrees/worktree-first` (branch `feat/worktree-first`); appends `.worktrees/` to `.git/info/exclude` (local, untracked); copies `docs/specs/2026-11-20-worktree-first-design.md` and `docs/plans/2026-11-20-worktree-first.md` into the worktree at the same paths.

Brief carries `Mode: git` and `Plan: docs/plans/2026-11-20-worktree-first.md`.

- [ ] **Step 1:** In the main checkout: `git fetch`, then `git merge --ff-only origin/main` (only untracked files exist, so this must succeed; if it refuses, stop and report, never reset).
- [ ] **Step 2:** If `.worktrees/` is not already a line in the file `git rev-parse --git-path info/exclude` names, append it. Do not touch the tracked `.gitignore`.
- [ ] **Step 3:** `git worktree add .worktrees/worktree-first -b feat/worktree-first main`.
- [ ] **Step 4:** Copy the spec and this plan from the main checkout into the worktree at the same relative paths (create `docs/specs` and `docs/plans` there if needed; they already exist in the tracked tree).

**Acceptance:**
- `git worktree list` shows `.worktrees/worktree-first` on `[feat/worktree-first]`; `git -C .worktrees/worktree-first rev-parse HEAD` equals `git rev-parse main`.
- `git status --short` in the main checkout does not list `.worktrees/` (excluded) and still lists the untracked spec, plan, `.codegraph/`, `TODO.md`, `problems/`.
- `git diff --no-index` between each main-checkout copy and its worktree copy prints nothing (identical).
- `git ls-files .gitignore` is unchanged and `git diff -- .gitignore` is empty (Security: no changes to tracked ignore files); the exclude line lives in `.git/info/exclude`.
- No commit, push or tag was made.

---

### Task 1: Branch guard hook, per-worktree trap paths, changelog entry (tests first)

**Agent:** implementer
**Files:** Modify `scripts/foreman_hooks.py` (new `branch_guard`, `HOOKS` entry, `trap_inject` root resolution), `hooks/hooks.json`, `CHANGELOG.md`; Test `tests/test_branch_guard.py` (create), `tests/test_context_hooks.py` (worktree trap test), `tests/test_dispatch.py` only if it enumerates the hooks or `hooks.json` entries (inspect it first; extend it only if it does)

Brief carries `Worktree:`, `Branch:` and `Plan:` lines; all work happens inside the worktree.

- [ ] **Step 1 (tests first):** Create `tests/test_branch_guard.py` with a helper that makes a repo (`git init -q -b main`, initial commit) and calls `run_hook("branch-guard", payload, env)` with `FOREMAN_HOME` pointing into `tmp_path` and `FOREMAN_SOLO` empty. Payloads are `{"cwd": ..., "tool_name": "Edit", "tool_input": {"file_path": ...}, "agent_id": "a1"}` unless stated. Tests:
  - deny: subagent edits `src/app.py` while HEAD is `main`; output is `permissionDecision: deny` with a reason containing `git worktree add .worktrees/<slug> -b <type>/<slug>` and `foreman:releasing`; also deny when the edit is `Write` of a not-yet-existing file in an existing dir, and for `NotebookEdit` (`notebook_path`).
  - deny uses `refs/remotes/origin/HEAD` when set (create it with `git symbolic-ref refs/remotes/origin/HEAD refs/remotes/origin/trunk` after creating `refs/remotes/origin/trunk` and a branch `trunk` checked out): HEAD `trunk` is denied, HEAD `main` is then allowed. If this is too fiddly with plain git, cover origin/HEAD with an in-process test that imports `foreman_hooks` (conftest puts `scripts/` on `sys.path`).
  - default branch `master` is used when only `master` exists.
  - allow: HEAD on `feat/x`; a file in a real linked worktree created with `git worktree add <repo>/.worktrees/x -b feat/x` (cwd = main checkout on `main`, file under `.worktrees/x/`; the file's own checkout is the feature branch, so allow); detached HEAD; file outside any git repo; `docs/specs/s.md` and `docs/plans/p.md` on `main`; a path under the user's memory dir; `FOREMAN_SOLO=1`; main session (no `agent_id`) on `main`, which is left to `guard`.
  - path handling (Security): `docs/specs/../../src/x.py`, `docs/plansX/a.py` and `docs-evil/specs/x.md` are still denied on `main`; a backslash-mixed absolute path to a default-branch file is denied; a `..` path from a feature-branch worktree into the main checkout's file is denied (the file's own checkout is `main`).
  - fail-open (Security): in-process test that monkeypatches `subprocess.run` in `foreman_hooks` and `memory` to raise `OSError` and `subprocess.TimeoutExpired`, and a nonzero-return fake; each time `branch_guard(payload)` returns `None`. Also an out-of-process test with a payload whose cwd is not a directory, and invalid JSON stdin, both exit 0 with empty stdout (existing `main()` fail-open).
  In `tests/test_context_hooks.py` add a test that creates a repo with a commit, a linked worktree `.worktrees/x`, a trap memory entry with `paths: ["src/**/*.py"]` (use the existing `_user`, `write` and `_edit` helpers), and asserts `trap_inject` for `<repo>/.worktrees/x/src/a.py` with cwd the main checkout returns the trap text; and returns `None` for a file outside any git repo.
- [ ] **Step 2:** Run `python -m pytest tests/test_branch_guard.py tests/test_context_hooks.py -q`; expected: new tests FAIL (red). Paste the failure summary.
- [ ] **Step 3:** In `scripts/foreman_hooks.py` add `branch_guard(payload)` and register `"branch-guard"` in `HOOKS`:
  - return `None` if `"agent_id"` not in payload or `FOREMAN_SOLO == "1"`;
  - take `file_path` or `notebook_path`; resolve with `(cwd / raw.replace("\\", "/")).resolve()`; walk up to the nearest existing directory; all git calls use that directory as `cwd=`, `timeout=5`, `capture_output=True`, and any `OSError`, `subprocess.TimeoutExpired` or nonzero return means allow (`None`);
  - toplevel via `git rev-parse --show-toplevel` (none: allow); current branch via `git symbolic-ref --short -q HEAD` (detached or unborn: allow); default branch via `git symbolic-ref --short -q refs/remotes/origin/HEAD` with the `origin/` prefix stripped, else `main` then `master` when `git show-ref --verify --quiet refs/heads/<name>` succeeds, else allow;
  - allow when `path` is under `<toplevel>/docs/specs` or `<toplevel>/docs/plans`, or under `memory.user_dir()` or `memory.project_dir(cwd)` (use the existing `_under`, which normalises case; compare resolved paths only);
  - deny with `_deny(BRANCH_DENY)` when the current branch equals the default branch, where `BRANCH_DENY = "Create a worktree first: git worktree add .worktrees/<slug> -b <type>/<slug> (see foreman:releasing)."`
  Change `trap_inject` to compute `root` from the edited file's nearest existing directory (`memory._toplevel(<that dir>)`) instead of the session cwd; keep the "outside any repo returns `None`" behaviour and keep `_traps(cwd, [rel])` using the session cwd for memory layers.
- [ ] **Step 4:** In `hooks/hooks.json` add a `PreToolUse` entry, matcher `Edit|Write|NotebookEdit`, running `branch-guard` with the same `command`, `commandWindows` and `timeout: 30` shape as the `guard` entry (JSON must stay valid; `|| true` and `try/catch ... exit 0` wrappers kept). Add a test (in `tests/test_branch_guard.py`) that loads `hooks/hooks.json`, finds the `branch-guard` command and asserts its matcher is `Edit|Write|NotebookEdit` and that `"branch-guard"` is a key of `foreman_hooks.HOOKS`.
- [ ] **Step 5:** In `CHANGELOG.md` under `## [Unreleased]` add `### Added` (above the existing `### Fixed`) with one behaviour line: every request works in its own git worktree and branch, and a branch guard denies subagent edits on the default branch (fails open). No secrets or private paths.
- [ ] **Step 6:** Run `python -m pytest -q`; expected: PASS.

**Acceptance:**
- `python -m pytest -q` passes in the worktree; the new tests were seen failing first.
- Tests cover and pass for: deny on the default branch in a subagent; allow on a feature branch; allow in a linked worktree; allow for `docs/specs` and `docs/plans`; allow outside git and on detached HEAD; allow when git fails (OSError, timeout, nonzero); allow in the main session; `FOREMAN_SOLO=1`; memory paths allowed.
- Path handling (Security): `Path.resolve()` is applied before any comparison; tests with `..` segments and mixed slashes prove a default-branch file cannot slip past.
- Fail-open (Security): a git failure or timeout never blocks the edit, covered by a test.
- `trap_inject` test: a memory `paths: src/**/*.py` trap matches a file under `.worktrees/<slug>/src/`.
- `hooks/hooks.json` is valid JSON and registers `branch-guard` for `Edit|Write|NotebookEdit`.
- Adds an [Unreleased] entry under Added in `CHANGELOG.md`; no version bump.
- `git diff --name-only main..HEAD` (plus uncommitted changes) lists only the Files above.
- No tracked ignore file changed; no `--force`, `-D`, `--tags` in anything added.

---

### Task 2: Releasing rules, agent and skill text, README, text tests

**Agent:** implementer
**Files:** Modify `skills/releasing/SKILL.md`, `skills/orchestrating/SKILL.md`, `agents/builder.md`, `agents/implementer.md`, `agents/ui.md`, `agents/generalist.md`, `agents/verifier.md`, `scripts/foreman_hooks.py` (`ORCHESTRATOR_RULES` text only), `README.md`; Test `tests/test_components.py`, `tests/test_context_hooks.py`

Brief carries `Worktree:`, `Branch:` and `Plan:` lines. `CHANGELOG.md` was handled in task 1 and is not touched again.

- [ ] **Step 1 (tests first):** In `tests/test_components.py` add:
  - `test_releasing_worktree_rules`: `skills/releasing/SKILL.md` contains `git worktree add`, `.worktrees/`, `.git/info/exclude`, `git worktree remove`, `branch -d`, `Worktree:` and `Branch:`; it states `--force` is not used and `-D` is never used (assert the words `no --force` or `without --force`, and `never -D`, matching the exact text you write); it says the tracked `.gitignore` is not edited; it names the fallback (plain branch in the main checkout, reason under Evidence) and says editing the default branch is never allowed.
  - `test_agents_reference_worktree`: `builder`, `implementer` and `verifier` contain `Worktree:`; `ui` and `generalist` contain `Worktree:` too; `skills/orchestrating/SKILL.md` contains `Worktree:` and `Branch:` (in the brief template and the quick lane).
  - `test_verifier_fails_default_branch`: verifier text mentions the default branch together with `FAIL: impl`.
  - Keep the existing invariants tests green (`test_agents_reference_changelog_rule`, `test_task_agents_scope_and_dispute`, `test_agents_follow_mvc_layering`, frontmatter tests).
  In `tests/test_context_hooks.py` add `test_orchestrator_rules_name_worktree_and_branch`: `ORCHESTRATOR_RULES` contains `Worktree:` and `Branch:`, and the existing `<= 15` line-cap test stays unchanged and passing.
- [ ] **Step 2:** Run `python -m pytest tests/test_components.py tests/test_context_hooks.py -q`; expected: new tests FAIL (red).
- [ ] **Step 3:** `skills/releasing/SKILL.md`, section "Branches and PRs": add rules 1 to 5 from the spec: worktree by default (`git worktree add .worktrees/<slug> -b <type>/<slug> <default-branch>` from the main checkout after `git fetch` and a fast-forward of the default branch); location and `.git/info/exclude` (never the tracked `.gitignore`); fallback plain branch with the reason under Evidence, never the default branch; every brief after creation carries `Worktree: <path>` and `Branch: <name>` and agents run everything inside that path; cleanup after merge (`git worktree remove <path>` without `--force`, report if it refuses; `git branch -d`, never `-D`; then `--ff-only` the default branch in the main checkout, after deleting the main checkout's untracked spec/plan copies only if `git diff --no-index` shows them identical to the merged ones). Keep the existing rules (changelog, tags, "Never commit directly to `main`"), and keep "Ask the user first before `reset --hard`, `branch -D` or `clean -fdx`".
- [ ] **Step 4:** `skills/orchestrating/SKILL.md`: add `Worktree: <path>` and `Branch: <type>/<slug>` lines to the task brief template (required for every brief that edits or runs git, after the worktree exists); in the quick lane say the brief names `Worktree: .worktrees/<slug>` and `Branch: <type>/<slug>`, the first agent creates it as step 1, and the verifier and the later `Mode: git` dispatch get the same lines; in the plan lane say the builder creates the worktree before task 1 and copies the untracked spec and plan; the orchestrator still never runs git writes and writes specs and plans in the main checkout.
- [ ] **Step 5:** Agents. `builder.md`: create the worktree before task 1 (through a first `Mode: git` task agent, the plan's task 0, or itself if it has the tools), copy the spec and plan, and pass `Worktree:` and `Branch:` to every task and verifier brief. `implementer.md`, `ui.md`, `generalist.md`: work only inside the brief's `Worktree:` path; if a brief has edits but no `Worktree:`, create it first in the quick lane or report `BLOCKED: plan` (generalist has no Bash: it reports `BLOCKED: plan` instead of creating one). `implementer.md` also: a `Mode: git` brief never uses `--force` on `git worktree remove` and never `git branch -D`. `verifier.md`: run tests and `git diff` inside the worktree; `FAIL: impl` if the work's branch is the default branch. Keep every invariant listed in Global Constraints.
- [ ] **Step 6:** `ORCHESTRATOR_RULES` in `scripts/foreman_hooks.py`: fold "every brief that edits names `Worktree:` and `Branch:`" into an existing line (for example the plan-lane or the "Plans written by the planner" line); do not add a line.
- [ ] **Step 7:** `README.md`: add a "Branch guard" section between "Orchestrator guard" and "Search guard" (or next to "Plan gate"): PreToolUse on `Edit|Write|NotebookEdit`, subagents only, denies when the edited file's own checkout is on the default branch (`origin/HEAD`, else `main` or `master`), allows `docs/specs/`, `docs/plans/`, memory folders, detached HEAD, files outside git and `FOREMAN_SOLO=1`, fails open on any git error or a 5 s timeout; one line on the worktree convention (`.worktrees/<slug>`, excluded via `.git/info/exclude`). Mention in "Layout" or "Agents" only if those sections already list hooks or skills in a way that needs the new hook.
- [ ] **Step 8:** Run `python -m pytest -q`; expected: PASS.

**Acceptance:**
- `python -m pytest -q` passes in the worktree; the new text tests were seen failing first.
- `skills/releasing/SKILL.md` names `git worktree add`, `.worktrees/`, `.git/info/exclude`, `git worktree remove`, `branch -d`; states no `--force` and never `-D`, and that the tracked ignore file is never edited (Security: no destructive cleanup, no tracked-ignore changes); the untracked spec/plan copies are deleted only after an identical-content check.
- `builder`, `implementer`, `verifier` (and `ui`, `generalist`, orchestrating skill) reference `Worktree:`; verifier text fails a default-branch work branch with `FAIL: impl`.
- `ORCHESTRATOR_RULES` has at most 15 lines and names `Worktree:` and `Branch:`.
- Invariants intact in every agent file: `BLOCKED: plan`, `DISPUTE`, `docs/plans/`, verdict strings, `## Evidence`, `## Unverified`, the MVC sentences, the changelog sentence, frontmatter.
- README has a "Branch guard" section that matches the hook behaviour built in task 1.
- `git diff --name-only main..HEAD` lists only task 1 and task 2 Files (plus `docs/specs`, `docs/plans` copies from task 0).

---

### Task 3: Commit, push, PR, merge, cleanup

**Agent:** implementer
**Files:** none edited. Git only: commits of the worktree's changed files (`scripts/foreman_hooks.py`, `hooks/hooks.json`, `CHANGELOG.md`, `tests/test_branch_guard.py`, `tests/test_context_hooks.py`, `tests/test_components.py`, `skills/releasing/SKILL.md`, `skills/orchestrating/SKILL.md`, `agents/builder.md`, `agents/implementer.md`, `agents/ui.md`, `agents/generalist.md`, `agents/verifier.md`, `README.md`, `docs/specs/2026-11-20-worktree-first-design.md`, `docs/plans/2026-11-20-worktree-first.md`, and `tests/test_dispatch.py` only if task 1 changed it); deletes the main checkout's untracked spec and plan copies.

Brief carries `Mode: git`, `Worktree:`, `Branch:` and `Plan:` lines. Intent for the brief: stage the files above by name, commit, push the branch, open a PR, merge, clean up.

- [ ] **Step 1:** In the worktree run `python -m pytest -q`; it must pass before anything is committed. Stage by name only (never `git add -A` / `git add .`), in Conventional Commits, summary at most 72 chars, e.g. `feat(hooks): add branch-guard and per-worktree trap paths` (scripts, hooks, tests, CHANGELOG), `docs(releasing): worktree-first rules and agent wiring` (skills, agents, README, text tests), `docs(plans): add worktree-first spec and plan`. End each message with the attribution line from the session's system reminder.
- [ ] **Step 2:** `git push -u origin feat/worktree-first` (branch only; no `--tags`, no `--follow-tags`, no tag refs, no force). Open the PR with `gh pr create` (title in Conventional Commit style; body states what and why, test result, no release cut).
- [ ] **Step 3:** From the main checkout run `gh pr merge --merge --delete-branch` (never `--admin`). If gh cannot delete the local branch because the worktree has it checked out, report that line and carry on; the remote branch must be deleted.
- [ ] **Step 4:** `git worktree remove .worktrees/worktree-first` (no `--force`; if it refuses, stop and report, never force). Then `git branch -d feat/worktree-first` (never `-D`). If `-d` refuses only because the main checkout is not yet fast-forwarded, do step 5 and retry `-d`; do not switch to `-D`.
- [ ] **Step 5:** `git fetch`. For each of the spec and plan, save the merged version (`git show origin/main:<path>` into a temp file outside the repo) and run `git diff --no-index <temp> <main-checkout copy>`. Only when both print nothing, delete the two untracked copies in the main checkout (nothing else), then `git merge --ff-only origin/main` (or `git pull --ff-only`). If any diff is non-empty, delete nothing and report.
- [ ] **Step 6:** Report the PR URL, merge commit SHA and the final `git status --short` and `git worktree list`.

**Acceptance:**
- Every commit message follows Conventional Commits and files were staged by name; `git log --stat origin/main -5` shows only the Files above.
- `git ls-remote --tags origin` shows no new tag; no tag was created locally (`git tag --list` unchanged); push used the branch ref only.
- PR is merged with a merge commit (`gh pr view --json state,mergeCommit`), `--admin` unused, remote branch gone (`git ls-remote --heads origin feat/worktree-first` empty).
- Security (no destructive cleanup): `git worktree remove` ran without `--force`, `git branch -d` without `-D`; the two untracked copies were deleted only after `git diff --no-index` printed nothing for both.
- Security (tracked ignore files): `git log -1 -- .gitignore` is not the merged PR's commit range (the PR did not modify `.gitignore`).
- Main checkout: `git rev-parse main` equals `git rev-parse origin/main`; `git worktree list` shows only the main checkout; `git branch --list feat/worktree-first` is empty; `.codegraph/`, `TODO.md`, `problems/` still exist untouched.
- The spec and plan exist as tracked files in main (`git ls-files docs/specs/2026-11-20-worktree-first-design.md docs/plans/2026-11-20-worktree-first.md`).
- No release cut: `CHANGELOG.md` still has the entry under `[Unreleased]`, no version file changed.
