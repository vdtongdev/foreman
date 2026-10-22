from conftest import run_hook


def test_unknown_hook_fails_open():
    out, err, code = run_hook("nope", {})
    assert out == "" and code == 0 and "nope" in err


def test_bad_stdin_fails_open():
    out, err, code = run_hook("guard", "not json")
    assert out == "" and code == 0


def test_hooks_json_fail_open_and_known_hooks():
    import json
    from pathlib import Path
    import foreman_hooks
    d = json.loads((Path(__file__).resolve().parent.parent / "hooks" / "hooks.json").read_text())
    cmds = [h for g in d["hooks"].values() for e in g for h in e["hooks"]]
    assert cmds
    for h in cmds:
        assert h["command"].endswith("|| true") and h["timeout"] == 30
        assert h["command"].split("||")[0].split()[-1] in foreman_hooks.HOOKS

