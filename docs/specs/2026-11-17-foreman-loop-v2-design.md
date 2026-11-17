# Foreman loop v2: two lanes, builder, triaged failures, UI agent (design)

Date: 2026-11-17. Status: decided in conversation, builder-checked, awaiting user approval.
Extends `2026-10-22-foreman-design.md`; where they differ, this document wins.

## 1. Intent

Foreman is a plug-and-play plugin: install it on any PC and work right away with a team of agents foreman defines. Every request, feature or bug, runs through one loop:

request → spec → plan → build (code, UI/UX, security built in) → review → loop back on failure → done when the goal is met and reviews pass.

Why change the current loop:

- **Handoffs are expensive and Opus does too much.** The orchestrator (Opus) currently writes every plan and receives every task report. Simple requests still pay for a plan.
- **Second fail → expert fires too often.** Two attempts is an easy threshold, so the Opus expert ends up on most non-trivial tasks.
- **Failures are fixed at the wrong layer.** Today every fail goes back to the coder, even when the plan or the requirement was wrong.
- **UI work has no design discipline.** Impeccable (impeccable.style) supplies it.

### Goals

1. The orchestrator sorts each request into a **quick lane** (cheap agent, no plan) or a **plan lane** (spec → planner → builder).
2. A dedicated **planner** writes plans; a dedicated **builder** executes them, so the Opus orchestrator never receives per-task reports.
3. The reviewer **labels each failure** and the label decides which upstream step fixes it; bounded retries replace the expert.
4. A **`ui` agent** builds UI with Impeccable; the verifier checks UI with Impeccable's detector.
5. Bugs and features share the same loop.

### Non-goals

- A security builder agent. Security is designed in the spec and reviewed by the verifier.
- Vendoring Impeccable. It is a plugin dependency.
- Changing the memory system (`mem`, traps, validation hooks).

### Anti-goals (failure even if it works)

- Opus executing simple tasks, or reading per-task reports of a planned build.
- Loops without an end: every path below has a retry cap that ends at the user.
- A failure label without evidence.

## 2. Platform facts relied on

Checked 2026-11-17.

| Fact | Source |
|---|---|
| Subagents can start nested subagents; a nested subagent defaults to its parent's model unless its definition sets `model` | code.claude.com/docs/en/sub-agents, "Which model a nested subagent runs on" |
| `plugin.json` `dependencies` accepts `"name@marketplace"` or `{name, marketplace, version}`; without a version it tracks the dependency's latest release | code.claude.com/docs/en/plugin-dependencies |
| A cross-marketplace dependency installs only if the root marketplace lists it in `allowCrossMarketplaceDependenciesOn`; otherwise a plugin.json dependency is skipped and the plugin fails to load | same page |
| Impeccable: marketplace `impeccable`, plugin `impeccable` v4.9.2, Apache-2.0, ships one skill (`/impeccable <command>`, 24 commands); detector runs via `npx impeccable` with exit codes | github.com/pbakaus/impeccable `.claude-plugin/*.json`, `LICENSE`; impeccable.style |
| Plan gate and guard exempt any call whose payload has `agent_id` (i.e. from a subagent) | `scripts/foreman_hooks.py` `guard`, `plan_gate` |

## 3. The loop

```
request ─► bug? ─► implementer diagnoses (Mode: diagnose): failing test + root cause file:line
           │        └─ intended behavior undefined → spec failure → orchestrator asks user
           ▼
     orchestrator sorts (quick-lane test, §4)
       ├─ quick lane ─► generalist | implementer | ui ─► verifier ─► done
       │                 (2 impl fails, or BLOCKED → promoted to plan lane)
       └─ plan lane ─► orchestrator writes spec (§5)
                        ─► planner writes plan (each task: Agent: line)
                        ─► orchestrator reviews plan, dispatches builder
                        ─► builder, per task: implementer | ui | generalist ─► verifier
                             routes failures (§6)
                        ─► builder returns one summary with verifier evidence ─► done
```

The orchestrator reports "done" only by quoting verifier evidence (unchanged rule).

## 4. Quick-lane test

A request is quick only if all hold:

- One dispatch finishes it; the files it touches are known and few (about 3).
- No open behavior decisions (nothing a spec would need to settle).
- It does not touch auth, secrets, data migrations, or a public API.
- One command checks that it is done.

When unsure, choose quick: a wrong quick pick costs at most 2 cheap attempts before promotion; a wrong plan pick always costs a spec.

Quick-lane routing: text, docs, mechanical edits → `generalist`; small code change → `implementer` (test first); small UI change → `ui`. Anything that changed code goes to the verifier. For a bug, the diagnosis report decides the lane; its regression test is the quick brief's acceptance.

## 5. Spec and plan

**Spec** (orchestrator, Opus, with the user, via superpowers:brainstorming). Required sections besides the usual ones:

