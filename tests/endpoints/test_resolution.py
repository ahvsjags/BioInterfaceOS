"""Endpoint and measurement ontology resolution tests."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from biointerfaceos.endpoint_resolution import EndpointResolutionError, EndpointResolver
from biointerfaceos.ledgers import AppendOnlyJSONL


class EndpointResolverTests(unittest.TestCase):
    project_root: Path

    @classmethod
    def setUpClass(cls) -> None:
        cls.project_root = Path(__file__).resolve().parents[2]

    def _resolver(self, root: Path) -> EndpointResolver:
        return EndpointResolver(
            self.project_root,
            endpoints_path=root / "endpoint_entities.json",
            strata_path=root / "endpoint_strata.json",
            review_path=root / "endpoint_review_queue.jsonl",
            report_path=root / "endpoint_resolution.md",
        )

    def test_families_assays_bases_times_and_compatible_effects(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            summary = self._resolver(Path(temporary)).run()
            self.assertEqual(summary.endpoints, 9)
            self.assertEqual(summary.normalized, 8)
            self.assertEqual(summary.families, 7)
            self.assertEqual(summary.strata, 7)
            self.assertEqual(summary.harmonized_strata, 1)
            self.assertEqual(summary.review_items, 1)
            payload = json.loads(summary.endpoints_path.read_text())
            uptake = next(item for item in payload["endpoints"] if item["endpoint_id"] == "uptake-001")
            self.assertEqual(uptake["normalized_value"], 0.4)
            self.assertEqual(uptake["time_seconds"], 86400.0)
            viability = next(item for item in payload["endpoints"] if item["endpoint_id"] == "viability-001")
            self.assertNotEqual(uptake["stratum_id"], viability["stratum_id"])
            coagulation = next(item for item in payload["endpoints"] if item["endpoint_id"] == "coagulation-001")
            self.assertEqual(coagulation["time_seconds"], 1800.0)
            strata = json.loads(summary.strata_path.read_text())["strata"]
            uptake_stratum = next(item for item in strata if "uptake" in item["stratum_id"])
            self.assertAlmostEqual(uptake_stratum["harmonized_mean"], 0.45)
            self.assertEqual(uptake_stratum["member_count"], 2)

    def test_missing_time_is_explicit_and_review_queue_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            resolver = self._resolver(Path(temporary))
            first = resolver.run()
            resolver.run()
            payload = json.loads(first.endpoints_path.read_text())
            missing = next(item for item in payload["endpoints"] if item["endpoint_id"] == "delivery-missing-time")
            self.assertEqual(missing["status"], "REVIEW_REQUIRED")
            self.assertEqual(missing["resolution_reason"], "MISSING_ENDPOINT_TIMEPOINT")
            self.assertIsNone(missing["stratum_id"])
            reviews = [json.loads(line) for line in first.review_path.read_text().splitlines() if line.strip()]
            self.assertEqual(len(reviews), 1)
            AppendOnlyJSONL(first.review_path).validate()

    def test_invalid_fixture_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "bad.json"
            path.write_text(json.dumps({"schema_version": 2}), encoding="utf-8")
            resolver = EndpointResolver(self.project_root, fixture_path=path)
            with self.assertRaisesRegex(EndpointResolutionError, "envelope"):
                resolver.run()


if __name__ == "__main__":
    unittest.main()
