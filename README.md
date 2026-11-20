# foreman

A Claude Code plugin that keeps the main session as an orchestrator. It:

- routes work to six model-tiered subagents (generalist on haiku; implementer, ui, planner, builder and verifier on sonnet);
- runs each request through a quick lane or a plan lane (spec → planner → builder), and sends each failure to the step that can fix it;
- keeps a typed memory knowledge base, validated by hooks;
- requires `## Evidence` / `## Unverified` sections in every subagent report.

Design: [docs/specs/2026-11-17-foreman-loop-v2-design.md](docs/specs/2026-11-17-foreman-loop-v2-design.md) (loop v2; it wins where it differs from the earlier [foreman design](docs/specs/2026-10-22-foreman-design.md)).

## Installation

### Prerequisites

- [Claude Code](https://docs.claude.com/en/docs/claude-code/overview)
- [uv](https://docs.astral.sh/uv/) (required for Python-based hooks and scripts)

### Install Foreman

Add the Foreman marketplace:

```bash
claude plugin marketplace add vdtongdev/foreman
```

Install the plugin:

```bash
claude plugin install foreman@foreman
```

No GitHub authentication is required for this public repository.

### Optional: Impeccable

Impeccable gives the `ui` agent its design guidance and the verifier its UI detector. Install it as its own plugin:

```bash
claude plugin install impeccable --marketplace pbakaus/impeccable
```

Foreman works without it: the `ui` agent then falls back to implementer behavior and reports "Impeccable not installed". The UI detector check needs Node (`npx`); without it, the check is listed under Unverified.

### Troubleshooting

If installation fails, verify that the repository is publicly accessible and that Git, Claude Code, and uv are installed correctly. If you encounter an authentication error, check whether Git is configured to use SSH or a credential helper that requires authentication.

**Auto-update** is off for custom marketplaces, and `marketplace.json` has no field to turn it on. Turn it on once per machine: `/plugin` → Marketplaces → foreman → Enable auto-update. `plugin.json` sets `version`; installs update only when it changes, so bump it with every release.

To turn it off for one project, disable the plugin at local scope.

## Progress

Current version: 0.2.2. See [CHANGELOG.md](CHANGELOG.md) for details; versioning and git rules are in the `releasing` skill.

- **0.1:** four-agent roster (generalist, implementer, verifier, expert), typed memory with `mem`, orchestrator guard, plan gate and evidence check hooks.
- **0.2:** loop v2: quick and plan lanes, `ui`, `planner` and `builder` agents, one verdict per review, failure routing, search guard, optional Impeccable.
- **0.2.1:** patch: `releasing` skill and git rules, MVC layering rules for agents.
- **0.2.2:** patch: changelog links use commit SHAs, worktree-first with a branch guard, a codegraph index per worktree, `antipatterns` skill.

## Layout

```
foreman/
├── .claude-plugin/   plugin.json, marketplace.json (this repo is its own marketplace)
├── agents/           builder.md  generalist.md  implementer.md  planner.md  ui.md  verifier.md
├── skills/           antipatterns/  orchestrating/  memory/  releasing/  verifying/
├── hooks/hooks.json  every hook calls scripts/foreman_hooks.py <hook>
├── scripts/          foreman_hooks.py (guard, plan-gate, plan-record, trap-inject,
│                     memory-write, session-start, subagent-start, evidence-check)  memory.py (memory library + mem CLI)
├── bin/              mem, mem.cmd (CLI launchers, on the Bash PATH)
├── tests/            pytest
└── docs/             specs/, plans/
```

## Agents

The main session is the orchestrator. Each subagent pins its model in its frontmatter, so routing is decided by which agent is picked.

| Agent | Model | Effort | Tools | Use for |
|---|---|---|---|---|
| `generalist` | haiku | low | Read, Edit, Write, Grep, Glob, WebFetch, WebSearch, Skill | Lookups (`Mode: lookup`: file:line and quotes), summaries, doc/text edits, and exact mechanical edits. No behavior changes, bug work, test work, or architecture. |
| `implementer` | sonnet | medium | all except Agent | Code behavior changes, tests, bug diagnosis, and complex synthesis |
| `ui` | sonnet | medium | all except Agent | UI tasks: the implementer plus the Impeccable skill |
| `planner` | sonnet | medium | all except Agent | Turns an approved spec into a plan in `docs/plans/`; revises tasks on `FAIL: plan` |
| `builder` | sonnet | medium | all | Runs an approved plan: dispatches the task agents and the verifier, routes failures, returns one summary |
| `verifier` | sonnet | medium | Read, Grep, Glob, Bash | Reviews the diff against the brief, runs the tests and the UI detector; issues one verdict. Never edits. |

Every agent ends its report with `## Evidence` and `## Unverified` sections; a `SubagentStop` hook sends a report without them back once. The implementer and ui load `antipatterns` (scope, code smells, design patterns, agent workflow) before writing code, and the verifier fails only its clear-cut items.

## The loop

Every request, feature or bug, runs through one loop: request → spec → plan → build → review → loop back on failure → done when the goal is met and the verifier's evidence passes.

1. **Clarify and recall.** Ask the user only what no code, doc, memory or command can show. Run `mem select` and paste the matching facts and traps into each task brief.
2. **Sort.** A request is quick only if one dispatch finishes it, the few files it touches are known, no behavior decision is open, it doesn't touch auth, secrets, data migrations or a public API, and one command checks it. When unsure, choose quick.
   - **Quick lane:** `generalist` for text, docs and mechanical edits; `implementer` for a small code change (test first); `ui` for a small UI change. The verifier checks anything that changed code. Two implementer fails, or a `BLOCKED` report, promote the request to the plan lane.
   - **Plan lane:** the orchestrator writes a short spec with the user (with Security, and Design for UI work); `planner` writes the plan (every task has `Agent:`, `Files:` and acceptance criteria); the orchestrator reviews the plan and dispatches `builder`. The builder runs each task with its agent and the verifier, and returns one summary with the verifier's evidence.
3. **Bugs** use the same loop. The first move is `implementer` in `Mode: diagnose`: it reproduces the bug with a failing test and reports the root cause. The diagnosis decides the lane, and its regression test becomes the first task or the quick brief's acceptance.
4. **Verify and route.** The verifier ends every review with exactly one verdict. Each failure goes to the lowest step that can fix it:

   | Verdict | Meaning | Goes to |
   |---|---|---|
   | `PASS` | All acceptance criteria met | next task |
   | `FAIL: impl` | Logic or execution bug in the task's files | same agent |
   | `FAIL: plan` | The plan is wrong: integration or dependency mismatch, wrong task order, or a diff outside the task's `Files:` | planner |
   | `FAIL: spec` | Conflicting acceptance criteria or an undefined business rule | orchestrator → user |
   | `FAIL: env` | Missing tool, service down, network, or a flaky test | orchestrator (does not count toward retry caps) |

   Retry caps: a task that fails `impl` twice is treated as `FAIL: plan`; a planner that revises the same task twice returns to the orchestrator; a problem the orchestrator cannot resolve goes to the user with the reports. An implementer or ui agent may answer a FAIL with `DISPUTE` once per task, with evidence.
5. **Report.** "Done" is reported only by quoting the verifier's evidence.

At session start, a hook injects a short summary of these rules; the full version is the `foreman:orchestrating` skill. The loop replaces superpowers' subagent-driven-development, which has no per-task model routing; superpowers' brainstorming and writing-plans are still used for planning.

## Orchestrator guard

In the main session, `Edit`/`Write`/`NotebookEdit` on files inside the project (git top-level, or cwd outside git) are denied; paths outside the project are allowed. Subagents can edit. These paths are always allowed:

- the memory folders
- `docs/specs/`, `docs/plans/` and `docs/superpowers/`
- any `CLAUDE.md` or `CLAUDE.local.md`

To work solo for a session, set `FOREMAN_SOLO=1` in the environment before starting `claude`.

## Branch guard

PreToolUse on `Edit|Write|NotebookEdit`, subagents only. It denies an edit when the edited file's own checkout is on the default branch (`origin/HEAD`, else `main` or `master`). It allows `docs/specs/`, `docs/plans/`, memory folders, detached HEAD, files outside git and `FOREMAN_SOLO=1`, and fails open on any git error or a 5 s timeout. Every request works in its own worktree under `.worktrees/<slug>` (excluded via `.git/info/exclude`, never the tracked `.gitignore`); see `skills/releasing/SKILL.md`. When the main checkout has `.codegraph/`, each worktree gets its own codegraph index (`codegraph init`), queried through the codegraph CLI from the worktree (never the MCP `projectPath`) and removed with `codegraph uninit` before `git worktree remove`. The extra `uv run` launch on Edit/Write is unmeasured.

## Search guard

In the main session, `Grep`, `Glob`, `WebFetch` and `WebSearch` are denied, so the orchestrator never searches itself. `Read` stays allowed for files it can name. For a search, the deny reason tells it to dispatch `generalist` with `Mode: lookup` (Haiku, no plan needed); the report must give `file:line` and exact quotes, not conclusions. Shell searches (`grep`, `find`, `rg` through Bash) are forbidden by rule, not enforced by a hook. Subagents are not affected.

## Plan gate

In the main session, dispatching an edit agent (`generalist`, `implementer`, `ui`, `builder`, `general-purpose`) is denied unless there is a plan. A `PreToolUse` hook on `Agent|Task` allows the dispatch when any of these holds:

- the brief has a line `Mode: quick` (quick lane; accepted only for `generalist`, `implementer` and `ui`), `Mode: diagnose` (diagnosis) or `Mode: git` (git-only work); or the generalist brief has `Mode: lookup` (read-only lookup);
- the brief names an existing plan file, `docs/plans/<file>.md` or `docs/superpowers/plans/<file>.md`; a `builder` dispatch also needs every task in that plan to have `Agent:` and `Files:` lines;
- the session already wrote a plan under those folders (a `PostToolUse` hook records it);
- the agent is `planner` (it writes the plan), or read-only (`verifier`, `Explore`, `Plan`, ...), or the caller is a subagent, or `FOREMAN_SOLO=1` is set.

## Memory: `mem`

`bin/mem` is on the Bash PATH inside Claude Code sessions.

| Command | Does |
|---|---|
| `mem select [--path P]... [--topic T]... [--type X] [--traps]` | Matching active entries, project layer first, with the reason each matched |
| `mem stale` | Entries past `stale_after` |
| `mem validate` | Check every entry; exit 1 with the problems |
| `mem index` | Regenerate both `MEMORY.md` indexes (a hand-written `MEMORY.md` is first saved once as `MEMORY.md.bak`) |
| `mem deprecate NAME [--by NEW]` | Mark an entry deprecated (and superseded) |

Memory layers:

- **User:** `~/.claude/memory/`
- **Project:** Claude Code's auto memory, `~/.claude/projects/<slug>/memory/`

For the entry format, see the `foreman:memory` skill.

## Hook latency

Each hook runs `uv run --no-project --script`. The median of 10 runs of the guard on this Windows PC was **163 ms** (range 129–178 ms). That is under the 300 ms budget, so the hooks don't call Python directly.

## Known issues

- **The `MEMORY.md.bak` notice reads as an error.** When a hand-written `MEMORY.md` is backed up, the notice is listed with the memory "problems", under "Invalid memory entries" at session start or in the memory-write hook's block message. The write itself went through and the entry is valid. It happens at most once per memory folder.
- **`mem deprecate NAME` can exit 1 by mistake.** The exit code checks the problem list with a substring match on the name. When another invalid entry's name contains `NAME` (for example `bold` when deprecating `old`), it returns 1 even though the deprecation succeeded.
- **The invalid-entries list can start with "; … N more".** The session-start list is capped at 3,000 characters. If the first problem alone is longer than that, the list starts with this odd prefix. This is cosmetic.

## Development

```bash
uv run --with pytest pytest -q        # tests
claude plugin validate .              # manifests
claude plugin marketplace add "<path to this clone>"
claude plugin install foreman@foreman # loads the clone in place; /reload-plugins applies edits
```
