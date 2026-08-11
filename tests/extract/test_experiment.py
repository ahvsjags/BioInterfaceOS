"""Dual-path structured extraction tests."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from biointerfaceos.experiment_extraction import DualExperimentExtractor, DualExtractionError
from biointerfaceos.ledgers import AppendOnlyJSONL


class DualExperimentExtractorTests(unittest.TestCase):
    project_root: Path

    @classmethod
    def setUpClass(cls) -> None:
        cls.project_root = Path(__file__).resolve().parents[2]

    def _extractor(self, root: Path) -> DualExperimentExtractor:
        return DualExperimentExtractor(
            self.project_root,
            candidates_path=root / "experiment_candidates.json",
            consensus_path=root / "experiment_consensus.json",
            review_path=root / "consensus_review_queue.jsonl",
            report_path=root / "dual_extraction.md",
        )

    def test_both_paths_share_schema_and_consensus_requires_locators(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            summary = self._extractor(Path(temporary)).run()
            self.assertEqual(summary.records, 1)
            self.assertEqual(summary.rule_fields, 5)
            self.assertEqual(summary.mock_fields, 5)
            self.assertEqual(summary.agreements, 4)
            self.assertEqual(summary.disagreements, 1)
            self.assertEqual(summary.accepted_fields, 4)
            self.assertEqual(summary.review_items, 1)
            candidates = json.loads(summary.candidates_path.read_text())
            record = candidates["records"][0]
            self.assertTrue(record["schema_equal"])
            self.assertFalse(record["network_accessed"])
            self.assertEqual(
                {field["field_name"] for field in record["rule_path"]["fields"]},
                {field["field_name"] for field in record["mock_path"]["fields"]},
            )
            for path_name in ("rule_path", "mock_path"):
                for field in record[path_name]["fields"]:
                    self.assertTrue(field["evidence_locators"])
                    self.assertTrue(
                        all(locator.startswith("asset:") for locator in field["evidence_locators"])
                    )
            consensus = json.loads(summary.consensus_path.read_text())
            disagreement = next(
                field
                for field in consensus["records"][0]["fields"]
                if field["status"] == "REVIEW_REQUIRED"
            )
            self.assertIsNone(disagreement["accepted_value"])
            self.assertIsNotNone(disagreement["review_id"])

    def test_disagreement_queue_is_append_only_and_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            extractor = self._extractor(Path(temporary))
            extractor.run()
            extractor.run()
            review_path = Path(temporary) / "consensus_review_queue.jsonl"
            reviews = [
                json.loads(line) for line in review_path.read_text().splitlines() if line.strip()
            ]
            self.assertEqual(len(reviews), 1)
            self.assertEqual(reviews[0]["field_name"], "outcome_mean")
            AppendOnlyJSONL(review_path).validate()

    def test_invalid_fixture_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "bad.json"
            path.write_text(json.dumps({"schema_version": 2}), encoding="utf-8")
            extractor = DualExperimentExtractor(self.project_root, fixture_path=path)
            with self.assertRaisesRegex(DualExtractionError, "envelope"):
                extractor.run()


if __name__ == "__main__":
    unittest.main()
