"""Unit normalization and uncertainty propagation tests."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from biointerfaceos.ledgers import AppendOnlyJSONL
from biointerfaceos.unit_normalizer import UnitNormalizationError, UnitNormalizer


class UnitNormalizerTests(unittest.TestCase):
    project_root: Path

    @classmethod
    def setUpClass(cls) -> None:
        cls.project_root = Path(__file__).resolve().parents[2]

    def _normalizer(self, root: Path) -> UnitNormalizer:
        return UnitNormalizer(
            self.project_root,
            output_path=root / "normalized_units.json",
            review_path=root / "unit_clarification_queue.jsonl",
            report_path=root / "unit_normalization.md",
        )

    def test_dimensions_and_conversions_are_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            summary = self._normalizer(Path(temporary)).run()
            self.assertEqual(summary.assertions, 8)
            self.assertEqual(summary.normalized, 6)
            self.assertEqual(summary.review_items, 2)
            self.assertEqual(summary.uncertainty_records, 5)
            payload = json.loads(summary.output_path.read_text())
            size = next(item for item in payload["assertions"] if item["assertion_id"] == "size-001")
            self.assertEqual(size["normalized_value"], 1e-8)
            self.assertEqual(size["dimension"], "length")
            time = next(item for item in payload["assertions"] if item["assertion_id"] == "time-001")
            self.assertEqual(time["normalized_value"], 7200.0)
            concentration = next(item for item in payload["assertions"] if item["assertion_id"] == "concentration-001")
            self.assertEqual(concentration["normalized_value"], 2.0)
            self.assertEqual(concentration["target_unit"], "g/L")

    def test_uncertainty_uses_the_same_valid_conversion_factor(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            payload = json.loads(self._normalizer(Path(temporary)).run().output_path.read_text())
            size = next(item for item in payload["assertions"] if item["assertion_id"] == "size-001")
            self.assertEqual(size["normalized_uncertainty"], 2e-9)
            self.assertAlmostEqual(size["relative_uncertainty"], 0.2)
            dose = next(item for item in payload["assertions"] if item["assertion_id"] == "dose-001")
            self.assertEqual(dose["normalized_uncertainty"], 0.2)

    def test_unknown_basis_and_incompatible_dimensions_are_not_converted(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            summary = self._normalizer(Path(temporary)).run()
            payload = json.loads(summary.output_path.read_text())
            unknown = next(item for item in payload["assertions"] if item["assertion_id"] == "unknown-basis-001")
            incompatible = next(item for item in payload["assertions"] if item["assertion_id"] == "incompatible-001")
            self.assertIsNone(unknown["normalized_value"])
            self.assertEqual(unknown["clarification_reason"], "UNKNOWN_BASIS_FOR_DOSE")
            self.assertIsNone(incompatible["normalized_value"])
            self.assertEqual(incompatible["clarification_reason"], "INCOMPATIBLE_DIMENSIONS")
            self.assertEqual(unknown["raw_value"], 5.0)
            self.assertTrue(unknown["evidence_locator"].startswith("asset:"))
            AppendOnlyJSONL(summary.review_path).validate()

    def test_invalid_fixture_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "bad.json"
            path.write_text(json.dumps({"schema_version": 2}), encoding="utf-8")
            normalizer = UnitNormalizer(self.project_root, fixture_path=path)
            with self.assertRaisesRegex(UnitNormalizationError, "envelope"):
                normalizer.run()


if __name__ == "__main__":
    unittest.main()
