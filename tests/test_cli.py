import subprocess
import memory
from test_memory_index import write


def setup(tmp_path, monkeypatch, git=True):
    home, repo = tmp_path / "home", tmp_path / "repo"
    repo.mkdir()
    if git:
        subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    monkeypatch.setenv("FOREMAN_HOME", str(home))
    monkeypatch.chdir(repo)
    u = memory.user_dir()
    u.mkdir(parents=True)
    return u, repo


def test_cli_select_traps(tmp_path, monkeypatch, capsys):
    u, _ = setup(tmp_path, monkeypatch)
    write(u, "gotcha", trap=True, paths=["src/**"], body="watch out", desc="a trap")
    write(u, "plain", paths=["src/**"])
    assert memory.main(["select", "--path", r"src\x.py", "--traps"]) == 0
    out = capsys.readouterr().out
    assert out == "[user] gotcha (path src/**)\n  a trap\n  watch out\n"


def test_cli_validate_exit_code(tmp_path, monkeypatch, capsys):
    u, _ = setup(tmp_path, monkeypatch)
    write(u, "good")
    assert memory.main(["validate"]) == 0
    assert capsys.readouterr().out == ""
    (u / "bad.md").write_text("no frontmatter\n")
    assert memory.main(["validate"]) == 1
    assert "bad.md" in capsys.readouterr().out


def test_cli_deprecate_sets_status_and_superseded(tmp_path, monkeypatch, capsys):
    u, _ = setup(tmp_path, monkeypatch)
    write(u, "old")
    write(u, "new")
    assert memory.main(["deprecate", "old", "--by", "new"]) == 0
    e = memory.load_entry(u / "old.md")
    assert (e.status, e.superseded_by) == ("deprecated", "new")
    assert "old.md" not in (u / "MEMORY.md").read_text()
    assert memory.main(["deprecate", "nope"]) == 1
    assert "nope" in capsys.readouterr().err


def test_cli_stale_and_no_git(tmp_path, monkeypatch, capsys):
    u, _ = setup(tmp_path, monkeypatch, git=False)
    write(u, "oldie", stale="2020-01-01")
    assert memory.main(["stale"]) == 0
    assert capsys.readouterr().out == "[user] oldie (stale_after 2020-01-01)\n"


def test_cli_deprecate_entry_without_status_line(tmp_path, monkeypatch, capsys):
    u, _ = setup(tmp_path, monkeypatch)
    write(u, "new")
    (u / "nost.md").write_text(
        "---\nname: nost\ndescription: d\nmetadata:\n  type: user\n---\nbody\n")
    (u / "nometa.md").write_text("---\nname: nometa\ndescription: d\n---\nbody\n")
    assert memory.main(["deprecate", "nost", "--by", "new"]) == 0
    e = memory.load_entry(u / "nost.md")
    assert (e.status, e.superseded_by, e.type) == ("deprecated", "new", "user")
    assert memory.main(["deprecate", "nometa"]) == 1
    assert "metadata" in capsys.readouterr().err
