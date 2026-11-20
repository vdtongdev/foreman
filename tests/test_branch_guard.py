import json
import subprocess
from pathlib import Path

import pytest

import foreman_hooks
from conftest import run_hook

GIT = ["git", "-c", "user.name=t", "-c", "user.email=t@t"]


def _git(cwd, *args):
    subprocess.run([*GIT, *args], cwd=cwd, check=True, capture_output=True)


def _repo(tmp_path, branch="main"):
    r = tmp_path / "repo"
    r.mkdir()
    _git(r, "init", "-q", "-b", branch)
    _git(r, "commit", "--allow-empty", "-q", "-m", "init")
    return r


def _env(tmp_path):
    return {"FOREMAN_HOME": str(tmp_path / "home"), "FOREMAN_SOLO": ""}


def _run(tmp_path, cwd, path, tool="Edit", agent="a1", env=None):
    key = "notebook_path" if tool == "NotebookEdit" else "file_path"
    p = {"cwd": str(cwd), "tool_name": tool, "tool_input": {key: str(path)}}
    if agent:
        p["agent_id"] = agent
    out, err, rc = run_hook("branch-guard", p, {**_env(tmp_path), **(env or {})})
    assert rc == 0, err
    return json.loads(out) if out.strip() else None


def _denied(res):
    return res is not None and res["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_deny_on_default_branch(tmp_path):
    r = _repo(tmp_path)
    res = _run(tmp_path, r, r / "src" / "app.py")
    assert _denied(res)
    reason = res["hookSpecificOutput"]["permissionDecisionReason"]
    assert "git worktree add .worktrees/<slug> -b <type>/<slug>" in reason
    assert "foreman:releasing" in reason


def test_deny_write_new_file_and_notebook(tmp_path):
    r = _repo(tmp_path)
    (r / "src").mkdir()
    assert _denied(_run(tmp_path, r, r / "src" / "new.py", tool="Write"))
    assert _denied(_run(tmp_path, r, r / "n.ipynb", tool="NotebookEdit"))


def test_origin_head_is_default_branch(tmp_path):
    r = _repo(tmp_path, "trunk")
    _git(r, "update-ref", "refs/remotes/origin/trunk", "HEAD")
    _git(r, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/trunk")
    assert _denied(_run(tmp_path, r, r / "a.py"))
    _git(r, "checkout", "-q", "-b", "main")
    assert _run(tmp_path, r, r / "a.py") is None


def test_master_default(tmp_path):
    r = _repo(tmp_path, "master")
    assert _denied(_run(tmp_path, r, r / "a.py"))


def test_allow_feature_branch(tmp_path):
    r = _repo(tmp_path)
    _git(r, "checkout", "-q", "-b", "feat/x")
    assert _run(tmp_path, r, r / "a.py") is None


def test_allow_linked_worktree(tmp_path):
    r = _repo(tmp_path)
    _git(r, "worktree", "add", "-q", str(r / ".worktrees" / "x"), "-b", "feat/x")
    assert _run(tmp_path, r, r / ".worktrees" / "x" / "src" / "a.py") is None


def test_allow_detached_and_outside_git(tmp_path):
    r = _repo(tmp_path)
    _git(r, "checkout", "-q", "--detach")
    assert _run(tmp_path, r, r / "a.py") is None
    out = tmp_path / "plain"
    out.mkdir()
    assert _run(tmp_path, out, out / "a.py") is None


def test_allow_docs_memory_solo_main_session(tmp_path):
    r = _repo(tmp_path)
    assert _run(tmp_path, r, r / "docs" / "specs" / "s.md") is None
    assert _run(tmp_path, r, r / "docs" / "plans" / "p.md") is None
    mem = tmp_path / "home" / ".claude" / "memory"
    mem.mkdir(parents=True)
    assert _run(tmp_path, r, mem / "m.md") is None
    assert _run(tmp_path, r, r / "a.py", env={"FOREMAN_SOLO": "1"}) is None
    assert _run(tmp_path, r, r / "a.py", agent=None) is None


def test_path_tricks_still_denied(tmp_path):
    r = _repo(tmp_path)
    (r / "docs" / "specs").mkdir(parents=True)
    for rel in ("docs/specs/../../src/x.py", "docs/plansX/a.py", "docs-evil/specs/x.md"):
        assert _denied(_run(tmp_path, r, r / rel)), rel
    mixed = str(r / "src" / "x.py").replace("/", chr(92))
    assert _denied(_run(tmp_path, r, mixed))


def test_dotdot_from_worktree_into_main_denied(tmp_path):
    r = _repo(tmp_path)
    wt = r / ".worktrees" / "x"
    _git(r, "worktree", "add", "-q", str(wt), "-b", "feat/x")
    assert _denied(_run(tmp_path, wt, wt / ".." / ".." / "a.py"))


PAYLOAD = lambda r: {"cwd": str(r), "tool_input": {"file_path": str(r / "a.py")}, "agent_id": "a1"}  # noqa: E731


@pytest.mark.parametrize("exc", [OSError("x"), subprocess.TimeoutExpired("git", 5)])
def test_git_exceptions_allow(tmp_path, monkeypatch, exc):
    r = _repo(tmp_path)

    def boom(*a, **k):
        raise exc
    monkeypatch.setattr(foreman_hooks.subprocess, "run", boom)
    assert foreman_hooks.branch_guard(PAYLOAD(r)) is None


def test_git_nonzero_allows(tmp_path, monkeypatch):
    r = _repo(tmp_path)
    monkeypatch.setattr(foreman_hooks.subprocess, "run",
                        lambda *a, **k: subprocess.CompletedProcess(a, 1, "", ""))
    assert foreman_hooks.branch_guard(PAYLOAD(r)) is None


def test_bad_cwd_and_bad_json_fail_open(tmp_path):
    f = tmp_path / "afile"
    f.write_text("x")
    out, err, rc = run_hook("branch-guard", {"cwd": str(f), "agent_id": "a1",
                                             "tool_input": {"file_path": "a.py"}}, _env(tmp_path))
    assert rc == 0 and out == ""
    out, err, rc = run_hook("branch-guard", "not json", _env(tmp_path))
    assert rc == 0 and out == ""


def test_hooks_json_registers_branch_guard():
    d = json.loads((Path(__file__).resolve().parent.parent / "hooks" / "hooks.json").read_text())
    ents = [e for g in d["hooks"].values() for e in g
            if any(" branch-guard " in h["command"] for h in e["hooks"])]
    assert len(ents) == 1 and ents[0]["matcher"] == "Edit|Write|NotebookEdit"
    assert "branch-guard" in foreman_hooks.HOOKS
