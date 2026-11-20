# Worktree first: no edits on the default branch

Date: 2026-11-20. Status: approved by user (worktree by default).

## Goal

Agents currently edit the main checkout on `main` and create the branch only at commit time (seen this session for the MVC and versioning work). Two requests running together would mix changes. Every request now gets its own git worktree on its own branch before the first edit, and a hook makes editing the default branch impossible.

## Rules (added to `skills/releasing/SKILL.md`, "Branches and PRs")

1. **Worktree by default.** Before the first edit of a request, create a worktree on a new branch:
   `git worktree add .worktrees/<slug> -b <type>/<slug> <default-branch>` from the main checkout, after `git fetch` and a fast-forward of the default branch.
2. **Location:** `.worktrees/<slug>` inside the repo, so subagents stay inside the session's working directory (no permission prompts). It is ignored through `.git/info/exclude` (local only; never edit the project's tracked `.gitignore` for this).
3. **Fallback: plain branch in the main checkout.** Allowed only when a worktree is impractical (e.g. heavy per-checkout installs, submodules that fail to init); the agent states the reason under Evidence. Editing the default branch is never allowed.
4. **Every brief after creation carries `Worktree: <path>` and `Branch: <name>`.** Agents run all commands (tests, git) and edit all files inside that path.
5. **Cleanup after merge** (part of the `Mode: git` merge task): `git worktree remove <path>` (no `--force`; if it refuses, report), `git branch -d <branch>` (never `-D`), then `--ff-only` the default branch in the main checkout.

## Who creates it

- **Plan lane:** the builder creates the worktree (via its first task agent, `Mode: git`, or itself) before task 1, then copies the untracked spec and plan from the main checkout into the worktree so they are committed with the work. Every task brief carries the `Worktree:`/`Branch:` lines. The final git task deletes the main checkout's untracked copies of that spec and plan (only after `git diff --no-index` shows them identical to the committed ones) before the `--ff-only` pull, which would otherwise refuse to overwrite them.
- **Quick lane:** the orchestrator's brief carries `Worktree: .worktrees/<slug>` and `Branch: <type>/<slug>`; the first agent creates it (step 1 of the brief). The verifier and the later `Mode: git` dispatch get the same lines.
- **Orchestrator:** still never runs git writes; it names the slug and branch in briefs. Specs and plans are still written in the main checkout (`docs/specs/`, `docs/plans/`), as today.

## Enforcement: hook `branch-guard`

PreToolUse on Edit, Write and NotebookEdit, **in subagents only** (payload has `agent_id`):

- Resolve the edited file's own checkout: `git -C <file's dir> rev-parse --show-toplevel` and `--abbrev-ref HEAD`.
- Deny when HEAD is the default branch. The default branch is `refs/remotes/origin/HEAD` if set, else `main` or `master` if that branch exists. Deny reason: "Create a worktree first: git worktree add .worktrees/<slug> -b <type>/<slug> (see foreman:releasing)."
- Allow: files outside any git repo; detached HEAD; files under `docs/specs/` and `docs/plans/` (specs and plans are drafted in the main checkout); paths under the user's memory dirs; `FOREMAN_SOLO=1`.
- Any git error or timeout (5 s) allows the edit; the hook never blocks on its own failure.
- Main-session edits stay covered by the existing `guard`.

## Hooks must resolve paths per worktree

Files edited in `.worktrees/<slug>/...` sit under the main checkout's root. Hooks that compute repo-relative paths (`trap_inject`, any scope logic) must use the file's own worktree toplevel, so memory `paths:` globs still match (`agents/x.md`, not `.worktrees/<slug>/agents/x.md`). Memory stays shared across worktrees (`project_dir` already uses the git common dir).

## Agent and skill text

- `skills/releasing/SKILL.md`: rules 1 to 5 above.
- `skills/orchestrating/SKILL.md` and the task brief template: `Worktree:` and `Branch:` lines; quick lane names them.
- `agents/builder.md`: creates the worktree before task 1, copies spec and plan, passes the lines to every task.
- `agents/implementer.md`, `agents/ui.md`, `agents/generalist.md`: work only inside the brief's `Worktree:` path; if a brief has edits but no worktree, create it first (quick lane) or report `BLOCKED: plan`.
- `agents/verifier.md`: run tests and `git diff` inside the worktree; fail `FAIL: impl` if the work's branch is the default branch.
- `ORCHESTRATOR_RULES`: fold "every brief that edits names `Worktree:` and `Branch:`" into an existing line (line cap is 15).
- README: "Branch guard" section next to "Orchestrator guard" and "Plan gate"; CHANGELOG `[Unreleased]` → Added.

## Security

- **No destructive cleanup:** `git worktree remove` without `--force`, `git branch -d` never `-D`; untracked spec/plan copies are deleted only after an identical-content check.
- **No changes to tracked ignore files:** the worktree dir is excluded via `.git/info/exclude` only.
- **Fail-open hook:** a git failure never blocks edits (availability over enforcement), and that case is covered by a test.
- **Path handling:** the hook resolves paths with `Path.resolve()` before comparing, so `..` segments or mixed slashes cannot slip a default-branch file past the check.
- Auth, secrets, input validation and data exposure: none applicable.

## Out of scope

- The Haiku git agent and the main-session git-read hook (option 2, separate spec).
- Codegraph indexing of worktrees (it indexes the main checkout; agents in a worktree use Read for their own edits).

## Acceptance

- `python -m pytest -q` passes, with tests for the branch-guard:
  - deny on the default branch in a subagent
  - allow on a feature branch
  - allow in a linked worktree
  - allow for docs/specs and docs/plans
  - allow outside git and on detached HEAD
  - allow when git fails
  - allow in the main session (left to `guard`)
  - `FOREMAN_SOLO=1`
- A worktree path test: `trap_inject` matches a memory `paths:` glob for a file under `.worktrees/<slug>/`.
- Skill and agent text tests: releasing names `git worktree add`, `.worktrees/`, `.git/info/exclude`, `git worktree remove`, `branch -d`. Builder, implementer and verifier reference `Worktree:`.
- The hook is registered in `hooks/hooks.json` for Edit|Write|NotebookEdit.
- This work itself is done in a worktree (`.worktrees/worktree-first`, branch `feat/worktree-first`).
