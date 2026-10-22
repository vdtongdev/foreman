import json

from conftest import run_hook

REASON = "Add ## Evidence and ## Unverified sections."


def test_missing_sections_block():
    out, _, rc = run_hook("evidence-check", {"last_assistant_message": "All done."})
    assert rc == 0
    assert json.loads(out) == {"decision": "block", "reason": REASON}


def test_sections_present_allow():
    msg = "Result: pass\n\n## Evidence\n- pytest: 3 passed\n\n## unverified\n- none"
    out, _, rc = run_hook("evidence-check", {"last_assistant_message": msg})
    assert rc == 0
    assert out == ""


def test_stop_hook_active_allows():
    out, _, rc = run_hook("evidence-check",
                          {"last_assistant_message": "All done.", "stop_hook_active": True})
    assert rc == 0
    assert out == ""
