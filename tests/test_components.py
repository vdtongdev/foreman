from pathlib import Path
import memory

ROOT = Path(__file__).resolve().parent.parent
NAMES = ["scout", "drafter", "implementer", "verifier", "expert"]


def agents():
    out = {}
    for n in NAMES:
        meta, body = memory.parse_frontmatter((ROOT / "agents" / f"{n}.md").read_text(encoding="utf-8"))
        out[n] = (meta, body)
    return out


def test_agent_models():
    got = {n: (m["model"], m["effort"]) for n, (m, _) in agents().items()}
    assert got == {
        "scout": ("haiku", "low"), "drafter": ("haiku", "low"),
        "implementer": ("sonnet", "medium"), "verifier": ("sonnet", "medium"),
        "expert": ("opus", "high"),
    }
    assert all(m["name"] == n and m["description"] for n, (m, _) in agents().items())


def test_only_expert_has_agent_tool():
    a = agents()
    assert not any("Agent" in str(m.get("tools", "")) for m, _ in a.values())
    assert "Agent" in a["implementer"][0]["disallowedTools"]
    assert "tools" not in a["expert"][0] and "disallowedTools" not in a["expert"][0]
    assert sorted(n for n, (m, _) in a.items() if "tools" in m) == ["drafter", "scout", "verifier"]


def test_every_agent_requires_evidence_sections():
    for n, (_, body) in agents().items():
        assert "## Evidence" in body and "## Unverified" in body, n


def test_skills_have_frontmatter():
    for s in ["orchestrating", "memory", "verifying"]:
        meta, _ = memory.parse_frontmatter((ROOT / "skills" / s / "SKILL.md").read_text(encoding="utf-8"))
        assert meta["name"] == s and meta["description"]
