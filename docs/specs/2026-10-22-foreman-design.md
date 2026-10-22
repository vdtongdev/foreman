# Foreman: orchestrated AI coding workflow (design)

Date: 2026-10-22. Status: approved in conversation, awaiting spec review.

## 1. Goal

A Claude Code plugin, used in every project, that:

1. Keeps the main session as the **orchestrator**: it plans and hands off work, and does not edit code.
2. Runs the work in **subagents whose model fits the task's difficulty**: haiku for cheap tasks, sonnet for clear implementation, opus only for escalations.
3. Turns memory into a **structured knowledge base**: typed facts with provenance, staleness and traps, validated by hooks.
4. Makes **"verify before asking or asserting"** a hard rule, enforced by hooks and by a verifier agent wherever a hook can do it.

It's private to its owner and installs on any machine with one command.

### Non-goals

- Syncing user memory across machines. Memory is machine-local for now; a private memory repo is a later add-on.
- Cloud sessions (claude.ai/code). They don't load locally installed plugins.
- Replacing superpowers or ponytail. Foreman sits next to them (section 7).

## 2. Verified platform facts this design relies on

Checked against code.claude.com docs on 2026-10-22, Claude Code 2.1.303.

| Fact | Used for |
|---|---|
| Hook input carries `agent_id`/`agent_type` when the hook fires inside a subagent; plugin and settings hooks run inside subagents too | Telling the main session apart from subagents (guard) |
| `PreToolUse` output: `permissionDecision: "deny"` + `permissionDecisionReason` (shown to Claude); `additionalContext` is supported | Guard; trap injection before an edit |
| `PostToolUse` output: `decision: "block"` + `reason` is shown to Claude next to the tool result | Memory write validation |
| `SessionStart` / `SubagentStart` output `additionalContext` is inserted at the start of the conversation; over 10,000 chars it is saved to a file with a 2,000-char preview | Injecting rules, memory status, traps |
| `SubagentStop` input has `last_assistant_message`; a blocking result feeds the reason back and the agent continues | Evidence-section check |
| Subagents don't load the main session's auto memory; they do load the CLAUDE.md hierarchy and path-scoped rules | Why traps must be delivered explicitly |
| Agent frontmatter: `model` (`haiku`/`sonnet`/`opus`/`fable`/`inherit`), `effort`, `tools`, `memory`; plugin agents ignore `hooks`, `mcpServers`, `permissionMode` | Agent roster |
| Auto memory: `~/.claude/projects/<repo>/memory/`, per repo, machine-local; first 200 lines / 25 KB of `MEMORY.md` loaded at session start; topic files read on demand | Project memory layer |
| A plugin-root `CLAUDE.md` is not loaded; files in a plugin's `bin/` are on the Bash `PATH` | Rules arrive via hooks; `mem` is a bare command |
| `claude plugin install <name> --marketplace <owner/repo>` adds the marketplace and installs in one step (v2.1.292+); private GitHub repos clone with the machine's git credentials | Distribution |
| Custom marketplaces have auto-update off by default | Install note |

## 3. Distribution

- Private GitHub repo `vdtongdev/foreman`, holding both the marketplace (`.claude-plugin/marketplace.json`) and the plugin.
- Install on any machine (needs `gh auth login` or an SSH key, plus `uv`):
  ```bash
  claude plugin install foreman --marketplace vdtongdev/foreman
  ```
  The default user scope enables it in every project. Then turn on auto-update once in `/plugin` → Marketplaces. If the marketplace entry can carry that flag, the step disappears; check during the build.
- Plugin development: `claude plugin marketplace add <local clone path>` loads the plugin in place; `/reload-plugins` applies edits.
- Per-project opt-out: disable at local scope.

## 4. Layout

```
foreman/
├── .claude-plugin/
│   ├── plugin.json
│   └── marketplace.json
├── agents/        scout.md  drafter.md  implementer.md  verifier.md  expert.md
├── skills/
│   ├── orchestrating/SKILL.md   the loop, routing table, task brief template, escalation
│   ├── memory/SKILL.md          entry format, fitness test, when to write, how to verify
│   └── verifying/SKILL.md       evidence rules, report format
├── hooks/hooks.json
├── scripts/       foreman_hooks.py (one entry point, subcommand per hook)  memory.py (shared lib)
├── bin/mem        memory CLI, calls scripts/memory.py
├── tests/
└── docs/specs/
```

- Hooks are stdlib-only Python run as `uv run --no-project --script "${CLAUDE_PLUGIN_ROOT}/scripts/foreman_hooks.py" <hook>`. `uv` gives the same command on every OS; `python3` doesn't exist on the owner's Windows PC.
- Every hook fails open: on an internal error it logs to stderr and allows the action, except the guard, which also fails open but prints a warning. A broken hook must never lock a session.

## 5. Roles

### 5.1 Orchestrator (main session)

The model the user talks to: the session model (currently opus, effort medium). It:

