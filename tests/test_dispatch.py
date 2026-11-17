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
        command = h["command"]
        windows = h["commandWindows"]
        hook = command.split("||")[0].split()[-1]
        assert command.endswith("|| true") and h["timeout"] == 30
        assert hook in foreman_hooks.HOOKS
        assert windows.startswith("try { & uv run --no-project --script (Join-Path $env:PLUGIN_ROOT")
        assert windows.endswith(f" {hook} }} catch {{}}; exit 0")
        assert "||" not in windows

