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
    """Split a comma-separated string into a stripped, order-preserving,
    de-duplicated list of non-empty items.

    Dedup rationale: `related_sources` and `tags` are surfaced verbatim in
    the emitted YAML flow list. Duplicates would round-trip through
    `yaml.safe_load` as `list[str]` with repeated entries — `wiki-lint-check`
    §7 ("validate related_sources are actual pages") would then double-
    report the same missing target, and human readers see visual noise.
    Kept in sync with write_analysis.py's identical helper.
    """
    if not raw:
        return []
    seen: set[str] = set()
    out: list[str] = []
    for item in raw.split(","):
        s = item.strip()
        if s and s not in seen:
            seen.add(s)
            out.append(s)
    return out


def _single_line(value: str) -> str:
    """Collapse any run of whitespace (including embedded newlines) to a single
    space, then strip. Kept in sync with update_index.py and append_log.py's
    identical treatment of user-supplied single-line fields. Without this,
    multi-line values in `summary.key_points` or `summary.date` produce broken
    bullet lists where the second line orphans as a stray paragraph.
    """
    return re.sub(r"\s+", " ", str(value)).strip()


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
    verbatim in the body's Date line for human readability, or a summary
    field with the wrong Python type that was coerced to a safe default).
    """
    warnings: list[str] = []
    # Collapse whitespace in the title before it becomes the H1. Slugify
    # already handles embedded newlines internally (they collapse to `_`),
    # so this only affects the body's `# <title>` line — without the collapse,
    # a multi-line title (e.g. from a summary field that captured a two-line
    # header) produces `# Line1\nLine2`, which CommonMark renders as an H1
    # containing only the first line + a following paragraph. Downstream
    # readers (Obsidian, wiki-read-page, any LLM re-citing the title) see a
    # truncated title. Callers of main() already verified `isinstance(title, str)`.
    title = _single_line(summary["title"])

    # Defensive type coercion: the summary is caller-generated (often by an
    # LLM), so a schema slip is plausible. Without these guards, a string
    # accidentally passed where a list is expected would iterate character-
    # by-character and emit `[[f]] [[r]] [[o]] [[d]] [[o]]`. Coerce silently
    # to a safe empty default and surface a warning in the return JSON so
    # the orchestrator can see the drift instead of receiving corrupt output.
    for key in ("key_points", "entities", "concepts"):
        v = summary.get(key)
        if v is not None and not isinstance(v, list):
            warnings.append(f"{key}_not_list: expected array, got {type(v).__name__}")
            summary[key] = []

    prov = summary.get("provenance")
    if prov is not None and not isinstance(prov, dict):
        warnings.append(f"provenance_not_dict: expected object, got {type(prov).__name__}")
        prov = {}
    elif prov is None:
        prov = {}
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
    #
    # When `raw_path` is missing/empty (an unusual summary shape — the
    # wiki-summarize-source SKILL contract requires it), fall back to an
    # italic placeholder rather than emitting an empty code span (`` `` ``)
    # which is visually confusing and semantically empty.
    if raw_path:
        prov_line = f"- **Provenance**: {_code_span(raw_path)}"
    else:
        prov_line = "- **Provenance**: _(unknown)_"
    if original_url:
        prov_line += f" · [original]({original_url})"
    lines.append(prov_line)
    # Body's `- **Date**:` line uses the normalized ISO value when the
    # summary's `date` parsed cleanly (that's the best form for humans too),
    # or falls back to the raw string when parsing failed but the raw value
    # is still a legitimate human-readable string like "May 2024".
    # Whitespace-collapsed so a multi-line raw value (e.g. `date: "May\n2024"`)
    # does not break the bullet.
    #
    # Non-string `date` values (dict, list, int — LLM schema slip) are already
    # captured in `warnings` by `_normalize_source_date` and dropped from the
    # frontmatter. Skip the body line too rather than emitting a Python repr
    # like `- **Date**: {'raw': 'May 2024'}`, which is neither ISO nor
    # human-readable and defeats the SKILL.md contract ("kept in the body's
    # `- **Date**:` line for human readability").
    if isinstance(normalized_source_date, str) and normalized_source_date:
        lines.append(f"- **Date**: {normalized_source_date}")
    elif isinstance(raw_source_date, str) and raw_source_date.strip():
        lines.append(f"- **Date**: {_single_line(raw_source_date)}")
    lines.append("")

    key_points = summary.get("key_points") or []
    if key_points:
        lines.append("## Summary")
        lines.append("")
        for kp in key_points:
            # Collapse whitespace so a multi-line takeaway stays on one bullet.
            lines.append(f"- {_single_line(kp)}")
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
            for i, item in enumerate(items):
                # Per-item type guard: the outer coercion above ensures `items`
                # is a list, but individual entries can still be non-strings
                # (LLM slip: numeric IDs, nested dicts, None). `slugify` calls
                # `unicodedata.normalize("NFKD", text)` which raises TypeError
                # on non-str — that would violate the module's "exit 0 always,
                # report via JSON" contract. Skip + warning instead.
                if not isinstance(item, str):
                    warnings.append(
                        f"{key}[{i}]_not_string: got {type(item).__name__}"
                    )
                    continue
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
    if not isinstance(domain_items, dict):
        warnings.append(f"domain_items_not_dict: expected object, got {type(domain_items).__name__}")
        domain_items = {}
    for dtype, items in domain_items.items():
        # Skip keys that would duplicate the hardcoded sections above.
        # Case-fold the comparison so a title-case key (e.g. `"Entities"`)
        # is also skipped instead of producing a duplicate `## Entities`
        # heading. `wiki-summarize-source/SKILL.md` §3 uses lowercase keys
        # but nothing enforces it upstream.
        if isinstance(dtype, str) and dtype.lower() in ("entities", "concepts"):
            continue
        if not isinstance(items, list):
            warnings.append(f"domain_items.{dtype}_not_list: expected array, got {type(items).__name__}")
            continue
        if items:
            seen = set()
            slugs = []
            for i, item in enumerate(items):
                # Symmetric per-item guard with the Entities/Concepts loop
                # above: skip non-string items so `slugify` (which requires
                # `str`) cannot raise TypeError and violate the exit-0 contract.
                if not isinstance(item, str):
                    warnings.append(
                        f"domain_items.{dtype}[{i}]_not_string: got {type(item).__name__}"
                    )
                    continue
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
