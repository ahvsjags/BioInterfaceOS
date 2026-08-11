"""Saturation and coverage-gap analysis tests."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from biointerfaceos.saturation import SaturationAnalyzer, SaturationError


class SaturationAnalyzerTests(unittest.TestCase):
    project_root: Path

    @classmethod
    def setUpClass(cls) -> None:
        cls.project_root = Path(__file__).resolve().parents[1]

    def test_metrics_report_batch_and_axis_yield(self) -> None:
        metrics = SaturationAnalyzer(self.project_root).analyze()
        self.assertEqual(metrics["search"]["raw_hits"], 17)
        self.assertEqual(metrics["search"]["unique_candidates"], 14)
        self.assertEqual(metrics["search"]["admitted_candidates"], 13)
        self.assertEqual(metrics["expansion"]["raw_edges"], 44)
        self.assertEqual(metrics["expansion"]["unique_targets"], 17)
        self.assertEqual(len(metrics["batches"]), 13)
        self.assertEqual(len(metrics["axis_totals"]), 7)
        self.assertEqual(metrics["stopping"]["decision"], "CONTINUE")

    def test_report_is_self_contained_and_lists_required_gaps(self) -> None:
        metrics = SaturationAnalyzer(self.project_root).analyze()
        gap_ids = {gap["id"] for gap in metrics["coverage_gaps"]}
        self.assertIn("validation-2024-not-executed", gap_ids)
        self.assertIn("material-polymeric", gap_ids)
        self.assertIn("endpoint-biodistribution", gap_ids)
        self.assertEqual(len(metrics["gap_query_proposals"]), 8)
        html = SaturationAnalyzer.render_html(metrics)
        self.assertIn("Novel eligible-study yield by batch", html)
        self.assertIn("saturation-data", html)
        with tempfile.TemporaryDirectory() as temporary:
            output, _ = SaturationAnalyzer(self.project_root).write_report(
                Path(temporary) / "saturation.html"
            )
            self.assertEqual(output.read_text(encoding="utf-8"), html)

    def test_invalid_expectations_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "bad_expectations.json"
            path.write_text(json.dumps({"schema_version": 2}), encoding="utf-8")
            analyzer = SaturationAnalyzer(self.project_root, expectations_path=path)
            with self.assertRaisesRegex(SaturationError, "schema"):
                analyzer.analyze()


if __name__ == "__main__":
    unittest.main()
