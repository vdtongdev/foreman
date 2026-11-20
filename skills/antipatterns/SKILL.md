---
name: antipatterns
description: "Use before writing or reviewing code: scope and simplicity, code smells, design-pattern overuse and agent-workflow mistakes to avoid, each with its reason."
---

# Antipatterns

A short checklist to follow while writing code and to check a diff against. Group 1 paraphrases ideas from `karpathy-guidelines` (MIT, plugin `karpathy-skills`); the rest is foreman's own. Every item has a reason, so judge by the reason when the wording does not fit.

## Scope and simplicity

- Features beyond the brief: nobody asked for them, and each one is more code to review and break.
- Abstraction for single-use code: it adds indirection before a second use shows the right shape.
- Options or settings nobody requested: unused knobs are untested paths.
- Handling for errors that cannot happen: it hides the real failure modes and bloats the diff.
- Refactoring or reformatting adjacent code: it buries the real change and risks regressions.
- Deleting unrelated dead code: mention it instead, because the owner may know why it stays.
- Picking an interpretation silently when the brief is unclear: stop and ask, because a wrong guess costs a whole retry.

## Code smells

- A function over about 50 lines or with more than 3 nesting levels: it is hard to hold in your head and hard to test.
- A class or module with unrelated responsibilities (a god object): every change to one concern risks the others.
- A duplicated block, from the third copy on: a fix must then be made in three places and one gets missed.
- Magic numbers or strings without a named constant: the reader cannot tell what the value means or where else it applies.
- Dead code introduced by the change: remove what your change made unused, since nobody else will.
- Boolean flag parameters that switch behaviour: two behaviours behind one name; use two functions instead.

## Design patterns

- Use a GoF pattern only when 2 or more concrete variants exist now, or the codebase already uses that pattern: otherwise it is speculation.
- An interface with one implementation: it is indirection with no second user to justify it.
- A factory that builds one type: a plain constructor call says the same thing with less code.
- A Visitor or Abstract Factory chain without a present need: these are heavy and pay off only with many variants.
- Keep the project's existing MVC layering rules: do not add layers to a project that has none, because the cost lands on everyone who edits it.

## Agent workflow

- The orchestrator doing simple work itself instead of dispatching: it burns the expensive context the loop protects.
- Re-checking evidence a subagent already quoted: it doubles the cost; spot-check only when the quote looks wrong.
- Briefs that dictate commands instead of intent: the agent cannot adapt when the commands do not fit.
- Querying a worktree through the codegraph MCP tool: it locks the index DB, so use the CLI and never pass the worktree as `projectPath`.
- Splitting tasks by layer instead of by feature: no layer is testable alone, so nothing can be verified until all are done.
- Writing to the default branch: work lands unreviewed; use a feature branch and a PR.
- Committing with `git add -A`: it sweeps in unrelated and secret files; stage by name.

The verifier fails only the clear-cut items of groups 2 and 3 listed in `agents/verifier.md`; everything else is a note.
