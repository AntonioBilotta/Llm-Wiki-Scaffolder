#!/usr/bin/env python3
"""Append a dated entry to wiki/log.md.

Deterministic, atomic append-only. Uses stdlib only (Python 3.8+).

Entry format is fixed for greppability:
    ## [YYYY-MM-DD] <kind> | <summary>
    Touched pages: [[page_a]], [[page_b]], ...   (optional line)

The `<kind>` must be a single word — enforced here to keep the log
parseable with `grep '^## \\['`.

Exit code 0 always. Success/failure is reported in the JSON on stdout.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault-path", required=True, help="Absolute path to the vault root.")
    parser.add_argument(
        "--kind",
        required=True,
        help="Single word: ingest | query | lint | batch-ingest | other.",
    )
    parser.add_argument("--summary", required=True, help="One-line description of the operation.")
    parser.add_argument(
        "--touched-pages",
        default="",
        help="Comma-separated wiki page names (without .md), optional.",
    )
    args = parser.parse_args()

    if not re.match(r"^[a-z][a-z0-9-]*$", args.kind):
        print(
            json.dumps(
                {
                    "appended": False,
                    "reason": "kind_invalid",
                    "detail": "kind must be a single lowercase word (letters, digits, hyphens)",
                    "kind": args.kind,
                }
            )
        )
        sys.exit(0)

    if not args.summary.strip():
        print(json.dumps({"appended": False, "reason": "empty_summary"}))
        sys.exit(0)

    vault = Path(args.vault_path).expanduser().resolve()
    if not vault.is_dir():
        print(json.dumps({"appended": False, "reason": "vault_not_found", "vault_path": str(vault)}))
        sys.exit(0)

    log_path = vault / "wiki" / "log.md"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    if not log_path.exists():
        log_path.write_text("# Log\n", encoding="utf-8")

    today = date.today().isoformat()
    prefix = f"## [{today}] {args.kind} | {args.summary.strip()}"
    entry_lines: list[str] = ["", prefix]

    touched = [p.strip() for p in args.touched_pages.split(",") if p.strip()]
    if touched:
        wl = ", ".join(f"[[{p}]]" for p in touched)
        entry_lines.append(f"Touched pages: {wl}")

    # Append: ensure the file ends with a newline first.
    current = log_path.read_text(encoding="utf-8")
    if not current.endswith("\n"):
        current += "\n"
    with log_path.open("w", encoding="utf-8") as f:
        f.write(current)
        f.write("\n".join(entry_lines))
        f.write("\n")

    print(
        json.dumps(
            {
                "appended": True,
                "path": str(log_path),
                "line_prefix": prefix,
            }
        )
    )


if __name__ == "__main__":
    main()
