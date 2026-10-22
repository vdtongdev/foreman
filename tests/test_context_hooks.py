import json
import subprocess

from conftest import run_hook
from test_memory_index import write


def _env(tmp_path):
    return {"FOREMAN_HOME": str(tmp_path / "home"), "FOREMAN_DATA": str(tmp_path / "data"),
            "CLAUDE_PLUGIN_DATA": ""}


def _repo(tmp_path):
    r = tmp_path / "repo"
    r.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=r, check=True)
    return r


def _user(tmp_path):
    d = tmp_path / "home" / ".claude" / "memory"
    d.mkdir(parents=True)
    return d


def _run(name, payload, tmp_path):
    out, err, rc = run_hook(name, payload, _env(tmp_path))
    assert rc == 0, err
    return json.loads(out) if out.strip() else None


def test_session_start_lists_stale(tmp_path):
    d = _user(tmp_path)
    write(d, "old-fact", stale="2020-01-01")
    (d / "bad.md").write_text("---\nname: bad\n---\nb\n")
    write(d, "linker", body="see [[ghost]]")
    out = _run("session-start", {"cwd": str(tmp_path)}, tmp_path)
    h = out["hookSpecificOutput"]
    assert h["hookEventName"] == "SessionStart"
    c = h["additionalContext"]
    assert "foreman:orchestrating" in c
    assert "- [old-fact](old-fact.md)" in c
    assert "Stale (re-check before use): old-fact" in c
    assert "Invalid memory entries: " in c and "bad" in c
    assert "Dangling links: " in c and "[[ghost]]" in c


def test_session_start_silent_in_subagent(tmp_path):
    assert _run("session-start", {"cwd": str(tmp_path), "agent_id": "a1"}, tmp_path) is None


def test_subagent_start_caps_2000(tmp_path):
    d = _user(tmp_path)
    for i in range(60):
        write(d, f"trap-{i:02}", trap=True, desc="x" * 80)
    c = _run("subagent-start", {"cwd": str(tmp_path), "agent_id": "a1"}, tmp_path)["hookSpecificOutput"]["additionalContext"]
    assert "## Evidence" in c
    sec = c.split("Traps (full text injected when you edit a matching file):", 1)[1]
    assert len(sec) <= 2000 and sec.rstrip().endswith("x" * 80)
    assert "trap-00" in sec and "trap-59" not in sec


def _edit(tmp_path, agent, path, repo):
    p = {"cwd": str(repo), "tool_name": "Edit", "tool_input": {"file_path": path}}
    if agent:
        p["agent_id"] = agent
    return _run("trap-inject", p, tmp_path)


def test_trap_inject_once_per_agent(tmp_path):
    d, repo = _user(tmp_path), _repo(tmp_path)
    write(d, "lockfile", trap=True, paths=["src/*.py"], body="never touch it")
    first = _edit(tmp_path, "a1", str(repo / "src" / "x.py"), repo)
    ctx = first["hookSpecificOutput"]["additionalContext"]
    assert first["hookSpecificOutput"]["hookEventName"] == "PreToolUse"
    assert "lockfile" in ctx and "never touch it" in ctx
    assert _edit(tmp_path, "a1", str(repo / "src" / "x.py"), repo) is None
    assert _edit(tmp_path, "a2", str(repo / "src" / "x.py"), repo) is not None


def test_trap_glob_matches_backslash_path(tmp_path):
    bs = chr(92)
    d, repo = _user(tmp_path), _repo(tmp_path)
    write(d, "deep", trap=True, paths=["src/**/*.py"])
    out = _edit(tmp_path, "a1", str(repo).replace("/", bs) + bs + bs.join(["src", "a", "b.py"]), repo)
    assert "deep" in out["hookSpecificOutput"]["additionalContext"]
    assert _edit(tmp_path, "a1", bs.join(["src", "a", "other.txt"]), repo) is None


def test_trap_inject_ignores_main_session(tmp_path):
    d, repo = _user(tmp_path), _repo(tmp_path)
    write(d, "t", trap=True, paths=["src/*.py"])
    assert _edit(tmp_path, None, str(repo / "src" / "x.py"), repo) is None
