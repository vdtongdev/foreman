import json
import subprocess

from conftest import run_hook

REASON = ("Orchestrator doesn't edit project files: dispatch a subagent "
          "(see foreman:orchestrating), or set FOREMAN_SOLO=1.")


def _run(tmp_path, file_path, solo=None, **extra):
    repo = tmp_path / "repo"
    repo.mkdir(exist_ok=True)
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    payload = {"cwd": str(repo), "tool_name": "Edit",
               "tool_input": {"file_path": file_path}, **extra}
    env = {"FOREMAN_HOME": str(tmp_path / "home"), "FOREMAN_SOLO": solo or ""}
    out, _, rc = run_hook("guard", payload, env)
    assert rc == 0
    return json.loads(out) if out.strip() else None


def test_guard_denies_main_session_edit(tmp_path):
    assert _run(tmp_path, "src/app.py") == {"hookSpecificOutput": {
        "hookEventName": "PreToolUse", "permissionDecision": "deny",
        "permissionDecisionReason": REASON}}


def test_guard_allows_subagent(tmp_path):
    assert _run(tmp_path, "src/app.py", agent_id="a1") is None


def test_guard_allows_solo(tmp_path):
    assert _run(tmp_path, "src/app.py", solo="1") is None


def test_guard_allows_memory_path_with_backslashes(tmp_path):
    p = str(tmp_path / "home" / ".claude" / "memory" / "x.md").replace("/", "\\")
    assert _run(tmp_path, p) is None


def test_guard_allows_plan_doc(tmp_path):
    assert _run(tmp_path, "docs/plans/p.md") is None
    assert _run(tmp_path, "docs/specs/s.md") is None


def test_guard_allows_claude_md(tmp_path):
    assert _run(tmp_path, "sub/CLAUDE.md") is None
