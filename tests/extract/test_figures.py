"""Scientific figure panel and axis detector tests."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from biointerfaceos.figure_detector import FigureDetectionError, FigureDetector
from biointerfaceos.ledgers import AppendOnlyJSONL


class FigureDetectorTests(unittest.TestCase):
    project_root: Path

    @classmethod
    def setUpClass(cls) -> None:
        cls.project_root = Path(__file__).resolve().parents[2]

    def _detector(self, root: Path) -> FigureDetector:
        return FigureDetector(
            self.project_root,
            normalized_path=root / "figure_detection.json",
            review_path=root / "figure_review_queue.jsonl",
            report_path=root / "figure_detection.md",
        )

    def test_detects_panels_axes_scales_legends_and_curve_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            summary = self._detector(Path(temporary)).run()
            self.assertEqual(summary.figures, 2)
            self.assertEqual(summary.panels, 3)
            self.assertEqual(summary.supported_panels, 2)
            self.assertEqual(summary.unsupported_panels, 1)
            self.assertEqual(summary.axes, 4)
            self.assertEqual(summary.legend_entries, 3)
            self.assertEqual(summary.curve_candidates, 3)
            self.assertEqual(summary.uncertainty_cues, 2)
            self.assertEqual(summary.review_items, 1)
            payload = json.loads(summary.normalized_path.read_text())
            panel_a = payload["figures"][0]["panels"][0]
            panel_b = payload["figures"][0]["panels"][1]
            self.assertEqual(
                {axis["scale_type"] for axis in panel_a["axes"]},
                {"linear"},
            )
            b_x_axis = next(axis for axis in panel_b["axes"] if axis["orientation"] == "x")
            self.assertEqual(b_x_axis["scale_type"], "log")
            self.assertEqual(panel_a["label"], "A")
            self.assertTrue(panel_a["curve_candidates"][0]["locator"].startswith("asset:"))
            self.assertNotIn("digitized_values", panel_a["curve_candidates"][0])

    def test_unsupported_panel_and_confidence_calibration_are_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            summary = self._detector(Path(temporary)).run()
            payload = json.loads(summary.normalized_path.read_text())
            unsupported = payload["figures"][1]["panels"][0]
            self.assertFalse(unsupported["supported"])
            self.assertEqual(unsupported["panel_type"], "heatmap")
            self.assertEqual(
                unsupported["review_items"][0]["reason"],
                "UNSUPPORTED_PANEL_TYPE_HEATMAP",
            )
            self.assertEqual(payload["confidence_calibration"]["HIGH"], ">=0.85")
            for panel in payload["figures"][0]["panels"]:
                self.assertGreaterEqual(panel["confidence"], 0.85)
                self.assertIn(panel["confidence_band"], {"HIGH", "MEDIUM", "LOW"})

    def test_review_queue_is_append_only_and_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            detector = self._detector(Path(temporary))
            detector.run()
            detector.run()
            review_path = Path(temporary) / "figure_review_queue.jsonl"
            reviews = [
                json.loads(line) for line in review_path.read_text().splitlines() if line.strip()
            ]
            self.assertEqual(len(reviews), 1)
            self.assertEqual(reviews[0]["reason"], "UNSUPPORTED_PANEL_TYPE_HEATMAP")
            AppendOnlyJSONL(review_path).validate()

    def test_invalid_fixture_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "bad.json"
            path.write_text(json.dumps({"schema_version": 2}), encoding="utf-8")
            detector = FigureDetector(self.project_root, fixture_path=path)
            with self.assertRaisesRegex(FigureDetectionError, "envelope"):
                detector.run()


if __name__ == "__main__":
    unittest.main()
