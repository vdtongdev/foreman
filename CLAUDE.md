# foreman

Claude Code plugin. Versioning and git rules: `skills/releasing/SKILL.md`. A project's own convention wins; here this file is it.

## Tests

`python -m pytest -q`

## Release checklist

Work in a worktree: `git worktree add .worktrees/<slug> -b chore/release-x.y.z main`, then `codegraph init -y <worktree>`; use the codegraph CLI there, never the MCP tool. After merge: `codegraph uninit -f <worktree>`, then `git worktree remove`.

1. Move the `[Unreleased]` entries in `CHANGELOG.md` into a new `## [x.y.z] - YYYY-MM-DD` section; update the link references.
2. Bump `version` in `.claude-plugin/plugin.json`.
3. Update the README `## Progress` section and this file.
4. Commit as `chore(release): vX.Y.Z`.
5. Tag that commit locally: `git tag -a vX.Y.Z -m "vX.Y.Z"`.
6. Never push tags.
