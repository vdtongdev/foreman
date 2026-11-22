import datetime
import re
from pathlib import Path

import pytest
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
    for s in ["orchestrating", "memory", "verifying", "releasing", "antipatterns"]:
        meta, _ = memory.parse_frontmatter((ROOT / "skills" / s / "SKILL.md").read_text(encoding="utf-8"))
        assert meta["name"] == s and meta["description"]


KARPATHY = Path.home() / ".claude/plugins/marketplaces/karpathy-skills/skills/karpathy-guidelines/SKILL.md"


def test_antipatterns_skill_content():
    raw = (ROOT / "skills" / "antipatterns" / "SKILL.md").read_text(encoding="utf-8")
    meta, body = memory.parse_frontmatter(raw)
    assert meta["name"] == "antipatterns" and meta["description"]
    lines = raw.splitlines()
    assert [l for l in lines if l.startswith("## ")] == [
        "## Scope and simplicity", "## Code smells", "## Design patterns", "## Agent workflow"]
    assert "karpathy-guidelines" in raw and "MIT" in raw
    assert 40 <= len(lines) <= 80
    for group in re.split(r"^## ", body, flags=re.M)[1:]:
        bullets = [l for l in group.splitlines() if l.startswith("- ")]
        assert len(bullets) >= 4, group.splitlines()[0]
        assert all(": " in b for b in bullets), group.splitlines()[0]
    for w in ("50 lines", "3 nesting", "third copy", "2 or more concrete variants", "MVC", "dispatch",
              "already quoted", "intent", "projectPath", "by layer", "default branch", "git add -A"):
        assert w in raw, w


def test_antipatterns_no_verbatim_karpathy():
    import pytest
    if not KARPATHY.exists():
        pytest.skip("karpathy-guidelines not installed")
    mine = (ROOT / "skills" / "antipatterns" / "SKILL.md").read_text(encoding="utf-8")
    for l in KARPATHY.read_text(encoding="utf-8").splitlines():
        l = l.strip()
        if len(l) >= 30:
            assert l not in mine, l


def test_memory_skill_fitness_rules():
    t = (ROOT / "skills" / "memory" / "SKILL.md").read_text(encoding="utf-8")
    for w in ("dead weight", "share a root rule", "moved past"):
        assert w in t, w
    assert t.count("recurrent") == 1


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


def test_implementer_git_mode_merges_via_pr_and_overrides_brief():
    body = agents()["implementer"][1]
    assert "gh pr merge --merge" in body
    assert "override" in body and "Unverified" in body


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


def _parse_changelog(text):
    """Return [(heading, body)] per `## ` section; assert Keep a Changelog heading rules."""
    heads = re.findall(r"^## (.+)$", text, re.M)
    bodies = re.split(r"^## .+$", text, flags=re.M)[1:]
    assert heads and heads[0] == "[Unreleased]"
    prev = None
    for h in heads[1:]:
        m = re.fullmatch(r"\[(\d+)\.(\d+)\.(\d+)\] - (\d{4}-\d{2}-\d{2})", h)
        assert m, h
        datetime.date.fromisoformat(m.group(4))
        ver = tuple(int(x) for x in m.groups()[:3])
        assert prev is None or ver < prev, h
        prev = ver
    return list(zip(heads, bodies))


def _released_versions(sections):
    return [re.match(r"\[([^\]]+)\]", h).group(1) for h, _ in sections[1:]]


def test_changelog_keep_a_changelog():
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    sections = _parse_changelog(text)
    allowed = {"Added", "Changed", "Deprecated", "Removed", "Fixed", "Security"}
    assert set(re.findall(r"^### (.+)$", text, re.M)) <= allowed
    for ref in ["Unreleased"] + _released_versions(sections):
        assert re.search(rf"^\[{re.escape(ref)}\]: \S+", text, re.M), ref
    for url in re.findall(r"^\[[^\]]+\]: (\S+)", text, re.M):
        assert not any(b in url for b in ("/compare/v", "/tree/v", "/releases/tag/")), url


def test_parse_changelog_rejects_bad_input():
    def log(*heads):
        return "".join(f"## {h}\n\n" for h in heads)

    ok = log("[Unreleased]", "[0.2.0] - 2026-01-02", "[0.1.0] - 2026-01-01")
    assert _released_versions(_parse_changelog(ok)) == ["0.2.0", "0.1.0"]
    swapped = log("[Unreleased]", "[0.1.0] - 2026-01-01", "[0.2.0] - 2026-01-02")
    bad_date = log("[Unreleased]", "[0.2.0] - 2026-13-45")
    for bad in (swapped, bad_date):
        with pytest.raises((AssertionError, ValueError)):
            _parse_changelog(bad)


