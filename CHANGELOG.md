# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.2] - 2026-11-20

### Added

- `antipatterns` skill (scope, code smells, design patterns, agent workflow) that the implementer and ui follow and the verifier enforces only for clear-cut items; memory entry-fitness rules extended.
- Every request works in its own git worktree and branch, and a branch guard denies subagent edits on the default branch (fails open on any git error).
- Worktrees get their own codegraph index when the project already uses codegraph, and cleanup uninits it before removing the worktree.

### Fixed

- Changelog links use commit SHAs, since release tags stay local.
- The merge cleanup deletes the remote branch when a worktree held the local one (merge without `--delete-branch`, then `git push origin --delete`).

## [0.2.1] - 2026-11-20

### Added

- `releasing` skill: Keep a Changelog, SemVer, Conventional Commits, GitHub Flow, and local-only release tags.
- Orchestrator rule: the main session runs git reads only; every git write goes to a `Mode: git` dispatch.
- Planner, implementer, ui and verifier apply the `[Unreleased]` changelog rule when a project has a `CHANGELOG.md`.
- MVC layering rules for the agents.

## [0.2.0] - 2026-11-17

### Added

- Loop v2: a quick lane and a plan lane (spec, planner, builder), with each failure routed to the step that can fix it.
- `ui`, `planner` and `builder` agents; the verifier issues one verdict per review.
- Search guard: the orchestrator delegates searches to `generalist` in `Mode: lookup`.
- Optional Impeccable plugin for the `ui` agent and the verifier's UI detector.

### Changed

- Plan gate accepts `Mode: quick` briefs and checks that every task in a builder plan has `Agent:` and `Files:` lines.
- Bug requests use the same loop, starting with `implementer` in `Mode: diagnose`.

### Removed

- The `expert` agent.

[Unreleased]: https://github.com/vdtongdev/foreman/compare/c242f14...HEAD
[0.2.2]: https://github.com/vdtongdev/foreman/compare/9c93ac8...c242f14
[0.2.1]: https://github.com/vdtongdev/foreman/compare/eaf4fb6...9c93ac8
[0.2.0]: https://github.com/vdtongdev/foreman/commit/eaf4fb6
