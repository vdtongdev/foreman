# Anti-patterns skill Implementation Plan

> **For agentic workers:** Execute with the foreman loop (`foreman:orchestrating`). Tasks are sequential (0, 1, 2, 3). The verifier runs after tasks 1 and 2 (they change files) and read-only after task 3. Task 0 only creates the worktree (no tracked file changes) and is checked by its own acceptance, as in the codegraph-worktrees plan. Tasks 0 and 3 are `Mode: git`.

**Goal:** Add one `antipatterns` skill (four groups: scope and simplicity, code smells, design patterns, agent workflow), wire it into the implementer, ui, verifier and orchestrating text, borrow the entry-fitness rules into the memory skill, and document it in README and CHANGELOG. Text only. Ship through a PR with no release cut and no tags.

**Spec:** `docs/specs/2026-11-20-antipatterns-design.md`

## Global Constraints

- **Worktree:** `.worktrees/antipatterns` (relative to the main checkout root; resolve to an absolute path in briefs). **Branch:** `feat/antipatterns`. Tasks 1 to 3 carry `Worktree:`, `Branch:` and `Plan: docs/plans/2026-11-20-antipatterns.md`. Agents edit, test and run git only inside that path.
- **Codegraph in the worktree:** the main checkout has `.codegraph/`, so task 0 runs `codegraph init -y` there. Inside the worktree agents use the codegraph CLI only (`codegraph explore`, `node`, `callers`, run with the worktree as working directory; `codegraph sync` after edits). Never pass the worktree as the MCP `projectPath` (the MCP server keeps the DB locked and blocks `codegraph uninit` and `git worktree remove`). Put this in every brief.
- The spec says to run after `2026-11-20-codegraph-worktrees` is merged. It is: main `c654567` is its merge commit (`Merge pull request #7`).
- This plan and the spec live untracked in the main checkout. Task 0 copies both into the worktree; if either changed since, task 3 re-copies them and checks identity with `git diff --no-index` before committing.
- Follow `skills/releasing/SKILL.md`: Conventional Commits, named-file staging (never `git add -A` / `git add .`), no `--tags` / `--follow-tags`, GitHub Flow, worktree-first. No release cut, no version bump, no tags. The `[Unreleased]` entry is written in task 2.
- Untracked files in the main checkout that are not part of this work (`.codegraph/`, `TODO.md`, `problems/`) are never copied, staged or deleted. The main `.codegraph/` is never uninit-ed.
- **Invariants kept in every agent file:** `BLOCKED: plan`, `DISPUTE`, `docs/plans/`, the verdict strings, `## Evidence` / `## Unverified`, the MVC sentences, the changelog sentence, `Worktree:` lines, the codegraph CLI rule (`codegraph explore`, never a worktree as `projectPath`), frontmatter (values containing `: ` stay quoted; `test_frontmatter_values_with_colon_space_are_quoted`).
- `ORCHESTRATOR_RULES` in `scripts/foreman_hooks.py` is at its 15-line cap: this plan does not touch that file. The single orchestrator reference goes into `skills/orchestrating/SKILL.md` (one sentence folded into an existing paragraph, no new section).
- **Karpathy license finding (checked 2026-11-20):** the installed `karpathy-skills` marketplace directory has no `LICENSE` file (`ls` shows CLAUDE.md, CURSOR.md, EXAMPLES.md, README.md, README.zh.md, skills/, .claude-plugin/, .cursor/). The license is declared as MIT in three places: `skills/karpathy-guidelines/SKILL.md` frontmatter (`license: MIT`), `README.md:169-171` (`## License` / `MIT`) and `.claude-plugin/*.json` (`"license": "MIT"`). MIT requires the copyright notice to travel with verbatim copies, and no copyright line or LICENSE text is available here. Decision: paraphrase only, no verbatim sentences from karpathy-guidelines, and credit it by name with its MIT declaration. Task 1 acceptance enforces this.
- **Fitness borrow (checked against the raw `antipatterning/SKILL.md`, 2026-11-20):** `skills/memory/SKILL.md` already has the five criteria as one Rules bullet (recurrent, not caught by a tool or test, not duplicated, still relevant, non-obvious). What it lacks, and what task 1 adds in foreman's own words (no copied text): a one-shot lesson already applied everywhere is dead weight; entries sharing a root rule are merged, with different failure modes as one entry's guidance, not two entries; an entry whose condition the codebase has moved past is deprecated. Do not duplicate the existing bullet.
- Full suite: `python -m pytest -q` (inside the worktree) passes after tasks 1 and 2. Baseline on main `c654567`: 138 passed, 1 skipped.

