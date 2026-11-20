# Versioning and git rules Implementation Plan

> **For agentic workers:** Execute with the foreman loop (`foreman:orchestrating`). Tasks are sequential (1, 2, 3). The verifier runs after tasks 1 and 2; task 3 is git only.

**Goal:** Add a `releasing` skill (Keep a Changelog, SemVer, Conventional Commits, GitHub Flow, local-only tags), wire it into the agents and orchestrator rules, and make the foreman repo follow it (CHANGELOG, CLAUDE.md, README Progress, version 0.2.1, local tags).

**Spec:** `docs/specs/2026-11-20-versioning-git-rules-design.md`

## Global Constraints

- Agent files keep: `BLOCKED: plan`, `DISPUTE`, `docs/plans/`, verdict strings, `## Evidence` / `## Unverified`, frontmatter, and the MVC sentences added in commit 95a18ec.
- Frontmatter values containing `: ` are quoted (`test_frontmatter_values_with_colon_space_are_quoted`).
- `ORCHESTRATOR_RULES` stays within the line cap in `test_orchestrator_rules_cover_bugs_within_line_cap` (`<= 15` lines; currently 14, so add at most one line or merge into an existing one).
- Foreman's own `CHANGELOG.md` does not exist until Task 2, so Task 1 adds no `[Unreleased]` line; Task 2 writes the 0.2.1 section that already lists these changes. The verifier treats this as not a FAIL for tasks 1 and 2.
- No command, text or example in skills/agents pushes tags (`--tags`, `--follow-tags`, tag refs) except as a "never" rule.
- Full suite: `python -m pytest -q` passes after tasks 1 and 2.
- Plug-and-play: on other projects the changelog rules apply only when the project has a `CHANGELOG.md`. Agents never create one unasked; the skill tells the orchestrator to offer adopting it. The planner, implementer, ui and verifier wording must carry this condition, so the verifier never fails a task for a missing `[Unreleased]` line in a project with no `CHANGELOG.md`.
- The verifier also runs after Task 3, read-only, and checks Task 3's acceptance: tags, `ls-remote`, the files in each commit, and that main equals origin/main.

## Review Focus

1. The skill states the project's own convention wins when one exists.
2. Orchestrator text allows only git reads; every git write goes to `Mode: git`.
3. Tag `v0.2.0` sits on eaf4fb6 and `v0.2.1` on the release commit; neither is on `origin`.

---

### Task 1: Releasing skill, agent and orchestrator wiring, with tests

**Agent:** implementer
**Files:** Create `skills/releasing/SKILL.md`; Modify `agents/planner.md`, `agents/implementer.md`, `agents/ui.md`, `agents/verifier.md`, `skills/orchestrating/SKILL.md`, `scripts/foreman_hooks.py` (`ORCHESTRATOR_RULES` text only); Test `tests/test_components.py`, `tests/test_context_hooks.py`

