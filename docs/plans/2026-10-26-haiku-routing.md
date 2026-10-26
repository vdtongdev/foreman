# Route docs and git work to the haiku drafter

Goal: doc edits and git operations run on haiku (drafter) instead of sonnet (implementer). Verifier stays sonnet for all diffs, docs included.

## Task 1: Widen the drafter (Agent: drafter)
Files: `agents/drafter.md`, `skills/orchestrating/SKILL.md` (routing table), `README.md` (line ~5 summary is fine; the drafter row near line 64), session-start text in `scripts/foreman_hooks.py` (~line 137, only if it describes drafter scope).
- drafter `description` and body: "Doc and text edits of any length, mechanical edits the brief spells out exactly, and git operations (stage, commit, branch, push) the brief lists. No new logic and no tests."
- drafter `tools`: add `Bash` -> `Read, Edit, Write, Grep, Glob, Bash`. Body: Bash only for the git commands the brief lists, plus read commands.
- Routing table: drafter row as above; implementer row "A spec or plan task that changes code behaviour (TDD); reading and synthesizing docs".
Acceptance: `uv run --with pytest pytest -q` green (tests/test_components.py checks drafter is haiku/low and has `tools`, no `Agent`).

## Task 2: Plan tasks name their agent (Agent: drafter)
Files: `skills/orchestrating/SKILL.md`, `README.md` loop section, session-start text in `scripts/foreman_hooks.py` if it lists the loop.
- Loop step 2: each plan task carries an `Agent: <name>` line; dispatch by it. When writing a plan, tag a task `implementer` if it changes code behaviour or needs a test, otherwise `drafter`.
- Do NOT change the verifier rule: every task that changed files goes to the sonnet verifier, docs included (LLM-facing docs need real review).
Acceptance: suite green.

## Task 3: `Mode: git` plan-gate exemption (Agent: implementer)
Files: `scripts/foreman_hooks.py` (`plan_gate`, `PLAN_DENY`), `tests/test_plan_gate.py`, `skills/orchestrating/SKILL.md` (template + plan gate paragraph), `README.md` plan gate section.
- Test first: `Mode: git` brief to `foreman:drafter` without a plan is allowed (case-insensitive, line-anchored like diagnose); a brief without it is still denied.
- Change regex `^Mode:\s*diagnose\b` to `^Mode:\s*(?:diagnose|git)\b`. Update `PLAN_DENY` to mention `'Mode: git'` for git-only briefs, and update `REASON` in the test to match.
- Skill template: add `Mode: git   (optional: git-only brief, e.g. commit/push; exempt from the plan gate)`.
Acceptance: new test fails before, passes after; suite green.
