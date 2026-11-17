import json
import subprocess

from conftest import run_hook

REASON = ("Edit work needs a plan: write one under docs/plans/ (superpowers:writing-plans) and name it in the brief, "
          "or put 'Mode: quick' in a small task brief, 'Mode: lookup' in a read-only generalist brief, "
          "'Mode: diagnose' in a diagnosis-only brief, or 'Mode: git' in a git-only brief "
          "(see foreman:orchestrating).")
BUILDER_REASON = ("Builder needs a named plan (Plan: docs/plans/<file>.md) whose every task has "
                  "Agent: and Files: lines.")


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


def _deny(reason):
    return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                   "permissionDecisionReason": reason}}


DENIED = _deny(REASON)
BUILDER_DENIED = _deny(BUILDER_REASON)


def test_denies_edit_agents_without_plan(tmp_path):
    for a in ("foreman:implementer", "foreman:ui", "general-purpose", "foreman:generalist"):
        assert _gate(tmp_path, agent=a) == DENIED


def test_allows_subagent_solo_and_readonly(tmp_path):
    assert _gate(tmp_path, agent_id="a1") is None
    assert _gate(tmp_path, solo="1") is None
    assert _gate(tmp_path, agent="foreman:generalist", prompt="Mode: lookup\nFind a file.") is None
    assert _gate(tmp_path, agent="foreman:generalist", prompt="see Mode: lookup") == DENIED
    assert _gate(tmp_path, agent="foreman:generalist", prompt="Mode: lookupfoo") == DENIED
    assert _gate(tmp_path, agent="foreman:verifier") is None


def test_allows_diagnose_mode(tmp_path):
    assert _gate(tmp_path, prompt="## Goal\nx\nmode:  Diagnose\n") is None


def test_allows_git_mode(tmp_path):
    assert _gate(tmp_path, agent="foreman:generalist", prompt="## Goal\nx\nmode: Git\n") is None
    assert _gate(tmp_path, agent="foreman:generalist", prompt="Mode: gitfoo") == DENIED
    assert _gate(tmp_path, agent="foreman:generalist", prompt="see Mode: git") == DENIED


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


def test_quick_mode_task_agents(tmp_path):
    for a in ("foreman:generalist", "foreman:implementer", "foreman:ui"):
        assert _gate(tmp_path, agent=a, prompt="## Goal\nx\nMode: quick\n") is None


def test_quick_mode_only_task_agents(tmp_path):
    assert _gate(tmp_path, agent="foreman:builder", prompt="## Goal\nx\nMode: quick\n") == BUILDER_DENIED
    assert _gate(tmp_path, agent="general-purpose", prompt="## Goal\nx\nMode: quick\n") == DENIED
    assert _gate(tmp_path, prompt="see Mode: quick") == DENIED


def test_planner_needs_no_plan(tmp_path):
    assert _gate(tmp_path, agent="foreman:planner", prompt="do it") is None


def _plan(tmp_path, text):
    p = _repo(tmp_path) / "docs" / "plans"
    p.mkdir(parents=True, exist_ok=True)
    (p / "x.md").write_text(text)


def test_builder_needs_named_plan(tmp_path):
    _record(tmp_path, "docs/plans/p.md")
    assert _gate(tmp_path, agent="foreman:builder") == BUILDER_DENIED


def test_builder_needs_agent_and_files_per_task(tmp_path):
    brief = "Plan: docs/plans/x.md"
    _plan(tmp_path, "### Task 1\n**Agent:** implementer\n**Files:** a.py\n### Task 2\n**Agent:** ui\n")
    assert _gate(tmp_path, agent="foreman:builder", prompt=brief) == BUILDER_DENIED
    _plan(tmp_path, "### Task 1\n**Agent:** implementer\n**Files:** a.py\n"
                    "### Task 4b: y\n**Agent:** ui\n**Files:** b.tsx\n")
    assert _gate(tmp_path, agent="foreman:builder", prompt=brief) is None
    _plan(tmp_path, "no tasks here")
    assert _gate(tmp_path, agent="foreman:builder", prompt=brief) == BUILDER_DENIED
