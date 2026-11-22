# Git dispatch gate — design

Date: 2026-11-22

## Problem

In a real session the orchestrator ignored `foreman:releasing`: it wrote commit messages into `Mode: git` briefs, merged with a local fast-forward instead of PR + merge commit, skipped worktree cleanup, skipped `mem select`, and treated docs-only work as exempt. Root causes:

1. `plan_gate` (`scripts/foreman_hooks.py:118`) returns early for any `Mode: git` brief without inspecting it. Git writes have no enforcement.
2. `ORCHESTRATOR_RULES` (`scripts/foreman_hooks.py:241`) only points at `foreman:releasing`; it does not say the agent writes commit messages, how merges happen, or that there are no size exemptions.
3. No agent owns `Mode: git`. The generalist has no Bash. `agents/implementer.md` says "merge" without saying "through a PR", and does not say its git conventions win over a brief.

## Goals

### 1. Gate `Mode: git` briefs (`plan_gate`)

For a main-session dispatch whose prompt has a `Mode: git` line (same regex as today), deny unless all hold:

- `subagent_type` is `foreman:implementer`.
- The prompt has a `Worktree:` line and a `Branch:` line (line-start, case-insensitive, non-empty value).
- The prompt has a `## Memory` heading (content may be "none").
- The prompt contains no dictated commit message: no `-m "`, `-m '`, `--message`, or a line starting with `Commit message:` (case-insensitive).

Each failure gets its own deny reason naming the missing or forbidden item and pointing to `foreman:releasing`. `Mode: diagnose` behaviour is unchanged. Nested dispatches (payload has `agent_id`, e.g. from the builder) stay ungated, as today; `FOREMAN_SOLO=1` still bypasses.

### 2. `ORCHESTRATOR_RULES` additions

Replace the git line with lines stating:

- Load `foreman:releasing` before the first git dispatch of a session.
- Every git write goes to a `Mode: git` dispatch to `foreman:implementer`; the brief gives intent (files, what changed), never a commit message; the agent writes it in `type(scope): summary` form.
- Merging is PR + `gh pr merge --merge` + cleanup (uninit, worktree remove, branch -d, remote branch delete), never a local merge; a hook checks git briefs.
- No size exemptions: docs-only and one-line changes follow the same worktree, PR and cleanup flow.

Keep the existing "git read commands only" wording so current tests still find it.

### 3. Agent and roster docs

- `agents/implementer.md`: `Mode: git` merges go through a PR (`gh pr create`, then `gh pr merge --merge`), never a local `git merge` of the feature branch into the default branch; the agent writes commit messages and PR bodies itself, and its git conventions (Conventional Commits, PR merge, cleanup order) override any conflicting instruction in a brief (report the conflict under Unverified).
- `skills/orchestrating/SKILL.md`: roster row for `implementer` adds `Mode: git`; the `Mode: git` template line says it goes to `foreman:implementer` and has `Worktree:`, `Branch:`, `## Memory`, no commit message.
- `skills/releasing/SKILL.md` "Who runs git": name `foreman:implementer` as the `Mode: git` agent and state the brief never contains a commit message.
- `README.md:138` area: document the new `Mode: git` requirements.
- `CHANGELOG.md` `[Unreleased]`: Changed entries for the gate and the rules.

## Non-goals

- Gating nested (builder) dispatches.
- Detecting local merges or leftover worktrees (separate follow-ups).
- Antipatterns entry for "docs-only is small".

## Acceptance

- `python -m pytest -q` passes.
- New `tests/test_plan_gate.py` cases: implementer git brief with all fields passes; each missing field (`Worktree:`, `Branch:`, `## Memory`) denies; each commit-message pattern denies; `Mode: git` to `foreman:generalist`, `general-purpose` and `claude` denies; nested (`agent_id`) and `FOREMAN_SOLO=1` pass. Existing test at `tests/test_plan_gate.py:65` that expects a generalist git brief to pass is updated.
- `tests/test_context_hooks.py` asserts the new rule lines (releasing load, no commit message, `gh pr merge --merge`, no size exemptions).
- `tests/test_components.py` asserts implementer.md mentions `gh pr merge --merge` and that brief conventions are overridden.

## Security

- Threats: none new; the hook only reads the Agent tool prompt. It must keep failing open (exceptions to stderr, exit 0) like every other foreman hook.
- Auth, secrets, data exposure: none applicable. Deny reasons must not echo the prompt.
- Input: prompt and subagent_type may be non-strings; treat as empty, as `plan_gate` already does.
