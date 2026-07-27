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
from datetime import datetime, timezone
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
    today = datetime.now(timezone.utc).date().isoformat()

    # Guard: content must not start with `---`. If it does, the resulting page
    # would have two frontmatter blocks, confusing readers and parsers.
    # SKILL.md's gotcha documents this constraint; enforce it here as a
    # machine-checkable refusal so misuse fails loudly, not silently.
    if args.content.lstrip().startswith("---"):
        print(json.dumps({
            "created": False,
            "reason": "content_starts_with_frontmatter_fence",
            "detail": "--content must not start with `---`; the script wraps its own frontmatter.",
        }))
        sys.exit(0)

    # Symmetric guard: content must not start with a Markdown H1 heading
    # (`# ` — hash followed by whitespace), because the script emits its own
    # `# <title>` H1 immediately before the content. A leading H1 would
    # produce two adjacent H1s (see SKILL.md gotcha: "Do NOT include ... an
    # H1 heading in the content — the script wraps both"). Fail loudly
    # instead of writing a visibly broken page.
    #
    # Only H1 is rejected: `## Subsection` or `### Deep dive` are legitimate
    # opening structures for an analysis, and `#tag inline mention.` is a
    # legitimate Obsidian hashtag start-of-paragraph.
    if re.match(r"^#\s", args.content.lstrip()):
        print(json.dumps({
            "created": False,
            "reason": "content_starts_with_h1",
            "detail": "--content must not start with `# ` (H1); the script wraps its own `# <title>`. `##`/`###` and `#tag` are allowed.",
        }))
        sys.exit(0)

    # Bare page names (no `[[...]]` wrapping) — see wiki-conventions.
    # This is what wiki-lint-check and wiki-read-page expect: a YAML list of
    # strings, each a page name under wiki/sources/. `[[wikilink]]` syntax
    # belongs to the body, not to YAML values.
    #
    # Each item is emitted as a JSON string (JSON strings are a strict subset
    # of YAML strings), which guarantees the value parses back as a string
    # regardless of content. Without quoting, YAML flow-sequence parsing has
    # sharp edges that corrupt output:
    #   - a tag starting with `#` starts a YAML comment → parse error
    #   - `key: value` (colon+space) inside `[...]` becomes a dict, not a str
    #   - `2026-01-01` (ISO date) becomes a datetime.date, not a str
    # Quoting via json.dumps sidesteps all three. ensure_ascii=False preserves
    # unicode readability (accents, emoji) instead of escaping to \uXXXX.
    related_yaml = "[" + ", ".join(json.dumps(x, ensure_ascii=False) for x in related) + "]"
    tags_yaml = "[" + ", ".join(json.dumps(x, ensure_ascii=False) for x in tags) + "]"

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
        # Strip leading blank lines so the emitted body reads as
        # `# <title>` \n \n <first content line>, matching what the SKILL.md
        # documents ("script wraps its own `# <title>` immediately before the
        # content"). Trailing whitespace is normalized as before.
        args.content.strip("\n").rstrip(),
        "",
    ]

    body = "\n".join(lines)
    target.write_text(body, encoding="utf-8")

    print(json.dumps({"created": True, "path": str(target), "page": slug}))


if __name__ == "__main__":
    main()
