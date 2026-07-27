#!/usr/bin/env python3
"""Create wiki/analysis/<slug>.md archiving a substantive answer.

Deterministic, atomic single-file write. Refuses to overwrite an
existing analysis page. Uses stdlib only (Python 3.8+).

The `--content` argument is passed through verbatim as the page body —
this script does not re-synthesize or truncate. It wraps the content in
the standard analysis frontmatter and writes the file.

Exit code 0 always. Success/failure is reported in the JSON on stdout.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from datetime import date
from pathlib import Path


def slugify(text: str) -> str:
    """Lowercase snake_case slug, Unicode-safe.

    See write_source_page.py for the full rationale. Kept in sync so both
    skills produce identical slugs for the same title.
    """
    normalized = unicodedata.normalize("NFKD", text)
    stripped = "".join(c for c in normalized if not unicodedata.combining(c))
    s = re.sub(r"[^a-z0-9]+", "_", stripped.lower()).strip("_")
    if s:
        return s
    if text.strip():
        return "page_" + hashlib.md5(text.encode("utf-8")).hexdigest()[:8]
    return ""


def parse_list_arg(raw: str) -> list[str]:
    """Split a comma-separated string into a stripped list of non-empty items."""
    if not raw:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault-path", required=True, help="Absolute path to the vault root.")
    parser.add_argument("--title", required=True, help="Human-readable analysis title.")
    parser.add_argument(
        "--content",
        required=True,
        help="Full markdown body, verbatim. Do not include frontmatter or an H1.",
    )
    parser.add_argument(
        "--related-sources",
        default="",
        help="Comma-separated wiki source page names (without .md).",
    )
    parser.add_argument(
        "--tags",
        default="",
        help="Comma-separated tags.",
    )
    args = parser.parse_args()

    vault = Path(args.vault_path).expanduser().resolve()
    if not vault.is_dir():
        print(json.dumps({"created": False, "reason": "vault_not_found", "vault_path": str(vault)}))
        sys.exit(0)

    if not args.title.strip():
        print(json.dumps({"created": False, "reason": "empty_title"}))
        sys.exit(0)

    slug = slugify(args.title)
    if not slug:
        print(json.dumps({"created": False, "reason": "empty_slug_from_title", "title": args.title}))
        sys.exit(0)

    target = vault / "wiki" / "analysis" / f"{slug}.md"
    target.parent.mkdir(parents=True, exist_ok=True)

    if target.exists():
        print(
            json.dumps(
                {
                    "created": False,
                    "reason": "already_exists",
                    "existing_path": str(target),
                    "page": slug,
                }
            )
        )
        sys.exit(0)

    related = parse_list_arg(args.related_sources)
    tags = parse_list_arg(args.tags)
    today = date.today().isoformat()

    # Bare page names (no `[[...]]` wrapping) — see wiki-conventions.
    # This is what wiki-lint-check and wiki-read-page expect: a YAML list of
    # strings, each a page name under wiki/sources/. `[[wikilink]]` syntax
    # belongs to the body, not to YAML values.
    related_yaml = "[" + ", ".join(related) + "]"
    tags_yaml = "[" + ", ".join(tags) + "]"

    lines: list[str] = [
        "---",
        "type: analysis",
        f"creation_date: {today}",
        f"update_date: {today}",
        f"related_sources: {related_yaml}",
        f"tags: {tags_yaml}",
        "---",
        "",
        f"# {args.title}",
        "",
        args.content.rstrip(),
        "",
    ]

    body = "\n".join(lines)
    target.write_text(body, encoding="utf-8")

    print(json.dumps({"created": True, "path": str(target), "page": slug}))


if __name__ == "__main__":
    main()
