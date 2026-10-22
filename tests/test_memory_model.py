import pytest
from pathlib import PureWindowsPath
import memory

SPEC = """---
name: wsl-stops-postgres            # kebab-case
description: one line, used for recall
metadata:
  type: reference
  trap: true
  paths: [scripts/dev_db.ps1, tests/**]
  topics: [wsl, postgres]
  status: active
  verified: human
  verified_on: 2026-10-22
  stale_after: 2027-04-22
---
Body.
"""


def entry(tmp_path, **over):
    meta = dict(type="reference", status="active", verified="model",
                verified_on="2026-10-22", stale_after="never")
    meta.update(over)
    name = meta.pop("name", "a")
    lines = "".join(f"  {k}: {v}\n" for k, v in meta.items())
    p = tmp_path / "a.md"
    p.write_text(f"---\nname: {name}\ndescription: d\nmetadata:\n{lines}---\nb\n")
    return memory.load_entry(p)


def test_parse_metadata_nested_and_lists():
    meta, body = memory.parse_frontmatter(SPEC)
    assert meta["name"] == "wsl-stops-postgres"
    assert meta["metadata"]["paths"] == ["scripts/dev_db.ps1", "tests/**"]
    assert body.strip() == "Body."


def test_parse_rejects_unsupported_yaml():
    with pytest.raises(ValueError, match="line 4"):
        memory.parse_frontmatter("---\nname: a\npaths:\n  - a\n---\n")


def test_validate_ok_and_trap_bool(tmp_path):
    e = entry(tmp_path, trap="true")
    assert e.trap is True
    assert memory.validate(e, {"a"}) == []


def test_validate_requires_stale_after_for_reference(tmp_path):
    p = tmp_path / "a.md"
    p.write_text("---\nname: a\ndescription: d\nmetadata:\n  type: reference\n"
                 "  status: active\n  verified: model\n  verified_on: 2026-10-22\n---\n")
    probs = memory.validate(memory.load_entry(p), {"a"})
    assert any("stale_after required" in x for x in probs)


def test_validate_accepts_never(tmp_path):
    assert memory.validate(entry(tmp_path, stale_after="never"), {"a"}) == []


def test_validate_name_must_match_filename(tmp_path):
    assert memory.validate(entry(tmp_path, name="b"), {"a", "b"})


def test_validate_bad_enum(tmp_path):
    assert any("type" in x for x in memory.validate(entry(tmp_path, type="fact"), {"a"}))


def test_validate_superseded_by_must_exist(tmp_path):
    e = entry(tmp_path, status="deprecated", superseded_by="zzz")
    assert any("superseded_by" in x for x in memory.validate(e, {"a"}))


def test_validate_bad_date(tmp_path):
    assert memory.validate(entry(tmp_path, verified_on="22/10/2026"), {"a"})


def test_project_dir_matches_existing_case_insensitive(tmp_path, monkeypatch):
    monkeypatch.setenv("FOREMAN_HOME", str(tmp_path))
    (tmp_path / ".claude" / "projects" / "c--x-repo").mkdir(parents=True)
    monkeypatch.setattr(memory, "_git_root", lambda cwd: PureWindowsPath(r"C:\x\repo"))
    assert memory.project_dir(tmp_path) == tmp_path / ".claude/projects/c--x-repo/memory"


def test_load_layer_missing_dir(tmp_path):
    assert memory.load_layer(tmp_path / "nope") == ([], [])


def test_validate_non_string_values_report_not_raise(tmp_path):
    for k, v in (("type", "[a]"), ("verified_on", "true"), ("verified_on", "[x]"), ("stale_after", "true")):
        assert memory.validate(entry(tmp_path, **{k: v}), {"a"})


def test_scalar_paths_coerced_to_list(tmp_path):
    e = entry(tmp_path, paths="foo")
    assert e.paths == ["foo"] and e.topics == []


def test_bom_tolerated(tmp_path):
    p = tmp_path / "a.md"
    p.write_bytes(b"\xef\xbb\xbf---\nname: a\n---\n")
    assert memory.load_entry(p).name == "a"


def test_project_dir_slug_replaces_every_non_alnum(tmp_path, monkeypatch):
    monkeypatch.setenv("FOREMAN_HOME", str(tmp_path))
    monkeypatch.setattr(memory, "_git_root", lambda cwd: PureWindowsPath(r"C:\a_b\slug_test.x"))
    assert memory.project_dir(tmp_path) == tmp_path / ".claude/projects/C--a-b-slug-test-x/memory"
