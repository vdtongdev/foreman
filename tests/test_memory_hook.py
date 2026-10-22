import json

from conftest import run_hook
from test_memory_index import write


def _run(tmp_path, file_path):
    payload = {"cwd": str(tmp_path), "tool_name": "Write",
               "tool_input": {"file_path": str(file_path)}}
    out, _, rc = run_hook("memory-write", payload, {"FOREMAN_HOME": str(tmp_path / "home")})
    assert rc == 0
    return json.loads(out) if out.strip() else None


def _layer(tmp_path):
    d = tmp_path / "home" / ".claude" / "memory"
    d.mkdir(parents=True)
    return d


def test_valid_write_regenerates_index(tmp_path):
    d = _layer(tmp_path)
    p = write(d, "alpha", desc="the alpha")
    assert _run(tmp_path, p) is None
    assert "- [alpha](alpha.md) — the alpha" in (d / "MEMORY.md").read_text(encoding="utf-8")


def test_invalid_write_blocks_with_reason(tmp_path):
    d = _layer(tmp_path)
    p = d / "bad.md"
    p.write_text("---\nname: bad\n---\nb\n")
    out = _run(tmp_path, p)
    assert out["decision"] == "block"
    assert out["reason"].startswith("Memory entry problems:\n")
    assert "bad" in out["reason"]


def test_non_memory_path_ignored(tmp_path):
    _layer(tmp_path)
    assert _run(tmp_path, tmp_path / "src.py") is None
    assert _run(tmp_path, tmp_path / "home" / ".claude" / "memory" / "MEMORY.md") is None


def test_dangling_link_is_context_not_block(tmp_path):
    d = _layer(tmp_path)
    p = write(d, "alpha", body="see [[ghost]]")
    out = _run(tmp_path, p)
    h = out["hookSpecificOutput"]
    assert h["hookEventName"] == "PostToolUse"
    assert h["additionalContext"].startswith("Dangling memory links (write or remove): ")
    assert "[[ghost]]" in h["additionalContext"]