def test_plugin_version_matches_changelog():
    import json
    version = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]
    sections = _parse_changelog((ROOT / "CHANGELOG.md").read_text(encoding="utf-8"))
    assert version == _released_versions(sections)[0]


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


NEVER_PP = "never pass a worktree as `projectPath`"


def test_releasing_codegraph_rules():
    t = _read("skills", "releasing", "SKILL.md")
    for w in ("codegraph init", "codegraph sync", "codegraph uninit", "git push origin --delete",
              NEVER_PP, "`codegraph explore` with the worktree as the working directory",
              "only if the main checkout has `.codegraph/`", "a project without `.codegraph/` gets nothing",
              "the main index must not contain `.worktrees/`",
              "tracked `.gitignore` is never edited"):
        assert w in t, w


def test_releasing_cleanup_order():
    t = _read("skills", "releasing", "SKILL.md")
    assert "`gh pr merge --merge` without `--delete-branch`" in t
    assert "remote branch" in t and "while a worktree holds the local" in t
    assert "daemon" not in t
    pos = [t.index(s) for s in ("codegraph uninit", "git worktree remove", "branch -d", "git push origin --delete")]
    assert pos == sorted(pos)
    assert "never -D" in t and "without --force" in t and "--ff-only" in t
    assert "git diff --no-index" in t
    assert "delete the branch after merge" not in t


def test_agents_codegraph_cli_only_in_worktrees():
    for n in ("implementer", "ui", "verifier"):
        t = _read("agents", f"{n}.md")
        assert "codegraph explore" in t and NEVER_PP in t, n
    for n in ("implementer", "ui"):
        assert "codegraph sync" in _read("agents", f"{n}.md"), n
    g = _read("agents", "generalist.md")
    assert "Read only inside worktrees" in g and NEVER_PP in g
    assert "does not run `codegraph sync`" in g
    assert g.count("codegraph sync") == 1
    for n in ("builder", "implementer"):
        assert "codegraph init" in _read("agents", f"{n}.md"), n
    files = [ROOT / "agents" / f"{n}.md" for n in ("builder", "generalist", "implementer", "planner", "ui", "verifier")]
    files.append(ROOT / "skills" / "releasing" / "SKILL.md")
    for f in files:
        for line in f.read_text(encoding="utf-8").splitlines():
            if "projectPath" in line and "worktree" in line.lower():
                assert "never" in line, (f.name, line)


def test_task_agents_load_antipatterns():
    for n in ("implementer", "ui"):
        t = _read("agents", f"{n}.md")
        assert "Load the `foreman:antipatterns` skill with the Skill tool before writing code" in t, n
        for s in ("BLOCKED: plan", "DISPUTE", "Worktree:", "codegraph explore"):
            assert s in t, (n, s)
    assert "business rules go in the model" in _read("agents", "implementer.md")
    assert "business rules stay in the model or controller layer" in _read("agents", "ui.md")


def test_verifier_antipattern_fail_rules():
    t = _read("agents", "verifier.md")
    for s in ("interface or factory with one implementation", "added magic number in logic",
              "duplicated block of 3 or more copies", "function over 80 lines",
              "only for items introduced by the diff", "not a FAIL",
              "FAIL: impl", "FAIL: plan", "FAIL: spec", "FAIL: env", "PASS"):
        assert s in t, s


def test_orchestrating_references_antipatterns():
    t = _read("skills", "orchestrating", "SKILL.md")
    assert t.count("foreman:antipatterns") == 1
    line = next(l for l in t.splitlines() if "foreman:antipatterns" in l)
    assert "agent-workflow group" in line


def test_antipatterns_in_readme_and_changelog():
    r = _read("README.md")
    row = next(l for l in r.splitlines() if l.startswith("├── skills/"))
    assert "antipatterns/" in row
    assert "load `antipatterns`" in r
    c = _read("CHANGELOG.md")
    addeds = [
        body.split("### Added")[1].split("\n### ")[0]
        for _, body in _parse_changelog(c)
        if "### Added" in body
    ]
    assert any("antipatterns" in a for a in addeds)