- **Clarifies.** It asks only what it can't verify (section 8).
- **Recalls.** It runs `mem select --path <files> --topic <topics>` for the work.
- **Plans.** It uses superpowers brainstorming / writing-plans for larger work.
- **Writes task briefs.** Each task brief is self-contained: goal, files, acceptance criteria, the selected facts and traps pasted in, and the report format.
- **Dispatches** to the cheapest fitting agent (5.2), runs independent tasks in parallel, and judges the results.
- **Escalates** (5.3), **writes memory** and **reports** to the user with the verifier's evidence.
- **May run** read and check tools itself: Read, Grep, Glob, codegraph, git read commands, test runs.
- **Does not edit** project files. This is enforced by the guard (5.4).

### 5.2 Subagents

| Agent | model | effort | tools | Use for |
|---|---|---|---|---|
| `scout` | haiku | low | Read, Grep, Glob, Bash, WebFetch, WebSearch | Finding files, docs, facts, versions; answers with sources |
| `drafter` | haiku | low | Read, Edit, Write, Grep, Glob | Short text (commit/PR messages, doc snippets); one-line fixes the brief spells out exactly |
| `implementer` | sonnet | medium | all except Agent | Implementing a clear spec or plan task (TDD); reading and synthesizing docs |
| `verifier` | sonnet | medium | Read, Grep, Glob, Bash | Reviewing the diff against the brief, running the tests; pass/fail with output. Never edits |
| `expert` | opus | high | all | Bugs that two attempts didn't fix; real architecture tradeoffs |

- Only `expert` keeps the Agent tool (for scouting).
- Every agent prompt ends with the report format from section 8.

### 5.3 Loop and escalation

1. Dispatch the task to its agent.
2. Every task that changed code goes to the `verifier` with the brief and the diff range.
3. On a fail:
   - The first fail goes back to the same agent, with the verifier's report.
   - A second fail on the same task moves up one tier: `drafter` → `implementer` → `expert`. `scout` doesn't escalate; a failed lookup is re-briefed or answered by `implementer`.
4. If `expert` fails, the orchestrator stops and asks the user, with both reports.

### 5.4 Guard

`PreToolUse`, matcher `Edit|Write|NotebookEdit`:

- **Inside a subagent** (`agent_id` present): allow.
- **Main session, path in the always-allowed list**: allow. The list is the user memory folder, the project's auto-memory folder, the project's `docs/superpowers/` and `docs/specs/`, `docs/plans/`, and any `CLAUDE.md`.
- **Main session, `FOREMAN_SOLO=1` set in the environment**: allow (the escape hatch).
- **Otherwise**: deny, with the reason "Orchestrator doesn't edit project files: dispatch a subagent (see foreman:orchestrating), or set FOREMAN_SOLO=1."

Bash writes aren't classified (too fragile). The orchestrating skill forbids them.

## 6. Memory knowledge base

### 6.1 Layers

| Layer | Location | Holds |
|---|---|---|
| User | `~/.claude/memory/` | `type: user`, `feedback`, and global `reference`/traps |
| Project | Claude Code auto memory, `~/.claude/projects/<repo>/memory/` | `type: project`, project `reference`/traps |

Each layer has its own `MEMORY.md` index, generated by the hooks and never hand-edited. Built-in auto memory stays on: the project layer *is* its directory, and Claude Code loads its index in the main session.

### 6.2 Entry format

One fact per file, `<name>.md`:

```markdown
---
name: wsl-stops-postgres            # kebab-case, equals the filename
description: one line, used for recall and the index
metadata:
  type: user | feedback | project | reference
  trap: true                        # optional; costly gotchas
  paths: [scripts/dev_db.ps1, tests/**]   # optional globs, repo-relative; selects traps by file
  topics: [wsl, postgres]           # optional
  status: active | deprecated
  superseded_by: other-name         # optional, with deprecated
  verified: human | model
  verified_on: 2026-10-22
  stale_after: 2027-04-22 | never   # required for project and reference
---
Body. Traps use the headings **Symptom:**, **Cause:**, **Do instead:**.
Links to other entries: [[name]].
```

### 6.3 Rules

- **`verified: human`** only when the user stated or confirmed the fact in the current conversation; everything else is `model`. A human fact beats a model fact; a conflict is flagged, not silently resolved. This rule is followed, not enforced.
- **`stale_after`** is required for `project` and `reference`: a date or `never`. Suggested defaults:
  - `reference`: about 6 months
  - `project` state: about 1 month
  - a version fact: the next release
- **Re-verifying** a fact sets `verified_on` to today and moves `stale_after` forward.
- **Deprecate, don't delete.** Set `status: deprecated` and, when replaced, `superseded_by`.
- **Entry fitness.** Write an entry only when it is all of these:
  - recurrent
  - not already caught by a tool or test
  - not duplicated in CLAUDE.md or another entry
  - still relevant
  - non-obvious to a competent reader of the code

### 6.4 Hooks