- **Security**: threats, auth/authz, input handling, secrets, data exposure. "None applicable" must be stated, not omitted.
- **Design** (when UI is involved): references `PRODUCT.md` and `DESIGN.md` (Impeccable's project context), or says they will be created.

**Plan** (`planner` agent, Sonnet). Input: the approved spec path. Output: a plan under `docs/plans/` where every task has `Agent:`, `Files:`, and acceptance criteria. Each spec Security item becomes an acceptance criterion on some task; each UI task's acceptance includes the detector check (§7). Bug plans: task 1 is the regression test.

The orchestrator reads the plan and sends it back to the planner if it misses spec items, before dispatching the builder.

## 6. Failure triage and routing

The verifier ends every review with exactly one verdict:

| Verdict | Meaning | Required evidence | Goes to |
|---|---|---|---|
| `PASS` | All acceptance criteria met | commands + output | next task |
| `FAIL: impl` | Execution/logic bug: syntax, off-by-one, missing import, null check, misread a clear plan instruction | failing command + output, file:line | same agent |
| `FAIL: plan` | Integration, dependency or codebase mismatch the plan got wrong: wrong API assumption, incompatible library version, wrong task order, unplanned caller broken | the plan step that is wrong and why | planner |
| `FAIL: spec` | Conflicting acceptance criteria, impossible constraint, undefined business rule | quote of the conflicting criteria or the undefined case | orchestrator → user |
| `FAIL: env` | Missing tool, service down, network, flaky test | command + output; for flaky, two runs with different results | orchestrator |

**Cheapest-fixer rule.** A failure goes to the lowest step that can fix it without changing the document above it. Integration problems go to the planner only when the fix changes the plan (tasks, order, files, interfaces); otherwise `impl`.

**Scope guard.** An implementer/ui agent may change only the files and interfaces its task names. If a correct fix needs more, it stops and reports `BLOCKED: plan` with the reason. The verifier fails with `plan` any diff that touches files outside the task's `Files:`, even if tests pass.

**Retry caps (replace the expert).**

- Same task fails `impl` twice → treated as `plan`.
- Planner revises the same task twice → orchestrator.
- Orchestrator cannot resolve → ask the user with the reports.
- `env` does not count toward caps. Flaky: the verifier reruns once before labeling.

**Disputes.** An implementer/ui agent may answer a FAIL with `DISPUTE` once per task, with evidence. The builder (or orchestrator in the quick lane) either re-dispatches the verifier with the dispute or accepts the evidence. A dispute counts as one attempt.

## 7. Roster

| Agent | Model/effort | Dispatched by | Role |
|---|---|---|---|
| orchestrator (main session) | Opus | user | Sorts requests, writes specs, reviews plans, handles `spec`/`env` and capped escalations; never edits project files |
| `planner` | Sonnet | orchestrator, builder | Spec → plan; revises plans on `FAIL: plan` |
| `builder` | Sonnet | orchestrator | Runs a plan: dispatches task agents and verifier, routes failures per §6, returns one summary |
| `generalist` | Haiku low | orchestrator, planner, builder | Lookups for everyone (`Mode: lookup`: file search, web; reports `file:line` + quotes), docs, mechanical edits |
| `implementer` | Sonnet medium | orchestrator, builder | Code, tests, bug diagnosis |
| `ui` | Sonnet medium | orchestrator, builder | `implementer` base + loads the Impeccable skill; builds from the spec's Design section; keeps `PRODUCT.md`/`DESIGN.md` current |
| `verifier` | Sonnet medium | orchestrator, builder | Reviews diff vs brief, runs tests, security review against the spec's Security section, Impeccable detector on UI tasks; issues §6 verdicts; never edits |

Removed: `expert`. Each agent definition sets `model` explicitly so nested dispatch from the builder does not inherit the wrong model.

**UI check.** On UI tasks the verifier runs `npx impeccable detect --json <task's UI files or dev-server URL>`. Exit 0 = pass (advisories allowed); exit 2 = `FAIL: impl` with the findings as evidence; exit 1 (target could not be scanned) = `FAIL: env`. Intentional exceptions are recorded with `npx impeccable ignores add-value …`, never by skipping the scan. The planner writes the exact command into each UI task's acceptance. If Node/`npx` is unavailable, the detector check is reported under Unverified, not as a fail. (Source: impeccable.style/docs/detector.)

**Builder frontmatter.** `builder` must have the `Agent` tool; every agent it dispatches sets `model` explicitly. Task agents (`implementer`, `ui`, `generalist`, `verifier`) keep `Agent` disallowed.

## 8. Impeccable as a dependency

**Soft dependency (user decision 2026-11-17): foreman must install and work without Impeccable.** A `plugin.json` dependency that fails to resolve makes foreman fail to load, so foreman does not declare one.

- README install adds a second step: `claude plugin install impeccable --marketplace pbakaus/impeccable`. Impeccable then updates through its own marketplace, independently of foreman.
- The `ui` agent checks whether the `impeccable` skill is available. If not, it works as `implementer` and says "Impeccable not installed" under Unverified; the orchestrator relays that warning to the user once per session.
- The verifier's detector check is likewise Unverified (not a fail) when Impeccable or `npx` is missing.

## 9. Hook changes

- **Plan gate**: add `Mode: quick` exemption (anchored line, like `Mode: diagnose`) for quick-lane briefs to `generalist`, `implementer`, `ui`. Add `foreman:planner` as allowed without a plan (it writes the plan). `foreman:builder` requires a named plan. Dispatches from subagents stay exempt.
- **Orchestrator rules** (`ORCHESTRATOR_RULES`) and `skills/orchestrating/SKILL.md`: rewritten for the two lanes, builder, triage table and caps; expert references removed.
- **Builder plan check** (mechanical): a `foreman:builder` dispatch is allowed only if the named plan file exists and every task in it has `Agent:` and `Files:` lines. (Builder's call.)
- **Verdict check** (mechanical): extend the SubagentStop evidence check so a `verifier` reply must contain exactly one verdict line matching `PASS` or `FAIL: impl|plan|spec|env`. (Builder's call.)
- **Scope check**: prompt-level, but with a fixed command — the verifier compares `git diff --name-only <base>..HEAD` against the task's `Files:`.
- **Evidence check**: unchanged; applies to new agents too.
- **Search guard** (new, user decision 2026-11-17): in the main session (no `agent_id`, `FOREMAN_SOLO` unset), deny `Grep`, `Glob`, `WebFetch` and `WebSearch`. The deny reason tells the orchestrator to dispatch `generalist` with `Mode: lookup` (Haiku; already plan-gate exempt), whose report must be `file:line` and exact quotes, not conclusions. `Read` and codegraph stay allowed: the orchestrator reads files it can name, specs, plans and reports. Shell searches (`grep`/`find`/`rg` via Bash) are forbidden by rule, not enforced, like Bash writes today. No dedicated scout agent: `generalist` lookup mode covers it.
- Retry caps and failure routing inside the builder are prompt-enforced; hooks cannot see nested dispatch state cheaply. Accepted trade-off. (Builder's call.)

## 9a. Promotion and bug details

- A quick-lane task promoted to the plan lane gets a short spec: the original request, the two failure reports, and the open question that made it non-quick. The reports go to the planner too. (Builder's call.)
- For bugs, the regression test written during diagnosis is reused: plan task 1 is "keep the regression test", not "write it". (Builder's call.)

## 9b. First plan task: nesting spike

Before any other work, a throwaway spike confirms in a real session: (1) a plugin `builder` agent with the `Agent` tool can dispatch `foreman:implementer` and `foreman:verifier`; (2) each nested agent runs on its own `model`; (3) foreman's PreToolUse/SubagentStop hooks fire inside nested agents. If (1) fails, stop and return to the user: the builder design does not hold. (Builder's call.)

## 10. Approaches considered

- **Who plans.** (A) Orchestrator specs and plans — keeps context but spends Opus on the longest step. (B, chosen) Orchestrator specs, planner plans — the spec needs the user, the plan doesn't. (C) Planner does both — it cannot ask the user, so specs become guesses.
- **Who dispatches plan tasks.** (A) Orchestrator — fewer handoffs, but every report lands in Opus context. (B, chosen) Builder always runs planned work; simple work skips planning entirely via the quick lane, which is where the handoff savings come from.
- **Failure handling.** (A) Today: retry, then Opus expert on second fail — fires too often. (B, chosen) Labeled failures routed upstream with retry caps ending at the user.
- **Search offloading.** (A) Dedicated Haiku `scout` — read-only by tool list, but one more agent. (B, chosen) `generalist` in `Mode: lookup` plus a hook denying search tools in the main session — same savings, no new agent. (C) Prompt rule only — orchestrator drifts back to searching itself.
- **Impeccable install.** (A) Vendor — pinned, manual updates. (B, chosen) Install as its own plugin so updates flow through; first considered as a hard `plugin.json` dependency, then made soft so foreman still loads without it. (C) `npx impeccable install` on first run — needs Node and writes into every project.

## 11. Left to the builder of this change

- Exact wording of agent prompts and the brief templates for planner/builder.
- Test layout for the new hook rules and agent frontmatter.
- Whether the builder resumes or re-dispatches the same agent on `FAIL: impl`.

## 12. Unverified

- That `claude plugin install impeccable --marketplace pbakaus/impeccable` is the exact working install command on a fresh PC.
- Whether subagents can ask the user questions (design assumes not: `spec` failures always return to the orchestrator).
- How often second-fail escalation actually happened under the old roster (roster plan Task 4 never ran).
