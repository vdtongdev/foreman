# Versioning and git rules

Date: 2026-11-20. Status: approved by user (scope: both; Conventional Commits; merge commits).

## Goal

Foreman has no changelog, no tags and no standing git rules; PR #3 merged without a version bump, so installs never got it. Add one standard for versioning and git that foreman's agents apply on any project, and that the foreman repo itself follows.

## Scope

1. **Plugin:** a new skill `skills/releasing/SKILL.md` (versioning + git), wired into the agents and the orchestrator rules. It applies on any project unless that project already documents its own convention (CONTRIBUTING, CLAUDE.md, an existing changelog format); then the project's convention wins.
2. **Foreman repo:** follows the skill: `CHANGELOG.md`, `CLAUDE.md`, README progress section, version bump, local tags.

## Versioning rules (user-given)

- **Changelog format:** Keep a Changelog 1.1.0 (https://keepachangelog.com/en/1.1.0/). `CHANGELOG.md` at repo root; `## [Unreleased]` on top; sections Added, Changed, Deprecated, Removed, Fixed, Security; newest release first; `## [x.y.z] - YYYY-MM-DD`.
- **Versions:** SemVer 2.0.0 (major.minor.patch). Before 1.0, minor goes up once per delivery phase; every other release before 1.0 is a patch.
- **Tags:** each release gets a local annotated tag `vX.Y.Z` on the release commit. Tags are never pushed (no `git push --tags`, `--follow-tags`, or pushing a tag ref).
- **Upkeep:** every user-visible change adds a line under `[Unreleased]` in the same commit as the change. Internal-only changes (tests, refactors with no visible effect, plan files) add none.
- **Release cut (at each milestone):** one commit that moves `[Unreleased]` entries into a new version section, bumps the project's version file (foreman: `.claude-plugin/plugin.json`), updates the README progress section and updates `CLAUDE.md`. Commit message `chore(release): vX.Y.Z`. Then the local tag.

## Git rules (suggested standard, user-approved)

- **Commits:** Conventional Commits 1.0.0 (https://www.conventionalcommits.org/en/v1.0.0/): `type(scope): summary`, imperative, summary ≤ 72 chars. Types: feat, fix, docs, refactor, test, chore, perf, build, ci, style, revert. Breaking change: `!` after type/scope or `BREAKING CHANGE:` footer. Changelog mapping: feat → Added or Changed, fix → Fixed, a removal → Removed, security fix → Security.
- **Branches:** GitHub Flow. One branch per request off up-to-date `main`, named `<type>/<short-slug>` (e.g. `feat/mvc-agent-rules`). Never commit directly to `main`.
- **Staging:** stage named files only; never `git add -A` / `git add .`. Never commit secrets, `.env`, credentials or local settings.
- **PRs:** one PR per request; the full test suite passes before merge; merge with a merge commit (`gh pr merge --merge`); never `--admin`; never force-push `main`; delete the branch after merge; update local `main` with `--ff-only`.
- **Main session (orchestrator):** git read commands only: `status`, `log`, `diff`, `show`, `branch` (list), `tag` (list), plain `fetch`. Every git write goes to a `Mode: git` dispatch. The brief gives intent (files, what changed); the agent writes the commit message and PR body.

## Who does what

- **planner:** for tasks with a user-visible change, include `CHANGELOG.md` in `Files:` and an acceptance line "adds an [Unreleased] entry".
- **implementer / ui:** add the `[Unreleased]` line in the same diff as a user-visible change.
- **verifier:** a user-visible change without an `[Unreleased]` line is `FAIL: impl`. `CHANGELOG.md` edits are not a scope failure.
- **orchestrator:** decides when a milestone is reached and dispatches the release cut (`Mode: git`); never runs git writes itself.

## Foreman repo changes

- Create `CHANGELOG.md`: `[Unreleased]` (empty after the cut), `[0.2.1] - 2026-11-20` (MVC layering rules; versioning and git rules), `[0.2.0] - 2026-11-17` (loop v2, from commit eaf4fb6's README/spec), with link references at the bottom.
- Create `CLAUDE.md` (short): points to the releasing skill, the test command, and the release checklist.
- README: add a `## Progress` section (current version, what each delivery phase shipped); mention the releasing skill under Layout/Agents where skills are listed.
- Cut 0.2.1 (patch: no new delivery phase): `plugin.json` → `0.2.1`.
- Local tags: `v0.2.0` on eaf4fb6, `v0.2.1` on the release commit. Not pushed.

## Security

- **Tags never leave the machine:** no command in skills/agents pushes tags; verifier fails any brief or diff that adds `--tags`/`--follow-tags`.
- **Secrets:** named-file staging only; the skill forbids committing `.env`, credentials, `.claude/settings.local.json`.
- **Destructive git:** no force-push to `main`, no `--admin`, no `reset --hard` / `branch -D` / `clean -fdx` without asking the user.
- **Changelog content:** entries describe behaviour; no secrets, tokens, internal hostnames or private paths.
- Auth, input validation, data exposure beyond the above: none applicable.

## Out of scope

- A hook enforcing main-session git reads (planned with the Haiku git agent, option 2).
- Pushing tags or GitHub Releases.

## Acceptance

- `python -m pytest -q` passes, with tests that: the releasing skill exists with frontmatter and names Keep a Changelog, SemVer, Conventional Commits, local-only tags and `[Unreleased]`; planner/implementer/ui/verifier reference the changelog rule; orchestrator rules mention git reads only (within the existing line cap test).
- `CHANGELOG.md` parses as Keep a Changelog (headings in order, dates ISO).
- `plugin.json` version is `0.2.1`; `git tag` lists `v0.2.0` and `v0.2.1`; `git ls-remote --tags origin` lists neither.
