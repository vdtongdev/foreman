# Loop v2 follow-ups Implementation Plan

> **For agentic workers:** Execute with the foreman loop (`foreman:orchestrating`). Tasks 1 and 2 are independent and may run in parallel.

**Goal:** Fix two gaps found while building loop v2: memory entries rewritten by Claude Code fail to parse, and plan-file edits trip the verifier's scope check. Also tighten the README's `Mode: quick` wording.

**Spec:** `docs/specs/2026-11-17-foreman-loop-v2-design.md` (§6 scope guard); memory format in `skills/memory/SKILL.md`.

## Global Constraints

- Top-level block lists stay unsupported (`test_parse_rejects_unsupported_yaml` keeps passing unchanged).
- Unknown metadata keys (`node_type`, `originSessionId`, `modified`) stay ignored, as today.
- Full suite: `uv run --with pytest pytest -q` passes.

## Review Focus

1. A block list under `metadata:` followed by another scalar key parses both — Task 1 test `test_parses_claude_code_rewritten_frontmatter`.
2. `mem deprecate` on an entry with block lists keeps the file parseable — Task 1 test `test_deprecate_block_list_entry`.
3. A `- x` line outside any key, or under a non-empty key, still raises — Task 1 test `test_stray_list_item_rejected`.

---

### Task 1: Parser accepts block-style lists in metadata (bug)

**Agent:** implementer
**Files:** Modify `scripts/memory.py` (`parse_frontmatter`); Test `tests/test_memory_model.py`

Diagnosis (confirmed 2026-11-17): Claude Code rewrites memory files written into its auto-memory dir, turning inline lists into block lists under `metadata:` and adding `node_type`, `originSessionId`, `modified`. `parse_frontmatter` (`scripts/memory.py:49-65`) raises "nested mappings deeper than one level" on an indented key with an empty value, so `memory_write` blocks and the entry is unusable. Unknown keys are already ignored by `load_entry`/`validate`.

- [ ] **Step 1:** Keep the regression test `test_parses_claude_code_rewritten_frontmatter` (already written, failing). Add:
  - `test_deprecate_block_list_entry`: write the rewritten entry to a tmp layer, run the deprecate path (`_set_status` / `mem deprecate`), reload → `status == "deprecated"` and `paths` unchanged.
  - `test_stray_list_item_rejected`: a `  - x` line directly after `metadata:` (no key) and a `    - x` line after `  type: reference` both raise `ValueError`.
- [ ] **Step 2:** Run `uv run --with pytest pytest tests/test_memory_model.py -q`; expected: new tests FAIL.
- [ ] **Step 3:** In `parse_frontmatter`, an indented (2-space) key with an empty value starts a list; following lines `    - item` (4-space) append `_scalar(item)` to it. Any other shape raises as today.
- [ ] **Step 4:** Run `uv run --with pytest pytest -q`; expected: PASS. Verifier confirms the regression test fails on the base commit and passes on head.
- [ ] **Step 5:** Commit `Memory: accept block-style metadata lists`.

### Task 2: Scope check exempts plan files; README Mode: quick wording

**Agent:** implementer
**Files:** Modify `agents/verifier.md`, `agents/implementer.md`, `agents/ui.md`, `README.md`; Test `tests/test_components.py`

- [ ] **Step 1:** Extend `test_verifier_lists_verdicts` to assert the verifier body contains `docs/plans/`; extend `test_task_agents_scope_and_dispute` to assert implementer and ui bodies contain `docs/plans/`.
- [ ] **Step 2:** Run `uv run --with pytest pytest tests/test_components.py -q`; expected: FAIL.
- [ ] **Step 3:** Verifier scope check: files under `docs/plans/` are outside the scope check (plan revisions travel with tasks). Implementer/ui scope rule: same exemption, one clause. README plan-gate bullet: `Mode: quick` is accepted only for `generalist`, `implementer` and `ui`.
- [ ] **Step 4:** Run `uv run --with pytest pytest -q`; expected: PASS.
- [ ] **Step 5:** Commit `Scope check exempts plan files; README quick-mode wording`.

### Task 3: Verify

**Agent:** verifier
**Files:** everything changed in Tasks 1–2

- [ ] **Step 1:** Review both commits against this plan; bug-fix check for Task 1 on its base commit.
- [ ] **Step 2:** `uv run --with pytest pytest -q` and `claude plugin validate .` pass.