- [ ] **Step 1 (tests first):** In `tests/test_components.py` add `"releasing"` to the list in `test_skills_have_frontmatter`. Add `test_releasing_skill_content` (reads `skills/releasing/SKILL.md`; asserts it names `Keep a Changelog`, `SemVer`, `Conventional Commits`, `[Unreleased]`, `vX.Y.Z`, `Mode: git`, and that a project's own convention wins). Add `test_agents_reference_changelog_rule` (planner, implementer, ui, verifier each contain `CHANGELOG.md` and `[Unreleased]`; verifier also contains `--follow-tags`). In `tests/test_context_hooks.py` add `test_orchestrator_rules_git_reads_only` (rules mention `Mode: git` and `git read`), keeping the existing line-cap test unchanged.
- [ ] **Step 2:** Run `python -m pytest tests/test_components.py tests/test_context_hooks.py -q`; expected: the new tests FAIL (red).
- [ ] **Step 3:** Write `skills/releasing/SKILL.md` per spec sections "Versioning rules" and "Git rules": frontmatter `name: releasing` and a `description` starting "Use when ..." (quote it if it contains `: `); changelog format and sections; SemVer with the pre-1.0 rule; local annotated tags, never pushed; upkeep rule; release-cut checklist (`chore(release): vX.Y.Z`, version file, README progress, CLAUDE.md, then tag); Conventional Commits with type to changelog mapping; GitHub Flow branches `<type>/<short-slug>`; named-file staging; PR rules (suite passes, `gh pr merge --merge`, no `--admin`, delete branch, `--ff-only` local main); main-session git reads only, writes via `Mode: git`; destructive git asks the user first; changelog entries carry no secrets, tokens, internal hostnames or private paths.
- [ ] **Step 4:** Edit the four agents: planner adds `CHANGELOG.md` to `Files:` and the acceptance line "adds an [Unreleased] entry" for user-visible tasks; implementer and ui add the `[Unreleased]` line in the same diff as a user-visible change, and implementer documents `Mode: git` (named-file staging, Conventional Commits, never push tags); verifier returns `FAIL: impl` for a user-visible change with no `[Unreleased]` line, treats `CHANGELOG.md` edits as in scope, and fails any brief or diff adding `--tags` / `--follow-tags`. Add one sentence to `skills/orchestrating/SKILL.md`: git reads only in the main session, release cut dispatched as `Mode: git` at a milestone.
- [ ] **Step 5:** In `ORCHESTRATOR_RULES` add one line (total 15, or merge into an existing line): main session runs git read commands only (`status`, `log`, `diff`, `show`, `branch`, `tag` list, plain `fetch`); every git write goes to a `Mode: git` dispatch with intent in the brief; see skill `foreman:releasing`.
- [ ] **Step 6:** Run `python -m pytest -q`; expected: PASS, including the line-cap test.

**Acceptance:**
- All Step 1 tests fail before Step 3-5 and pass after; full suite passes.
- Existing agent invariants (Global Constraints) still hold: `git diff -U0 agents/` removes no `BLOCKED: plan`, `DISPUTE`, MVC or verdict text.
- Security (tags): `grep -rnE -- "--tags|--follow-tags" skills agents` matches only "never" rules and the verifier's fail rule; no push-tags command exists.
- Security (secrets): the skill requires named-file staging and forbids committing `.env`, credentials and `.claude/settings.local.json`.
- Security (destructive git): the skill forbids force-push to `main`, `--admin`, and asks the user before `reset --hard`, `branch -D`, `clean -fdx`.
- Security (changelog content): the skill states entries describe behaviour and contain no secrets, tokens, internal hostnames or private paths.
- Planner/implementer/ui/verifier changelog rule is present (the "adds an [Unreleased] entry" wording is in `agents/planner.md`).

### Task 2: Foreman repo release files and 0.2.1 version bump

**Agent:** implementer
**Files:** Create `CHANGELOG.md`, `CLAUDE.md`; Modify `README.md`, `.claude-plugin/plugin.json`; Test `tests/test_components.py`

- [ ] **Step 1 (tests first):** Add `test_changelog_keep_a_changelog` (headings in order: `## [Unreleased]`, `## [0.2.1] - 2026-11-20`, `## [0.2.0] - 2026-11-17`; dates match `\d{4}-\d{2}-\d{2}`; only sections Added/Changed/Deprecated/Removed/Fixed/Security; link references present at the bottom) and `test_plugin_version_matches_changelog` (`plugin.json` version equals the newest released heading in `CHANGELOG.md`, `0.2.1`). Run; expected: FAIL.
- [ ] **Step 2:** Create `CHANGELOG.md` per spec "Foreman repo changes": empty `[Unreleased]`, `[0.2.1]` (Added: releasing skill and git rules; MVC layering rules for agents), `[0.2.0]` (loop v2, taken from `git show eaf4fb6 --stat` and its README/spec), link references at the bottom (compare URLs, no tag pushes implied).
- [ ] **Step 3:** Create short `CLAUDE.md`: points to `skills/releasing/SKILL.md`, the test command `python -m pytest -q`, and the release checklist (move `[Unreleased]`, bump `.claude-plugin/plugin.json`, README Progress, CLAUDE.md, commit `chore(release): vX.Y.Z`, local tag, never push tags).
- [ ] **Step 4:** README: add `## Progress` (current version 0.2.1; one line per delivery phase: 0.1 and 0.2 contents from existing README/spec text, 0.2.1 patch) and list the releasing skill where skills appear under Layout/Agents. Set `plugin.json` `"version": "0.2.1"`.
- [ ] **Step 5:** Run `python -m pytest -q`; expected: PASS.

**Acceptance:**
- `python -m pytest -q` passes; the Step 1 tests fail before and pass after.
- `.claude-plugin/plugin.json` version is `0.2.1`.
- `CHANGELOG.md` parses as Keep a Changelog 1.1.0 with ISO dates.
- Security (changelog content): `grep -nEi "token|secret|password|C:\\\\Users|/home/" CHANGELOG.md CLAUDE.md` returns nothing; entries describe behaviour only.
- Security (tags): neither `CLAUDE.md` nor `README.md` shows a command that pushes tags.

### Task 3: Branch, commits, PR, merge, local tags (git only)

**Agent:** implementer
**Files:** none edited. Git operations only on the files from tasks 1 and 2, plus `docs/specs/2026-11-20-versioning-git-rules-design.md` and `docs/plans/2026-11-20-versioning-git-rules.md`; never `TODO.md`, `problems/`, `.codegraph/`.

**Brief must start with `Mode: git` and `Plan: docs/plans/2026-11-20-versioning-git-rules.md`.**

- [ ] **Step 1:** `git switch main`, `git pull --ff-only` (or `git fetch` then confirm up to date), then `git switch -c feat/versioning-git-rules`.
- [ ] **Step 2:** Commit 1, named files `skills/releasing/SKILL.md agents/planner.md agents/implementer.md agents/ui.md agents/verifier.md skills/orchestrating/SKILL.md scripts/foreman_hooks.py tests/test_components.py tests/test_context_hooks.py` plus the spec and plan: `feat(releasing): add releasing skill and wire it into agents`. Agent writes the body.
- [ ] **Step 3:** Commit 2, the release cut, files `CHANGELOG.md CLAUDE.md README.md .claude-plugin/plugin.json`: `chore(release): v0.2.1`.
- [ ] **Step 4:** Run `python -m pytest -q`; expected PASS. Then `git push -u origin feat/versioning-git-rules` (branch only), `gh pr create` (agent writes title and body), `gh pr merge --merge --delete-branch` (no `--admin`).
- [ ] **Step 5:** `git switch main`, `git pull --ff-only`. The release commit `chore(release): v0.2.1` is reachable from main (merge commit keeps it).
- [ ] **Step 6:** Local annotated tags: `git tag -a v0.2.0 eaf4fb6 -m "v0.2.0"` and `git tag -a v0.2.1 <sha of chore(release): v0.2.1> -m "v0.2.1"`. Do not push them.

**Acceptance:**
- `git tag` lists `v0.2.0` and `v0.2.1`; `git rev-list -n1 v0.2.0` starts with `eaf4fb6`; `git rev-list -n1 v0.2.1` equals the release commit sha.
- `git ls-remote --tags origin` lists neither tag.
- Security (tags): no executed command contains `--tags`, `--follow-tags` or a push of a tag ref (verifier reads the agent's command log).
- Security (secrets): `git show --stat` for each commit lists only the named files; `TODO.md`, `problems/`, `.codegraph/` are not committed; no `git add -A` or `git add .`.
- Security (destructive git): no force-push, `--admin`, `reset --hard`, `branch -D` or `clean -fdx` was run; `main` has no direct commits (merge arrived via the PR).
- Commit subjects are Conventional Commits, each at most 72 characters; local `main` equals `origin/main` after `--ff-only`.
