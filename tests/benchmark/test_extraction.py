"""Extraction benchmark tests."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from biointerfaceos.extraction_benchmark import BenchmarkError, ExtractionBenchmark


class BenchmarkTests(unittest.TestCase):
    project_root: Path

    @classmethod
    def setUpClass(cls) -> None:
        cls.project_root = Path(__file__).resolve().parents[2]

    def test_metrics_calibration_taxonomy_and_g2(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            summary = ExtractionBenchmark(
                self.project_root,
                output_root=Path(temporary),
            ).run()
            self.assertEqual(summary.rows, 8)
            self.assertEqual(summary.correct, 4)
            self.assertEqual(summary.errors, 4)
            self.assertEqual(summary.eligible_rows, 4)
            self.assertEqual(summary.eligible_correct, 4)
            self.assertEqual(summary.precision, 1.0)
            self.assertEqual(summary.recall, 1.0)
            self.assertLessEqual(summary.calibration_error, 0.1)
            self.assertEqual(summary.g2_status, "PASS")
            metrics = json.loads(summary.metrics_path.read_text())
            self.assertEqual(set(metrics["by_modality"]), {"arm", "entity", "evidence", "numeric"})
            taxonomy = json.loads(summary.taxonomy_path.read_text())
            self.assertEqual(len(taxonomy["errors"]), 4)

    def test_invalid_fixture_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "bad.json"
            path.write_text(json.dumps({"schema_version": 2}), encoding="utf-8")
            benchmark = ExtractionBenchmark(self.project_root, fixture_path=path)
            with self.assertRaisesRegex(BenchmarkError, "envelope"):
                benchmark.run()


if __name__ == "__main__":
    unittest.main()
