---
name: orchestrating
description: Use in the main session before planning or dispatching any work: the foreman loop, agent routing table, task-brief template and escalation rule.
---

# Orchestrating

The main session plans, dispatches and judges. It does not edit project files: the guard denies Edit/Write/NotebookEdit there (set `FOREMAN_SOLO=1` to escape). It also does not write files through Bash (no `>`, `tee`, `sed -i`, `git apply`); that is forbidden, not enforced. It may Read, Grep, Glob, use codegraph, git read commands and run tests.

This replaces `superpowers:subagent-driven-development` for execution (it has no per-task model routing). Still use superpowers brainstorming, writing-plans, systematic-debugging and verification-before-completion.

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
2. Dispatch the task, with a brief, to its agent.
3. Every task that changed code goes to the `verifier` with the brief and the diff range.
4. Fail: the first fail goes back to the same agent with the verifier's report.

## Escalation

A second fail on the same task moves up one tier: `drafter` -> `implementer` -> `expert`. `scout` doesn't escalate; re-brief it or give the lookup to `implementer`. If `expert` fails, stop and ask the user, with both reports.

Report "done" to the user only by quoting the verifier's evidence. Write memory (`foreman:memory`) for lessons worth keeping.

## Task brief template

Self-contained; the agent has no other context.

```
## Goal
<one or two sentences>
## Files
<paths to read or change>
## Acceptance
<checkable criteria, test commands>
## Memory
<paste `mem select` output: facts and traps>
## Report format
Result, then `## Evidence` and `## Unverified` (either may say "none").
```
