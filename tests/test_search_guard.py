import json

import pytest

from conftest import run_hook

REASON = ("Orchestrator doesn't search: dispatch foreman:generalist with a 'Mode: lookup' line "
          "(reports file:line and quotes), or set FOREMAN_SOLO=1.")


def _run(tool, solo="", **extra):
    payload = {"cwd": ".", "tool_name": tool, "tool_input": {}, **extra}
    out, _, rc = run_hook("search-guard", payload, {"FOREMAN_SOLO": solo})
    assert rc == 0
    return json.loads(out) if out.strip() else None


@pytest.mark.parametrize("tool", ["Grep", "Glob", "WebFetch", "WebSearch"])
def test_search_guard_denies_main_session(tool):
    assert _run(tool) == {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                          "permissionDecision": "deny", "permissionDecisionReason": REASON}}


def test_search_guard_allows_subagent_and_solo():
    assert _run("Grep", agent_id="a1") is None
    assert _run("Grep", solo="1") is None


@pytest.mark.parametrize("tool", ["Read", "Bash"])
def test_search_guard_ignores_other_tools(tool):
    assert _run(tool) is None
