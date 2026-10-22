# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Foreman memory model: parse, validate, locate layers."""
import os
import re
import subprocess
from datetime import date
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
    if entry.superseded_by and not (
            isinstance(entry.superseded_by, str) and entry.superseded_by in names):
        bad(f"superseded_by '{entry.superseded_by}' does not exist")
    return out


def _home() -> Path:
    return Path(os.environ.get("FOREMAN_HOME") or Path.home())


def user_dir() -> Path:
    return _home() / ".claude" / "memory"


def _rev_parse(cwd: Path, flag: str) -> str:
    try:
        r = subprocess.run(["git", "rev-parse", "--path-format=absolute", flag],
                           cwd=cwd, capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return r.stdout.strip() if r.returncode == 0 else ""


def _git_root(cwd: Path) -> Path | None:
    """Main checkout (shared by worktrees); used for the memory folder slug."""
    out = _rev_parse(cwd, "--git-common-dir")
    return Path(out).parent if out else None


def _toplevel(cwd: Path) -> Path | None:
    """Root of the current checkout, worktree-aware."""
    out = _rev_parse(cwd, "--show-toplevel")
    return Path(out) if out else None


def project_dir(cwd: Path) -> Path | None:
    root = _git_root(cwd)
    if root is None:
        return None
    slug = re.sub(r"[^A-Za-z0-9]", "-", str(root))
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


TYPE_ORDER = {t: i for i, t in enumerate(("user", "feedback", "project", "reference"))}
LINK = re.compile(r"\[\[([^\]\n]+)\]\]")
MAX_LINES, MAX_BYTES = 200, 25000


def render_index(entries: list[Entry]) -> str:
    act = sorted((e for e in entries if e.status != "deprecated"),
                 key=lambda e: (not e.trap, TYPE_ORDER.get(e.type, 9), e.name))
    lines = [f"- {'TRAP: ' if e.trap else ''}[{e.name}]({e.file.name}) — {e.description}"
             for e in act]
    size = lambda ls: len(("\n".join(ls) + "\n").encode())  # noqa: E731
    if len(lines) <= MAX_LINES and size(lines) <= MAX_BYTES:
        return "\n".join(lines) + "\n" if lines else ""
    k = min(len(lines), MAX_LINES - 1)
    while k and size(lines[:k] + [f"- … {len(lines) - k} more: run mem select"]) > MAX_BYTES:
        k -= 1
    return "\n".join(lines[:k] + [f"- … {len(lines) - k} more: run mem select"]) + "\n"


def rewrite_superseded(dir: Path, entries: list[Entry]) -> list[str]:
    sup = {e.name: e.superseded_by for e in entries if isinstance(e.superseded_by, str)}
    names = {e.name for e in entries}

    def final(n: str) -> str:
        seen = {n}
        while sup.get(n) in names and sup[n] not in seen:
            n = sup[n]
            seen.add(n)
        return n

    changed = []
    for e in entries:
        p = Path(dir) / e.file.name
        text = p.read_text(encoding="utf-8-sig")
        new = LINK.sub(lambda m: f"[[{final(m[1])}]]" if m[1] in sup else m[0], text)
        if new != text:
            p.write_text(new, encoding="utf-8", newline="\n")
            e.body = LINK.sub(lambda m: f"[[{final(m[1])}]]" if m[1] in sup else m[0], e.body)
            changed.append(p.name)
    return changed


def dangling_links(entries: list[Entry]) -> list[str]:
    names = {e.name for e in entries}
    return [f"{e.file.name}: [[{x}]]" for e in entries
            for x in LINK.findall(e.body) if x not in names]


def refresh_layer(dir: Path) -> list[str]:
    if not Path(dir).is_dir():
        return []
    entries, problems = load_layer(dir)
    rewrite_superseded(dir, entries)
    names = {e.name for e in entries}
    ok = []
    for e in entries:
        errs = validate(e, names)
        problems += errs
        if not errs:
            ok.append(e)
    idx, new = Path(dir) / "MEMORY.md", render_index(ok)
    if idx.is_file():
        old = idx.read_text(encoding="utf-8-sig")
        bak = idx.with_name("MEMORY.md.bak")
        if not bak.exists() and set(filter(str.strip, old.splitlines())) - set(new.splitlines()):
            bak.write_text(old, encoding="utf-8", newline="")
            problems.append(f"{idx} had hand-written lines; saved to MEMORY.md.bak")
    idx.write_text(new, encoding="utf-8", newline="\n")
    return problems


def stale(entries: list[Entry], today: date) -> list[Entry]:
    t = today.isoformat()
    return [e for e in entries if e.status != "deprecated"
            and isinstance(e.stale_after, str) and DATE.match(e.stale_after) and e.stale_after < t]


def _glob(pat: str) -> re.Pattern:
    out, i = "", 0
    while i < len(pat):
        if pat.startswith("**/", i):
            out, i = out + "(?:.*/)?", i + 3
        elif pat.startswith("**", i):
            out, i = out + ".*", i + 2
        else:
            c = pat[i]
            out += "[^/]*" if c == "*" else "[^/]" if c == "?" else re.escape(c)
            i += 1
    return re.compile(out + r"\Z")


def select(entries: list[Entry], paths: list[str], topics: list[str],
           type: str | None, traps_only: bool) -> list[tuple[Entry, str]]:
    out = []
    for e in entries:
        if e.status == "deprecated" or (type and e.type != type) or (traps_only and not e.trap):
            continue
        if not paths and not topics:
            out.append((e, "all"))
            continue
        why = next((f"path {g}" for g in e.paths for p in paths if _glob(g).match(p)), None)             or next((f"topic {t}" for t in e.topics if t in topics), None)
        if why:
            out.append((e, why))
    return out


def _rel(p: str, root: Path | None) -> str:
    if root:
        try:
            return (Path.cwd() / p).resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            pass
    return p.replace("\\", "/")


def _set_status(text: str, new: str | None) -> str | None:
    lines, in_md, last, has = text.splitlines(keepends=True), False, None, False
    nl = "\n"
    for i in range(1, _end(lines)):
        ln = lines[i]
        if ln[:1] not in " \t" and ln.strip() and not ln.startswith("#"):
            in_md = bool(re.match(r"metadata:\s*$", ln))
            continue
        if not in_md or not ln.strip():
            continue
        nl = ln[len(ln.rstrip("\r\n")):] or nl
        if ln.startswith("  superseded_by:"):
            lines[i] = ""
            continue
        elif ln.startswith("  status:"):
            lines[i], has = "  status: deprecated" + nl, True
        last = i
    if last is None:
        return None
    if not has:
        lines[last] += ("" if lines[last].endswith(nl) else nl) + "  status: deprecated" + nl
    if new:
        lines[last] += ("" if lines[last].endswith(nl) else nl) + f"  superseded_by: {new}" + nl
    return "".join(lines)


def _end(lines: list[str]) -> int:
    return next(i for i in range(1, len(lines)) if lines[i].strip() == "---")


def main(argv: list[str]) -> int:
    import argparse
    import sys
    ap = argparse.ArgumentParser(prog="mem")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("select")
    s.add_argument("--path", action="append", default=[])
    s.add_argument("--topic", action="append", default=[])
    s.add_argument("--type")
    s.add_argument("--traps", action="store_true")
    for c in ("stale", "validate", "index"):
        sub.add_parser(c)
    d = sub.add_parser("deprecate")
    d.add_argument("name")
    d.add_argument("--by")
    a = ap.parse_args(argv)

    root = _toplevel(Path.cwd())
    pd = project_dir(Path.cwd())
    layers = ([("project", pd)] if pd else []) + [("user", user_dir())]
    loaded = [(n, d_, *load_layer(d_)) for n, d_ in layers]

    if a.cmd == "select":
        paths = [_rel(p, root) for p in a.path]
        for n, _, entries, _ in loaded:
            for e, why in select(entries, paths, a.topic, a.type, a.traps):
                print(f"[{n}] {e.name} ({why})\n  {e.description}")
                if e.trap:
                    print("".join(f"  {ln}\n" for ln in e.body.strip("\n").splitlines()), end="")
    elif a.cmd == "stale":
        for n, _, entries, _ in loaded:
            for e in stale(entries, date.today()):
                print(f"[{n}] {e.name} (stale_after {e.stale_after})")
    elif a.cmd == "validate":
        probs = []
        for _, _, entries, errs in loaded:
            names = {e.name for e in entries}
            probs += errs + [p for e in entries for p in validate(e, names)]
        for x in probs:
            print(x)
        return 1 if probs else 0
    elif a.cmd == "index":
        for _, d_, _, _ in loaded:
            for x in refresh_layer(d_):
                print(x)
    else:
        for _, d_, entries, _ in loaded:
            hit = next((e for e in entries if e.name == a.name), None)
            if hit:
                if a.by and a.by not in {e.name for e in entries}:
                    print(f"mem: no entry named '{a.by}'", file=sys.stderr)
                    return 1
                p = hit.file
                text = _set_status(p.read_bytes().decode("utf-8-sig"), a.by)
                if text is None:
                    print(f"mem: '{a.name}' has no metadata block", file=sys.stderr)
                    return 1
                p.write_text(text, encoding="utf-8", newline="")
                probs = refresh_layer(d_)
                for x in probs:
                    print(x)
                return 1 if any(p.name in x for x in probs) else 0
        print(f"mem: no entry named '{a.name}'", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main(sys.argv[1:]))