## Review Focus

1. The skill has exactly four group headings, is about 60 lines, every item is one line with a "why".
2. The verifier's FAIL list is exactly the four clear-cut items (interface or factory with one implementation, added magic number in logic, duplicated block of 3 or more copies, function over 80 lines added by the change), all introduced by the diff; everything else is an Unverified note, never a FAIL.
3. No verbatim karpathy text; credit present.
4. No agent invariant removed; `scripts/foreman_hooks.py` untouched; the generalist file untouched (it has no Bash and is not a code writer).
5. Security (spec): no new commands, hooks or network access; the diff touches text and tests only.

---

### Task 0: Create the worktree and index it

**Agent:** implementer
**Files:** none tracked. Creates `.worktrees/antipatterns` (branch `feat/antipatterns`); copies `docs/specs/2026-11-20-antipatterns-design.md` and `docs/plans/2026-11-20-antipatterns.md` into the worktree at the same paths; creates the worktree's own untracked `.codegraph/`.

Brief carries `Mode: git` and `Plan: docs/plans/2026-11-20-antipatterns.md`. Every codegraph command is the CLI; never the MCP tool with the worktree as `projectPath`.

- [ ] **Step 1:** In the main checkout: `git fetch`, then `git merge --ff-only origin/main` (only untracked files exist, so this must succeed; if it refuses, stop and report, never reset). Confirm `git rev-parse main` equals `origin/main`.
- [ ] **Step 2:** If `.worktrees/` is not already a line in the file `git rev-parse --git-path info/exclude` names, append it. Do not touch the tracked `.gitignore`.
- [ ] **Step 3:** `git worktree add .worktrees/antipatterns -b feat/antipatterns main`.
- [ ] **Step 4:** Copy the spec and this plan from the main checkout into the worktree at the same relative paths.
- [ ] **Step 5:** The main checkout has `.codegraph/`, so run `codegraph init -y <absolute worktree path>`, then `codegraph status <path>` and `git -C <path> status --short`.

**Acceptance:**
- `git worktree list` shows `.worktrees/antipatterns` on `[feat/antipatterns]`; its `HEAD` equals `git rev-parse main`.
- `git status --short` in the main checkout does not list `.worktrees/` and still lists the untracked spec, plan, `.codegraph/`, `TODO.md`, `problems/`.
- `git diff --no-index` between each main-checkout copy and its worktree copy prints nothing.
- `<worktree>/.codegraph/` exists and `codegraph status <worktree>` reports an index with files.
- Security: `git diff -- .gitignore` is empty; no `codegraph uninit` or re-index touched the main checkout; no commit, push or tag was made.

---

### Task 1: The antipatterns skill and the memory fitness rules (tests first)

**Agent:** implementer
**Files:** Create `skills/antipatterns/SKILL.md`; Modify `skills/memory/SKILL.md`; Test `tests/test_components.py`

Brief carries `Worktree:`, `Branch:`, `Plan:`, the codegraph CLI-only rule and the spec path. Content comes from the spec's "Skill content" section; sources are `C:\Users\tong2\.claude\plugins\marketplaces\karpathy-skills\skills\karpathy-guidelines\SKILL.md` (read it; paraphrase, see the license finding above) and the Global Constraints fitness-borrow paragraph.

- [ ] **Step 1 (tests first):** In `tests/test_components.py`:
  - Add `"antipatterns"` to the skill list in `test_skills_have_frontmatter`.
  - `test_antipatterns_skill_content`: `skills/antipatterns/SKILL.md` parses with `memory.parse_frontmatter`, `name == "antipatterns"`, non-empty description; it contains exactly four `## ` headings, in order: `## Scope and simplicity`, `## Code smells`, `## Design patterns`, `## Agent workflow`; it contains `karpathy-guidelines` and `MIT`; its length is between 40 and 80 lines; every bullet line (`- `) is a single line containing a why (assert each group has at least 4 bullets and each bullet contains `: ` or ` because ` or ` so `; match the separator you write). It mentions the clear-cut thresholds as guidance (`50 lines`, `3 nesting`, `third copy`) and the design-pattern rule (`2 or more concrete variants`), the MVC sentence (`MVC`), and the seven agent-workflow items by short keyword (`dispatch`, `already quoted`, `intent`, `projectPath`, `by layer`, `default branch`, `git add -A`).
  - `test_antipatterns_no_verbatim_karpathy`: read the installed karpathy `SKILL.md` if the path exists (skip otherwise, with `pytest.skip`); no non-empty line of 30 or more characters from it appears verbatim in the antipatterns skill.
  - `test_memory_skill_fitness_rules`: `skills/memory/SKILL.md` contains the phrases you write for: a one-shot lesson already applied everywhere is dead weight; merge entries that share a root rule; deprecate an entry once the code has moved past its condition (assert the exact phrases, for example `dead weight`, `share a root rule`, `moved past`), and the original `recurrent` rule is still present exactly once (no duplicated bullet).
