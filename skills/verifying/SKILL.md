---
name: verifying
description: Use before asking the user a question or asserting that something works, passes, has a version or has a cause: the evidence rules and report format.
---

# Verifying

## Asserting

- A claim (works, passes, has version X, the cause is Y) must cite evidence observed in this session: a command plus an output excerpt, a `file:line`, or a URL plus a quote.
- A memory fact counts only if it is `verified: human` and not stale; otherwise re-check it first.
- Anything else is listed as unverified.

## Asking

Ask the user only for decisions, preferences, or facts no code, doc, memory, web page or command can show. Each question states what was already checked. (Followed, not enforced.)

## Report format (every subagent)

The result, then `## Evidence` and `## Unverified`, either of which may say "none". A `SubagentStop` hook sends back a report missing either heading ("Add ## Evidence and ## Unverified sections.") once.

## Enforcement

- The `verifier` fails claims whose evidence doesn't support them.
- The orchestrator reports "done" only by quoting the verifier's evidence.
