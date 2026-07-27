#!/usr/bin/env python3
"""Insert or replace a page entry under a section in wiki/index.md.

Deterministic, atomic single-file update. Uses stdlib only (Python 3.8+).

If the target section does not exist, it is appended to the end of the
file. Within a section, an existing entry for the given page is replaced;
otherwise the new entry is appended at the end of the section (after the
`_(no entries yet)_` placeholder, if present, which is removed on first
real insert).

If the file has YAML frontmatter with an `update_date:` field, it is
bumped to today. Everything outside the touched section and the
`update_date` line is preserved byte-identical (aside from trailing
newline normalization).

Exit code 0 always. Success/failure is reported in the JSON on stdout.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


PLACEHOLDER_RE = re.compile(r"^\s*-\s*_\(no entries yet\)_\s*$")

# Update-date line matcher that preserves any trailing YAML comment.
# Captures: (1) `update_date: ` prefix, (2) current value token, (3) trailing
# whitespace + optional `# comment`. Rewriting only group 2 keeps comments.
UPDATE_DATE_RE = re.compile(r"^(\s*update_date:\s*)(\S+)(.*)$")

# Canonical Title Case for the four standard index sections. When the caller
# passes a case/whitespace variant of one of these and the section does not
# yet exist, we create it with the canonical form to avoid drift like
# `## entities` vs `## Entities` co-existing in the same index.
STANDARD_SECTIONS = {
    "entities": "Entities",
    "concepts": "Concepts",
    "sources": "Sources",
    "analysis": "Analysis",
}


def _normalize(name: str) -> str:
    """Fold whitespace/underscore differences and case for section matching.

    Callers may pass a section as either the folder name (`open_questions`)
    or the display heading (`Open Questions`). Both should match the same
    scaffolded `## Open Questions` section rather than creating a duplicate.

    Leading markdown heading markers (`## `, `# `, etc.) are stripped up-front
    so a caller passing the visible heading form (`--section "## Entities"`)
    does not produce a `## ## Entities` section. This is defensive input
    normalization, not a documented invocation form.
    """
    stripped = re.sub(r"^#+\s+", "", name)
    return re.sub(r"[_\s]+", " ", stripped).strip().lower()


def find_section_bounds(lines: list[str], section: str) -> tuple[int | None, int | None]:
    """Return (start, end) indices for a `## <section>` block.

    start is the index of the heading line.
    end is the index of the next `## ` heading, or len(lines) if none.
    Case-insensitive on the section name; ignores trailing whitespace.
    """
    pattern = re.compile(r"^##\s+(.+?)\s*$")
    target = _normalize(section)
    start = None
    for i, line in enumerate(lines):
        m = pattern.match(line)
        if m and _normalize(m.group(1)) == target:
            start = i
            break
    if start is None:
        return None, None
    end = len(lines)
    for j in range(start + 1, len(lines)):
        if lines[j].startswith("## "):
            end = j
            break
    return start, end


def bump_update_date(lines: list[str], today: str) -> None:
    """If the file starts with YAML frontmatter containing `update_date:`,
    rewrite the value in place while preserving any trailing YAML comment
    or indentation. No-op if there's no frontmatter or no update_date line."""
    if not lines or lines[0].strip() != "---":
        return
    for i in range(1, len(lines)):
        stripped = lines[i].strip()
        if stripped == "---":
            return
        if stripped.startswith("update_date:"):
            m = UPDATE_DATE_RE.match(lines[i])
            if m:
                lines[i] = f"{m.group(1)}{today}{m.group(3)}"
            else:
                # Fallback if the line doesn't match the expected shape
                # (e.g. multi-line block scalar): rewrite conservatively.
                lines[i] = f"update_date: {today}"
            return


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault-path", required=True, help="Absolute path to the vault root.")
    parser.add_argument("--section", required=True, help="Section name (e.g. 'Entities', 'Concepts', 'Sources', 'Analysis').")
    parser.add_argument("--page", required=True, help="Page name without .md extension.")
    parser.add_argument("--summary", required=True, help="One-line description shown after the page link.")
    args = parser.parse_args()

    vault = Path(args.vault_path).expanduser().resolve()
    if not vault.is_dir():
        print(json.dumps({"updated": False, "reason": "vault_not_found", "vault_path": str(vault)}))
        sys.exit(0)

    idx_path = vault / "wiki" / "index.md"
    idx_path.parent.mkdir(parents=True, exist_ok=True)

    today = datetime.now(timezone.utc).date().isoformat()

    if not idx_path.exists():
        # Seed the four canonical sections (matching bin/scaffold.py:render_index)
        # so the auto-created index converges to the same shape as a fresh scaffold
        # regardless of the order of first inserts. Extra domain sections (e.g.
        # `## Open Questions`, `## Decisions`) are inserted by the section-not-found
        # branch below on demand (before `## Sources`, matching scaffolder order).
        #
        # H1 title is `# Wiki Index` (scaffolder uses `# Wiki Index — <project>`;
        # the project name is not available here since --vault-path is the only
        # location signal). Autocreate should be rare in practice — the scaffolder
        # always emits index.md — this branch exists only as defensive fallback.
        placeholder = "- _(no entries yet)_"
        idx_path.write_text(
            "---\n"
            "type: index\n"
            f"update_date: {today}\n"
            "---\n"
            "\n"
            "# Wiki Index\n"
            "\n"
            "## Entities\n"
            "\n"
            f"{placeholder}\n"
            "\n"
            "## Concepts\n"
            "\n"
            f"{placeholder}\n"
            "\n"
            "## Sources\n"
            "\n"
            f"{placeholder}\n"
            "\n"
            "## Analysis\n"
            "\n"
            f"{placeholder}\n",
            encoding="utf-8",
        )

    content = idx_path.read_text(encoding="utf-8")
    lines = content.split("\n")
    # Trim trailing empty strings from split
    while lines and lines[-1] == "":
        lines.pop()

    # Collapse whitespace (including embedded newlines) in the summary. Without
    # this, a multi-line summary breaks the index bullet contract
    # `- [[page]] — summary · YYYY-MM-DD` — wiki-search's regex fails to match
    # the entry, and the trailing lines survive as permanent orphans that
    # subsequent runs cannot self-heal (the `- [[page]]` anchor matches only
    # the first line during replacement).
    summary_clean = re.sub(r"\s+", " ", args.summary).strip()
    new_entry = f"- [[{args.page}]] — {summary_clean} · {today}"

    start, end = find_section_bounds(lines, args.section)

    if start is None:
        # Section does not exist — create it.
        # For the four standard sections, force canonical Title Case so we
        # never emit `## entities` when the vault already conventionally uses
        # `## Entities`. For non-standard sections (e.g. `open_questions`,
        # `findings`, `decisions`, `characters`), apply the same Title Case
        # transformation the scaffolder uses in render_index
        # (`folder.replace("_", " ").title()`) so the auto-created heading
        # matches what a fresh scaffold would produce. This prevents drift
        # like `## open_questions` co-existing with `## Open Questions`.
        canonical = STANDARD_SECTIONS.get(_normalize(args.section))
        if canonical:
            section_heading = canonical
        else:
            section_heading = _normalize(args.section).title()

        # For NON-standard sections, insert immediately before `## Sources`
        # if it exists — this matches bin/scaffold.py:render_index, where extra
        # domain sections (findings, open_questions, decisions, characters …)
        # sit BETWEEN Concepts and Sources, not after Analysis. Without this,
        # a scaffolded vault with an extra section added later would drift
        # from a fresh-scaffold layout. Standard sections (or a hand-crafted
        # index without `## Sources`) fall back to appending at end.
        is_non_standard = canonical is None
        sources_idx: int | None = None
        if is_non_standard:
            for i, line in enumerate(lines):
                if line.strip() == "## Sources":
                    sources_idx = i
                    break

        if sources_idx is not None:
            # Splice `## <section>` + blank + entry before `## Sources`, keeping
            # the pre-existing blank line that separates `## Sources` from what
            # came before. Rewinding past that blank line and then re-emitting a
            # trailing blank in the block would stack two blanks; instead we
            # rewind, add one LEADING blank to separate from the previous
            # section's last entry, and reuse the existing blank as the trailing
            # separator to `## Sources`. Net: exactly one blank line on each
            # side of the new section, matching scaffolder output.
            insert_at = sources_idx
            while insert_at > 0 and lines[insert_at - 1] == "":
                insert_at -= 1
            new_block = ["", f"## {section_heading}", "", new_entry]
            lines[insert_at:insert_at] = new_block
        else:
            if lines and lines[-1] != "":
                lines.append("")
            lines.append(f"## {section_heading}")
            lines.append("")
            lines.append(new_entry)
        action = "inserted"
        section_name_written = section_heading
    else:
        # First, drop any `_(no entries yet)_` placeholder inside this section.
        drop_indices = [
            k for k in range(start + 1, end)
            if PLACEHOLDER_RE.match(lines[k])
        ]
        for k in reversed(drop_indices):
            del lines[k]
            end -= 1

        # Search for an existing entry for this page in the (now clean) section.
        entry_pattern = re.compile(rf"^-\s+\[\[{re.escape(args.page)}\]\]")
        existing_idx = None
        for k in range(start + 1, end):
            if entry_pattern.match(lines[k]):
                existing_idx = k
                break

        if existing_idx is not None:
            lines[existing_idx] = new_entry
            action = "replaced"
        else:
            # Append at end of the section, preserving exactly one blank
            # line between the heading and the (first) entry.
            insert_at = end
            while insert_at > start + 2 and lines[insert_at - 1] == "":
                insert_at -= 1
            lines.insert(insert_at, new_entry)
            action = "inserted"

        # Recover the actual heading text as it appears in the file.
        heading_match = re.match(r"^##\s+(.+?)\s*$", lines[start])
        section_name_written = heading_match.group(1) if heading_match else args.section

    bump_update_date(lines, today)

    output = "\n".join(lines) + "\n"
    idx_path.write_text(output, encoding="utf-8")

    print(
        json.dumps(
            {
                "updated": True,
                "path": str(idx_path),
                "action": action,
                "section": section_name_written,
            }
        )
    )


if __name__ == "__main__":
    main()