- [ ] **Step 2:** Run `python -m pytest tests/test_components.py -q` in the worktree; expected: the new tests FAIL (red). Paste the failure summary.
- [ ] **Step 3:** Write `skills/antipatterns/SKILL.md` (about 60 lines). Frontmatter: `name: antipatterns` and a `description` that begins "Use when" (quote it, since it will contain `: `). One intro line crediting `karpathy-guidelines` (MIT, plugin `karpathy-skills`) as the source of group 1's ideas, written in foreman's own words. Four groups, each bullet one line with a why:
  1. **Scope and simplicity:** no features beyond the brief; no abstraction for single-use code; no options nobody asked for; no handling for impossible errors; do not refactor or reformat adjacent code; mention unrelated dead code instead of deleting it; if something is unclear, stop and ask instead of picking silently.
  2. **Code smells:** a function over about 50 lines or with more than 3 nesting levels; a class or module with unrelated responsibilities (god object); a duplicated block, from the third copy on; magic numbers or strings without a named constant; dead code the change introduced; boolean flag parameters that switch behaviour.
  3. **Design patterns:** use a GoF pattern only when 2 or more concrete variants exist now or the codebase already uses that pattern; flag an interface with one implementation, a factory building one type, and a Visitor or Abstract Factory chain without a present need; keep the project's existing MVC layering rules (do not introduce layers into a project without them).
  4. **Agent workflow:** the orchestrator doing simple work itself instead of dispatching; re-checking evidence a subagent already quoted; briefs that dictate commands instead of intent; querying a worktree through the codegraph MCP tool (use the CLI, never `projectPath`); splitting tasks by layer instead of by feature; writing to the default branch; committing with `git add -A`.
  A closing line: the verifier fails only the clear-cut items in groups 2 and 3 listed in `agents/verifier.md`; everything else is a note.
- [ ] **Step 4:** `skills/memory/SKILL.md`: in "Rules", add the three borrowed fitness rules in your own words without repeating the existing "recurrent, not already caught..." bullet (either one new bullet or a short sentence appended to it; do not add a heading). No other change to that file.
- [ ] **Step 5:** Run `python -m pytest -q` in the worktree; expected: PASS (baseline 138 passed, 1 skipped, plus the new tests). Run `codegraph sync <worktree>` after the edits if any later query is needed.

**Acceptance:**
- The new tests were seen failing first, then `python -m pytest -q` passes (counts quoted).
- `skills/antipatterns/SKILL.md` has valid frontmatter (quoted description), the four group headings, about 60 lines (`wc -l` quoted), credits `karpathy-guidelines` with MIT, and passes the no-verbatim test.
- Security (spec: text only): `git diff --name-only main..HEAD` lists only `skills/antipatterns/SKILL.md`, `skills/memory/SKILL.md`, `tests/test_components.py` and the task 0 `docs/` copies; no hook, script, command or network change.
- Security (spec: licensing): no verbatim karpathy line of 30 or more characters in the skill; the credit and MIT mention are present.
- `skills/memory/SKILL.md` contains the three borrowed rules and one copy of the original `recurrent` bullet; its frontmatter and tables are unchanged.
- No agent file and no `scripts/foreman_hooks.py` change in this task.

---

### Task 2: Wire the skill into agents, orchestrating text, README and CHANGELOG (tests first)

**Agent:** implementer
**Files:** Modify `agents/implementer.md`, `agents/ui.md`, `agents/verifier.md`, `skills/orchestrating/SKILL.md`, `README.md`, `CHANGELOG.md`; Test `tests/test_components.py`

Brief carries `Worktree:`, `Branch:`, `Plan:` and the codegraph CLI-only rule. Task 1 must have PASSed. `agents/planner.md`, `agents/builder.md`, `agents/generalist.md` and `scripts/foreman_hooks.py` are not changed.