- **`PostToolUse` (`Write|Edit`, file under a memory layer):**
  1. Validate the frontmatter: required fields, `name` matches the filename, enums, date formats, `stale_after` per type, `superseded_by` exists.
  2. Rewrite `[[old]]` → `[[new]]` across the layer for each deprecated entry with `superseded_by`. Fuzzy-matching is never done.
  3. Regenerate the layer's `MEMORY.md`: active entries only, traps first, one line each (`- [name](file) — description`), staying under 200 lines / 25 KB.
  4. On a validation error, return `decision: "block"` with every problem listed, so the writer fixes it next step. Dangling links are reported in `additionalContext`, not blocked; they mark entries worth writing.
- **`SessionStart` (main session)** injects:
  - the orchestrating rules (a short summary plus a pointer to the skill)
  - the user layer's index
  - stale entries ("re-check before use")
  - invalid entries (e.g. hand-edited ones)
  - dangling links
- **`SubagentStart`** injects the verify rule (section 8), plus the one-line summaries of all active traps from both layers, capped at 2,000 chars.
- **`PreToolUse` (`Edit|Write`, inside a subagent)** injects, as `additionalContext`, the full guidance of traps whose `paths` match the file being edited. Each trap is injected once per agent; the hook records `(agent_id, trap name)` pairs in `${CLAUDE_PLUGIN_DATA}/served.json` and prunes entries older than a day.

### 6.5 `mem` CLI

| Command | Does |
|---|---|
| `mem select [--path P]... [--topic T]... [--type X] [--traps]` | Matching active entries from both layers, project first, with the reason each one matched |
| `mem stale` | Entries past `stale_after` |
| `mem validate` | All entries; exit 1 with the problems |
| `mem index` | Regenerate both indexes |
| `mem deprecate NAME [--by NEW]` | Set `status` (and `superseded_by`), then reindex |

The project layer's directory is derived the way Claude Code derives it: from the git root path, with `:`, `\`, `/` and spaces replaced by `-`. The rule is checked against the existing folders (`c--Users-Asus-ROG-projects-smallie`). Writing new entries uses the Write tool (the hooks validate it), so there's no `mem add`.

### 6.6 Migration

smallie's 11 `.antipatterns/AP-*.yaml` records become project-layer trap entries:

- `avoid`/`prefer`/`why` → Do instead / Symptom / Cause
- `paths` and `topics` carried over
- `verified: human`, `stale_after: never` unless the trap is tied to a version

`.antipatterns/` and the `antipatterning` skill stay until the user retires them.

## 7. Relation to installed plugins

- **superpowers.** The orchestrator still uses brainstorming, writing-plans, systematic-debugging and verification-before-completion. The foreman loop replaces `subagent-driven-development` for execution, because that skill has no per-task model routing. The orchestrating skill says so explicitly.
- **ponytail.** Unchanged. Its "smallest change" rules apply inside implementer and expert.
- **codegraph.** Agents use it as now (global CLAUDE.md, loaded in subagents too).

## 8. Verify before asking or asserting

1. **Asserting.**
   - A claim (works, passes, has version X, the cause is Y) must cite evidence observed in this session: a command plus an output excerpt, a `file:line`, or a URL plus a quote.
   - A memory fact counts only if it is `verified: human` and not stale; otherwise it is re-checked first.
   - Anything else is listed as unverified.
2. **Asking.**
   - Ask the user only for decisions, preferences, or facts that no code, doc, memory, web page or command can show.
   - Each question states what was already checked.
   - This rule is followed, not enforced.
3. **Report format** (every subagent): the result, then `## Evidence` and `## Unverified` sections, either of which may say "none".
4. **Enforcement.**
   - A `SubagentStop` hook blocks a stop whose `last_assistant_message` lacks either heading, with the reason "Add ## Evidence and ## Unverified sections." It allows the stop when `stop_hook_active` is true (the agent was already sent back once), so it can't loop.
   - The verifier fails claims whose evidence doesn't support them.
   - The orchestrator reports "done" only by quoting the verifier's evidence.

## 9. Testing

- `tests/` with pytest (run via `uv run --with pytest pytest`): each hook subcommand gets fixture JSON in and expected JSON out.
  - guard: main vs subagent, allowed paths, solo flag
  - memory validation: each error, link rewrite, index generation and size cap
  - trap selection by glob
  - evidence check
  - fail-open on bad input
- `mem` CLI tests on a temp layer.
- `claude plugin validate .` passes.
- Manual check in a scratch project:
  - the guard blocks a main-session edit
  - a dispatched implementer edits
  - a trap is injected on a matching edit
  - a bad memory write is blocked
  - a report without evidence is sent back

## 10. Risks

- **Hook latency.** `uv run --script` on each Edit/Write adds startup time. Measure; if it's over ~300 ms, run the hooks with the uv-managed Python directly.
- **Guard friction.** A trivial one-line fix now costs a haiku dispatch. That's accepted by design; `FOREMAN_SOLO=1` is the escape.
- **Rules that are followed, not enforced** (asking, `verified: human`, Bash writes). These are stated as such; the verifier and the user's review catch the slips.
- **Project-layer path derivation.** Wrong derivation means writing to a folder Claude Code never loads. Test it against real folders.
