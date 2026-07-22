#!/usr/bin/env python3
"""Insert or replace a page entry under a section in wiki/index.md.

Deterministic, atomic single-file update. Uses stdlib only (Python 3.8+).

If the target section does not exist, it is appended to the end of the
file. Within a section, an existing entry for the given page is replaced;
otherwise the new entry is appended at the end of the section.

Byte-identical outside the touched section (aside from trailing newline
normalization).

Exit code 0 always. Success/failure is reported in the JSON on stdout.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path


def find_section_bounds(lines: list[str], section: str) -> tuple[int | None, int | None]:
    """Return (start, end) indices for a `## <section>` block.

    start is the index of the heading line.
    end is the index of the next `## ` heading, or len(lines) if none.
    Case-insensitive on the section name; ignores trailing whitespace.
    """
    pattern = re.compile(r"^##\s+(.+?)\s*$")
    start = None
    for i, line in enumerate(lines):
        m = pattern.match(line)
        if m and m.group(1).strip().lower() == section.strip().lower():
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

    if not idx_path.exists():
        idx_path.write_text("# Index\n", encoding="utf-8")

    content = idx_path.read_text(encoding="utf-8")
    lines = content.split("\n")
    # Trim trailing empty strings from split
    while lines and lines[-1] == "":
        lines.pop()

    today = date.today().isoformat()
    new_entry = f"- [[{args.page}]] — {args.summary} · {today}"

    start, end = find_section_bounds(lines, args.section)

    if start is None:
        # Section does not exist — append it at the end.
        if lines and lines[-1] != "":
            lines.append("")
        lines.append(f"## {args.section}")
        lines.append("")
        lines.append(new_entry)
        action = "inserted"
        section_name_written = args.section
    else:
        # Search for an existing entry for this page in the section.
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
            # Append at end of the section (before any trailing blank line).
            insert_at = end
            while insert_at > start + 1 and lines[insert_at - 1] == "":
                insert_at -= 1
            lines.insert(insert_at, new_entry)
            action = "inserted"

        # Recover the actual heading text as it appears in the file.
        heading_match = re.match(r"^##\s+(.+?)\s*$", lines[start])
        section_name_written = heading_match.group(1) if heading_match else args.section

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