- [ ] **Step 1 (tests first):** In `tests/test_components.py` add:
  - `test_task_agents_load_antipatterns`: `agents/implementer.md` and `agents/ui.md` each contain `antipatterns` in a sentence that says to load the skill before writing code (assert the exact phrase you write, for example `Load the `foreman:antipatterns` skill before writing code`); neither file loses `BLOCKED: plan`, `DISPUTE`, the MVC sentence, `Worktree:` or `codegraph explore`.
  - `test_verifier_antipattern_fail_rules`: `agents/verifier.md` contains the four clear-cut items as written (`interface or factory with one implementation`, `added magic number in logic`, `duplicated block of 3 or more copies`, `function over 80 lines`), says they apply only to items introduced by the diff, says everything else is a note under Unverified and not a FAIL (assert the exact phrase you write, for example `not a FAIL`), and still contains `FAIL: impl`, `FAIL: plan`, `FAIL: spec`, `FAIL: env` and `PASS`.
  - `test_orchestrating_references_antipatterns`: `skills/orchestrating/SKILL.md` contains `foreman:antipatterns` exactly once, in a sentence naming the agent-workflow group; `ORCHESTRATOR_RULES` line count is unchanged (the existing 15-line cap test still passes; do not edit `scripts/foreman_hooks.py`).
  - `test_antipatterns_in_readme_and_changelog`: `README.md` lists `antipatterns` in the Layout skills line (`skills/` row) and in one sentence describing it; `CHANGELOG.md` has an `antipatterns` line under `## [Unreleased]` before the first `## [0.` heading, within `### Added`.
  - Keep the existing invariant tests green (`test_agents_codegraph_cli_only_in_worktrees`, `test_agents_follow_mvc_layering`, `test_agents_reference_changelog_rule`, the frontmatter test, the 15-line cap test).
- [ ] **Step 2:** Run `python -m pytest tests/test_components.py -q`; expected: the new tests FAIL (red). Paste the failure summary.
- [ ] **Step 3:** `agents/implementer.md` and `agents/ui.md`: add one sentence to the existing second paragraph (after the "Make the smallest change..." sentence): load the `foreman:antipatterns` skill with the Skill tool before writing code and follow it. Keep the file's other sentences and the frontmatter unchanged.
- [ ] **Step 4:** `agents/verifier.md`: add to the existing review paragraph (no new section): for the diff only, `FAIL: impl` for the clear-cut `antipatterns` items introduced by the change, namely an interface or factory with one implementation, an added magic number in logic, a duplicated block of 3 or more copies, or a function over 80 lines added by the change (evidence: file:line); every other smell or design-pattern concern is a note under Unverified, not a FAIL (this avoids FAIL loops on judgment calls). Keep every invariant sentence (verdict list, scope check, Security, MVC, changelog, tags, detector, regression test) and the frontmatter.
- [ ] **Step 5:** `skills/orchestrating/SKILL.md`: fold one clause into the existing paragraph that starts "Report "done" only by quoting..." (or the "Task brief template" intro): the agent-workflow group of `foreman:antipatterns` lists the orchestrator mistakes to avoid. No new section, no table change.
- [ ] **Step 6:** `README.md`: add `antipatterns/` to the Layout `skills/` row, and one sentence under "Agents" (after the Evidence sentence) saying the implementer and ui load `antipatterns` and the verifier fails only its clear-cut items. No new section, no version change.
- [ ] **Step 7:** `CHANGELOG.md`: under `## [Unreleased]` → `### Added` add one behaviour line: an `antipatterns` skill (scope, code smells, design patterns, agent workflow) that the implementer and ui follow and the verifier enforces only for clear-cut items; memory entry-fitness rules extended. No secrets or private paths; no version bump.
- [ ] **Step 8:** Run `python -m pytest -q` in the worktree; expected: PASS.

**Acceptance:**
- `python -m pytest -q` passes; the four new tests were seen failing first.
- `implementer` and `ui` carry the load-before-writing sentence; `verifier` lists exactly the four clear-cut FAIL items, limited to items introduced by the diff, plus the note-only rule; no other smell or pattern item is a FAIL.
- Security (spec: no new commands, hooks, network): `git diff main..HEAD -- scripts/ hooks/ bin/` is empty and the text adds no command beyond the existing ones.
- Invariants intact in all three edited agent files (`BLOCKED: plan`, `DISPUTE`, `docs/plans/`, verdict strings, `## Evidence`, `## Unverified`, MVC sentences, changelog sentence, `Worktree:`, `codegraph explore` and the never-`projectPath` rule, quoted frontmatter); `ORCHESTRATOR_RULES` unchanged (`git diff main..HEAD -- scripts/foreman_hooks.py` empty).
- `agents/planner.md`, `agents/builder.md`, `agents/generalist.md` unchanged.
- README lists the skill; `CHANGELOG.md` has one new Added line under `[Unreleased]`, no version bump.
- `git diff --name-only main..HEAD` (plus uncommitted changes) lists only the Files of tasks 1 and 2 plus the `docs/specs` and `docs/plans` copies.

