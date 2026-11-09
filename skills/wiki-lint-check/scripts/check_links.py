#!/usr/bin/env python3
"""check_links.py — mechanical link-integrity check for an LLM Wiki vault.

Read-only. Never modifies any file. Prints one JSON document on stdout and
always exits 0: the report is the interface, not the exit code.

Obsidian (and every wiki-* skill) resolves a bare [[name]] by file name,
case-insensitively, across the whole vault. Two sweeps follow from that:

1. duplicate_basenames — page names held by two or more files under wiki/
                         (e.g. hats/cappello_rosso.md and
                         agents/cappello_rosso.md). Every bare [[name]] to
                         such a page is ambiguous: Obsidian silently picks
                         one, and so does check_evidence.py. Reported once per
                         name, with the files and the pages that link to it
                         without a folder. Always computed over the whole
                         vault; --pages only narrows ambiguous_links_from.
2. broken_links        — wikilinks and embeds whose target matches no file in
                         the vault. A target with a folder ([[hats/x]]) must
                         match that path suffix; a target with an extension
                         other than .md ([[img.png]]) must match a file name.

Scanned: every page under wiki/, frontmatter included (vaults keep
[[links]] in fields such as related_sources). Masked before scanning: fenced
code and inline code. Ignored: .obsidian/, .git/, .trash/ and dot-folders.
Handled link forms: [[name]], [[name|alias]], [[name\\|alias]] (table
escape), [[name#heading]], [[name#^block]], ![[embed]], [[#local heading]]
(skipped: it points into the same page).

Usage:
  check_links.py --vault-path <vault root> [--pages name1,name2,...]

Requires Python 3.8+. Standard library only (ADR-0001).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Set

FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
INLINE_CODE_RE = re.compile(r"(`+)(?:(?!\1).)+?\1")
WIKILINK_RE = re.compile(r"!?\[\[([^\]\n]*)\]\]")


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------


def mask_code(text: str) -> str:
    """Blank fenced and inline code, keeping line structure."""
    out: List[str] = []
    in_fence: Optional[str] = None
    for line in text.split("\n"):
        fence = FENCE_RE.match(line)
        if in_fence is not None:
            if fence and fence.group(1)[0] == in_fence[0] and len(fence.group(1)) >= len(in_fence):
                in_fence = None
            out.append("")
            continue
        if fence:
            in_fence = fence.group(1)
            out.append("")
            continue
        out.append(INLINE_CODE_RE.sub("", line))
    return "\n".join(out)


def link_target(inner: str) -> str:
    """[[target#h|alias]] -> target. Handles the table-escaped alias pipe."""
    target = re.split(r"\\?\|", inner, maxsplit=1)[0]
    target = re.split(r"#", target, maxsplit=1)[0]
    return target.strip().replace("\\", "/")


def is_hidden(rel_parts: tuple) -> bool:
    return any(part.startswith(".") for part in rel_parts[:-1])


# ---------------------------------------------------------------------------
# Check
# ---------------------------------------------------------------------------


def check(root: Path, scope: Optional[List[str]]) -> Dict[str, object]:
    wiki = root / "wiki"
    md_by_stem: Dict[str, List[str]] = defaultdict(list)
    any_by_name: Dict[str, List[str]] = defaultdict(list)
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if is_hidden(rel.parts):
            continue
        rel_s = rel.as_posix()
        if path.suffix.lower() == ".md":
            md_by_stem[path.stem.casefold()].append(rel_s)
        any_by_name[path.name.casefold()].append(rel_s)

    duplicates: Dict[str, List[str]] = {}
    for stem, paths in md_by_stem.items():
        in_wiki = sorted(p for p in paths if p.startswith("wiki/"))
        if len(in_wiki) > 1:
            duplicates[stem] = in_wiki

    pages = [p for p in sorted(wiki.rglob("*.md")) if not is_hidden(p.relative_to(root).parts)]
    wanted: Optional[Set[str]] = None
    not_found: List[str] = []
    if scope is not None:
        wanted = set()
        for ref in scope:
            name = link_target(ref.strip().strip("[]")).rsplit("/", 1)[-1]
            if name.lower().endswith(".md"):
                name = name[:-3]
            if name.casefold() in md_by_stem:
                wanted.add(name.casefold())
            else:
                not_found.append(name)
        pages = [p for p in pages if p.stem.casefold() in wanted]

    broken: Dict[str, Set[str]] = defaultdict(set)
    ambiguous: Dict[str, Set[str]] = defaultdict(set)
    links_checked = 0
    for page in pages:
        rel_page = page.relative_to(root).as_posix()
        text = page.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")
        for m in WIKILINK_RE.finditer(mask_code(text)):
            target = link_target(m.group(1))
            if not target:
                continue  # [[#heading]] points into the same page
            links_checked += 1
            name = target.rsplit("/", 1)[-1]
            suffix = Path(name).suffix.lower()
            if suffix and suffix != ".md":
                hits = any_by_name.get(name.casefold(), [])
                if "/" in target:
                    hits = [h for h in hits if h.casefold().endswith(target.casefold())]
            else:
                stem = name[:-3] if suffix == ".md" else name
                hits = md_by_stem.get(stem.casefold(), [])
                if "/" in target:
                    want = target if suffix == ".md" else target + ".md"
                    hits = [h for h in hits if h.casefold().endswith(want.casefold())]
                elif stem.casefold() in duplicates:
                    ambiguous[stem.casefold()].add(rel_page)
            if not hits:
                broken[rel_page].add(target)

    dup_report = [
        {"name": stem, "paths": duplicates[stem], "ambiguous_links_from": sorted(ambiguous.get(stem, ()))}
        for stem in sorted(duplicates)
    ]
    broken_report = [{"page": p, "targets": sorted(t)} for p, t in sorted(broken.items())]
    report: Dict[str, object] = {
        "version": 1,
        "vault": str(root),
        "scope": "vault" if scope is None else sorted(wanted or ()),
        "checked": len(pages),
        "duplicate_basenames": dup_report,
        "broken_links": broken_report,
        "summary": {
            "pages_checked": len(pages),
            "links_checked": links_checked,
            "duplicate_basenames": len(dup_report),
            "ambiguous_links": sum(len(d["ambiguous_links_from"]) for d in dup_report),
            "broken_links": sum(len(b["targets"]) for b in broken_report),
        },
    }
    if not_found:
        report["pages_not_found"] = sorted(set(not_found))
    return report


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Mechanical link-integrity check (read-only, JSON on stdout).")
    parser.add_argument("--vault-path", required=True, help="Vault root (contains wiki/).")
    parser.add_argument("--pages", default="", help="Comma-separated page names to limit the per-page scan.")
    args = parser.parse_args(argv)
    # Windows consoles default to a legacy code page; the report may contain
    # any Unicode from wiki pages, so force UTF-8 on stdout when possible.
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except (ValueError, OSError):
            pass

    root = Path(args.vault_path).expanduser()
    if not (root / "wiki").is_dir():
        json.dump({"version": 1, "vault": str(root), "note": "no wiki/ directory under vault path",
                   "duplicate_basenames": [], "broken_links": []},
                  sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        return 0
    scope = [p for p in (x.strip() for x in args.pages.split(",")) if p] or None
    json.dump(check(root, scope), sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
