"""Figure digitization, calibration, uncertainty, and QC tests."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from biointerfaceos.figure_digitizer import FigureDigitizationError, FigureDigitizer
from biointerfaceos.ledgers import AppendOnlyJSONL


class FigureDigitizerTests(unittest.TestCase):
    project_root: Path

    @classmethod
    def setUpClass(cls) -> None:
        cls.project_root = Path(__file__).resolve().parents[2]

    def _digitizer(self, root: Path) -> FigureDigitizer:
        return FigureDigitizer(
            self.project_root,
            normalized_path=root / "digitized_figure_points.json",
            review_path=root / "digitization_review_queue.jsonl",
            overlay_path=root / "digitization_qc_overlay.json",
            report_path=root / "figure_digitization.md",
        )

    def test_recovers_curve_bar_scatter_and_linear_log_values(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            summary = self._digitizer(Path(temporary)).run()
            self.assertEqual(summary.figures, 1)
            self.assertEqual(summary.panels, 2)
            self.assertEqual(summary.series_seen, 5)
            self.assertEqual(summary.digitized_series, 4)
            self.assertEqual(summary.excluded_series, 1)
            self.assertEqual(summary.points, 12)
            self.assertEqual(summary.uncertainty_records, 4)
            self.assertEqual(summary.review_items, 1)
            payload = json.loads(summary.normalized_path.read_text())
            panel_d = payload["figures"][0]["panels"][0]
            curve = next(item for item in panel_d["series"] if item["series_id"] == "curve-main")
            self.assertEqual([point["x_value"] for point in curve["points"]], [1.0, 5.0, 9.0])
            self.assertEqual(
                [round(point["y_value"], 6) for point in curve["points"]],
                [4.0, 10.0, 16.0],
            )
            self.assertEqual(
                {item["series_type"] for item in panel_d["series"]},
                {"curve", "bar", "scatter"},
            )
            panel_e = payload["figures"][0]["panels"][1]
            log_curve = panel_e["series"][0]
            self.assertEqual(
                [point["x_value"] for point in log_curve["points"]],
                [1.0, 10.0, 100.0],
            )

    def test_uncertainty_is_propagated_and_qc_overlay_keeps_locators(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            summary = self._digitizer(Path(temporary)).run()
            payload = json.loads(summary.normalized_path.read_text())
            curve = payload["figures"][0]["panels"][0]["series"][0]
            uncertain = curve["points"][1]
            self.assertEqual(uncertain["error_type"], "SD")
            self.assertAlmostEqual(uncertain["y_error"], 1.0)
            calibration = payload["figures"][0]["panels"][0]["calibrations"]
            self.assertTrue(all(axis["max_residual"] <= 1e-9 for axis in calibration))
            overlay = json.loads(summary.overlay_path.read_text())
            overlay_series = overlay["overlays"][0]["series"][0]
            self.assertTrue(overlay_series["detector_locator"].startswith("asset:"))
            self.assertEqual(len(overlay_series["digitized_point_locators"]), 3)
            self.assertTrue(overlay_series["normalized_points"])

    def test_low_quality_candidate_is_quarantined_and_queue_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            digitizer = self._digitizer(Path(temporary))
            digitizer.run()
            digitizer.run()
            review_path = Path(temporary) / "digitization_review_queue.jsonl"
            reviews = [
                json.loads(line) for line in review_path.read_text().splitlines() if line.strip()
            ]
            self.assertEqual(len(reviews), 1)
            self.assertEqual(reviews[0]["reason"], "LOW_RESOLUTION_CANDIDATE_EXCLUDED")
            AppendOnlyJSONL(review_path).validate()

    def test_invalid_fixture_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "bad.json"
            path.write_text(json.dumps({"schema_version": 2}), encoding="utf-8")
            digitizer = FigureDigitizer(self.project_root, fixture_path=path)
            with self.assertRaisesRegex(FigureDigitizationError, "envelope"):
                digitizer.run()


if __name__ == "__main__":
    unittest.main()
