"""Tests for bin/package_skills.py and the self-contained wiki-init skill.

Run from the repo root:  python3 -m unittest discover -s tests -v
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PACKAGER = REPO / "bin" / "package_skills.py"
SPEC_KEYS = {"name", "description", "license", "allowed-tools", "metadata", "compatibility"}


def frontmatter_keys(skill_md: str) -> set:
    lines = skill_md.replace("\r\n", "\n").split("\n")
    end = lines.index("---", 1)
    return {line.split(":", 1)[0] for line in lines[1:end] if line and not line.startswith(" ") and ":" in line}


class TestPackageSkills(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.out = Path(cls._tmp.name) / "dist"
        res = subprocess.run([sys.executable, str(PACKAGER), "--out", str(cls.out)],
                             capture_output=True, text=True, encoding="utf-8")
        cls.returncode = res.returncode
        cls.report = json.loads(res.stdout)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def test_every_skill_packages_with_spec_only_frontmatter(self) -> None:
        self.assertEqual(self.returncode, 0, self.report)
        names = sorted(d.name for d in (REPO / "skills").glob("wiki-*") if d.is_dir())
        self.assertEqual(sorted(r["skill"] for r in self.report["results"]), names)
        for name in names:
            with zipfile.ZipFile(self.out / f"{name}.zip") as zf:
                keys = frontmatter_keys(zf.read(f"{name}/SKILL.md").decode("utf-8"))
            self.assertTrue(keys <= SPEC_KEYS, f"{name}: {keys - SPEC_KEYS}")
            self.assertIn("name", keys)
            self.assertIn("description", keys)

    def test_wiki_init_bundles_scaffold_and_templates(self) -> None:
        with zipfile.ZipFile(self.out / "wiki-init.zip") as zf:
            names = set(zf.namelist())
        self.assertIn("wiki-init/scripts/scaffold.py", names)
        self.assertIn("wiki-init/templates/CLAUDE.md", names)
        self.assertIn("wiki-init/templates/AGENTS.md", names)
        overviews = {n for n in names if n.startswith("wiki-init/templates/overview/")}
        self.assertEqual(len(overviews), len(list((REPO / "templates" / "overview").glob("*.md"))))

    def test_bundled_scaffold_creates_a_vault_from_the_archive(self) -> None:
        extract = Path(self._tmp.name) / "extract"
        with zipfile.ZipFile(self.out / "wiki-init.zip") as zf:
            zf.extractall(extract)
        skill = extract / "wiki-init"
        vault = Path(self._tmp.name) / "vault"
        res = subprocess.run(
            [sys.executable, str(skill / "scripts" / "scaffold.py"), "--templates", str(skill / "templates"),
             "--path", str(vault), "--name", "Demo", "--type", "development", "--desc", "Synthetic",
             "--lang", "italian", "--json-out"],
            capture_output=True, text=True, encoding="utf-8",
        )
        self.assertEqual(res.returncode, 0, res.stderr)
        payload = json.loads(res.stdout)
        self.assertEqual(payload["status"], "ok")
        self.assertIn("internal_type", payload)
        self.assertTrue((vault / "CLAUDE.md").is_file())
        self.assertTrue((vault / "wiki" / "overview.md").is_file())

    def test_archives_are_deterministic(self) -> None:
        again = Path(self._tmp.name) / "again"
        subprocess.run([sys.executable, str(PACKAGER), "--out", str(again), "--only", "wiki-init"],
                       capture_output=True, check=True)
        self.assertEqual((again / "wiki-init.zip").read_bytes(), (self.out / "wiki-init.zip").read_bytes())


if __name__ == "__main__":
    unittest.main()
