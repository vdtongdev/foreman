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
| `scout` | haiku low | Finding files, docs, facts, versions; answers with sources |
| `drafter` | haiku low | Short text (commit/PR messages, doc snippets); one-line fixes the brief spells out exactly |
| `implementer` | sonnet medium | A clear spec or plan task (TDD); reading and synthesizing docs |
| `verifier` | sonnet medium | Review the diff against the brief, run the tests; never edits |
| `expert` | opus high | Bugs two attempts didn't fix; real architecture tradeoffs |

Run independent tasks in parallel.

## Loop

1. Clarify only what you can't verify (see `foreman:verifying`). Run `mem select --path <files> --topic <topics>`.
2. Dispatch the task, with a brief, to its agent. Edit dispatches (`implementer`, `drafter`, `expert`, general-purpose) need a plan: name one in the brief (`Plan: docs/plans/<file>.md`) or have written one this session; a hook denies them otherwise.
3. Every task that changed code goes to the `verifier` with the brief and the diff range.
4. Fail: the first fail goes back to the same agent with the verifier's report.

## Escalation

A second fail on the same task moves up one tier: `drafter` -> `implementer` -> `expert`. `scout` doesn't escalate; re-brief it or give the lookup to `implementer`. If `expert` fails, stop and ask the user, with both reports.

Report "done" to the user only by quoting the verifier's evidence. Write memory (`foreman:memory`) for lessons worth keeping.

## Bug requests

A described bug follows the same workflow as a feature: diagnose, plan, execute with the loop. Never fix it ad hoc, even when the cause looks obvious. Every bug fix ships with a regression test.

1. **Diagnose.** Don't read or debug the code to find the cause yourself. Your first action on a bug report is to dispatch an `implementer` (brief: the line `Mode: diagnose`, symptom, repro steps; acceptance: a failing test that reproduces it plus the root cause with file:line; do not fix yet). Use `superpowers:systematic-debugging` as guidance for that brief.
2. **Plan.** Once the diagnosis report is in, write the plan file before dispatching any fix; a fix task never goes out without a saved plan, however small the fix. Write a plan with `superpowers:writing-plans`, saved under `docs/plans/`. Task 1 is the failing regression test (if the diagnosis task already wrote it, task 1 is to keep it); the fix tasks follow, each with acceptance "the regression test passes and the suite is green".
The plan gate: a hook denies edit dispatches (`implementer`, `drafter`, `expert`, general-purpose) unless the brief names an existing plan or you wrote one this session. The diagnosis brief is exempt through its `Mode: diagnose` line.
3. **Execute.** Run the plan with the loop above; the verifier confirms the regression test fails on the base commit and passes after the fix. Escalation is unchanged (two failed fixes -> expert).

## Task brief template

Self-contained; the agent has no other context.

```
## Goal
<one or two sentences>
Mode: diagnose   (optional: diagnosis-only brief, exempt from the plan gate)
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
