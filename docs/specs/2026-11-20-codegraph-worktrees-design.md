# Codegraph in worktrees

Date: 2026-11-20. Status: approved by user. Depends on: `2026-11-20-worktree-first-design.md` (merged first).

## Goal

Codegraph cuts tokens and speeds agents up, so it must stay correct inside worktrees. Today a worktree at `.worktrees/<slug>` has no index of its own. `codegraph_explore` then falls through to "the nearest `.codegraph/` at or above" the path, which is the main checkout's index, and serves `main`'s version of files the agent has already changed, labelled as current on-disk source.

## Rules (added to `skills/releasing/SKILL.md`, next to the worktree rules)

1. **Index on creation, only if the project already uses codegraph.** When the main checkout has `.codegraph/`, the agent that creates the worktree runs `codegraph init <worktree>` right after `git worktree add`. A project with no `.codegraph/` gets nothing; indexing stays the user's decision.
2. **Query the worktree's index through the command line only.** Inside a worktree, run `codegraph explore` (or `node`, `callers` and so on) with the worktree as the working directory. **Never pass a worktree path as `projectPath` to the MCP tool.** The long-running codegraph MCP server keeps any database it opens locked, and that blocks `uninit` and `git worktree remove` (observed 2026-11-20: EPERM until the server process exited). The MCP tool stays in use for the main checkout. After editing files, run `codegraph sync <worktree>` before the next query, so line numbers match.
3. **Clean up before removing.** In the merge task, before `git worktree remove`, run `codegraph uninit -f <worktree>`. With CLI-only use (rule 2), no daemon holds the database, so no stop step is needed. If uninit fails, report it and do not use `--force` on the worktree removal.
4. **Keep the main index free of worktrees.** The main checkout's index must not contain `.worktrees/` files, or every symbol shows up twice. Verify how codegraph decides what to index (`.gitignore`, `.git/info/exclude`, its own config). If `.git/info/exclude` is not honoured, exclude `.worktrees/` through codegraph's own mechanism, never the project's tracked `.gitignore`.

## Who does what

- **Worktree creator** (builder's task 0 agent, or the quick-lane first agent): rule 1.
- **implementer, ui, verifier:** rule 2 (the command line through Bash). The verifier queries the worktree index for read-only checks.
- **generalist:** it has no Bash and must not use MCP on a worktree, so inside worktrees it uses Read only.
- **Merge task (`Mode: git`):** rule 3.
- **Orchestrator:** the main session keeps using the main checkout's index for planning. Briefs name `Worktree:`, and agents derive `projectPath` from it.

## Security

- **No destructive cleanup:** `codegraph uninit` only targets the worktree path, never the main checkout; `git worktree remove` still never uses `--force`.
- **No tracked-file changes for exclusion:** rule 4 never edits the tracked `.gitignore`.
- Auth, secrets, input and data exposure: none applicable (local index files only).

## Out of scope

- Sharing or copying the main index into worktrees, as a speed-up. Possible later if first-index time is slow; measure it first.

## Acceptance

- `python -m pytest -q` passes. Text tests check that the releasing skill names `codegraph init`, `projectPath`, `codegraph sync` and `codegraph uninit`, and the "only if `.codegraph/` exists" condition. Implementer, ui, generalist and verifier mention `projectPath`.
- A real run on this repo, recorded under Evidence:
  - create a worktree
  - `codegraph init` it, and record how long that takes
  - edit a function in the worktree, `codegraph sync`, and confirm `codegraph explore` with that projectPath returns the edited line
  - confirm the main index returns the unedited line
  - confirm `codegraph files` on the main checkout lists no `.worktrees/` path
  - after CLI-only queries, `uninit -f` succeeds and then `git worktree remove` succeeds without `--force`
- README "Branch guard" (or the worktree section) gains one line on codegraph per worktree. CHANGELOG `[Unreleased]` → Added entry.
