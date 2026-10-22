"""Opt-in end-to-end check: a bug report must go diagnose -> plan -> execute via the foreman loop.

Run with FOREMAN_E2E=1 (needs the foreman plugin installed at user scope and a working `claude` CLI).
"""
import json
import os
import subprocess
import sys

import pytest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

pytestmark = pytest.mark.skipif(os.environ.get("FOREMAN_E2E") != "1", reason="set FOREMAN_E2E=1 to run")

PROMPT = (
    "average() in calc.py returns the wrong number. average([2, 4, 6]) should return 4.0 "
    "but it returns 2.0; average([10]) should be 10.0 but gives 0.0. "
    "Fix it. Don't ask me questions; carry the work through to the end."
)


def git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def tool_uses(path):
    """Yield (index, name, input, is_main_session) for every allowed (not plan-gate-denied) tool_use in the stream-json transcript."""
    uses, denied = [], set()
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f):
            try:
                ev = json.loads(line)
            except ValueError:
                continue
            content = (ev.get("message") or {}).get("content")
            if not isinstance(content, list):
                continue
            for b in content:
                if ev.get("type") == "assistant" and b.get("type") == "tool_use":
                    uses.append((i, b["name"], b["input"], not ev.get("parent_tool_use_id"), b["id"]))
                elif b.get("type") == "tool_result" and "Edit work needs a plan" in json.dumps(b.get("content")):
                    denied.add(b.get("tool_use_id"))
    return [u[:4] for u in uses if u[4] not in denied]


def test_bug_goes_through_diagnose_plan_execute(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    # the cause lives in a second file so it is not a one-glance fix
    (repo / "calc.py").write_text("from helpers import total\n\n\ndef average(xs):\n    return total(xs) / len(xs)\n")
    (repo / "helpers.py").write_text("def total(xs):\n    return sum(xs[:-1])\n")
    git(repo, "init", "-q")
    git(repo, "add", ".")
    git(repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "init")

    out = tmp_path / "transcript.jsonl"
    with open(out, "w", encoding="utf-8") as f:
        subprocess.run(
            ["claude", "-p", PROMPT, "--model", os.environ.get("FOREMAN_E2E_MODEL", "sonnet"),
             "--permission-mode", "acceptEdits", "--allowedTools", "Bash",
             "--output-format", "stream-json", "--verbose",
             "--plugin-dir", str(ROOT)],  # test the working tree, not the (possibly older) installed copy
            cwd=repo, stdout=f, stderr=subprocess.STDOUT, timeout=900, check=False,
        )
    print(f"\ntranscript: {out}")

    uses = list(tool_uses(out))
    agents = [(i, inp.get("subagent_type")) for i, n, inp, main in uses if n in ("Agent", "Task") and main]
    plans = [i for i, n, inp, main in uses if main and n == "Write"
             and inp.get("file_path", "").replace("\\", "/").endswith(".md")
             and "/docs/" in inp["file_path"].replace("\\", "/")]
    assert plans, "no plan .md written under docs/ by the main session"
    plan_at = plans[0]
    assert any(t == "foreman:implementer" and i < plan_at for i, t in agents), "1: no implementer dispatch before the plan"
    assert any(p.is_file() for p in (repo / "docs").rglob("*.md")), "2: plan file missing after run"
    assert any(t == "foreman:verifier" and i > plan_at for i, t in agents), "3: no verifier dispatch after the plan"

    r = subprocess.run([sys.executable, "-c", "import calc; print(calc.average([2, 4, 6]), calc.average([10]))"],
                       cwd=repo, capture_output=True, text=True)
    assert r.stdout.strip() == "4.0 10.0", f"4: bug not fixed: {r.stdout!r} {r.stderr!r}"
    tests = [p for p in repo.rglob("*.py") if p.name not in ("calc.py", "helpers.py") and "average" in p.read_text(encoding="utf-8")]
    assert tests, "4: no test file covering average"

    edits = [inp for i, n, inp, main in uses if main and n in ("Edit", "Write", "MultiEdit")
             and inp.get("file_path", "").replace("\\", "/").endswith(("calc.py", "helpers.py"))]
    # shortcut: counts attempted edits, not only successful ones; tighten with tool_result is_error if the guard's denials make this noisy
    assert not edits, f"5: main session touched product code: {edits}"
