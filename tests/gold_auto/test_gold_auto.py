"""Audited Gold-auto subset tests."""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from biointerfaceos.gold_auto import GoldAutoBuilder, GoldAutoError


class GoldAutoTests(unittest.TestCase):
    project_root: Path

    @classmethod
    def setUpClass(cls) -> None:
        cls.project_root = Path(__file__).resolve().parents[2]

    def _root(self, temporary: str) -> Path:
        root = Path(temporary)
        shutil.copytree(self.project_root / "registry", root / "registry")
        shutil.copytree(self.project_root / "data/cas", root / "data/cas")
        shutil.copytree(self.project_root / "release/bronze", root / "release/bronze")
        shutil.copytree(self.project_root / "release/silver", root / "release/silver")
        shutil.copytree(
            self.project_root / "tests/fixtures/bronze",
            root / "tests/fixtures/bronze",
        )
        shutil.copytree(
            self.project_root / "tests/fixtures/silver",
            root / "tests/fixtures/silver",
        )
        shutil.copytree(
            self.project_root / "tests/fixtures/extract",
            root / "tests/fixtures/extract",
        )
        shutil.copytree(
            self.project_root / "tests/fixtures/gold_auto",
            root / "tests/fixtures/gold_auto",
        )
        return root

    def test_build_validate_and_repeatability(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = self._root(temporary)
            builder = GoldAutoBuilder(root)
            first = builder.build(fixture=True)
            second = builder.build(fixture=True)
            self.assertEqual(first, second)
            self.assertEqual(first.admitted_fields, 3)
            self.assertEqual(first.excluded_fields, 2)
            self.assertEqual(first.agreement_fields, 4)
            self.assertEqual(first.disagreement_fields, 1)
            self.assertEqual(first.reverse_traces, 3)
            self.assertEqual(builder.validate(first.release_id), first)

    def test_disagreement_and_missing_evidence_stay_in_silver(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = self._root(temporary)
            summary = GoldAutoBuilder(root).build(fixture=True)
            exclusions = json.loads(summary.exclusions_path.read_text())["rows"]
            by_field = {row["field_name"]: row for row in exclusions}
            self.assertIn("CONSENSUS_DISAGREEMENT_OR_REVIEW", by_field["outcome_mean"]["reasons"])
            self.assertIn("NO_RESOLVED_EVIDENCE_ASSERTION", by_field["arm_label"]["reasons"])
            report = json.loads(summary.agreement_report_path.read_text())
            self.assertEqual(report["expert_gold_admitted"], 0)

    def test_invalid_fixture_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = self._root(temporary)
            fixture = root / "tests/fixtures/gold_auto/bad.json"
            fixture.write_text(json.dumps({"schema_version": 2}), encoding="utf-8")
            builder = GoldAutoBuilder(root, fixture_path=fixture)
            with self.assertRaisesRegex(GoldAutoError, "envelope"):
                builder.build(fixture=True)


if __name__ == "__main__":
    unittest.main()
