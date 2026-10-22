# foreman

A Claude Code plugin that keeps the main session as an orchestrator. It:

- routes work to model-tiered subagents (scout and drafter on haiku, implementer and verifier on sonnet, expert on opus);
- keeps a typed memory knowledge base, validated by hooks;
- requires `## Evidence` / `## Unverified` sections in every subagent report.

Design: [docs/specs/2026-10-22-foreman-design.md](docs/specs/2026-10-22-foreman-design.md).

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

### Troubleshooting

If installation fails, verify that the repository is publicly accessible and that Git, Claude Code, and uv are installed correctly. If you encounter an authentication error, check whether Git is configured to use SSH or a credential helper that requires authentication.

**Auto-update** is off for custom marketplaces, and `marketplace.json` has no field to turn it on. Turn it on once per machine: `/plugin` → Marketplaces → foreman → Enable auto-update. `plugin.json` has no `version` on purpose, so updates follow commits.

To turn it off for one project, disable the plugin at local scope.

## Layout

```
foreman/
├── .claude-plugin/   plugin.json, marketplace.json (this repo is its own marketplace)
├── agents/           scout.md  drafter.md  implementer.md  verifier.md  expert.md
├── skills/           orchestrating/  memory/  verifying/
├── hooks/hooks.json  every hook calls scripts/foreman_hooks.py <hook>
├── scripts/          foreman_hooks.py (guard, trap-inject, memory-write, session-start,
│                     subagent-start, evidence-check)  memory.py (memory library + mem CLI)
├── bin/              mem, mem.cmd (CLI launchers, on the Bash PATH)
├── tests/            pytest
└── docs/             specs/, plans/
```

## Agents

The main session is the orchestrator. Each subagent pins its model in its frontmatter, so routing is decided by which agent is picked.

| Agent | Model | Effort | Tools | Use for |
|---|---|---|---|---|
| `scout` | haiku | low | Read, Grep, Glob, Bash, WebFetch, WebSearch | Finding files, docs, facts and versions; answers with sources. Never edits. |
| `drafter` | haiku | low | Read, Edit, Write, Grep, Glob | Short text (commit/PR messages, doc snippets); one-line fixes the brief spells out exactly |
| `implementer` | sonnet | medium | all except Agent | A clear spec or plan task, test-first; reading and synthesizing docs |
| `verifier` | sonnet | medium | Read, Grep, Glob, Bash | Reviews the diff against the brief and runs the tests; reports PASS/FAIL with output. Never edits. |
| `expert` | opus | high | all | Bugs that two attempts didn't fix; real architecture tradeoffs. An escalation, not a default |

Only `expert` keeps the Agent tool, and it uses it only to dispatch scouts. Every agent ends its report with `## Evidence` and `## Unverified` sections; a `SubagentStop` hook sends a report without them back once.

## The loop

1. **Clarify and recall.** Ask the user only what no code, doc, memory or command can show. Run `mem select` and paste the matching facts and traps into each task brief.
2. **Dispatch.** Send each task, with a self-contained brief (Goal, Files, Acceptance, Memory, Report format), to the cheapest agent that fits. Independent tasks run in parallel.
3. **Verify.** Every task that changed code goes to the `verifier`.
4. **On a fail:**
   - The first fail goes back to the same agent with the verifier's report.
   - A second fail on the same task escalates one tier: `drafter` → `implementer` → `expert`. `scout` doesn't escalate; it is re-briefed, or the lookup goes to `implementer`.
   - If `expert` fails, the orchestrator stops and asks the user, with both reports.
5. **Report.** "Done" is reported only by quoting the verifier's evidence.

**Bug requests** always go through the same workflow, never an ad-hoc fix: the orchestrator's first move is to dispatch the implementer for diagnosis (it doesn't debug the code itself); the implementer reproduces the bug with a failing test and finds the root cause, the orchestrator writes a plan (regression test first, then the fix), and the loop executes it. The verifier checks that the regression test fails on the base commit and passes after the fix.

At session start, a hook injects a short summary of these rules; the full version is the `foreman:orchestrating` skill. The loop replaces superpowers' subagent-driven-development, which has no per-task model routing; superpowers' brainstorming and writing-plans are still used for planning.

## Orchestrator guard

In the main session, `Edit`/`Write`/`NotebookEdit` on files inside the project (git top-level, or cwd outside git) are denied; paths outside the project are allowed. Subagents can edit. These paths are always allowed:

- the memory folders
- `docs/specs/`, `docs/plans/` and `docs/superpowers/`
- any `CLAUDE.md` or `CLAUDE.local.md`

To work solo for a session, set `FOREMAN_SOLO=1` in the environment before starting `claude`.

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
