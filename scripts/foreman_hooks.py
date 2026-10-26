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
    if path.name in ("CLAUDE.md", "CLAUDE.local.md"):
        return None
    root = memory._toplevel(cwd) or cwd
    if not _under(path, root.resolve()):
        return None
    bases = [memory.user_dir(), memory.project_dir(cwd)]
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


PLAN_DENY = ("Edit work needs a plan: write one under docs/plans/ (superpowers:writing-plans) and name it "
             "in the brief, or put 'Mode: diagnose' in a diagnosis-only brief or 'Mode: git' in a git-only brief "
             "(see foreman:orchestrating).")
READ_ONLY = {"foreman:scout", "foreman:verifier", "Explore", "Plan", "claude-code-guide", "statusline-setup"}
PLAN_RE = re.compile(r"docs/(?:superpowers/)?plans/[^\s`'\")]+\.md")


def _plans_file():
    d = os.environ.get("CLAUDE_PLUGIN_DATA") or os.environ.get("FOREMAN_DATA")
    return Path(d) / "plans.json" if d else None


def _load_plans(f: Path) -> dict:
    try:
        d = json.loads(f.read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _is_plan(root: Path, path: Path, require_file: bool = True) -> bool:
    root, path = root.resolve(), path.resolve()
    return path.suffix.lower() == ".md" and (path.is_file() or not require_file) and any(
        _under(path, root / "docs" / p) for p in ("plans", "superpowers/plans"))


def plan_gate(payload: dict):
    if "agent_id" in payload or os.environ.get("FOREMAN_SOLO") == "1":
        return None
    ti = payload.get("tool_input") or {}
    prompt, agent = ti.get("prompt"), ti.get("subagent_type")
    prompt = prompt if isinstance(prompt, str) else ""
    agent = agent if isinstance(agent, str) else ""
    if agent in READ_ONLY or re.search(r"^Mode:\s*(?:diagnose|git)\b", prompt, re.I | re.M):
        return None
    cwd = Path(payload.get("cwd") or ".")
    root = memory._toplevel(cwd) or cwd
    if any(_is_plan(root, root / m.group(0)) for m in PLAN_RE.finditer(prompt.replace("\\", "/"))):
        return None
    f = _plans_file()
    if f and payload.get("session_id") in _load_plans(f):
        return None
    return {"hookSpecificOutput": {"hookEventName": "PreToolUse",
            "permissionDecision": "deny", "permissionDecisionReason": PLAN_DENY}}


def plan_record(payload: dict):
    raw = (payload.get("tool_input") or {}).get("file_path")
    f = _plans_file()
    if "agent_id" in payload or not raw or not f or not payload.get("session_id"):
        return None
    cwd = Path(payload.get("cwd") or ".")
    path = cwd / str(raw).replace("\\", "/")
    if not _is_plan(memory._toplevel(cwd) or cwd, path, False):
        return None
    now = time.time()
    plans = {k: v for k, v in _load_plans(f).items() if isinstance(v, (int, float)) and now - v <= 86400}
    plans[payload["session_id"]] = now
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(plans), encoding="utf-8")
    return None


ORCHESTRATOR_RULES = """Foreman orchestrator rules (full detail: skill foreman:orchestrating):
- You orchestrate; you do not edit project files (a guard denies it). Dispatch a subagent instead.
- Clarify: ask the user only what no code, doc, memory, web page or command can show; say what you already checked.
- Recall: run `mem select --path <files> --topic <topics>` and paste the facts and traps into each task brief.
- Memory entries follow the foreman:memory skill format (hooks validate them).
- Briefs are self-contained: goal, files, acceptance criteria, selected facts and traps, report format.
- Dispatch to the cheapest fitting agent: scout, drafter, implementer, verifier, expert. Plan tasks name theirs (`Agent: <name>` line); dispatch to it. Run independent tasks in parallel.
- Execute plans with this loop, not superpowers' Native / executing-plans / subagent-driven-development options (they have no model routing, and Native edits in the main session, which the guard denies).
- A bug report is always a workflow, never an ad-hoc fix, even if the cause looks obvious: first dispatch implementer (brief has the line `Mode: diagnose`) to reproduce it with a failing test and find the root cause (don't debug it yourself), then write a plan (regression test first), then run this loop. Edit dispatches need a plan named in the brief or written this session (a hook enforces it).
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
    problems = [p.replace(str(d) + os.sep, "") for d in layers if d for p in memory.refresh_layer(d)]
    entries = [e for d in layers if d for e in memory.load_layer(d)[0]]
    blocks = [ORCHESTRATOR_RULES]
    idx = memory.user_dir() / "MEMORY.md"
    if idx.is_file():
        blocks.append(idx.read_text(encoding="utf-8-sig").strip())
    st = memory.stale(entries, date.today())
    if st:
        blocks.append("Stale (re-check before use): " + ", ".join(e.name for e in st))
    if problems:
        txt = "; ".join(problems)
        if len(txt) > 3000:
            k = len(txt[:3000].split("; ")) - 1
            txt = "; ".join(problems[:k]) + f"; … {len(problems) - k} more: run mem validate"
        blocks.append("Invalid memory entries: " + txt)
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
    root = memory._toplevel(cwd)
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
         "evidence-check": evidence_check,
         "plan-gate": plan_gate, "plan-record": plan_record}


def main(argv):
    try:
        payload = json.loads(sys.stdin.buffer.read())
        result = HOOKS[argv[1]](payload)
        if result is not None:
            print(json.dumps(result))
    except BaseException:
        traceback.print_exc()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
