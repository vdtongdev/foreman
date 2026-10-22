# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Foreman hook dispatcher. Every hook fails open: errors go to stderr, exit 0."""
import json
import os
import re
import sys
import time
import traceback
from datetime import date
from pathlib import Path

import memory

DENY = ("Orchestrator doesn't edit project files: dispatch a subagent "
        "(see foreman:orchestrating), or set FOREMAN_SOLO=1.")


def _under(path: Path, base: Path) -> bool:
    return Path(os.path.normcase(path)).is_relative_to(os.path.normcase(base))


def guard(payload: dict):
    if "agent_id" in payload or os.environ.get("FOREMAN_SOLO") == "1":
        return None
    ti = payload.get("tool_input") or {}
    raw = ti.get("file_path") or ti.get("notebook_path")
    if not raw:
        return None
    cwd = Path(payload.get("cwd") or ".")
    path = (cwd / str(raw).replace("\\", "/")).resolve()
    if path.name == "CLAUDE.md":
        return None
    bases = [memory.user_dir(), memory.project_dir(cwd)]
    root = memory._git_root(cwd)
    if root:
        bases += [root / "docs" / d for d in ("specs", "plans", "superpowers")]
    if any(b and _under(path, b.resolve()) for b in bases):
        return None
    return {"hookSpecificOutput": {"hookEventName": "PreToolUse",
            "permissionDecision": "deny", "permissionDecisionReason": DENY}}


def memory_write(payload: dict):
    raw = (payload.get("tool_input") or {}).get("file_path")
    if not raw:
        return None
    cwd = Path(payload.get("cwd") or ".")
    path = (cwd / str(raw).replace("\\", "/")).resolve()
    if path.name == "MEMORY.md":
        return None
    layer = next((b for b in (memory.user_dir(), memory.project_dir(cwd))
                  if b and os.path.normcase(path.parent) == os.path.normcase(b.resolve())), None)
    if layer is None:
        return None
    problems = memory.refresh_layer(layer)
    if problems:
        return {"decision": "block", "reason": "Memory entry problems:\n" + "\n".join(problems)}
    dangling = memory.dangling_links(memory.load_layer(layer)[0])
    if dangling:
        return {"hookSpecificOutput": {"hookEventName": "PostToolUse",
                "additionalContext": "Dangling memory links (write or remove): " + "; ".join(dangling)}}
    return None


ORCHESTRATOR_RULES = """Foreman orchestrator rules (full detail: skill foreman:orchestrating):
- You orchestrate; you do not edit project files (a guard denies it). Dispatch a subagent instead.
- Clarify: ask the user only what no code, doc, memory, web page or command can show; say what you already checked.
- Recall: run `mem select --path <files> --topic <topics>` and paste the facts and traps into each task brief.
- Briefs are self-contained: goal, files, acceptance criteria, selected facts and traps, report format.
- Dispatch to the cheapest fitting agent: scout, drafter, implementer, verifier, expert. Run independent tasks in parallel.
- Every task that changed code goes to the verifier. First fail: back to the same agent. Second fail: escalate one tier (drafter, implementer, expert).
- If expert fails, stop and ask the user, with both reports.
- Claims need evidence observed this session (command plus output, file:line, or URL plus quote); a memory fact counts only if verified: human and not stale.
- Report "done" only by quoting the verifier's evidence. Write memory for what was learned."""

VERIFY_RULES = """Verify before asking or asserting:
1. Asserting: cite evidence observed this session (command plus output excerpt, file:line, or URL plus quote). A memory fact counts only if verified: human and not stale; otherwise re-check it. List the rest as unverified.
2. Asking: ask only for decisions, preferences or facts no code, doc, memory, web page or command can show; state what you already checked.
3. End your report with the result, then ## Evidence and ## Unverified sections (either may say "none")."""

TRAP_HEADER = "Traps (full text injected when you edit a matching file):"


def _layers(cwd: Path):
    return [d for d in (memory.project_dir(cwd), memory.user_dir()) if d]


