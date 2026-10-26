import json
import subprocess

from conftest import run_hook

REASON = ("Edit work needs a plan: write one under docs/plans/ (superpowers:writing-plans) and name it in the brief, "
          "or put 'Mode: diagnose' in a diagnosis-only brief or 'Mode: git' in a git-only brief "
          "(see foreman:orchestrating).")


def _repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir(exist_ok=True)
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    return repo


def _gate(tmp_path, prompt="do it", agent="foreman:implementer", solo=None, session="S", **extra):
    payload = {"cwd": str(_repo(tmp_path)), "session_id": session, "tool_name": "Agent",
               "tool_input": {"subagent_type": agent, "prompt": prompt}, **extra}
    out, _, rc = run_hook("plan-gate", payload, {"FOREMAN_DATA": str(tmp_path / "data"), "FOREMAN_SOLO": solo or ""})
    assert rc == 0
    return json.loads(out) if out.strip() else None


def _record(tmp_path, rel, session="S", **extra):
    repo = _repo(tmp_path)
    payload = {"cwd": str(repo), "session_id": session, "tool_name": "Write",
               "tool_input": {"file_path": str(repo / rel)}, **extra}
    out, _, rc = run_hook("plan-record", payload, {"FOREMAN_DATA": str(tmp_path / "data")})
    assert rc == 0 and not out.strip()


DENIED = {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                 "permissionDecisionReason": REASON}}


def test_denies_edit_agents_without_plan(tmp_path):
    for a in ("foreman:implementer", "general-purpose", "foreman:drafter"):
        assert _gate(tmp_path, agent=a) == DENIED


def test_allows_subagent_solo_and_readonly(tmp_path):
    assert _gate(tmp_path, agent_id="a1") is None
    assert _gate(tmp_path, solo="1") is None
    assert _gate(tmp_path, agent="foreman:scout") is None
    assert _gate(tmp_path, agent="foreman:verifier") is None


def test_allows_diagnose_mode(tmp_path):
    assert _gate(tmp_path, prompt="## Goal\nx\nmode:  Diagnose\n") is None


def test_allows_git_mode(tmp_path):
    assert _gate(tmp_path, agent="foreman:drafter", prompt="## Goal\nx\nmode: Git\n") is None
    assert _gate(tmp_path, agent="foreman:drafter", prompt="Mode: gitfoo") == DENIED
    assert _gate(tmp_path, agent="foreman:drafter", prompt="see Mode: git") == DENIED


def test_existing_plan_named(tmp_path):
    p = _repo(tmp_path) / "docs" / "plans"
    p.mkdir(parents=True)
    (p / "x.md").write_text("plan")
    assert _gate(tmp_path, prompt="Plan: docs/plans/x.md") is None
    assert _gate(tmp_path, prompt=r"Plan: docs\plans\x.md") is None
    assert _gate(tmp_path, prompt="Plan: docs/plans/nope.md") == DENIED


def test_plan_record_per_session(tmp_path):
    _record(tmp_path, "docs/plans/p.md", session="S")
    assert _gate(tmp_path, session="S") is None
    assert _gate(tmp_path, session="T") == DENIED


def test_plan_record_ignores_subagent_and_other_paths(tmp_path):
    _record(tmp_path, "docs/plans/p.md", agent_id="a1")
    _record(tmp_path, "src/p.md")
    _record(tmp_path, "docs/plans/p.txt")
    assert _gate(tmp_path) == DENIED


def test_traversal_and_bad_types_denied(tmp_path):
    r = _repo(tmp_path)
    (r / "docs" / "plans").mkdir(parents=True)
    (r / "docs" / "specs").mkdir(parents=True)
    (r / "docs" / "specs" / "s.md").write_text("s")
    (r / "x.md").write_text("x")
    for prompt in ("Plan: docs/plans/../../x.md", "Plan: docs/plans/../specs/s.md", 5, ["Mode: diagnose"]):
        assert _gate(tmp_path, prompt=prompt) == DENIED
    assert _gate(tmp_path, agent=["a"]) == DENIED


def test_plan_record_uppercase_suffix(tmp_path):
    _record(tmp_path, "docs/plans/B.MD")
    assert _gate(tmp_path) is None
