---
name: orchestrating
description: "Use in the main session before planning or dispatching any work: the foreman loop, agent routing table, task-brief template and escalation rule."
---

# Orchestrating

The main session plans, dispatches and judges. It does not edit project files: the guard denies Edit/Write/NotebookEdit there (set `FOREMAN_SOLO=1` to escape). It also does not write files through Bash (no `>`, `tee`, `sed -i`, `git apply`); that is forbidden, not enforced. It may Read, Grep, Glob, use codegraph, git read commands and run tests.

This replaces `superpowers:subagent-driven-development` for execution (it has no per-task model routing). Still use superpowers brainstorming, writing-plans, systematic-debugging (see Bug requests) and verification-before-completion.

## Routing

Pick the cheapest agent that fits.

| Agent | Model/effort | Use for |
|---|---|---|
| `generalist` | haiku low | Bounded lookups, summaries, doc/text edits, and exact mechanical edits. No behavior changes, bug work, tests, or architecture. Loads skills named in the brief. |
| `implementer` | sonnet medium | Code behavior changes, tests, bug diagnosis, and complex synthesis |
| `verifier` | sonnet medium | Review the diff against the brief, run the tests; never edits |
| `expert` | opus high | Bugs that two attempts didn't fix; real architecture tradeoffs. Escalation only |

The strong-model orchestrator remains read-only. Send real architecture tradeoffs directly to `expert`; after a second failed attempt, escalate to `expert`. If the expert fails, stop and ask the user with both reports. Run independent tasks in parallel.

## Loop

1. Clarify only what you can't verify (see `foreman:verifying`). Run `mem select --path <files> --topic <topics>`.
2. Dispatch the task, with a brief, to its agent. Each plan task carries an `Agent: <name>` line; dispatch it to that agent. Use `generalist` for bounded lookups and simple edits; use `implementer` for behavior changes, tests, bug diagnosis, or complex work; use `expert` for architecture tradeoffs. Edit dispatches (`generalist`, `implementer`, `expert`, general-purpose) need a plan: name one in the brief (`Plan: docs/plans/<file>.md`) or have written one this session. A generalist lookup may omit a plan only when its brief has an anchored `Mode: lookup` line; a hook enforces these rules.
3. Every task that changed code goes to the `verifier` with the brief and the diff range.
4. Fail: the first fail goes back to the same agent with the verifier's report. A second fail escalates to `expert`. If the expert fails, stop and ask the user with both reports.

## Escalation

Call `expert` only for bugs that remain unresolved after two attempts or for real architecture tradeoffs. If the expert cannot resolve the issue, stop and ask the user with both reports.

Report "done" to the user only by quoting the verifier's evidence. Write memory (`foreman:memory`) for lessons worth keeping.

## Bug requests

A described bug follows the same workflow as a feature: diagnose, plan, execute with the loop. Never fix it ad hoc, even when the cause looks obvious. Every bug fix ships with a regression test.

1. **Diagnose.** Don't read or debug the code to find the cause yourself. Your first action on a bug report is to dispatch an `implementer` (brief: the line `Mode: diagnose`, symptom, repro steps; acceptance: a failing test that reproduces it plus the root cause with file:line; do not fix yet). Use `superpowers:systematic-debugging` as guidance for that brief.
2. **Plan.** Once the diagnosis report is in, write the plan file before dispatching any fix; a fix task never goes out without a saved plan, however small the fix. Write a plan with `superpowers:writing-plans`, saved under `docs/plans/`. Task 1 is the failing regression test (if the diagnosis task already wrote it, task 1 is to keep it); the fix tasks follow, each with acceptance "the regression test passes and the suite is green".
The plan gate: a hook denies edit dispatches (`generalist`, `implementer`, `expert`, general-purpose) unless the brief names an existing plan or you wrote one this session. Generalist lookup briefs may omit a plan only with an anchored `Mode: lookup` line. Diagnosis briefs are exempt through `Mode: diagnose`, and git-only briefs through `Mode: git`.
3. **Execute.** Run the plan with the loop above; the verifier confirms the regression test fails on the base commit and passes after the fix. After two failed attempts, escalate to `expert`; real architecture tradeoffs go to `expert` directly.

## Task brief template

Self-contained; the agent has no other context.

```
## Goal
<one or two sentences>
Mode: diagnose   (optional: diagnosis-only brief, exempt from the plan gate)
Mode: git   (optional: git-only brief, e.g. commit/push; exempt from the plan gate)
Mode: lookup   (optional: read-only generalist lookup, exempt from the plan gate)
Plan: docs/plans/<file>.md   (optional: required for edit work unless you wrote a plan this session)
## Files
<paths to read or change>
## Acceptance
<checkable criteria, test commands>
## Memory
<paste `mem select` output: facts and traps>
## Report format
Result, then `## Evidence` and `## Unverified` (either may say "none").
```
