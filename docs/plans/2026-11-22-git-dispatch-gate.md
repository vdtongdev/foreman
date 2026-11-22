# Git dispatch gate - plan

Spec: docs/specs/2026-11-22-git-dispatch-gate-design.md
Worktree: .worktrees/git-dispatch-gate
Branch: fix/git-dispatch-gate

Test command for every task: `python -m pytest -q`. In the worktree use the codegraph CLI with the worktree as working directory; never pass the worktree as MCP `projectPath`.

### Task 0: Worktree
**Agent:** implementer
**Mode:** git
**Files:** (none edited) .worktrees/git-dispatch-gate, docs/specs/2026-11-22-git-dispatch-gate-design.md, docs/plans/2026-11-22-git-dispatch-gate.md
Steps: update main (`git fetch`, fast-forward main), `git worktree add .worktrees/git-dispatch-gate -b fix/git-dispatch-gate main`, copy the untracked spec and this plan from the main checkout into the same paths in the worktree, then `codegraph init -y .worktrees/git-dispatch-gate` (main checkout has `.codegraph/`).
Acceptance:
- `git worktree list` shows `.worktrees/git-dispatch-gate` on `fix/git-dispatch-gate`, branched from the up-to-date main tip.
- The spec and this plan exist inside the worktree.
- `.worktrees/git-dispatch-gate/.codegraph/` exists.
- No commit is made and nothing is pushed.

### Task 1: Failing tests for the git gate and rules (TDD red)
**Agent:** implementer
**Files:** tests/test_plan_gate.py, tests/test_context_hooks.py
Write the tests first; run them and confirm the new ones fail for the right reason (gate still returns early; rules and docs lack the text).
- `tests/test_plan_gate.py`: replace `test_allows_git_mode` (line 64-67; the generalist git brief must now deny). Add cases using a helper that builds a full git brief (`Mode: git`, `Worktree: .worktrees/x`, `Branch: fix/x`, `## Memory\nnone`):
  - implementer + full brief passes (None).
  - missing `Worktree:`, missing `Branch:`, missing `## Memory` each deny; empty value (`Worktree:` with nothing) denies; each deny reason differs and names the missing item and `foreman:releasing`.
  - each commit-message pattern denies: `-m "`, `-m '`, `--message`, a `Commit message:` line (any case); each reason names the forbidden item and `foreman:releasing`.
  - `Mode: git` to `foreman:generalist`, `general-purpose` and `claude` denies (reason names `foreman:implementer`).
  - nested (`agent_id`) and `FOREMAN_SOLO=1` pass; `Mode: gitfoo` and "see Mode: git" still deny with the plan-gate reason; `Mode: diagnose` unchanged.
  - Security: no deny reason contains a sentinel string placed in the prompt (reasons do not echo the prompt); non-string `prompt` and `subagent_type` (5, list) do not crash (rc 0) and deny/behave as empty; a hook exception still exits 0 (fails open) using the existing `run_hook` harness.
- `tests/test_context_hooks.py`: keep `test_orchestrator_rules_git_reads_only` (still `Mode: git` and `git read`); add asserts for `foreman:releasing` load before first git dispatch, no commit message in the brief, `gh pr merge --merge`, no size exemptions; keep the `<= 15` line cap test (rules must fit).
(`tests/test_components.py` assertions are written in Task 3, together with the doc change they check.)
Acceptance:
- New and changed tests exist covering every `plan_gate` and `ORCHESTRATOR_RULES` case in the spec's Acceptance section and every Security bullet.
- `python -m pytest -q` shows the new tests failing and no other test newly failing.
- Output excerpt of the failures is reported as evidence.
- No `CHANGELOG.md` change needed (tests only).

