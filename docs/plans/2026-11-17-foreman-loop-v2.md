# Foreman loop v2 Implementation Plan

> **For agentic workers:** Execute with the foreman loop (skill `foreman:orchestrating`), not superpowers' executing-plans / subagent-driven-development. Each task names its agent; every task that changes code goes to `foreman:verifier`. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Two-lane request flow (quick / plan), new `planner`, `builder`, `ui` agents, labeled failure verdicts with retry caps, search guard, Impeccable as a soft add-on; `expert` removed.

**Architecture:** Behavior lives in agent prompts (`agents/*.md`), the orchestrating skill, and `scripts/foreman_hooks.py` (one function per hook, registered in `HOOKS`, wired in `hooks/hooks.json`). Hooks enforce what is mechanical: plan gate, search guard, verdict line. Everything else is prompt-enforced.

**Tech Stack:** Python 3 stdlib hooks run via `uv run --no-project --script`; pytest via `uv run --with pytest pytest -q`; Claude Code plugin manifests.

**Spec:** `docs/specs/2026-11-17-foreman-loop-v2-design.md`

## Global Constraints

- Hooks fail open: any exception → exit 0, no output (existing `main`).
- Every `hooks.json` entry: `command` ends with `|| true`, `timeout` 30, `commandWindows` uses the existing `try { & uv run ... } catch {}; exit 0` shape (enforced by `tests/test_dispatch.py`).
- Main-session-only rules are skipped when payload has `agent_id` or `FOREMAN_SOLO=1`.
- Every agent sets `model` and `effort` explicitly; every agent body contains `## Evidence` and `## Unverified`.
- Frontmatter values containing `: ` are quoted (`tests/test_components.py`).
- `ORCHESTRATOR_RULES` stays ≤ 15 lines and keeps the phrase `not superpowers' Native`.
- Verdict set, exact strings: `PASS`, `FAIL: impl`, `FAIL: plan`, `FAIL: spec`, `FAIL: env`.
- Agent names: `foreman:generalist`, `foreman:implementer`, `foreman:ui`, `foreman:planner`, `foreman:builder`, `foreman:verifier`.

## Review Focus

1. A builder dispatch naming a plan where one task lacks `Files:` must be denied, not allowed because other tasks are fine — Task 3 test `test_builder_needs_agent_and_files_per_task`.
2. Search guard must never fire inside subagents (the generalist doing the lookup uses Grep) — Task 4 test `test_search_guard_allows_subagent_and_solo`.
3. Verdict check must not block non-verifier agents whose reports mention "FAIL" — Task 5 test `test_verdict_only_for_verifier`.
4. `Mode: quick` must not exempt `foreman:builder` or `general-purpose` — Task 3 test `test_quick_mode_only_task_agents`.
5. A verifier reply with two verdict lines (e.g. quoting an old `PASS`) is blocked — Task 5 test `test_verdict_exactly_one`.

---

### Task 0: Commit the pending four-agent roster work

