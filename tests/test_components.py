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
    for s in ["orchestrating", "memory", "verifying", "releasing"]:
        meta, _ = memory.parse_frontmatter((ROOT / "skills" / s / "SKILL.md").read_text(encoding="utf-8"))
        assert meta["name"] == s and meta["description"]


def test_releasing_skill_content():
    t = (ROOT / "skills" / "releasing" / "SKILL.md").read_text(encoding="utf-8")
    for w in ("Keep a Changelog", "SemVer", "Conventional Commits", "[Unreleased]", "vX.Y.Z", "Mode: git"):
        assert w in t, w
    assert "own convention wins" in t


def test_agents_reference_changelog_rule():
    for n in ("planner", "implementer", "ui", "verifier"):
        t = (ROOT / "agents" / f"{n}.md").read_text(encoding="utf-8")
        assert "CHANGELOG.md" in t and "[Unreleased]" in t, n
    assert "--follow-tags" in (ROOT / "agents" / "verifier.md").read_text(encoding="utf-8")


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
    i, j, k, m = (text.find(h) for h in ("\n## Lanes", "\n## Failure routing", "\n## Bug requests", "\n## Task brief template"))
    assert 0 < i < j < k < m
    sec = text[k:m].lower()
    for word in ["mode: diagnose", "implementer", "regression test", "verifier", "base commit", "quick", "docs/plans"]:
        assert word in sec, word
    assert "expert" not in text.lower()


def test_skill_covers_loop():
    text = _skill()
    for w in ["Mode: quick", "foreman:planner", "foreman:builder", "PASS", "FAIL: impl", "FAIL: plan",
              "FAIL: spec", "FAIL: env", "twice", "Mode: lookup", "Grep"]:
        assert w in text, w


def test_agents_describe_bug_handling():
    a = agents()
    impl = a["implementer"][1].lower()
    assert "bug" in impl and "failing test" in impl and "root cause" in impl
    ver = a["verifier"][1].lower()
    assert "regression test" in ver and "base commit" in ver and "git worktree" in ver


def test_verifier_lists_verdicts():
    body = agents()["verifier"][1]
    for w in ["PASS", "FAIL: impl", "FAIL: plan", "FAIL: spec", "FAIL: env",
              "git diff --name-only", "npx impeccable detect --json", "Security", "Impeccable", "first line", "docs/plans/"]:
        assert w in body, w
    assert "Unverified" in body


def test_task_agents_scope_and_dispute():
    a = agents()
    for n in ("implementer", "ui"):
        assert "BLOCKED: plan" in a[n][1] and "DISPUTE" in a[n][1], n
        assert "docs/plans/" in a[n][1], n


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


def test_agents_follow_mvc_layering():
    a = agents()
    for n in ("planner", "implementer", "ui", "verifier"):
        assert "mvc" in a[n][1].lower(), n
    assert "by feature" in a["planner"][1].lower()
    assert "layer" in a["verifier"][1].lower()


def test_changelog_keep_a_changelog():
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    heads = re.findall(r"^## (.+)$", text, re.M)
    assert heads == ["[Unreleased]", "[0.2.1] - 2026-11-20", "[0.2.0] - 2026-11-17"]
    for h in heads[1:]:
        assert re.search(r"\d{4}-\d{2}-\d{2}$", h)
    allowed = {"Added", "Changed", "Deprecated", "Removed", "Fixed", "Security"}
    assert set(re.findall(r"^### (.+)$", text, re.M)) <= allowed
    for ref in ("Unreleased", "0.2.1", "0.2.0"):
        assert re.search(rf"^\[{re.escape(ref)}\]: \S+", text, re.M)
    for url in re.findall(r"^\[[^\]]+\]: (\S+)", text, re.M):
        assert not any(b in url for b in ("/compare/v", "/tree/v", "/releases/tag/")), url


def test_plugin_version_matches_changelog():
    import json
    version = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    newest = re.search(r"^## \[(\d+\.\d+\.\d+)\] - ", text, re.M).group(1)
    assert version == newest == "0.2.1"


def _read(*p):
    return (ROOT.joinpath(*p)).read_text(encoding="utf-8")


def test_releasing_worktree_rules():
    t = _read("skills", "releasing", "SKILL.md")
    for w in ("git worktree add", ".worktrees/", ".git/info/exclude", "git worktree remove",
              "branch -d", "Worktree:", "Branch:", "without --force", "never -D",
              "tracked `.gitignore` is never edited", "plain branch in the main checkout",
              "reason under Evidence", "Editing the default branch is never allowed"):
        assert w in t, w


def test_agents_reference_worktree():
    for n in ("builder", "implementer", "verifier", "ui", "generalist"):
        assert "Worktree:" in _read("agents", f"{n}.md"), n
    t = _read("skills", "orchestrating", "SKILL.md")
    assert "Worktree:" in t and "Branch:" in t


def test_verifier_fails_default_branch():
    t = _read("agents", "verifier.md")
    assert "default branch" in t and "FAIL: impl" in t
    assert "default branch is `FAIL: impl`" in t
