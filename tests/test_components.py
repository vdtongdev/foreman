import re
from pathlib import Path
import memory

ROOT = Path(__file__).resolve().parent.parent
NAMES = ["generalist", "implementer", "ui", "planner", "builder", "verifier"]


def agents():
    out = {}
    for n in NAMES:
        meta, body = memory.parse_frontmatter((ROOT / "agents" / f"{n}.md").read_text(encoding="utf-8"))
        out[n] = (meta, body)
    return out


def test_agent_models():
    got = {n: (m["model"], m["effort"]) for n, (m, _) in agents().items()}
    assert got == {
        "generalist": ("haiku", "low"),
        "implementer": ("sonnet", "medium"), "verifier": ("sonnet", "medium"),
        "ui": ("sonnet", "medium"), "planner": ("sonnet", "medium"), "builder": ("sonnet", "medium"),
    }
    assert all(m["name"] == n and m["description"] for n, (m, _) in agents().items())


def test_agents_have_expected_tool_boundaries():
    a = agents()
    assert not any("Agent" in str(m.get("tools", "")) for m, _ in a.values())
    for n in ("implementer", "ui", "planner"):
        assert "Agent" in a[n][0]["disallowedTools"], n
    assert "tools" not in a["builder"][0] and "disallowedTools" not in a["builder"][0]
    assert "Skill" in a["generalist"][0]["tools"]
    assert "Bash" not in a["generalist"][0]["tools"]
    assert not (ROOT / "agents" / "expert.md").exists()
    assert sorted(n for n, (m, _) in a.items() if "tools" in m) == ["generalist", "verifier"]


def test_every_agent_requires_evidence_sections():
    for n, (_, body) in agents().items():
        assert "## Evidence" in body and "## Unverified" in body, n


def test_skills_have_frontmatter():
    for s in ["orchestrating", "memory", "verifying"]:
        meta, _ = memory.parse_frontmatter((ROOT / "skills" / s / "SKILL.md").read_text(encoding="utf-8"))
        assert meta["name"] == s and meta["description"]


def test_frontmatter_values_with_colon_space_are_quoted():
    # Unquoted `key: a: b` breaks Claude Code's YAML parser; the skill then loads with no description.
    files = sorted(ROOT.glob("skills/*/SKILL.md")) + sorted(ROOT.glob("agents/*.md"))
    bad = []
    for f in files:
        head = f.read_text(encoding="utf-8").split("---")[1]
        for line in head.splitlines():
            m = re.match(r"^[A-Za-z_-]+:\s+(.*)$", line)
            if m and ": " in m.group(1) and not m.group(1).startswith(('"', "'")):
                bad.append(f"{f.name}: {line}")
    assert bad == []


def _skill():
    return (ROOT / "skills" / "orchestrating" / "SKILL.md").read_text(encoding="utf-8")


def test_bug_requests_section_placement_and_content():
    text = _skill()
    i, j, k = (text.find(h) for h in ("\n## Escalation", "\n## Bug requests", "\n## Task brief template"))
    assert 0 < i < j < k
    sec = text[j:k].lower()
    for word in ["mode: diagnose", "implementer", "writing-plans", "regression test", "verifier", "base commit", "expert"]:
        assert word in sec, word
    assert "may skip the plan" not in sec and "trivial" not in sec
    assert "yourself" in sec and "docs/plans" in sec


def test_agents_describe_bug_handling():
    a = agents()
    impl = a["implementer"][1].lower()
    assert "bug" in impl and "failing test" in impl and "root cause" in impl
    ver = a["verifier"][1].lower()
    assert "regression test" in ver and "base commit" in ver and "git worktree" in ver


def test_verifier_lists_verdicts():
    body = agents()["verifier"][1]
    for w in ["PASS", "FAIL: impl", "FAIL: plan", "FAIL: spec", "FAIL: env",
              "git diff --name-only", "npx impeccable detect --json", "Security"]:
        assert w in body, w


def test_task_agents_scope_and_dispute():
    a = agents()
    for n in ("implementer", "ui"):
        assert "BLOCKED: plan" in a[n][1] and "DISPUTE" in a[n][1], n


def test_ui_loads_impeccable():
    meta, body = agents()["ui"]
    assert "impeccable" in body and "Impeccable not installed" in body
    assert "tools" not in meta or "Skill" in meta["tools"]


def test_builder_routes_failures():
    body = agents()["builder"][1]
    for w in ["FAIL: impl", "FAIL: plan", "FAIL: spec", "FAIL: env", "twice", "foreman:planner"]:
        assert w in body, w


def test_generalist_lookup_reports_quotes():
    body = agents()["generalist"][1]
    assert "Mode: lookup" in body and "file:line" in body