### Task 2: Implement the gate and the rules (TDD green)
**Agent:** implementer
**Files:** scripts/foreman_hooks.py, CHANGELOG.md
- `plan_gate` (lines 111-137): remove `git` from the early-return regex at line 118 (keep `diagnose` and `READ_ONLY`). After the nested/solo bail-out, if the prompt matches `^Mode:\s*git\b` (re.I | re.M), run a git check returning `_deny(...)` for the first failure: agent is not `foreman:implementer`; no non-empty `^Worktree:\s*\S` line; no non-empty `^Branch:\s*\S` line; no `^## Memory` heading; dictated commit message (`-m "`, `-m '`, `--message`, line starting `Commit message:`, case-insensitive). Otherwise return None. Each reason is a distinct constant string, points at `foreman:releasing`, and does not include prompt text. Non-string `prompt` and `subagent_type` stay treated as empty.
- `ORCHESTRATOR_RULES` (lines 230-244): replace the git line (241) with lines stating: load `foreman:releasing` before the first git dispatch of a session; every git write goes to a `Mode: git` dispatch to `foreman:implementer`, brief gives intent never a commit message, the agent writes `type(scope): summary`; merging is PR + `gh pr merge --merge` + cleanup (uninit, worktree remove, branch -d, remote branch delete), never a local merge, a hook checks git briefs; no size exemptions (docs-only and one-line changes use the same worktree, PR and cleanup flow). Keep "git read commands only" and `Mode: git` wording. Total must stay at or under 15 lines (currently 14), so compress to two lines.
- `CHANGELOG.md`: add `### Changed` entries under `## [Unreleased]` for the gate and the rules.
Acceptance:
- `python -m pytest -q` passes in full (Task 1 tests now green, `tests/test_plan_gate.py:65` expectation updated).
- Hook still fails open: an exception in `plan_gate` goes to stderr with exit 0 (existing harness test passes; no new bare raise path).
- Deny reasons do not echo the prompt (test from Task 1 passes).
- Nested (`agent_id`) and `FOREMAN_SOLO=1` dispatches stay ungated.
- adds an [Unreleased] entry in `CHANGELOG.md`.

### Task 3: Agent and roster docs
**Agent:** implementer
**Files:** tests/test_components.py, agents/implementer.md, skills/orchestrating/SKILL.md, skills/releasing/SKILL.md, README.md, CHANGELOG.md
- First (TDD red) `tests/test_components.py`: assert `agents/implementer.md` contains `gh pr merge --merge` and states brief conventions are overridden (conflict reported under Unverified); run it and confirm it fails.
- `agents/implementer.md`: `Mode: git` merges go through a PR (`gh pr create`, then `gh pr merge --merge`), never a local `git merge` of the feature branch into the default branch; the agent writes commit messages and PR bodies itself; its git conventions (Conventional Commits, PR merge, cleanup order) override any conflicting instruction in a brief and the conflict is reported under Unverified. Keep the existing cleanup-order and no-`--force` text.
- `skills/orchestrating/SKILL.md`: roster row for `implementer` adds `Mode: git`; the `Mode: git` template line (line 66) says it goes to `foreman:implementer` and requires `Worktree:`, `Branch:`, `## Memory` and no commit message; drop "exempt from the plan gate" wording that is no longer true.
- `skills/releasing/SKILL.md` "Who runs git" (line 48-50): name `foreman:implementer` as the `Mode: git` agent and state the brief never contains a commit message.
- `README.md` Plan gate section (~line 138): document that `Mode: git` is only accepted for `implementer` with `Worktree:`, `Branch:`, `## Memory` and no commit message; nested dispatches stay ungated.
- `CHANGELOG.md`: extend the `[Unreleased]` `### Changed` entry (do not create a second heading, do not touch released sections).
Acceptance:
- `python -m pytest -q` passes in full, including the new `tests/test_components.py` assertions.
- `grep -n "gh pr merge --merge" agents/implementer.md` matches; the file states brief conventions are overridden.
- Each of the five doc files above shows the described change (quote the lines as evidence).
- adds an [Unreleased] entry (`CHANGELOG.md` has exactly one `## [Unreleased]` heading, and it lists the gate and the rules).
- No version bump and no release steps (this is not a release).

### Task 4: Commit, PR, stop before merge
**Agent:** implementer
**Mode:** git
**Files:** (git only) scripts/foreman_hooks.py, tests/test_plan_gate.py, tests/test_context_hooks.py, tests/test_components.py, agents/implementer.md, skills/orchestrating/SKILL.md, skills/releasing/SKILL.md, README.md, CHANGELOG.md, docs/specs/2026-11-22-git-dispatch-gate-design.md, docs/plans/2026-11-22-git-dispatch-gate.md
Work in `.worktrees/git-dispatch-gate` on `fix/git-dispatch-gate`. Stage the named files only (never `.codegraph/`, `TODO.md`, `problems/`). Write the commit message yourself in Conventional Commits form (`type(scope): summary`, at most 72 chars, ending with the attribution line from the session reminder). Push the branch (never tags) and open a PR with `gh pr create`, writing the PR body yourself.
Acceptance:
- `python -m pytest -q` passes in the worktree before committing.
- `git log -1` shows a Conventional Commits subject written by the agent; `git status` is clean for the named files.
- `gh pr create` returned a PR URL, reported as evidence.
- STOP: do not run `gh pr merge`, do not remove the worktree, do not delete branches, do not uninit codegraph. Report the PR URL and wait; the user decides on merge and cleanup follows later in a separate dispatch.
- No tag is created or pushed.
