"""Consensus and expert-review packet tests."""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from biointerfaceos.review_packets import ReviewPacketBuilder, ReviewPacketError


class ReviewPacketTests(unittest.TestCase):
    project_root: Path

    @classmethod
    def setUpClass(cls) -> None:
        cls.project_root = Path(__file__).resolve().parents[2]

    def _root(self, temporary: str) -> Path:
        root = Path(temporary)
        shutil.copytree(self.project_root / "registry", root / "registry")
        shutil.copytree(self.project_root / "data/cas", root / "data/cas")
        shutil.copytree(self.project_root / "data/gold_auto", root / "data/gold_auto")
        shutil.copytree(self.project_root / "release/bronze", root / "release/bronze")
        shutil.copytree(self.project_root / "release/silver", root / "release/silver")
        shutil.copytree(self.project_root / "release/gold_auto", root / "release/gold_auto")
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
        shutil.copytree(
            self.project_root / "tests/fixtures/gold_auto",
            root / "tests/fixtures/gold_auto",
        )
        shutil.copytree(
            self.project_root / "tests/fixtures/review",
            root / "tests/fixtures/review",
        )
        return root

    def test_stratified_export_and_validation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = self._root(temporary)
            builder = ReviewPacketBuilder(root)
            summary = builder.export(sample="stratified")
            self.assertEqual(summary.packets, 3)
            self.assertEqual(summary.strata, 3)
            self.assertEqual(summary.unsigned_packets, 3)
            self.assertEqual(summary.signed_packets, 0)
            self.assertEqual(builder.validate(sample="stratified"), summary)
            packets = json.loads(summary.packets_path.read_text())["packets"]
            self.assertTrue(all(packet["annotation_status"] == "UNSIGNED" for packet in packets))
            self.assertEqual(
                {packet["stratum"] for packet in packets},
                {
                    "CONSENSUS_DISAGREEMENT",
                    "MISSING_EVIDENCE",
                    "BROKEN_LOCATOR",
                },
            )

    def test_invalid_fixture_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = self._root(temporary)
            fixture = root / "tests/fixtures/review/bad.json"
            fixture.write_text(json.dumps({"schema_version": 2}), encoding="utf-8")
            builder = ReviewPacketBuilder(root, fixture_path=fixture)
            with self.assertRaisesRegex(ReviewPacketError, "envelope"):
                builder.export()


if __name__ == "__main__":
    unittest.main()
