from datetime import date
import memory


def write(d, name, body="b", type="reference", status="active", trap=False,
          paths=None, topics=None, sup=None, stale="never", desc="d"):
    md = [f"type: {type}", f"status: {status}", "verified: model",
          "verified_on: 2026-10-22", f"stale_after: {stale}"]
    if trap: md.append("trap: true")
    if paths: md.append(f"paths: [{', '.join(paths)}]")
    if topics: md.append(f"topics: [{', '.join(topics)}]")
    if sup: md.append(f"superseded_by: {sup}")
    meta = "".join(f"  {m}\n" for m in md)
    p = d / f"{name}.md"
    p.write_text(f"---\nname: {name}\ndescription: {desc}\nmetadata:\n{meta}---\n{body}\n")
    return p


def load(d):
    return memory.load_layer(d)[0]


def test_index_traps_first_and_deprecated_hidden(tmp_path):
    write(tmp_path, "a-ref")
    write(tmp_path, "b-user", type="user")
    write(tmp_path, "c-trap", trap=True)
    write(tmp_path, "d-old", status="deprecated")
    lines = memory.render_index(load(tmp_path)).splitlines()
    assert lines == ["- TRAP: [c-trap](c-trap.md) — d",
                     "- [b-user](b-user.md) — d", "- [a-ref](a-ref.md) — d"]


def test_index_caps_at_200_lines(tmp_path):
    for i in range(250):
        write(tmp_path, f"e{i:03}")
    lines = memory.render_index(load(tmp_path)).splitlines()
    assert len(lines) == 200
    assert lines[-1] == "- … 51 more: run mem select"


def test_index_caps_bytes(tmp_path):
    for i in range(100):
        write(tmp_path, f"e{i:03}", desc="x" * 500)
    out = memory.render_index(load(tmp_path))
    assert len(out.encode()) <= 25000
    assert out.splitlines()[-1].endswith("run mem select")


def test_index_skips_invalid_entry(tmp_path):
    write(tmp_path, "good")
    (tmp_path / "bad.md").write_text("---\nname bad\n---\nx\n")
    problems = memory.refresh_layer(tmp_path)
    assert any("bad.md" in p for p in problems)
    idx = (tmp_path / "MEMORY.md").read_text(encoding="utf-8")
    assert "[good](good.md)" in idx and "bad" not in idx


def test_refresh_missing_dir_creates_nothing(tmp_path):
    assert memory.refresh_layer(tmp_path / "nope") == []
    assert not (tmp_path / "nope").exists()


def test_refresh_skips_invalid_semantics_and_list_superseded(tmp_path):
    write(tmp_path, "good")
    write(tmp_path, "weird", sup="[x]")
    problems = memory.refresh_layer(tmp_path)
    assert any("weird" in p for p in problems)
    assert "weird" not in (tmp_path / "MEMORY.md").read_text(encoding="utf-8")


def test_rewrite_follows_chain(tmp_path):
    write(tmp_path, "a", status="deprecated", sup="b")
    write(tmp_path, "b", status="deprecated", sup="c")
    write(tmp_path, "c")
    write(tmp_path, "d", body="see [[a]] and [[c]]")
    changed = memory.rewrite_superseded(tmp_path, load(tmp_path))
    assert changed == ["d.md"]
    assert "[[c]] and [[c]]" in (tmp_path / "d.md").read_text()


def test_dangling_reported_not_changed(tmp_path):
    write(tmp_path, "a", body="see [[ghost]] and [[b]]")
    write(tmp_path, "b", status="deprecated")
    assert memory.dangling_links(load(tmp_path)) == ["a.md: [[ghost]]"]
    assert "[[ghost]]" in (tmp_path / "a.md").read_text()


def test_stale_excludes_never_and_future(tmp_path):
    write(tmp_path, "old", stale="2026-01-01")
    write(tmp_path, "future", stale="2027-01-01")
    write(tmp_path, "never")
    write(tmp_path, "dep", stale="2026-01-01", status="deprecated")
    got = memory.stale(load(tmp_path), date(2026, 10, 22))
    assert [e.name for e in got] == ["old"]


def test_select_by_glob_and_topic(tmp_path):
    write(tmp_path, "t", trap=True, paths=["tests/**"], topics=["wsl"])
    write(tmp_path, "plain")
    es = load(tmp_path)
    sel = lambda **k: [(e.name, r) for e, r in memory.select(  # noqa: E731
        es, **{"paths": [], "topics": [], "type": None, "traps_only": False, **k})]
    assert sel(paths=["tests/x/test_a.py"]) == [("t", "path tests/**")]
    assert sel(paths=["src/a.py"]) == []
    assert sel(topics=["wsl"]) == [("t", "topic wsl")]
    assert [n for n, _ in sel()] == ["plain", "t"]
    assert sel(traps_only=True, paths=["tests/a"]) == [("t", "path tests/**")]
    assert sel(type="user") == []