**Agent:** implementer (generalist has no Bash, so it can't run git)
**Mode:** git (needs user go-ahead before dispatch)
**Files:** the files currently modified/untracked on `improving-agent-roster` except `.codegraph/`, `problems/`, `TODO.md`

- [ ] **Step 1:** Run `uv run --with pytest pytest -q`; expected: all pass. If not, stop and report.
- [ ] **Step 2:** Commit with message `Four-agent roster: generalist replaces scout and drafter`.

### Task 1: Nesting spike (throwaway)

**Agent:** implementer
**Mode:** diagnose (report only; delete all spike files afterwards)
**Files:** scratch dir outside the repo only

- [ ] **Step 1:** In a temp copy of the plugin, add `agents/spike-builder.md` (`model: sonnet`, tools include `Agent`) whose prompt dispatches `foreman:generalist` with `Mode: lookup` and `foreman:verifier` on a trivial brief.
- [ ] **Step 2:** Run `claude -p --plugin-dir <temp copy> --output-format stream-json --verbose "Use the spike-builder agent"`.
- [ ] **Step 3:** Report, with transcript excerpts: (a) nested dispatch happened; (b) each nested agent's model; (c) foreman `SubagentStart`/`SubagentStop` hooks fired for nested agents (evidence text injected / evidence check ran).
- [ ] **Step 4:** If (a) fails, the orchestrator stops the plan and asks the user (spec §9b).

### Task 2: Agent roster

**Agent:** implementer
**Files:**
- Create: `agents/planner.md`, `agents/builder.md`, `agents/ui.md`
- Modify: `agents/implementer.md`, `agents/verifier.md`, `agents/generalist.md`
- Delete: `agents/expert.md`
- Test: `tests/test_components.py`

**Interfaces — Produces:** agent names and models used by Tasks 3, 6:

| name | model/effort | tools |
|---|---|---|
| planner | sonnet/medium | `disallowedTools: Agent` |
| builder | sonnet/medium | no `tools`/`disallowedTools` (needs `Agent`) |
| ui | sonnet/medium | `disallowedTools: Agent` |
| implementer, verifier, generalist | unchanged | unchanged |

- [ ] **Step 1: Update tests.** In `tests/test_components.py`: `NAMES = ["generalist", "implementer", "ui", "planner", "builder", "verifier"]`; `test_agent_models` expects the table above; tool-boundary test: `Agent` disallowed for implementer, ui, planner; builder has neither `tools` nor `disallowedTools`; `sorted(names with tools) == ["generalist", "verifier"]`; `not (ROOT/"agents"/"expert.md").exists()`. Add:
  - `test_verifier_lists_verdicts`: verifier body contains each of the five verdict strings, `git diff --name-only`, `npx impeccable detect --json`, and `Security`.
  - `test_task_agents_scope_and_dispute`: implementer and ui bodies contain `BLOCKED: plan` and `DISPUTE`.
  - `test_ui_loads_impeccable`: ui body contains `impeccable` and `Impeccable not installed`; ui frontmatter `tools` absent or contains `Skill`.
  - `test_builder_routes_failures`: builder body contains `FAIL: impl`, `FAIL: plan`, `FAIL: spec`, `FAIL: env`, `twice`, `foreman:planner`.
  - `test_generalist_lookup_reports_quotes`: generalist body contains `Mode: lookup` and `file:line`.
  - Update `test_agents_describe_bug_handling`: drop the expert assertions.
- [ ] **Step 2:** Run `uv run --with pytest pytest tests/test_components.py -q`; expected: FAIL (missing files/strings).
- [ ] **Step 3: Write the agents** per spec §6–§7:
  - `planner`: input is an approved spec path; output a plan in `docs/plans/` whose every task has `**Agent:**` and `**Files:**` lines and acceptance; each spec Security item becomes an acceptance criterion; UI tasks carry the exact detector command; bug plans keep the diagnosis regression test as task 1; on `FAIL: plan` revise only the named tasks.
  - `builder`: input is a plan path; per task dispatch the named agent (`foreman:<name>`) with a self-contained brief, then `foreman:verifier`; route verdicts per spec §6 table; caps: `FAIL: impl` twice on a task → `foreman:planner`; planner revises the same task twice → stop and return to orchestrator; `FAIL: spec`/`FAIL: env` → stop and return; handle `DISPUTE` once per task (counts as an attempt); `BLOCKED: plan` → planner. Return one summary quoting verifier evidence per task.
  - `ui`: implementer body plus: load the `impeccable` skill via Skill; build from the spec's Design section and keep `PRODUCT.md`/`DESIGN.md` current; if the skill is unavailable, work as implementer and write `Impeccable not installed` under Unverified.
  - `implementer`: add scope rule (`BLOCKED: plan` when a correct fix needs files/interfaces outside the task) and one `DISPUTE` with evidence.
  - `verifier`: end with exactly one verdict line from the five; required evidence per verdict (spec §6); scope check `git diff --name-only <base>..HEAD` vs task `Files:` → `FAIL: plan`; Security review against the spec's Security section; UI tasks run `npx impeccable detect --json <target>` — exit 0 pass, 2 `FAIL: impl`, 1 `FAIL: env`, `npx` missing → Unverified; rerun a failing test once before labeling flaky `FAIL: env`.
  - `generalist`: `Mode: lookup` reports `file:line` and exact quotes, no conclusions.
- [ ] **Step 4:** Run `uv run --with pytest pytest tests/test_components.py -q`; expected: PASS.
- [ ] **Step 5:** Commit `Add planner, builder, ui agents; verdicts; remove expert`.

### Task 3: Plan gate — quick lane, planner, builder

**Agent:** implementer
**Files:** Modify `scripts/foreman_hooks.py` (`plan_gate`, `PLAN_DENY`, `READ_ONLY`); Test `tests/test_plan_gate.py`

**Interfaces — Produces:** `_plan_tasks_ok(text: str) -> bool` in `foreman_hooks.py`: splits on lines matching `^#{2,4} Task\b`; True iff ≥1 task and every task section has a line matching `^\s*(\*\*)?Agent:(\*\*)?\s*\S` and one matching `^\s*(\*\*)?Files:(\*\*)?`.

- [ ] **Step 1: Write failing tests** in `tests/test_plan_gate.py` (update `REASON` to the new `PLAN_DENY`):
  - `test_quick_mode_task_agents`: prompt `"## Goal\nx\nMode: quick\n"` → `None` for `foreman:generalist`, `foreman:implementer`, `foreman:ui`.
  - `test_quick_mode_only_task_agents`: same prompt → `DENIED` for `foreman:builder`, `general-purpose`; `"see Mode: quick"` → `DENIED` for implementer.
  - `test_planner_needs_no_plan`: `foreman:planner`, prompt `"do it"` → `None`.
  - `test_builder_needs_named_plan`: plan written this session (via `_record`) but not named → `DENIED` for builder.
  - `test_builder_needs_agent_and_files_per_task`: plan `docs/plans/x.md` with `### Task 1\n**Agent:** implementer\n**Files:** a.py\n### Task 2\n**Agent:** ui\n` → `DENIED` (builder-specific reason `BUILDER_DENY`); adding `**Files:** b.tsx` to Task 2 → `None`; a plan with no `Task` headings → `DENIED`.
  - Remove `foreman:expert` from `test_denies_edit_agents_without_plan`; add `foreman:ui`.
- [ ] **Step 2:** Run `uv run --with pytest pytest tests/test_plan_gate.py -q`; expected: FAIL.
- [ ] **Step 3:** Implement in `plan_gate`: anchored `^Mode:\s*quick\b` exempts the three task agents; `foreman:planner` added to the exempt set; for `foreman:builder` require a `PLAN_RE` match naming an existing plan whose text passes `_plan_tasks_ok`, else deny with `BUILDER_DENY = "Builder needs a named plan (Plan: docs/plans/<file>.md) whose every task has Agent: and Files: lines."`. Add `Mode: quick` to `PLAN_DENY` text.
- [ ] **Step 4:** Run the same command; expected: PASS.
- [ ] **Step 5:** Commit `Plan gate: quick lane, planner, builder plan check`.

### Task 4: Search guard

**Agent:** implementer
**Files:** Modify `scripts/foreman_hooks.py` (new `search_guard`, `SEARCH_DENY`, `HOOKS["search-guard"]`), `hooks/hooks.json` (PreToolUse matcher `Grep|Glob|WebFetch|WebSearch`); Create `tests/test_search_guard.py`

- [ ] **Step 1: Write failing tests:**
  - `test_search_guard_denies_main_session`: for each of `Grep`, `Glob`, `WebFetch`, `WebSearch` with no `agent_id` → PreToolUse deny with reason `SEARCH_DENY = "Orchestrator doesn't search: dispatch foreman:generalist with a 'Mode: lookup' line (reports file:line and quotes), or set FOREMAN_SOLO=1."`
  - `test_search_guard_allows_subagent_and_solo`: `agent_id` present → `None`; `FOREMAN_SOLO=1` → `None`.
  - `test_search_guard_ignores_other_tools`: `Read`, `Bash` → `None`.
- [ ] **Step 2:** Run `uv run --with pytest pytest tests/test_search_guard.py tests/test_dispatch.py -q`; expected: FAIL.
- [ ] **Step 3:** Implement `search_guard(payload: dict) -> dict | None`; register and wire in `hooks.json` in the existing shape.
- [ ] **Step 4:** Run the same command; expected: PASS.
- [ ] **Step 5:** Commit `Search guard: orchestrator delegates searches to generalist`.

### Task 5: Verdict check

**Agent:** implementer
**Files:** Modify `scripts/foreman_hooks.py` (`evidence_check`); Test `tests/test_evidence.py`

- [ ] **Step 1: Write failing tests** (verifier payload: `agent_type: "foreman:verifier"`; also accept `"verifier"`):
  - `test_verdict_required_for_verifier`: evidence sections present, no verdict line → block, reason `VERDICT_REASON = "Verifier must give exactly one verdict line: PASS, FAIL: impl, FAIL: plan, FAIL: spec or FAIL: env."`
  - `test_verdict_exactly_one`: two verdict lines → block.
  - `test_verdict_ok`: `"FAIL: plan\n...\n## Evidence\n- x\n## Unverified\n- none"` → no output; `"PASS"` likewise.
  - `test_verdict_only_for_verifier`: `agent_type: "foreman:implementer"`, message with sections and no verdict → no output.
  - `test_verdict_rejects_unknown_label`: `"FAIL: logic"` only → block.
- [ ] **Step 2:** Run `uv run --with pytest pytest tests/test_evidence.py -q`; expected: FAIL.
- [ ] **Step 3:** Implement: after the sections check, for verifier agent types count lines matching `^(PASS|FAIL: (impl|plan|spec|env))\b` (multiline); block unless exactly 1. `stop_hook_active` still short-circuits.
- [ ] **Step 4:** Run the same command; expected: PASS.
- [ ] **Step 5:** Commit `Evidence check: verifier must give one verdict`.

### Task 6: Orchestrator rules and orchestrating skill

**Agent:** implementer
**Files:** Modify `scripts/foreman_hooks.py` (`ORCHESTRATOR_RULES`), `skills/orchestrating/SKILL.md`; Test `tests/test_components.py`, `tests/test_context_hooks.py`

- [ ] **Step 1: Update tests:**
  - `test_bug_requests_section_placement_and_content`: headings order becomes `## Lanes` < `## Failure routing` < `## Bug requests` < `## Task brief template`; bug section contains `mode: diagnose`, `implementer`, `regression test`, `verifier`, `base commit`, `quick`, `docs/plans`; no `expert` anywhere in the skill.
  - New `test_skill_covers_loop`: skill contains `Mode: quick`, `foreman:planner`, `foreman:builder`, all five verdict strings, `twice`, `Mode: lookup`, `Grep`.
  - `test_orchestrator_rules_cover_bugs_within_line_cap`: also assert `quick`, `planner`, `builder` in rules and `expert` not in rules.
- [ ] **Step 2:** Run `uv run --with pytest pytest tests/test_components.py tests/test_context_hooks.py -q`; expected: FAIL.
- [ ] **Step 3:** Rewrite per spec §3–§6, §9: sorting and quick-lane test (§4), spec sections Security/Design (§5), plan review then builder dispatch, failure table and caps (§6), search guard and lookup delegation, bugs diagnose-then-sort with test reuse, promotion of a quick task to the plan lane with a short spec plus both failure reports (§9a), relay `Impeccable not installed` to the user once per session (§8), brief template gains `Mode: quick`. Keep `not superpowers' Native`, ≤15 rule lines.
- [ ] **Step 4:** Run the same command; expected: PASS.
- [ ] **Step 5:** Commit `Orchestrating: two lanes, builder, failure routing`.

### Task 7: README, Impeccable install, version

**Agent:** generalist
**Plan:** docs/plans/2026-11-17-foreman-loop-v2.md
**Files:** `README.md`, `.claude-plugin/plugin.json`

- [ ] **Step 1:** README: roster table and loop description match spec §3/§7 (no expert, no scout); install section adds optional step `claude plugin install impeccable --marketplace pbakaus/impeccable` with one line: foreman works without it, `ui` falls back to implementer behavior; Node is needed for the detector.
- [ ] **Step 2:** `plugin.json` `version` → `0.2.0`. No `dependencies` field.
- [ ] **Step 3:** Commit `Docs: loop v2, optional Impeccable; v0.2.0` — via a separate `foreman:implementer` dispatch with `Mode: git` (generalist has no Bash).

### Task 8: Verify

**Agent:** verifier
**Files:** everything changed in Tasks 2–7

- [ ] **Step 1:** Review the diff against the spec and this plan.
- [ ] **Step 2:** Run `uv run --with pytest pytest -q`; expected: all pass (e2e skipped).
- [ ] **Step 3:** Run `claude plugin validate .`; expected: valid.
- [ ] **Step 4:** Confirm `agents/expert.md` absent and no `expert` mention in `skills/`, `scripts/foreman_hooks.py`, `README.md`.
