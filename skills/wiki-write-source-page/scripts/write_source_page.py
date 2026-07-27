#!/usr/bin/env python3
"""Create wiki/sources/<slug>.md from a structured summary.

Deterministic, atomic single-file write. Refuses to overwrite an
existing source page. Uses stdlib only (Python 3.8+).

Invoked by the wiki-write-source-page skill. Reads a summary from
`--summary-json` (a compact JSON string matching the return shape of
wiki-summarize-source) and writes the page in the standard format.

Exit code 0 always. Success/failure is reported in the JSON on stdout.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path


def slugify(text: str) -> str:
    """Lowercase, non-alphanumeric to underscore, collapse runs, strip edges."""
    s = re.sub(r"[^a-z0-9]+", "_", text.lower())
    return s.strip("_")


def build_page(summary: dict, today: str) -> str:
    """Compose the source page markdown from a summary dict."""
    title = summary["title"]
    prov = summary.get("provenance") or {}
    raw_path = prov.get("raw_path", "")
    original_url = prov.get("original_url")

    lines: list[str] = [
        "---",
        "type: source",
        f"creation_date: {today}",
        f"update_date: {today}",
        "related_sources: []",
        "tags: []",
        "---",
        "",
        f"# {title}",
        "",
    ]

    prov_line = f"**Provenance**: `{raw_path}`"
    if original_url:
        prov_line += f" · [original]({original_url})"
    lines.append(prov_line)
    if summary.get("date"):
        lines.append(f"**Date**: {summary['date']}")
    lines.append("")

    key_points = summary.get("key_points") or []
    if key_points:
        lines.append("## Summary")
        lines.append("")
        for kp in key_points:
            lines.append(f"- {kp}")
        lines.append("")

    for section_name, key in (("Entities", "entities"), ("Concepts", "concepts")):
        items = summary.get(key) or []
        if items:
            lines.append(f"## {section_name}")
            lines.append("")
            for item in items:
                lines.append(f"- [[{slugify(item)}]]")
            lines.append("")

    domain_items = summary.get("domain_items") or {}
    for dtype, items in domain_items.items():
        if items:
            lines.append(f"## {dtype.capitalize()}")
            lines.append("")
            for item in items:
                lines.append(f"- [[{slugify(item)}]]")
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault-path", required=True, help="Absolute path to the vault root.")
    parser.add_argument(
        "--summary-json",
        required=True,
        help="Compact JSON string with the summary (title required; others optional).",
    )
    args = parser.parse_args()

    try:
        summary = json.loads(args.summary_json)
    except json.JSONDecodeError as e:
        print(json.dumps({"created": False, "reason": f"invalid_summary_json: {e}"}))
        sys.exit(0)

    if not isinstance(summary, dict):
        print(json.dumps({"created": False, "reason": "summary_not_object"}))
        sys.exit(0)

    title = summary.get("title")
    if not isinstance(title, str) or not title.strip():
        print(json.dumps({"created": False, "reason": "missing_title"}))
        sys.exit(0)

    vault = Path(args.vault_path).expanduser().resolve()
    if not vault.is_dir():
        print(json.dumps({"created": False, "reason": "vault_not_found", "vault_path": str(vault)}))
        sys.exit(0)

    slug = slugify(title)
    if not slug:
        print(json.dumps({"created": False, "reason": "empty_slug_from_title", "title": title}))
        sys.exit(0)

    target = vault / "wiki" / "sources" / f"{slug}.md"
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

    today = date.today().isoformat()
    body = build_page(summary, today)
    target.write_text(body, encoding="utf-8")

    print(json.dumps({"created": True, "path": str(target), "page": slug}))


if __name__ == "__main__":
    main()