---

### Task 3: Commit, push, PR, merge, cleanup

**Agent:** implementer
**Files:** none edited. Git only: commits of `skills/antipatterns/SKILL.md`, `skills/memory/SKILL.md`, `skills/orchestrating/SKILL.md`, `agents/implementer.md`, `agents/ui.md`, `agents/verifier.md`, `README.md`, `CHANGELOG.md`, `tests/test_components.py`, `docs/specs/2026-11-20-antipatterns-design.md`, `docs/plans/2026-11-20-antipatterns.md`; deletes the main checkout's untracked spec and plan copies.

Brief carries `Mode: git`, `Worktree:`, `Branch:` and `Plan:`. Never the MCP `codegraph_explore` with the worktree as `projectPath` (it locks the DB). Intent: stage the files above by name, commit, push the branch, open a PR, merge, clean up in the order below.

- [ ] **Step 0 (re-sync):** copy the current spec and plan from the main checkout over the worktree copies, then `git diff --no-index` each pair; both must print nothing.
- [ ] **Step 1:** In the worktree run `python -m pytest -q`; it must pass before anything is committed. Stage by name only (the worktree's untracked `.codegraph/` stays unstaged). Conventional Commits, summary at most 72 chars, for example `feat(skills): add antipatterns skill and wire it into agents` (skills, agents, README, CHANGELOG, tests) and `docs(plans): add antipatterns spec and plan`. End each message with the attribution line from the session's system reminder.
- [ ] **Step 2:** `git push -u origin feat/antipatterns` (branch only; no `--tags`, no `--follow-tags`, no force). `gh pr create` (Conventional Commit title; body states what and why, the test result, no release cut).
- [ ] **Step 3:** From the main checkout run `gh pr merge --merge` (never `--admin`, no `--delete-branch`; the worktree holds the local branch).
- [ ] **Step 4 (cleanup, in this order):** (a) `codegraph uninit -f <abs worktree path>` (CLI; never the main checkout); (b) `git worktree remove .worktrees/antipatterns` without `--force` (if it refuses, stop and report, never force); (c) `git branch -d feat/antipatterns` (never `-D`; if `-d` refuses only because the main checkout is not yet fast-forwarded, do step 5 and retry); (d) `git push origin --delete feat/antipatterns` (branch ref only). If (a) fails, report it and do not continue to (b).
- [ ] **Step 5:** `git fetch`. For the spec and plan, save the merged version (`git show origin/main:<path>` into a temp file outside the repo) and run `git diff --no-index <temp> <main-checkout copy>`. Only when both print nothing, delete the two untracked copies in the main checkout (nothing else), then `git merge --ff-only origin/main`. If any diff is non-empty, delete nothing and report.
- [ ] **Step 6:** Report the PR URL, merge commit SHA, final `git status --short`, `git worktree list` and `codegraph status` on the main checkout.

**Acceptance:**
- Every commit message follows Conventional Commits; files were staged by name; `git log --stat origin/main -5` shows only the Files above.
- `git ls-remote --tags origin` shows no new tag; `git tag --list` unchanged; the push used the branch ref only.
- PR merged with a merge commit (`gh pr view --json state,mergeCommit`); `--admin` and `--delete-branch` unused; `git ls-remote --heads origin feat/antipatterns` empty after step (d).
- Security (no destructive cleanup): the command log shows `codegraph uninit -f <worktree path>` before `git worktree remove`, which ran without `--force`; `git branch -d` without `-D`; `uninit` never named the main checkout; the two untracked copies were deleted only after both `git diff --no-index` checks printed nothing.
- Security (text only): the merged diff contains no file under `scripts/`, `hooks/` or `bin/`.
- Main checkout: `git rev-parse main` equals `git rev-parse origin/main`; `git worktree list` shows only the main checkout; `git branch --list feat/antipatterns` is empty; `.codegraph/` (`codegraph status` works), `TODO.md` and `problems/` exist untouched.
- The spec and plan are tracked in main (`git ls-files docs/specs/2026-11-20-antipatterns-design.md docs/plans/2026-11-20-antipatterns.md`).
- No release cut: `CHANGELOG.md` keeps the new line under `[Unreleased]`; no version file changed.
- The verifier then runs read-only over the final state and quotes the above.
