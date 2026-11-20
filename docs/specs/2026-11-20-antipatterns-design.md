# Anti-patterns skill

Date: 2026-11-20. Status: approved by user. Run after `2026-11-20-codegraph-worktrees` is merged, because both edit agents/*.md.

## Goal

Foreman's anti-pattern rules are scattered across files, and code smells, design-pattern overuse and agent-workflow mistakes are not covered. Add one `antipatterns` skill: a short, checkable list that the implementer and ui follow while writing code and that the verifier enforces only for high-confidence items.

## Sources (checked 2026-11-20)

- `karpathy-guidelines` (installed plugin `karpathy-skills`). It covers over-engineering, guessing silently and scope creep, e.g. "No abstractions for single-use code." Adapt the ideas in foreman's own words and credit the source in the skill. **Check its license before copying any text verbatim.**
- `llm-skills/antipatterning` (user's repo) is a registry of per-project records. It is **not imported**, because foreman memory traps already do path-scoped recall. Borrow only its entry-fitness rules (for example, "A one-shot lesson already applied everywhere is dead weight") into `skills/memory/SKILL.md`, re-checked against the raw file since the earlier quotes came from WebFetch summaries.

## Skill content: `skills/antipatterns/SKILL.md`, about 60 lines, four groups

1. **Scope and simplicity** (from karpathy): no features beyond the brief; no abstraction for single-use code; no options nobody asked for; no handling for impossible errors; don't refactor or reformat adjacent code; mention unrelated dead code instead of deleting it; if something is unclear, stop and ask instead of picking silently.
2. **Code smells** (new): a function over about 50 lines or with more than 3 nesting levels; a class or module with unrelated responsibilities (god object); a duplicated block, from the third copy on; magic numbers or strings without a named constant; dead code introduced by the change; boolean flag parameters that switch behaviour.
3. **Design patterns** (from the GoF analysis this session): use a GoF pattern only when 2 or more concrete variants exist now or the codebase already uses that pattern. Flag an interface with one implementation, a factory building one type, or a Visitor or Abstract Factory chain without a present need. Keep the existing MVC rules.
4. **Agent workflow** (observed this session):
   - The orchestrator doing simple work itself instead of dispatching.
   - Re-checking evidence a subagent already quoted.
   - Briefs that dictate commands instead of intent.
   - Querying a worktree through the codegraph MCP tool.
   - Splitting tasks by layer instead of by feature.
   - Writing to the default branch.
   - Committing with `git add -A`.

Each item is one line with a "why", so the list stays short.

## Wiring

- `agents/implementer.md` and `agents/ui.md`: load `antipatterns` before writing code (one sentence).
- `agents/verifier.md`: `FAIL: impl` only for items introduced by the diff in groups 2 and 3 that are clear-cut: an interface or factory with one implementation, an added magic number in logic, a duplicated block of 3 or more copies, or a function over 80 lines added by the change. Everything else goes under Unverified as a note, not a FAIL. This avoids FAIL loops on judgment calls.
- `agents/planner.md`: no change.
- `skills/orchestrating/SKILL.md`: group 4 is referenced from the orchestrator section (one line). `ORCHESTRATOR_RULES` is at its 15-line cap, so fold any change into an existing line.
- `skills/memory/SKILL.md`: the entry-fitness rules borrowed from `antipatterning`.
- README: the skill appears in the skills list. CHANGELOG `[Unreleased]` → Added.

## Security

- No new commands, hooks or network access. Text only.
- Licensing: only quote karpathy text verbatim if its license allows it, with credit. Otherwise paraphrase.
- Auth, secrets, input and data exposure: none applicable.

## Out of scope

- A per-project anti-pattern registry (memory traps cover it).
- `writing-llm-document` integration (a separate TODO item).
- Automated smell detection (linters). The verifier reads the diff.

## Acceptance

- `python -m pytest -q` passes. Text tests check that:
  - the skill exists with frontmatter and its four group headings
  - it credits karpathy-guidelines
  - implementer and ui reference `antipatterns`
  - the verifier lists the clear-cut FAIL items and the note-only rule
  - the memory skill has the fitness rule
- Agent invariants intact (BLOCKED: plan, DISPUTE, MVC, changelog, Worktree:, verdict strings, Evidence/Unverified).
- Done in a worktree, committed by Conventional Commits, merged by a merge commit, no release cut.
