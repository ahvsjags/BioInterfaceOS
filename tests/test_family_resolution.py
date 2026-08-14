"""Paper-family and study-identity resolution tests."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import pyarrow.parquet as pq

from biointerfaceos.family_resolution import FamilyResolutionError, FamilyResolver
from biointerfaceos.ledgers import AppendOnlyJSONL


class FamilyResolverTests(unittest.TestCase):
    project_root: Path

    @classmethod
    def setUpClass(cls) -> None:
        cls.project_root = Path(__file__).resolve().parents[1]

    def test_resolves_linked_family_and_preserves_split_conflicts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            resolver = FamilyResolver(
                self.project_root,
                parquet_path=root / "paper_families.parquet",
                report_path=root / "paper_family_dedup.md",
                review_path=root / "family_manual_review.jsonl",
            )
            summary = resolver.run()
            self.assertEqual(summary.family_count, 5)
            self.assertEqual(summary.member_rows, 10)
            self.assertEqual(summary.manual_review_rows, 2)
            self.assertTrue(summary.split_safe)
            rows = pq.read_table(summary.parquet_path).to_pylist()
            family_one = [row for row in rows if row["family_id"] == "FAMILY-001"]
            self.assertEqual(len(family_one), 6)
            self.assertEqual({row["split"] for row in family_one}, {"train"})
            self.assertIn("preprint_of", {row["relationship_to_family"] for row in family_one})
            self.assertIn("dataset_for", {row["relationship_to_family"] for row in family_one})
            self.assertTrue(all(row["study_key"].startswith("study:") for row in rows))
            self.assertTrue(all(row["lab_key"].startswith("lab:") for row in rows))
            review_rows = [json.loads(line) for line in (root / "family_manual_review.jsonl").read_text().splitlines()]
            self.assertEqual(
                {row["reason"] for row in review_rows},
                {
                    "SPLIT_BOUNDARY_CONFLICT",
                    "UNCERTAIN_RELATIONSHIP",
                },
            )

    def test_review_queue_is_append_only_and_rerun_does_not_duplicate(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            resolver = FamilyResolver(
                self.project_root,
                parquet_path=root / "paper_families.parquet",
                report_path=root / "paper_family_dedup.md",
                review_path=root / "family_manual_review.jsonl",
            )
            resolver.run()
            first = (root / "family_manual_review.jsonl").read_text()
            resolver.run()
            second = (root / "family_manual_review.jsonl").read_text()
            self.assertEqual(first, second)
            AppendOnlyJSONL(root / "family_manual_review.jsonl").validate()

    def test_invalid_fixture_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "bad.json"
            path.write_text(json.dumps({"schema_version": 1, "records": []}), encoding="utf-8")
            resolver = FamilyResolver(self.project_root, fixture_path=path)
            with self.assertRaisesRegex(FamilyResolutionError, "envelope"):
                resolver.run()


if __name__ == "__main__":
    unittest.main()