def session_start(payload: dict):
    if "agent_id" in payload:
        return None
    cwd = Path(payload.get("cwd") or ".")
    layers = [memory.user_dir(), memory.project_dir(cwd)]
    problems = [p for d in layers if d for p in memory.refresh_layer(d)]
    entries = [e for d in layers if d for e in memory.load_layer(d)[0]]
    blocks = [ORCHESTRATOR_RULES]
    idx = memory.user_dir() / "MEMORY.md"
    if idx.is_file():
        blocks.append(idx.read_text(encoding="utf-8-sig").strip())
    st = memory.stale(entries, date.today())
    if st:
        blocks.append("Stale (re-check before use): " + ", ".join(e.name for e in st))
    if problems:
        blocks.append("Invalid memory entries: " + "; ".join(problems))
    dangling = memory.dangling_links(entries)
    if dangling:
        blocks.append("Dangling links: " + "; ".join(dangling))
    return {"hookSpecificOutput": {"hookEventName": "SessionStart",
            "additionalContext": "\n\n".join(b for b in blocks if b)}}


def _traps(cwd: Path, paths: list[str]):
    return [e for d in _layers(cwd)
            for e, _ in memory.select(memory.load_layer(d)[0], paths, [], None, True)]


def subagent_start(payload: dict):
    cwd = Path(payload.get("cwd") or ".")
    lines = [f"- {e.name}: {e.description}" for e in _traps(cwd, [])]
    trap_block = ""
    if lines:
        trap_block = TRAP_HEADER
        for ln in lines:
            if len(trap_block) + 1 + len(ln) > 2000:
                break
            trap_block += "\n" + ln
    return {"hookSpecificOutput": {"hookEventName": "SubagentStart",
            "additionalContext": "\n\n".join(b for b in (VERIFY_RULES, trap_block) if b)}}


def _served_names(agent_id: str, names: list[str]) -> list[str]:
    """Return names not yet served to agent_id, recording them (24h prune)."""
    data_dir = os.environ.get("CLAUDE_PLUGIN_DATA") or os.environ.get("FOREMAN_DATA")
    if not data_dir:
        return names
    f = Path(data_dir) / "served.json"
    try:
        served = json.loads(f.read_text(encoding="utf-8"))
        if not isinstance(served, dict):
            served = {}
    except (OSError, ValueError):
        served = {}
    now = time.time()
    served = {k: v for k, v in served.items()
              if isinstance(v, dict) and now - v.get("t", 0) <= 86400}
    rec = served.setdefault(agent_id, {"t": now, "traps": []})
    new = [n for n in names if n not in rec["traps"]]
    rec["traps"] += new
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(served), encoding="utf-8")
    return new


def trap_inject(payload: dict):
    agent = payload.get("agent_id")
    raw = (payload.get("tool_input") or {}).get("file_path")
    if not agent or not raw:
        return None
    cwd = Path(payload.get("cwd") or ".")
    root = memory._git_root(cwd)
    if root is None:
        return None
    path = (cwd / str(raw).replace("\\", "/")).resolve()
    if not _under(path, root.resolve()):
        return None
    rel = Path(os.path.relpath(path, root.resolve())).as_posix()
    traps = _traps(cwd, [rel])
    fresh = set(_served_names(str(agent), [e.name for e in traps]))
    traps = [e for e in traps if e.name in fresh]
    if not traps:
        return None
    ctx = "\n\n".join(f"Trap {e.name}:\n{e.body.strip()}" for e in traps)
    return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": ctx}}


def evidence_check(payload: dict):
    if payload.get("stop_hook_active"):
        return None
    msg = payload.get("last_assistant_message")
    if not isinstance(msg, str):
        msg = ""
    if all(re.search(rf"^## {s}", msg, re.MULTILINE | re.IGNORECASE) for s in ("Evidence", "Unverified")):
        return None
    return {"decision": "block", "reason": "Add ## Evidence and ## Unverified sections."}


HOOKS = {"guard": guard, "memory-write": memory_write, "session-start": session_start,
         "subagent-start": subagent_start, "trap-inject": trap_inject,
         "evidence-check": evidence_check}


def main(argv):
    try:
        payload = json.loads(sys.stdin.read())
        result = HOOKS[argv[1]](payload)
        if result is not None:
            print(json.dumps(result))
    except BaseException:
        traceback.print_exc()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
