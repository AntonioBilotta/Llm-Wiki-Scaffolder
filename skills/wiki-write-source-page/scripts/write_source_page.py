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
import hashlib
import json
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path


def slugify(text: str) -> str:
    """Lowercase snake_case slug, Unicode-safe.

    Strategy:
    1. NFKD-normalize and strip combining marks (accents → base letter,
       so "Perché" → "perche", "café" → "cafe").
    2. Collapse runs of non-[a-z0-9] to `_` and strip edges.
    3. If the result is empty (e.g. title was all non-latin — CJK, Arabic,
       Cyrillic …), fall back to an 8-char MD5 hex prefix of the original
       text so we still produce a stable, unique slug.
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


def _yaml_flow_list(items: list[str]) -> str:
    """Emit a YAML flow sequence with each item JSON-quoted.

    JSON strings are a strict subset of YAML strings, so json.dumps guarantees
    the value parses back as a string regardless of content (tags with `#`,
    values with `:`, ISO dates that would otherwise become datetime.date).
    Kept in sync with write_analysis.py's identical helper.
    """
    return "[" + ", ".join(json.dumps(x, ensure_ascii=False) for x in items) + "]"


def _code_span(value: str) -> str:
    """Wrap `value` in a Markdown code span, picking a fence that survives
    any backticks the value itself may contain.

    Per CommonMark, a code span opened by N backticks is closed by the first
    run of exactly N backticks. So we choose the shortest run of backticks
    not present in `value`. If `value` starts or ends with a backtick, we
    pad with a single space on that side (the CommonMark stripping rule
    removes exactly one leading and one trailing space).
    """
    if "`" not in value:
        return f"`{value}`"
    # Find the smallest run length not present in the value.
    n = 1
    while ("`" * n) in value:
        n += 1
    fence = "`" * n
    pad_left = " " if value.startswith("`") else ""
    pad_right = " " if value.endswith("`") else ""
    return f"{fence}{pad_left}{value}{pad_right}{fence}"


def _normalize_source_date(raw) -> tuple[str | None, str | None]:
    """Coerce `raw` into a clean `YYYY-MM-DD` string for the `source_date`
    frontmatter field, or return `(None, warning)` if it cannot be parsed as
    an ISO date/datetime.

    Rationale: `wiki-lint-check` §3.4 sorts `wiki/sources/` by `source_date`
    ascending. PyYAML `safe_load` returns `datetime.date` for `YYYY-MM-DD`,
    `datetime.datetime` for `YYYY-MM-DDTHH:MM:SS[Z]`, and `str` for anything
    else — mixing these in a `sorted()` raises `TypeError`. By forcing the
    stored value to a pure date string, we guarantee uniform types across
    the vault.

    Accepts:
      - `YYYY-MM-DD` → passed through unchanged
      - `YYYY-MM-DDTHH:MM:SS` (with optional fractional seconds, `Z`, or
         `+HH:MM` timezone) → date component extracted
    Rejects anything else (e.g. `"May 2024"`, `"2024/05/10"`) and returns
    a warning; the caller writes the page without the `source_date` field
    and surfaces the warning to the user via JSON output.
    """
    if raw is None:
        return None, None
    if not isinstance(raw, str) or not raw.strip():
        return None, f"source_date_not_string: {raw!r}"
    text = raw.strip()
    # Python 3.8/3.9 `datetime.fromisoformat` does not accept the trailing `Z`
    # suffix (added in 3.11). Rewrite to the equivalent explicit UTC offset
    # so the parse works uniformly across supported Python versions.
    normalized = text.replace("Z", "+00:00") if text.endswith("Z") else text
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None, (
            f"source_date_not_iso: {text!r} — dropped from frontmatter "
            f"(consumers require YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)"
        )
    return parsed.date().isoformat(), None


def build_page(summary: dict, today: str, related: list[str], tags: list[str]) -> tuple[str, list[str]]:
    """Compose the source page markdown from a summary dict.

    Returns (body, warnings). `warnings` collects non-fatal issues (e.g. an
    unparseable `source_date` that was dropped from frontmatter but kept
    verbatim in the body's Date line for human readability).
    """
    warnings: list[str] = []
    title = summary["title"]
    prov = summary.get("provenance") or {}
    raw_path = prov.get("raw_path", "")
    original_url = prov.get("original_url")
    raw_source_date = summary.get("date")
    normalized_source_date, date_warning = _normalize_source_date(raw_source_date)
    if date_warning:
        warnings.append(date_warning)

    lines: list[str] = [
        "---",
        "type: source",
        f"creation_date: {today}",
        f"update_date: {today}",
    ]
    # Preserve the source's original date separately from ingest date so
    # wiki-lint-check stale detection can sort by publication date, not
    # ingest date (two sources ingested same day may be years apart). Only
    # emit the frontmatter field when the value normalized to a pure date;
    # unparseable values are surfaced via `warnings` instead of being written
    # (which would break `sorted()` in the lint check).
    if normalized_source_date:
        lines.append(f"source_date: {normalized_source_date}")
    lines.extend([
        f"related_sources: {_yaml_flow_list(related)}",
        f"tags: {_yaml_flow_list(tags)}",
        "---",
        "",
        f"# {title}",
        "",
    ])

    # Provenance + Date as a bullet list so each renders as a distinct item
    # (adjacent non-blank lines would collapse into one paragraph in Markdown).
    #
    # Fence adaptively: a single-backtick code span breaks if `raw_path`
    # itself contains backticks (unlikely but valid on POSIX filesystems).
    # Per CommonMark, a code span opened by N backticks is closed by the
    # first sequence of exactly N backticks, so pick the shortest run of
    # backticks not present inside the path, and pad with spaces when the
    # value starts or ends with a backtick.
    prov_line = f"- **Provenance**: {_code_span(raw_path)}"
    if original_url:
        prov_line += f" · [original]({original_url})"
    lines.append(prov_line)
    # Body's `- **Date**:` line uses the caller-supplied value (or the
    # normalized one when available) — this stays human-readable even for
    # non-ISO inputs like "May 2024".
    if raw_source_date:
        display_date = normalized_source_date if normalized_source_date else raw_source_date
        lines.append(f"- **Date**: {display_date}")
    lines.append("")

    key_points = summary.get("key_points") or []
    if key_points:
        lines.append("## Summary")
        lines.append("")
        for kp in key_points:
            lines.append(f"- {kp}")
        lines.append("")

    # Dedup happens per-section (Entities set, Concepts set) intentionally.
    # A term that appears in both `summary.entities` and `summary.concepts` will
    # produce two wikilinks (one in each section) pointing to the same page —
    # this reflects the taxonomic distinction the summarizer made, not a bug.
    for section_name, key in (("Entities", "entities"), ("Concepts", "concepts")):
        items = summary.get(key) or []
        if items:
            seen: set[str] = set()
            slugs: list[str] = []
            for item in items:
                slug = slugify(item)
                if slug and slug not in seen:
                    seen.add(slug)
                    slugs.append(slug)
            if slugs:
                lines.append(f"## {section_name}")
                lines.append("")
                for slug in slugs:
                    lines.append(f"- [[{slug}]]")
                lines.append("")

    domain_items = summary.get("domain_items") or {}
    for dtype, items in domain_items.items():
        # Skip keys that would duplicate the hardcoded sections above.
        if dtype in ("entities", "concepts"):
            continue
        if items:
            seen = set()
            slugs = []
            for item in items:
                slug = slugify(item)
                if slug and slug not in seen:
                    seen.add(slug)
                    slugs.append(slug)
            if slugs:
                heading = dtype.replace("_", " ").title()
                lines.append(f"## {heading}")
                lines.append("")
                for slug in slugs:
                    lines.append(f"- [[{slug}]]")
                lines.append("")

    return "\n".join(lines).rstrip() + "\n", warnings


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault-path", required=True, help="Absolute path to the vault root.")
    parser.add_argument(
        "--summary-json",
        required=True,
        help="Compact JSON string with the summary (title required; others optional).",
    )
    parser.add_argument(
        "--related-sources",
        default="",
        help="Optional comma-separated wiki source page names (without .md) "
             "to seed the `related_sources` frontmatter. Usually empty at creation "
             "time — populated later by the ingest orchestrator via file-edit tools.",
    )
    parser.add_argument(
        "--tags",
        default="",
        help="Optional comma-separated tags to seed the `tags` frontmatter.",
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

    today = datetime.now(timezone.utc).date().isoformat()
    related = parse_list_arg(args.related_sources)
    tags = parse_list_arg(args.tags)
    body, warnings = build_page(summary, today, related, tags)
    target.write_text(body, encoding="utf-8")

    # `body` is included for auditability, as documented in SKILL.md's return
    # value. Callers that only need the path/slug can ignore it.
    # `warnings` surfaces non-fatal issues (e.g. an unparseable `source_date`
    # that was dropped from the frontmatter) so the caller can present them
    # to the user without needing to re-parse the emitted body.
    result: dict = {"created": True, "path": str(target), "page": slug, "body": body}
    if warnings:
        result["warnings"] = warnings
    print(json.dumps(result))


if __name__ == "__main__":
    main()
