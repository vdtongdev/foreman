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


def test_reads_final_message_from_agent_transcript(tmp_path):
    # Real shape (CLI 2.1.322): the report is the input.message of a SubagentHandback
    # tool_use in the last assistant record; no trailing text block, and the SubagentStop
    # payload carries no last_assistant_message.
    report = "Result: pass\n\n## Evidence\n- pytest: 3 passed\n\n## Unverified\n- none"
    recs = [
        {"type": "assistant", "message": {"role": "assistant", "content": [
            {"type": "text", "text": "Tests pass."}]}},
        {"type": "assistant", "message": {"role": "assistant", "content": [
            {"type": "tool_use", "id": "toolu_1", "name": "SubagentHandback",
             "input": {"message": report}}]}},
        {"type": "user", "message": {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": "toolu_1", "content": [
                {"type": "text", "text": "{\"success\":true}"}]}]}},
    ]
    tp = tmp_path / "agent-abc.jsonl"
    tp.write_text("\n".join(json.dumps(r) for r in recs) + "\n", encoding="utf-8")
    out, _, rc = run_hook("evidence-check", {"agent_id": "abc", "agent_type": "foreman:generalist",
                                             "agent_transcript_path": str(tp),
                                             "hook_event_name": "SubagentStop",
                                             "stop_hook_active": False})
    assert rc == 0
    assert out == ""


def _handback_transcript(tmp_path, report):
    rec = {"type": "assistant", "message": {"role": "assistant", "content": [
        {"type": "tool_use", "id": "toolu_1", "name": "SubagentHandback",
         "input": {"message": report}}]}}
    tp = tmp_path / "agent-abc.jsonl"
    tp.write_text(json.dumps(rec) + "\n", encoding="utf-8")
    return tp


def test_handback_wins_over_closing_text(tmp_path):
    tp = _handback_transcript(
        tmp_path, "Result: pass\n\n## Evidence\n- x\n\n## Unverified\n- none")
    out, _, rc = run_hook("evidence-check", {"last_assistant_message": "Done.",
                                             "agent_transcript_path": str(tp)})
    assert rc == 0
    assert out == ""


def test_missing_transcript_falls_back(tmp_path):
    missing = str(tmp_path / "nope.jsonl")
    ok = "## Evidence\n- x\n\n## Unverified\n- none"
    out, _, rc = run_hook("evidence-check", {"last_assistant_message": ok,
                                             "agent_transcript_path": missing})
    assert rc == 0
    assert out == ""
    out, _, rc = run_hook("evidence-check", {"last_assistant_message": "Done.",
                                             "agent_transcript_path": missing})
    assert rc == 0
    assert json.loads(out) == {"decision": "block", "reason": REASON}
