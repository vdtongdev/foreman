# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Foreman memory model: parse, validate, locate layers."""
import os
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

TYPES = {"user", "feedback", "project", "reference"}
STATUSES = {"active", "deprecated"}
VERIFIED = {"human", "model"}
DATE = re.compile(r"\d{4}-\d{2}-\d{2}$")


def _scalar(v: str):
    v = v.strip()
    if v[:1] in "\"'":
        end = v.find(v[0], 1)
        if end < 0:
            raise ValueError("unterminated quote")
        return v[1:end]
    v = re.split(r"\s#", " " + v, 1)[0].strip()
    if v.startswith("["):
        if not v.endswith("]"):
            raise ValueError("unterminated list")
        return [_scalar(x) for x in v[1:-1].split(",") if x.strip()]
    return {"true": True, "false": False}.get(v, v)


def parse_frontmatter(text: str) -> tuple[dict, str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("line 1: missing opening ---")
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration:
        raise ValueError("line 1: missing closing ---") from None
    meta: dict = {}
    cur = None
    for i in range(1, end):
        raw = lines[i]
        n = i + 1
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        m = re.match(r"( *)([A-Za-z_][\w-]*):(?:\s+(.*)|\s*)$", raw)
        if not m:
            raise ValueError(f"line {n}: unsupported syntax: {raw.strip()}")
        indent, key, val = len(m[1]), m[2], m[3]
        target = meta
        if indent:
            if cur is None or indent != 2:
                raise ValueError(f"line {n}: bad indentation")
            target = meta[cur]
        elif val is None or not val.strip() or val.lstrip().startswith("#"):
            meta[key] = {}
            cur = key
            continue
        else:
            cur = None
        if val is None or not val.strip() or val.lstrip().startswith("#"):
            raise ValueError(f"line {n}: nested mappings deeper than one level")
        try:
            target[key] = _scalar(val)
        except ValueError as e:
            raise ValueError(f"line {n}: {e}") from None
    return meta, "\n".join(lines[end + 1:]) + ("\n" if text.endswith("\n") else "")


@dataclass
class Entry:
    name: str
    description: str
    type: str
    status: str
    verified: str
    verified_on: str
    stale_after: str
    body: str
    file: Path
    trap: bool = False
    paths: list[str] = field(default_factory=list)
    topics: list[str] = field(default_factory=list)
    superseded_by: str | None = None


def load_entry(path: Path) -> Entry:
    try:
        meta, body = parse_frontmatter(Path(path).read_text(encoding="utf-8-sig"))
    except ValueError as e:
        raise ValueError(f"{path}: {e}") from None
    md = meta.get("metadata") or {}
    if not isinstance(md, dict):
        raise ValueError(f"{path}: metadata must be a mapping")
    lst = lambda k: md[k] if isinstance(md.get(k), list) else [md[k]] if isinstance(md.get(k), str) else []  # noqa: E731
    g = lambda k: md.get(k, "")  # noqa: E731
    return Entry(
        name=meta.get("name", ""), description=meta.get("description", ""),
        type=g("type"), status=g("status"), verified=g("verified"),
        verified_on=g("verified_on"), stale_after=g("stale_after"), body=body,
        file=Path(path), trap=md.get("trap") is True,
        paths=lst("paths"), topics=lst("topics"),
        superseded_by=md.get("superseded_by") or None,
    )


def validate(entry: Entry, names: set[str]) -> list[str]:
    f, out = str(entry.file), []
    bad = lambda msg: out.append(f"{f}: {msg}")  # noqa: E731
    if not entry.name:
        bad("name required")
    elif entry.name != Path(f).stem:
        bad(f"name '{entry.name}' must equal filename")
    if not entry.description:
        bad("description required")
    for key, allowed in (("type", TYPES), ("status", STATUSES), ("verified", VERIFIED)):
        v = getattr(entry, key)
        if not v:
            bad(f"{key} required")
        elif not isinstance(v, str) or v not in allowed:
            bad(f"{key} '{v}' not in {sorted(allowed)}")
    if not entry.verified_on:
        bad("verified_on required")
    elif not isinstance(entry.verified_on, str) or not DATE.match(entry.verified_on):
        bad(f"verified_on '{entry.verified_on}' must be YYYY-MM-DD")
    if entry.type in ("project", "reference") and not entry.stale_after:
        bad("stale_after required for project and reference")
    elif entry.stale_after and entry.stale_after != "never" and not (
            isinstance(entry.stale_after, str) and DATE.match(entry.stale_after)):
        bad(f"stale_after '{entry.stale_after}' must be YYYY-MM-DD or never")
    if entry.superseded_by and entry.superseded_by not in names:
        bad(f"superseded_by '{entry.superseded_by}' does not exist")
    return out


def _home() -> Path:
    return Path(os.environ.get("FOREMAN_HOME") or Path.home())


def user_dir() -> Path:
    return _home() / ".claude" / "memory"


def _git_root(cwd: Path) -> Path | None:
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
            cwd=cwd, capture_output=True, text=True)
    except OSError:
        return None
    return Path(r.stdout.strip()).parent if r.returncode == 0 and r.stdout.strip() else None


def project_dir(cwd: Path) -> Path | None:
    root = _git_root(cwd)
    if root is None:
        return None
    slug = str(root).translate(str.maketrans(dict.fromkeys(chr(92) + ":/ ", "-")))
    projects = _home() / ".claude" / "projects"
    if projects.is_dir():
        for d in projects.iterdir():
            if d.name.lower() == slug.lower():
                return d / "memory"
    return projects / slug / "memory"


def load_layer(dir: Path) -> tuple[list[Entry], list[str]]:
    entries, errors = [], []
    if not Path(dir).is_dir():
        return entries, errors
    for p in sorted(Path(dir).glob("*.md")):
        if p.name == "MEMORY.md":
            continue
        try:
            entries.append(load_entry(p))
        except (ValueError, OSError) as e:
            errors.append(str(e))
    return entries, errors
