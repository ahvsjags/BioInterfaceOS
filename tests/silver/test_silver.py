"""Normalized Silver release tests."""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from biointerfaceos.silver_release import SilverReleaseBuilder, SilverReleaseError


class SilverReleaseTests(unittest.TestCase):
    project_root: Path

    @classmethod
    def setUpClass(cls) -> None:
        cls.project_root = Path(__file__).resolve().parents[2]

    def _root(self, temporary: str) -> Path:
        root = Path(temporary)
        shutil.copytree(self.project_root / "registry", root / "registry")
        shutil.copytree(self.project_root / "data/cas", root / "data/cas")
        shutil.copytree(self.project_root / "release/bronze", root / "release/bronze")
        shutil.copytree(
            self.project_root / "tests/fixtures/bronze",
            root / "tests/fixtures/bronze",
        )
        shutil.copytree(
            self.project_root / "tests/fixtures/extract",
            root / "tests/fixtures/extract",
        )
        shutil.copytree(
            self.project_root / "tests/fixtures/silver",
            root / "tests/fixtures/silver",
        )
        return root

    def test_build_validate_and_repeatability(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = self._root(temporary)
            builder = SilverReleaseBuilder(root)
            first = builder.build(fixture=True)
            second = builder.build(fixture=True)
            self.assertEqual(first, second)
            self.assertEqual(first.table_count, 8)
            self.assertEqual(first.total_rows, 36)
            self.assertEqual(first.quarantined_rows, 2)
            self.assertEqual(builder.validate(first.release_id), first)
            manifest = json.loads(first.manifest_path.read_text())
            self.assertEqual(len(manifest["tables"]), 8)

    def test_invalid_fixture_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = self._root(temporary)
            fixture = root / "tests/fixtures/silver/bad.json"
            fixture.write_text(json.dumps({"schema_version": 2}), encoding="utf-8")
            builder = SilverReleaseBuilder(root, fixture_path=fixture)
            with self.assertRaisesRegex(SilverReleaseError, "envelope"):
                builder.build(fixture=True)

    def test_missing_evidence_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = self._root(temporary)
            path = root / "registry/material_entities.json"
            value = json.loads(path.read_text())
            value["entities"][0]["source_locator"] = "not-an-evidence-locator"
            path.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaisesRegex(SilverReleaseError, "evidence"):
                SilverReleaseBuilder(root).build(fixture=True)


if __name__ == "__main__":
    unittest.main()
