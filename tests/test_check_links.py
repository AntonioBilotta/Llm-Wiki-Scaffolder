"""Tests for skills/wiki-lint-check/scripts/check_links.py.

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
CHECKER = REPO / "skills" / "wiki-lint-check" / "scripts" / "check_links.py"


def run_checker(vault: Path, *extra: str) -> dict:
    out = subprocess.run(
        [sys.executable, str(CHECKER), "--vault-path", str(vault), *extra],
        capture_output=True, text=True, encoding="utf-8", check=True,
    )
    return json.loads(out.stdout)


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class VaultFixture(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.vault = Path(self._tmp.name) / "vault"
        write(self.vault / "wiki" / "index.md", "# Index\n\n- [[acme]]\n")
        write(self.vault / "wiki" / "entities" / "acme.md", "---\ntype: entity\n---\n# Acme\n")
        write(self.vault / "raw" / "notes" / "launch.md", "raw text")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def page(self, rel: str, body: str) -> None:
        write(self.vault / "wiki" / rel, f"---\ntype: concept\n---\n{body}\n")


class TestBrokenLinks(VaultFixture):
    def test_clean_vault_has_no_findings(self) -> None:
        self.page("concepts/launch.md", "See [[acme]], [[Acme|the company]], [[acme#History]], [[#Intro]].")
        report = run_checker(self.vault)
        self.assertEqual(report["broken_links"], [])
        self.assertEqual(report["duplicate_basenames"], [])

    def test_missing_page_and_missing_attachment_are_broken(self) -> None:
        self.page("concepts/launch.md", "See [[ghost_page]] and ![[diagram.png]].")
        report = run_checker(self.vault)
        self.assertEqual(report["broken_links"],
                         [{"page": "wiki/concepts/launch.md", "targets": ["diagram.png", "ghost_page"]}])

    def test_attachment_and_raw_targets_resolve(self) -> None:
        write(self.vault / "raw" / "assets" / "diagram.png", "png")
        self.page("concepts/launch.md", "![[diagram.png]] from [[launch]] and [[raw/notes/launch]].")
        self.assertEqual(run_checker(self.vault)["broken_links"], [])

    def test_code_is_masked(self) -> None:
        self.page("concepts/launch.md", "`[[inline_ghost]]`\n\n```\n[[fenced_ghost]]\n```\n\n~~~~\n[[tilde_ghost]]\n~~~~")
        self.assertEqual(run_checker(self.vault)["broken_links"], [])

    def test_table_escaped_alias_pipe(self) -> None:
        self.page("concepts/launch.md", "| a | b |\n|---|---|\n| [[acme\\|Acme]] | x |")
        self.assertEqual(run_checker(self.vault)["broken_links"], [])

    def test_frontmatter_links_are_checked(self) -> None:
        write(self.vault / "wiki" / "concepts" / "launch.md",
              '---\ntype: concept\nfonti_correlate: ["[[missing_source]]"]\n---\n# Launch\n')
        report = run_checker(self.vault)
        self.assertEqual(report["broken_links"],
                         [{"page": "wiki/concepts/launch.md", "targets": ["missing_source"]}])

    def test_wrong_folder_qualified_link_is_broken(self) -> None:
        self.page("concepts/launch.md", "[[concepts/acme]] vs [[entities/acme]]")
        report = run_checker(self.vault)
        self.assertEqual(report["broken_links"],
                         [{"page": "wiki/concepts/launch.md", "targets": ["concepts/acme"]}])

    def test_hidden_folders_do_not_resolve_links(self) -> None:
        write(self.vault / ".obsidian" / "ghost.md", "x")
        self.page("concepts/launch.md", "[[ghost]]")
        report = run_checker(self.vault)
        self.assertEqual(report["broken_links"][0]["targets"], ["ghost"])


class TestDuplicateBasenames(VaultFixture):
    def setUp(self) -> None:
        super().setUp()
        self.page("hats/red_hat.md", "# Red hat (method)")
        self.page("agents/red_hat.md", "# Red hat (agent)")

    def test_duplicates_and_bare_links_are_reported(self) -> None:
        self.page("concepts/launch.md", "[[red_hat]] and [[Red_Hat|red]] and [[hats/red_hat]]")
        self.page("concepts/other.md", "[[agents/red_hat]] only")
        report = run_checker(self.vault)
        self.assertEqual(report["duplicate_basenames"], [{
            "name": "red_hat",
            "paths": ["wiki/agents/red_hat.md", "wiki/hats/red_hat.md"],
            "ambiguous_links_from": ["wiki/concepts/launch.md"],
        }])
        self.assertEqual(report["broken_links"], [])
        self.assertEqual(report["summary"]["ambiguous_links"], 1)

    def test_same_name_outside_wiki_is_not_a_duplicate(self) -> None:
        write(self.vault / "raw" / "notes" / "acme.md", "raw copy")
        names = [d["name"] for d in run_checker(self.vault)["duplicate_basenames"]]
        self.assertEqual(names, ["red_hat"])

    def test_pages_scope_narrows_scan_not_duplicates(self) -> None:
        self.page("concepts/launch.md", "[[red_hat]] [[ghost_a]]")
        self.page("concepts/other.md", "[[red_hat]] [[ghost_b]]")
        report = run_checker(self.vault, "--pages", "other,nowhere")
        self.assertEqual(report["broken_links"], [{"page": "wiki/concepts/other.md", "targets": ["ghost_b"]}])
        self.assertEqual(report["duplicate_basenames"][0]["ambiguous_links_from"], ["wiki/concepts/other.md"])
        self.assertEqual(report["pages_not_found"], ["nowhere"])


class TestEdgeCases(unittest.TestCase):
    def test_missing_wiki_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = run_checker(Path(tmp))
            self.assertIn("note", report)
            self.assertEqual(report["broken_links"], [])


if __name__ == "__main__":
    unittest.main()
