---
name: memory
description: Use when writing, updating or deprecating a memory entry, or looking facts up with the mem CLI: entry format, fitness test, verification rules.
---

# Memory

Two layers, each with a generated `MEMORY.md` index (never hand-edit): user `~/.claude/memory/` (`user`, `feedback`, global `reference`/traps) and project `~/.claude/projects/<repo>/memory/` (`project`, project `reference`/traps).

## Entry: one fact per `<name>.md`

Frontmatter is flat `key: value`, with one nested `metadata:` block (2-space indent).

```markdown
---
name: wsl-stops-postgres          # kebab-case, equals the filename
description: one line, used for recall and the index
metadata:
  type: user | feedback | project | reference
  trap: true                      # optional; costly gotchas
  paths: [scripts/dev_db.ps1, tests/**]   # optional, repo-relative globs
  topics: [wsl, postgres]         # optional
  status: active | deprecated
  superseded_by: other-name       # optional, with deprecated
  verified: human | model
  verified_on: 2026-10-22
  stale_after: 2027-04-22 | never # required for project and reference
---
Body. Traps use **Symptom:**, **Cause:**, **Do instead:**.
Link entries with [[name]].
```

Write entries with the Write tool; hooks validate them and block with every problem listed.

## Rules

- Write an entry only if it is all of: recurrent, not already caught by a tool or test, not duplicated in CLAUDE.md or another entry, still relevant, non-obvious to a competent reader of the code.
- `verified: human` only when the user stated or confirmed the fact in this conversation; otherwise `model`. A human fact beats a model fact; flag conflicts, don't silently resolve them.
- `stale_after` defaults: reference about 6 months; project state about 1 month; a version fact, the next release.
- Re-verifying: set `verified_on` to today and move `stale_after` forward.
- Deprecate, don't delete: `mem deprecate NAME --by NEW`.

## mem commands

| Command | Does |
|---|---|
| `mem select [--path P]... [--topic T]... [--type X] [--traps]` | Matching active entries, project first, with match reasons |
| `mem stale` | Entries past `stale_after` |
| `mem validate` | All entries; exit 1 with the problems |
| `mem index` | Regenerate both indexes |
| `mem deprecate NAME [--by NEW]` | Set `status` (and `superseded_by`), reindex |
