"""Immutable Bronze release tests."""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from biointerfaceos.bronze_release import BronzeReleaseBuilder, BronzeReleaseError


class BronzeReleaseTests(unittest.TestCase):
    project_root: Path

    @classmethod
    def setUpClass(cls) -> None:
        cls.project_root = Path(__file__).resolve().parents[2]

    def _root(self, temporary: str) -> Path:
        root = Path(temporary)
        (root / "registry").mkdir(parents=True)
        (root / "data/cas").mkdir(parents=True)
        shutil.copy2(
            self.project_root / "registry/SOURCE_MANIFEST.parquet",
            root / "registry/SOURCE_MANIFEST.parquet",
        )
        shutil.copy2(
            self.project_root / "registry/ASSET_INDEX.parquet",
            root / "registry/ASSET_INDEX.parquet",
        )
        shutil.copytree(
            self.project_root / "data/cas/sha256",
            root / "data/cas/sha256",
        )
        shutil.copytree(
            self.project_root / "tests/fixtures/bronze",
            root / "tests/fixtures/bronze",
        )
        shutil.copytree(
            self.project_root / "tests/fixtures/extract",
            root / "tests/fixtures/extract",
        )
        return root

    def test_build_verify_and_repeatability(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = self._root(temporary)
            builder = BronzeReleaseBuilder(root)
            first = builder.build(fixture=True)
            second = builder.build(fixture=True)
            self.assertEqual(first, second)
            self.assertEqual(first.raw_assets, 2)
            self.assertEqual(first.parsed_assets, 3)
            self.assertEqual(first.pointer_assets, 1)
            self.assertEqual(first.total_assets, 6)
            self.assertEqual(builder.verify(first.release_id), first)
            manifest = json.loads(first.manifest_path.read_text())
            self.assertEqual(len(manifest["assets"]), 6)
            self.assertTrue(all(entry["normalized"] is False for entry in manifest["assets"]))

    def test_license_tiers_and_restricted_pointer_are_separate(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = self._root(temporary)
            summary = BronzeReleaseBuilder(root).build(fixture=True)
            report = json.loads(summary.license_report_path.read_text())
            self.assertEqual(
                {tier["license_tier"] for tier in report["tiers"]},
                {"raw_allowed", "derived_allowed", "restricted_pointer"},
            )
            manifest = json.loads(summary.manifest_path.read_text())
            pointer = next(entry for entry in manifest["assets"] if entry["kind"] == "pointer")
            self.assertEqual(pointer["payload_mode"], "POINTER_ONLY")
            self.assertIsNone(pointer["sha256"])
            self.assertEqual(report["pointer_only"], 1)

    def test_invalid_fixture_is_rejected_without_payload_read(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = self._root(temporary)
            fixture = root / "tests/fixtures/bronze/bad.json"
            fixture.write_text(json.dumps({"schema_version": 2}), encoding="utf-8")
            builder = BronzeReleaseBuilder(root, fixture_path=fixture)
            with self.assertRaisesRegex(BronzeReleaseError, "envelope"):
                builder.build(fixture=True)


if __name__ == "__main__":
    unittest.main()
