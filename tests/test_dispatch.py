from conftest import run_hook


def test_unknown_hook_fails_open():
    out, err, code = run_hook("nope", {})
    assert out == "" and code == 0 and "nope" in err


def test_bad_stdin_fails_open():
    out, err, code = run_hook("guard", "not json")
    assert out == "" and code == 0
