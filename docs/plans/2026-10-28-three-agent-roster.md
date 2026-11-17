# Implement and validate the four-agent roster

## Goal

Use four specialist roles while keeping the strong-model orchestrator responsible for request analysis, planning, and coordination:

- `generalist` — Haiku/low for bounded lookups, summaries, doc/text edits, and exact mechanical edits.
- `implementer` — Sonnet/medium for code behavior, bug diagnosis, tests, and complex synthesis.
- `verifier` — Sonnet/medium for independent review; never edits.
- `expert` — Opus/high for bugs that remain after two attempts and real architecture tradeoffs. Preserve this existing call condition.

The generalist must not change code behavior, diagnose or fix bugs, create or edit tests, or make architecture decisions. It has no Bash tool. The orchestrator remains read-only. Keep the existing escalation sequence: first verifier failure returns to the same agent; a second failure escalates to expert; real architecture tradeoffs go to expert directly. If expert cannot resolve the issue, stop and ask the user with the reports.

## Task 1: Implement role definitions and routing (Agent: implementer)

Files: `agents/generalist.md`, `agents/scout.md`, `agents/drafter.md`, `agents/implementer.md`, `agents/verifier.md`, `agents/expert.md`, `scripts/foreman_hooks.py`, `skills/orchestrating/SKILL.md`, `README.md`, `docs/specs/2026-10-22-foreman-design.md`.

- Add the bounded Haiku `generalist` role.
- Remove the `scout` and `drafter` role definitions; retain `expert` on Opus/high with its existing Agent tool and call condition.
- Route simple research and edits to the generalist; route behavior changes, bugs, and complex work to the implementer; send changed code to the verifier.
- Route real architecture tradeoffs and work that still fails after two attempts to the expert. Keep the strong-model orchestrator read-only.
- Allow an unplanned request only when it is a generalist brief with its own anchored `Mode: lookup` line. Keep diagnosis and git exemptions; require plans for all other edit work.
- Update active docs and hook instructions. Leave historical plans unchanged.

Acceptance: exactly four agent definition files remain; model/tool scopes match this plan; active docs describe the same routing and expert call condition; the plan gate permits only the specified lookup exemption and still denies unplanned generalist edits.

## Task 2: Update regression coverage (Agent: implementer)

Files: `tests/test_components.py`, `tests/test_plan_gate.py`.

- Update roster and model expectations to the four roles, including expert Opus/high and Agent-tool access.
- Cover the anchored generalist lookup exemption, reject a lookup phrase that is not a standalone line, and confirm generalist edits without a plan remain denied.
- Keep the existing diagnosis and git exemption coverage.
- Keep or update existing checks that expert is only called after two failed attempts or for real architecture tradeoffs.

Acceptance: tests describe the new roster, expert call condition, and all plan-gate boundaries above.

## Task 3: Verify implementation (Agent: verifier)

Files: all files changed in Tasks 1–2.

- Review the diff against the plan.
- Run targeted plan-gate and component tests, then the full suite: `uv run --with pytest pytest -q`.
- Run plugin manifest validation: `claude plugin validate .`.

Acceptance: targeted tests, full suite, and plugin validation pass; verifier reports commands and output.

## Task 4: Compare task performance (Agent: verifier)

Use the same small, fixed set of representative prompts with the existing roster and the four-agent roster: one lookup, one exact doc edit, one code change, one bug diagnosis requiring expert escalation, and one architecture tradeoff. Record completion time, first-pass verifier acceptance, rework count, and model/cost where available.

Acceptance: report the before/after results. If implementation or review quality drops, revise the routing boundaries before considering the roster complete.

## Current state

The three-role roster implementation is already present as uncommitted work on branch `three-agent-roster`, before this revised plan received review. Review this four-role plan before any further implementation or validation work. After approval, reconcile the existing branch diff to Tasks 1–2, restore the expert role and its existing escalation condition, then execute Tasks 3–4.
