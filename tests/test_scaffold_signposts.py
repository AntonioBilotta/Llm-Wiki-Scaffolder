"""Tests for the multi-runtime signposts written by bin/scaffold.py.

Run from the repo root:  python3 -m unittest discover -s tests -v
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCAFFOLD = REPO / "bin" / "scaffold.py"


def scaffold(vault: Path, *extra: str) -> subprocess.CompletedProcess:
    env = dict(os.environ, LLM_WIKI_TEMPLATES=str(REPO / "templates"))
    return subprocess.run(
        [sys.executable, str(SCAFFOLD), "--path", str(vault), "--name", "Demo", "--type", "learning",
         "--desc", "Synthetic demo vault", "--lang", "english", *extra],
        capture_output=True, text=True, env=env,
    )


class TestSignposts(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.vault = Path(self._tmp.name) / "demo"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_fresh_scaffold_writes_claude_md_and_vault_block(self) -> None:
        res = scaffold(self.vault)
        self.assertEqual(res.returncode, 0, res.stderr)
        claude = (self.vault / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertTrue(claude.startswith("@AGENTS.md"))
        agents = (self.vault / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("## Vault", agents)
        self.assertIn(f"- **Path:** `{self.vault.resolve()}`", agents)
        self.assertNotIn("{{", agents)
        copilot = (self.vault / ".github" / "copilot-instructions.md").read_text(encoding="utf-8")
        self.assertIn(f"- **Path:** `{self.vault.resolve()}`", copilot)

    def test_conventions_carry_source_fidelity_rule(self) -> None:
        self.assertEqual(scaffold(self.vault).returncode, 0)
        conv = (self.vault / ".github" / "instructions" / "wiki-conventions.instructions.md").read_text(encoding="utf-8")
        self.assertIn("## Source fidelity", conv)

    def test_upgrade_adds_missing_claude_md_without_touching_agents_md(self) -> None:
        self.assertEqual(scaffold(self.vault).returncode, 0)
        (self.vault / "CLAUDE.md").unlink()
        agents = self.vault / "AGENTS.md"
        agents.write_text("# user-edited AGENTS.md\n", encoding="utf-8")
        res = scaffold(self.vault, "--upgrade")
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertTrue((self.vault / "CLAUDE.md").is_file())
        self.assertEqual(agents.read_text(encoding="utf-8"), "# user-edited AGENTS.md\n")


if __name__ == "__main__":
    unittest.main()
