---
name: releasing
description: "Use when a change is user-visible, when committing, branching, opening a PR or cutting a release: changelog, version, commit and git rules."
---

# Releasing: versioning and git rules

Applies on any project unless it already documents its own convention (CONTRIBUTING, CLAUDE.md, an existing changelog format). A project's own convention wins.

## Changelog (Keep a Changelog 1.1.0)

- Applies only when the project has a `CHANGELOG.md`. Never create one unasked; the orchestrator offers to adopt it once.
- Format: `CHANGELOG.md` at repo root, `## [Unreleased]` on top, sections Added, Changed, Deprecated, Removed, Fixed, Security, newest release first, `## [x.y.z] - YYYY-MM-DD`.
- Upkeep: every user-visible change adds a line under `[Unreleased]` in the same commit as the change. Internal-only changes (tests, invisible refactors, plan files) add none.
- Entries describe behaviour. They contain no secrets, tokens, internal hostnames or private paths.
- Link references at the bottom use commit SHAs (`compare/<prev-release-sha>...<release-sha>`, `[Unreleased]` → `compare/<release-sha>...HEAD`), never tag names, because tags stay local.

## Versions (SemVer 2.0.0)

- major.minor.patch. Before 1.0, minor goes up once per delivery phase; every other release before 1.0 is a patch.
- Each release gets a local annotated tag `vX.Y.Z` on the release commit. Tags are never pushed: no `--tags`, no `--follow-tags`, no pushing a tag ref.

## Release cut (at each milestone)

One commit `chore(release): vX.Y.Z` that: moves `[Unreleased]` entries into the new version section, bumps the project's version file, updates the README progress section, updates `CLAUDE.md`. Then the local tag `vX.Y.Z`.

## Commits (Conventional Commits 1.0.0)

- `type(scope): summary`, imperative, summary at most 72 chars. Types: feat, fix, docs, refactor, test, chore, perf, build, ci, style, revert.
- Breaking change: `!` after type/scope or a `BREAKING CHANGE:` footer.
- Changelog mapping: feat is Added or Changed, fix is Fixed, a removal is Removed, a security fix is Security.
- Stage named files only. Never `git add -A` or `git add .`. Never commit secrets, `.env`, credentials or `.claude/settings.local.json`.

## Branches and PRs (GitHub Flow)

- One branch per request off up-to-date `main`, named `<type>/<short-slug>`. Never commit directly to `main`.
- One PR per request. The full test suite passes before merge. Merge with `gh pr merge --merge`, never `--admin`; delete the branch after merge; update local `main` with `--ff-only`.
- Never force-push `main`. Ask the user first before `reset --hard`, `branch -D` or `clean -fdx`.

## Who runs git

The main session runs git read commands only: `status`, `log`, `diff`, `show`, `branch` (list), `tag` (list), plain `fetch`. Every git write goes to a `Mode: git` dispatch; the brief gives intent (files, what changed) and the agent writes the commit message and PR body. The orchestrator decides when a milestone is reached and dispatches the release cut as `Mode: git`.
