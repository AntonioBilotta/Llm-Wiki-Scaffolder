#!/usr/bin/env python3
"""package_skills.py — build uploadable skill archives for claude.ai.

Claude Code, VS Code Copilot and ~/.agents read the skills straight from the
folders that bin/install.sh copies. claude.ai (web, desktop, mobile) instead
takes one .zip per skill, uploaded from its skill settings, and validates the
SKILL.md frontmatter against the Agent Skills spec keys only. This script
builds those archives without changing the source skills:

  - one archive per skills/wiki-*/ folder:  dist/claude-ai/<name>.zip
  - wiki-init also gets bin/scaffold.py and templates/ (see BUNDLES)
  - archive layout:  <name>/SKILL.md, <name>/scripts/..., other files as-is
  - frontmatter keys outside the spec (argument-hint, user-invocable, ...)
    are dropped from the packaged SKILL.md only; the body is untouched
  - checks name (<= 64 chars, kebab-case) and description (<= 1024 chars)

Deterministic: fixed file order and timestamps, so rebuilding unchanged
skills produces byte-identical archives.

Usage:
  python3 bin/package_skills.py [--out dist/claude-ai] [--only wiki-ingest,wiki-query]

Requires Python 3.8+. Standard library only (ADR-0001).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from pathlib import Path
from typing import List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC_KEYS = ("name", "description", "license", "allowed-tools", "metadata", "compatibility")
SKIP_NAMES = {".DS_Store", "Thumbs.db", "__pycache__"}
# Repo files copied into a skill's archive at build time (the installers do
# the same). Keeps the repo the single source of truth: wiki-init runs the
# same scaffold.py and templates that bin/ and templates/ hold.
BUNDLES = {
    "wiki-init": [("bin/scaffold.py", "scripts/scaffold.py"), ("templates", "templates")],
}
FIXED_DATE = (2026, 1, 1, 0, 0, 0)


def split_frontmatter(text: str) -> Tuple[List[str], str]:
    lines = text.replace("\r\n", "\n").split("\n")
    if not lines or lines[0].strip() != "---":
        raise ValueError("SKILL.md has no YAML frontmatter")
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return lines[1:i], "\n".join(lines[i + 1:])
    raise ValueError("SKILL.md frontmatter is not closed")


def filter_frontmatter(fm_lines: List[str]) -> Tuple[List[str], List[str], dict]:
    """Keep top-level spec keys (and their indented continuation lines)."""
    kept: List[str] = []
    dropped: List[str] = []
    values: dict = {}
    keep_current = False
    for line in fm_lines:
        m = re.match(r"^([A-Za-z_][\w-]*):(.*)$", line)
        if m:
            key = m.group(1)
            keep_current = key in SPEC_KEYS
            if keep_current:
                values[key] = m.group(2).strip()
            else:
                dropped.append(key)
        if keep_current:
            kept.append(line)
    return kept, dropped, values


def unquote(value: str) -> str:
    value = value.strip()
    if value.startswith('"') and value.endswith('"'):
        try:
            return json.loads(value)
        except ValueError:
            return value[1:-1]
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1].replace("''", "'")
    return value


def package(skill_dir: Path, out_dir: Path) -> dict:
    skill_md = skill_dir / "SKILL.md"
    fm_lines, body = split_frontmatter(skill_md.read_text(encoding="utf-8"))
    kept, dropped, values = filter_frontmatter(fm_lines)
    name = unquote(values.get("name", ""))
    description = unquote(values.get("description", ""))
    problems: List[str] = []
    if name != skill_dir.name:
        problems.append(f"name '{name}' differs from folder '{skill_dir.name}'")
    if not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", name) or len(name) > 64:
        problems.append("name must be kebab-case, max 64 chars")
    if not description or len(description) > 1024:
        problems.append(f"description must be 1-1024 chars (got {len(description)})")
    if "<" in description or ">" in description:
        problems.append("description must not contain angle brackets")
    if problems:
        return {"skill": skill_dir.name, "ok": False, "problems": problems}

    packaged_md = "---\n" + "\n".join(kept) + "\n---\n" + body
    out_dir.mkdir(parents=True, exist_ok=True)
    archive = out_dir / f"{name}.zip"
    entries = {}  # arcname relative to the skill folder -> source path
    for p in skill_dir.rglob("*"):
        rel = p.relative_to(skill_dir)
        if p.is_file() and p.suffix != ".pyc" and not any(part in SKIP_NAMES or part.startswith(".git") for part in rel.parts):
            entries[rel.as_posix()] = p
    for src_rel, dest_rel in BUNDLES.get(skill_dir.name, []):
        src = REPO_ROOT / src_rel
        if src.is_file():
            entries[dest_rel] = src
        else:
            for p in src.rglob("*"):
                rel = p.relative_to(src)
                if p.is_file() and not any(part in SKIP_NAMES or part.startswith(".git") for part in rel.parts):
                    entries[f"{dest_rel}/{rel.as_posix()}"] = p
    files = [(k, entries[k]) for k in sorted(entries)]
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for rel_name, path in files:
            arcname = f"{name}/{rel_name}"
            info = zipfile.ZipInfo(arcname, date_time=FIXED_DATE)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o755 if path.suffix == ".py" else 0o644) << 16
            data = packaged_md.encode("utf-8") if path == skill_md else path.read_bytes()
            zf.writestr(info, data)
    return {"skill": name, "ok": True, "archive": str(archive), "files": len(files),
            "dropped_frontmatter_keys": dropped}


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Build claude.ai skill archives from skills/wiki-*/.")
    parser.add_argument("--out", default=str(REPO_ROOT / "dist" / "claude-ai"), help="Output folder.")
    parser.add_argument("--only", default="", help="Comma-separated skill names to package (default: all).")
    args = parser.parse_args(argv)

    only = {s.strip() for s in args.only.split(",") if s.strip()}
    skill_dirs = sorted(d for d in (REPO_ROOT / "skills").glob("wiki-*") if d.is_dir() and (not only or d.name in only))
    results = [package(d, Path(args.out)) for d in skill_dirs]
    json.dump({"out": args.out, "results": results}, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0 if all(r["ok"] for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
