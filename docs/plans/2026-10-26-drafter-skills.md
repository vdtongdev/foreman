# Let the drafter load skills

Goal: skill-guided doc edits (e.g. prompt files that need `writing-llm-document`) run on haiku. Today they go to implementer (sonnet) only because drafter has no Skill tool.

## Task 1: Branch and give drafter the Skill tool (Agent: drafter)
Files: `agents/drafter.md`, `skills/orchestrating/SKILL.md` (routing table drafter row, line 19), `README.md` (drafter row, line 64).
- `git switch -c drafter-skills` from `main` first.
- `agents/drafter.md` frontmatter: `tools: Read, Edit, Write, Grep, Glob, Bash, Skill`.
- `agents/drafter.md` body, after the "Touch only the files..." paragraph, add: "If the brief names a skill, load it with the Skill tool before editing and follow it."
- Drafter row description in both tables: append " Loads skills the brief names." README tools column: add `, Skill`.
- Do not commit.
Acceptance: `uv run --with pytest pytest -q` green; `git diff main --stat` shows only those three files plus this plan.

## Task 2: Version 0.1.1 (Agent: drafter)
Files: `.claude-plugin/plugin.json`, `README.md` (line 38).
- plugin.json: add `"version": "0.1.1"` after `description`.
- README:38: replace the sentence "`plugin.json` has no `version` on purpose, so updates follow commits." with "`plugin.json` sets `version`; installs update only when it changes, so bump it with every release."
Acceptance: plugin.json is valid JSON; suite green.

## Task 3: Ship (Agent: drafter, Mode: git)
Commit Tasks 1-2 plus this plan on `drafter-skills` (not foreman-model-routing-prompt.md), push, open a PR to main, merge it, update local main.
