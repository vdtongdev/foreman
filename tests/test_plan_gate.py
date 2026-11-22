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


FULL_GIT = "## Goal\nx\nMode: git\nWorktree: .worktrees/x\nBranch: fix/x\n## Memory\nnone\n"


def _git_reason(tmp_path, prompt, agent="foreman:implementer", **kw):
    out = _gate(tmp_path, prompt=prompt, agent=agent, **kw)
    assert out is not None, prompt
    return out["hookSpecificOutput"]["permissionDecisionReason"]


def test_git_brief_full_implementer_passes(tmp_path):
    assert _gate(tmp_path, prompt=FULL_GIT) is None
    assert _gate(tmp_path, prompt=FULL_GIT.replace("Mode: git", "mode: Git")) is None


def test_git_brief_missing_fields_deny_distinctly(tmp_path):
    cases = {
        "Worktree": FULL_GIT.replace("Worktree: .worktrees/x\n", ""),
        "Branch": FULL_GIT.replace("Branch: fix/x\n", ""),
        "## Memory": FULL_GIT.replace("## Memory\nnone\n", ""),
    }
    empty = {
        "Worktree": FULL_GIT.replace("Worktree: .worktrees/x", "Worktree:"),
        "Branch": FULL_GIT.replace("Branch: fix/x", "Branch:   "),
    }
    reasons = {}
    for item, prompt in cases.items():
        r = _git_reason(tmp_path, prompt)
        assert item in r and "foreman:releasing" in r, (item, r)
        reasons[item] = r
    assert len(set(reasons.values())) == 3
    for item, prompt in empty.items():
        assert _git_reason(tmp_path, prompt) == reasons[item]


def test_git_brief_commit_message_denies(tmp_path):
    cases = {
        '-m "': 'git commit -m "fix: x"',
        "-m '": "git commit -m 'fix: x'",
        "--message": "git commit --message=foo",
        "Commit message:": "commit message: fix: x",
    }
    for item, line in cases.items():
        r = _git_reason(tmp_path, FULL_GIT + line + "\n")
        assert item.lower() in r.lower() and "foreman:releasing" in r, (item, r)
    assert _git_reason(tmp_path, FULL_GIT + "Commit Message: x\n") == _git_reason(
        tmp_path, FULL_GIT + "commit message: x\n")


def test_git_brief_wrong_agent_denies(tmp_path):
    for a in ("foreman:generalist", "general-purpose", "claude"):
        r = _git_reason(tmp_path, FULL_GIT, agent=a)
        assert "foreman:implementer" in r and "foreman:releasing" in r, a


def test_git_brief_nested_solo_and_modes(tmp_path):
    assert _gate(tmp_path, prompt="Mode: git", agent_id="a1") is None
    assert _gate(tmp_path, prompt="Mode: git", agent="foreman:generalist", solo="1") is None
    assert _gate(tmp_path, agent="foreman:generalist", prompt="Mode: gitfoo") == DENIED
    assert _gate(tmp_path, agent="foreman:generalist", prompt="see Mode: git") == DENIED
    assert _gate(tmp_path, prompt="Mode: gitfoo") == DENIED
    assert _gate(tmp_path, prompt="see Mode: git") == DENIED
    assert _gate(tmp_path, prompt="Mode: diagnose") is None


def test_git_gate_reasons_do_not_echo_prompt(tmp_path):
    s = "SENTINEL_9f3a"
    for p in (f"Mode: git\n{s}", f'{FULL_GIT}-m "{s}"', f"Mode: git\nWorktree: {s}"):
        assert s not in _git_reason(tmp_path, p)
        assert s not in _git_reason(tmp_path, p, agent="foreman:generalist")


def test_git_gate_bad_types_and_fail_open(tmp_path):
    for prompt in (5, ["Mode: git"]):
        assert _gate(tmp_path, prompt=prompt) == DENIED
    assert _gate(tmp_path, agent=5, prompt=FULL_GIT) is not None
    assert _gate(tmp_path, agent=["a"], prompt=FULL_GIT) is not None
    payload = {"cwd": str(_repo(tmp_path)), "session_id": "S", "tool_name": "Agent", "tool_input": "oops"}
    out, _, rc = run_hook("plan-gate", payload, {"FOREMAN_DATA": str(tmp_path / "data")})
    assert rc == 0 and not out.strip()


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
