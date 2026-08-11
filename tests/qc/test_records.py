"""Physical and statistical plausibility-QC tests."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from biointerfaceos.ledgers import AppendOnlyJSONL
from biointerfaceos.plausibility_qc import PlausibilityChecker, PlausibilityQCError


class PlausibilityQCTests(unittest.TestCase):
    project_root: Path

    @classmethod
    def setUpClass(cls) -> None:
        cls.project_root = Path(__file__).resolve().parents[2]

    def _checker(self, root: Path) -> PlausibilityChecker:
        return PlausibilityChecker(
            self.project_root,
            flags_path=root / "qc_flags.json",
            quarantine_path=root / "qc_quarantine.json",
            metrics_path=root / "qc_metrics.json",
            review_path=root / "qc_review_queue.jsonl",
            report_path=root / "qc_records.md",
        )

    def test_controls_have_zero_false_positives_and_injected_errors_are_recalled(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            summary = self._checker(Path(temporary)).run(strict=True)
            self.assertEqual(summary.records, 7)
            self.assertEqual(summary.clean_controls, 2)
            self.assertEqual(summary.injected_error_records, 4)
            self.assertEqual(summary.flags, 5)
            self.assertEqual(summary.critical_flags, 4)
            self.assertEqual(summary.warning_flags, 1)
            self.assertEqual(summary.quarantined_records, 4)
            self.assertEqual(summary.false_positive_controls, 0)
            self.assertEqual(summary.injected_error_records_flagged, 4)
            self.assertEqual(summary.injected_error_recall, 1.0)
            metrics = json.loads(summary.metrics_path.read_text())
            self.assertEqual(metrics["clean_control_false_positive_rate"], 0.0)
            self.assertEqual(metrics["injected_error_recall"], 1.0)

    def test_flag_rules_and_review_ledger_are_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            checker = self._checker(Path(temporary))
            first = checker.run(strict=True)
            first_flags = json.loads(first.flags_path.read_text())["flags"]
            second = checker.run(strict=True)
            second_flags = json.loads(second.flags_path.read_text())["flags"]
            self.assertEqual(first_flags, second_flags)
            rules = {flag["rule"] for flag in first_flags}
            self.assertEqual(
                rules,
                {
                    "FRACTION_OUT_OF_RANGE",
                    "NEGATIVE_CONCENTRATION",
                    "DUPLICATE_SAMPLE_COUNT",
                    "SEM_SD_CONFUSION_CANDIDATE",
                    "PERCENT_OUT_OF_RANGE",
                },
            )
            AppendOnlyJSONL(first.review_path).validate()
            self.assertEqual(len(first.review_path.read_text().splitlines()), 5)

    def test_invalid_fixture_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "bad.json"
            path.write_text(json.dumps({"schema_version": 2}), encoding="utf-8")
            checker = PlausibilityChecker(self.project_root, fixture_path=path)
            with self.assertRaisesRegex(PlausibilityQCError, "envelope"):
                checker.run()


if __name__ == "__main__":
    unittest.main()
