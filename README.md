# foreman

A Claude Code plugin that keeps the main session as an orchestrator. It:

- routes work to model-tiered subagents (scout and drafter on haiku, implementer and verifier on sonnet, expert on opus);
- keeps a typed memory knowledge base, validated by hooks;
- requires `## Evidence` / `## Unverified` sections in every subagent report.

Design: [docs/specs/2026-10-22-foreman-design.md](docs/specs/2026-10-22-foreman-design.md).

## Install

Requires `uv` on PATH and git access to this private repo (`gh auth login` then `gh auth setup-git`, or an SSH key loaded in ssh-agent).

```bash
claude plugin install foreman --marketplace vdtongdev/foreman
```

It installs at user scope, so it is on in every project. On a machine without a GitHub SSH key, set `CLAUDE_CODE_PLUGIN_PREFER_HTTPS=1`.

**Auto-update** is off for custom marketplaces, and `marketplace.json` has no field to turn it on. Turn it on once per machine: `/plugin` → Marketplaces → foreman → Enable auto-update. `plugin.json` has no `version` on purpose, so updates follow commits.

To turn it off for one project, disable the plugin at local scope.

## Orchestrator guard

In the main session, `Edit`/`Write`/`NotebookEdit` on project files are denied. Subagents can edit. These paths are always allowed:

- the memory folders
- `docs/specs/`, `docs/plans/` and `docs/superpowers/`
- any `CLAUDE.md`

To work solo for a session, set `FOREMAN_SOLO=1` in the environment before starting `claude`.

## Memory: `mem`

`bin/mem` is on the Bash PATH inside Claude Code sessions.

| Command | Does |
|---|---|
| `mem select [--path P]... [--topic T]... [--type X] [--traps]` | Matching active entries, project layer first, with the reason each matched |
| `mem stale` | Entries past `stale_after` |
| `mem validate` | Check every entry; exit 1 with the problems |
| `mem index` | Regenerate both `MEMORY.md` indexes |
| `mem deprecate NAME [--by NEW]` | Mark an entry deprecated (and superseded) |

Memory layers:

- **User:** `~/.claude/memory/`
- **Project:** Claude Code's auto memory, `~/.claude/projects/<slug>/memory/`

For the entry format, see the `foreman:memory` skill.

## Hook latency

Each hook runs `uv run --no-project --script`. The median of 10 runs of the guard on this Windows PC was **163 ms** (range 129–178 ms). That is under the 300 ms budget, so the hooks don't call Python directly.

## Development

```bash
uv run --with pytest pytest -q        # tests
claude plugin validate .              # manifests
claude plugin marketplace add "<path to this clone>"
claude plugin install foreman@foreman # loads the clone in place; /reload-plugins applies edits
```
