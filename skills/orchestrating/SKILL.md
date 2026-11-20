---
name: orchestrating
description: "Use in the main session before planning or dispatching any work: the foreman loop, two lanes, failure routing, task-brief template and retry caps."
---

# Orchestrating

The main session plans, dispatches and judges. It does not edit project files: the guard denies Edit/Write/NotebookEdit there (set `FOREMAN_SOLO=1` to escape). It also does not write files through Bash (no `>`, `tee`, `sed -i`, `git apply`); that is forbidden, not enforced. It may Read, Grep, Glob, use codegraph, git read commands and run tests.

This replaces `superpowers:subagent-driven-development` for execution (it has no per-task model routing). Still use superpowers brainstorming, writing-plans, systematic-debugging (see Bug requests) and verification-before-completion.

## Roster

| Agent | Model/effort | Use for |
|---|---|---|
| `generalist` | haiku low | Lookups for everyone (`Mode: lookup`), docs/text edits, exact mechanical edits. No behavior changes, bug work or tests. |
| `implementer` | sonnet medium | Code behavior changes, tests, bug diagnosis |
| `ui` | sonnet medium | UI work; implementer plus the Impeccable skill, builds from the spec's Design section |
| `planner` | sonnet | Spec to plan under `docs/plans/` (every task has `Agent:`, `Files:`, acceptance); revises plans on `FAIL: plan` |
| `builder` | sonnet | Runs a plan: dispatches task agents and the verifier, routes failures, returns one summary |
| `verifier` | sonnet medium | Reviews diff vs brief, runs tests, security and scope checks, ends with one verdict; never edits |

Run independent tasks in parallel. Searches: Grep, Glob, WebFetch and WebSearch are denied to you in the main session. Dispatch `generalist` with `Mode: lookup`; it reports `file:line` and exact quotes, not conclusions. Read and codegraph stay allowed. Shell searches (`grep`, `find`, `rg`) are forbidden, not enforced.

## Lanes

Sort every request. It is quick only if all hold: one dispatch finishes it and the few (about 3) files are known; no open behavior decisions; it touches no auth, secrets, data migrations or public API; one command checks it. When unsure, choose quick.

1. **Quick lane.** Brief with `Mode: quick` to `generalist` (text, docs, mechanical), `implementer` (small code change, test first) or `ui` (small UI change). Anything that changed code goes to the `verifier`. Two `FAIL: impl` or a `BLOCKED` report promotes the task to the plan lane. The brief names `Worktree: .worktrees/<slug>` and `Branch: <type>/<slug>`; the first agent creates it as step 1 (`foreman:releasing`), and the verifier and the later `Mode: git` dispatch get the same lines.
2. **Plan lane.** Write the spec with the user (`superpowers:brainstorming`) with a Security section (threats, auth, input, secrets, data exposure; "None applicable" stated) and, for UI, a Design section (`PRODUCT.md`, `DESIGN.md`). Dispatch `foreman:planner` with the spec path. Read the plan; send it back if it misses spec items (each Security item is an acceptance criterion, each UI task has the detector command). Then dispatch `foreman:builder` with `Plan: docs/plans/<file>.md`; the builder creates the worktree before task 1 and copies the untracked spec and plan into it (you still write specs and plans in the main checkout and never run git writes); every task needs `Agent:` and `Files:` lines (a hook checks). Planner-written plans are not recorded as session plans, so name the plan in every non-quick edit brief.
3. **Promotion.** A promoted quick task gets a short spec: the original request, both failure reports and the open question that made it non-quick. Give the reports to the planner too.

Report "done" only by quoting the verifier's evidence. The agent-workflow group of `foreman:antipatterns` lists the orchestrator mistakes to avoid. Write memory (`foreman:memory`) for lessons worth keeping. Relay "Impeccable not installed" (from a `ui` or verifier report) to the user once per session; foreman works without it.

## Failure routing

The verifier's first line is exactly one verdict:

| Verdict | Goes to |
|---|---|
| `PASS` | next task |
| `FAIL: impl` | same agent, with the report |
| `FAIL: plan` | `foreman:planner` (fix changes tasks, order, files or interfaces) |
| `FAIL: spec` | you, then the user with the quoted criteria |
| `FAIL: env` | you (missing tool, service down, flaky); does not count toward caps |

Send a failure to the lowest step that can fix it. Caps: the same task failing `FAIL: impl` twice is treated as `plan`; the planner revising one task twice goes to you; if you cannot resolve it, stop and ask the user with the reports. An agent may answer a FAIL with `DISPUTE` once per task; it counts as one attempt. Inside a plan the builder routes failures; in the quick lane you do.

## Bug requests

A described bug follows the same workflow as a feature. Never fix it ad hoc, even when the cause looks obvious. Every bug fix ships with a regression test.

1. **Diagnose.** Don't read or debug the code yourself. First dispatch an `implementer` (brief: the line `Mode: diagnose`, symptom, repro steps; acceptance: a failing test that reproduces it plus the root cause with file:line; do not fix yet). Use `superpowers:systematic-debugging` as guidance. If the intended behavior is undefined, that is a spec failure: ask the user.
2. **Sort.** Apply the quick-lane test. Quick: the fix brief (`Mode: quick`) uses the regression test as acceptance. Otherwise plan lane: plan task 1 is "keep the regression test", not "write it", saved under `docs/plans/`.
3. **Execute.** The `verifier` confirms the regression test fails on the base commit and passes after the fix.

## Task brief template

Self-contained; the agent has no other context. In the main session run git reads only; at a milestone dispatch the release cut as `Mode: git` (see `foreman:releasing`), and if the project has no `CHANGELOG.md`, offer adopting one once.

```
## Goal
<one or two sentences>
Mode: quick   (optional: quick-lane brief to generalist, implementer or ui, exempt from the plan gate)
Mode: diagnose   (optional: diagnosis-only brief, exempt from the plan gate)
Mode: git   (optional: git-only brief, e.g. commit/push; exempt from the plan gate)
Mode: lookup   (optional: read-only generalist lookup, exempt from the plan gate)
Plan: docs/plans/<file>.md   (required for every non-quick edit brief and for foreman:builder)
Worktree: <path>   (required for every brief that edits or runs git, once the worktree exists; also the directory to run the codegraph CLI from, see `foreman:releasing`; never a worktree as MCP `projectPath`)
Branch: <type>/<slug>   (same briefs as Worktree:)
## Files
<paths to read or change>
## Acceptance
<checkable criteria, test commands>
## Memory
<paste `mem select` output: facts and traps>
## Report format
Result, then `## Evidence` and `## Unverified` (either may say "none").
```
