"""Tests for skills/wiki-lint-check/scripts/check_evidence.py.

Run from the repo root:  python3 -m unittest discover -s tests -v
Standard library only. Every fixture is synthetic and built in a temp dir.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CHECKER = REPO / "skills" / "wiki-lint-check" / "scripts" / "check_evidence.py"
WRITER = REPO / "skills" / "wiki-write-source-page" / "scripts" / "write_source_page.py"

RAW_TEXT = """# Acme Widget launch notes

Acme shipped the Widget 2.1.80 release on 2026-03-19.
Monthly active users reached 42K, up 12.5% from the previous quarter.
The team processed 10,000 tickets in 2025.

> "We will never trade reliability for speed," said the CTO.
"""


def run_checker(vault: Path, *extra: str) -> dict:
    out = subprocess.run(
        [sys.executable, str(CHECKER), "--vault-path", str(vault), *extra],
        capture_output=True, text=True, encoding="utf-8", check=True,
    )
    return json.loads(out.stdout)


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def entity(body: str, related=("acme_widget_launch_notes",), type_="entity") -> str:
    rel = ", ".join(json.dumps(r) for r in related)
    return (
        "---\n"
        f"type: {type_}\n"
        "creation_date: 2026-09-25\n"
        "update_date: 2026-09-25\n"
        f"related_sources: [{rel}]\n"
        "tags: []\n"
        "---\n\n"
        f"{body}\n"
    )


class VaultFixture(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.vault = Path(self._tmp.name) / "vault"
        write(self.vault / "raw" / "notes" / "acme-launch.md", RAW_TEXT)
        write(self.vault / "wiki" / "index.md", "---\ntype: index\n---\n# Wiki Index\n")
        write(self.vault / "wiki" / "log.md", "# Log\n")
        write(self.vault / "wiki" / "overview.md", "---\ntype: overview\n---\n# Overview 9999\n")
        summary = {
            "title": "Acme Widget launch notes",
            "provenance": {"raw_path": str(self.vault / "raw" / "notes" / "acme-launch.md"), "original_url": None},
            "date": "2026-03-19",
            "key_points": ["Widget 2.1.80 shipped on 2026-03-19.", "Monthly active users reached 42K."],
            "entities": ["acme"],
            "concepts": [],
            "domain_items": {},
        }
        subprocess.run(
            [sys.executable, str(WRITER), "--vault-path", str(self.vault), "--summary-json", json.dumps(summary)],
            capture_output=True, text=True, check=True,
        )
        self.assertTrue((self.vault / "wiki" / "sources" / "acme_widget_launch_notes.md").is_file())

    def tearDown(self) -> None:
        self._tmp.cleanup()


class TestFidelity(VaultFixture):
    def test_grounded_page_has_no_suspects(self) -> None:
        write(self.vault / "wiki" / "entities" / "acme.md", entity(
            "# Acme\n\nAcme released Widget 2.1.80 on 2026-03-19; MAU hit 42K (+12.5%). "
            "It handled 10,000 tickets in 2025. [[acme_widget_launch_notes]]\n\n"
            "> We will never trade reliability for speed"
        ))
        report = run_checker(self.vault)
        self.assertEqual(report["fidelity"], [], report["fidelity"])
        self.assertEqual(report["evidence_errors"], [])

    def test_reformatted_and_invented_literals_are_suspects(self) -> None:
        write(self.vault / "wiki" / "entities" / "acme.md", entity(
            "# Acme\n\nMAU hit 42,000 in 2026-04. Revenue grew 37%. "
            "The CTO said \"reliability always beats raw speed for us\"."
        ))
        report = run_checker(self.vault)
        values = {s["value"] for f in report["fidelity"] for s in f["suspects"]}
        self.assertEqual(values, {"42,000", "2026-04", "37%", "reliability always beats raw speed for us"})

    def test_small_integers_code_and_links_are_not_candidates(self) -> None:
        write(self.vault / "wiki" / "entities" / "acme.md", entity(
            "# Acme\n\nThe team has 42 people and 3 offices. See `port 8080` and "
            "[[release_2027_plan]] and [docs](https://example.com/v/9999).\n\n"
            "```\nversion 7.7.7 on 2030-01-01\n```"
        ))
        report = run_checker(self.vault)
        self.assertEqual(report["fidelity"], [], report["fidelity"])

    def test_source_page_metadata_lines_are_ignored(self) -> None:
        # The source page's Provenance/Date lines hold paths and ingest dates
        # that are not in the raw text; only its body literals are checked.
        report = run_checker(self.vault, "--pages", "acme_widget_launch_notes")
        self.assertEqual(report["fidelity"], [], report["fidelity"])

    def test_inline_wikilink_to_source_counts_as_evidence(self) -> None:
        write(self.vault / "wiki" / "concepts" / "launch.md", entity(
            "# Launch\n\nShipped on 2026-03-19 per [[acme_widget_launch_notes]].", related=()
        ))
        report = run_checker(self.vault, "--pages", "launch")
        self.assertEqual(report["evidence_errors"], [])
        self.assertEqual(report["fidelity"], [])


class TestEvidenceErrors(VaultFixture):
    def test_page_without_sources(self) -> None:
        write(self.vault / "wiki" / "entities" / "orphan.md", entity("# Orphan\n\nFounded in 1999.", related=()))
        report = run_checker(self.vault, "--pages", "orphan")
        self.assertEqual([e["issue"] for e in report["evidence_errors"]], ["no_sources"])

    def test_related_source_that_does_not_exist(self) -> None:
        write(self.vault / "wiki" / "entities" / "acme.md", entity(
            "# Acme\n\n42K users.", related=("acme_widget_launch_notes", "ghost_source")))
        report = run_checker(self.vault, "--pages", "acme")
        self.assertIn({"page": "acme", "issue": "related_source_not_found", "detail": "ghost_source"},
                      report["evidence_errors"])

    def test_provenance_recorded_on_another_machine_is_reanchored(self) -> None:
        src = self.vault / "wiki" / "sources" / "acme_widget_launch_notes.md"
        text = src.read_text(encoding="utf-8")
        text = text.replace(str(self.vault / "raw" / "notes" / "acme-launch.md"),
                            r"C:\Users\someone\vaults\demo\raw\notes\acme-launch.md")
        src.write_text(text, encoding="utf-8")
        write(self.vault / "wiki" / "entities" / "acme.md", entity("# Acme\n\n42K users."))
        report = run_checker(self.vault)
        self.assertEqual(report["evidence_errors"], [])
        self.assertEqual(report["fidelity"], [])
        self.assertEqual(report["unreferenced_raw"], [])

    def test_binary_raw_is_unverifiable_not_error(self) -> None:
        pdf = self.vault / "raw" / "notes" / "scan.pdf"
        pdf.write_bytes(b"%PDF-1.4 fake")
        write(self.vault / "wiki" / "sources" / "scan.md",
              "---\ntype: source\n---\n# Scan\n\n- **Provenance**: `raw/notes/scan.pdf`\n\n42K rows.\n")
        report = run_checker(self.vault, "--pages", "scan")
        self.assertEqual(report["evidence_errors"], [])
        self.assertEqual(report["unverifiable"][0]["raw"], "raw/notes/scan.pdf")


class TestInventory(VaultFixture):
    def test_unreferenced_raw_listed_and_no_material_excluded(self) -> None:
        write(self.vault / "raw" / "notes" / "dup.md", "copy of the launch notes")
        write(self.vault / "raw" / "notes" / "backlog.md", "not ingested yet")
        write(self.vault / "raw" / "assets" / "diagram.png", "png")
        write(self.vault / "raw" / "notes" / ".gitkeep", "")
        with (self.vault / "wiki" / "log.md").open("a", encoding="utf-8") as fh:
            fh.write("\n## [2026-09-25] ingest | no material: raw/notes/dup.md\n")
        report = run_checker(self.vault)
        self.assertEqual(report["unreferenced_raw"], ["raw/notes/backlog.md"])

    def test_missing_wiki_dir(self) -> None:
        empty = Path(self._tmp.name) / "empty"
        empty.mkdir()
        report = run_checker(empty)
        self.assertIn("note", report)


if __name__ == "__main__":
    unittest.main()
