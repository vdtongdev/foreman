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


def test_guard_allows_claude_local_md(tmp_path):
    assert _run(tmp_path, str(tmp_path / "repo" / "CLAUDE.local.md")) is None


def test_guard_negative_paths_denied(tmp_path):
    for p in ("docs/specs/../../src/x.py", "docs-evil/specs/x.md", "docs/plansX/a.py"):
        assert _run(tmp_path, p) is not None, p


def test_guard_allows_outside_project(tmp_path):
    assert _run(tmp_path, str(tmp_path / "elsewhere" / "plan.md")) is None


def test_guard_in_worktree(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    g = lambda *a, cwd=repo: subprocess.run(["git", *a], cwd=cwd, check=True, capture_output=True)  # noqa: E731
    g("init", "-q")
    g("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "i")
    wt = tmp_path / "wt"
    g("worktree", "add", "-q", str(wt))
    env = {"FOREMAN_HOME": str(tmp_path / "home")}

    def run(f):
        out, _, rc = run_hook("guard", {"cwd": str(wt), "tool_input": {"file_path": f}}, env)
        assert rc == 0
        return json.loads(out) if out.strip() else None
    assert run("docs/plans/p.md") is None
    assert run("src/x.py") is not None
    # trap path is relative to the worktree, not the main checkout
    import memory
    assert memory._toplevel(wt).resolve() == wt.resolve()
