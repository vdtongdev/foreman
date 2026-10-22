# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Foreman hook dispatcher. Every hook fails open: errors go to stderr, exit 0."""
import json
import os
import sys
import traceback
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


HOOKS = {"guard": guard}


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
