"""Protocol and bioenvironment ontology resolution tests."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from biointerfaceos.ledgers import AppendOnlyJSONL
from biointerfaceos.protocol_resolution import ProtocolResolutionError, ProtocolResolver


class ProtocolResolverTests(unittest.TestCase):
    project_root: Path

    @classmethod
    def setUpClass(cls) -> None:
        cls.project_root = Path(__file__).resolve().parents[2]

    def _resolver(self, root: Path) -> ProtocolResolver:
        return ProtocolResolver(
            self.project_root,
            protocols_path=root / "protocol_entities.json",
            clusters_path=root / "protocol_clusters.json",
            review_path=root / "protocol_review_queue.jsonl",
            report_path=root / "protocol_resolution.md",
        )

    def test_normalizes_protocol_fields_and_severity_features(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            summary = self._resolver(Path(temporary)).run()
            self.assertEqual(summary.protocols, 1)
            self.assertEqual(summary.fields, 10)
            self.assertEqual(summary.observed_fields, 9)
            self.assertEqual(summary.missing_fields, 1)
            self.assertEqual(summary.clusters, 1)
            self.assertEqual(summary.review_items, 0)
            payload = json.loads(summary.protocols_path.read_text())
            fields = payload["protocols"][0]["fields"]
            source = next(item for item in fields if item["name"] == "bioenvironment_source")
            self.assertEqual(source["normalized_value"], "Fetal bovine serum")
            concentration = next(item for item in fields if item["name"] == "concentration")
            self.assertEqual(concentration["normalized_value"], 0.1)
            exposure = next(item for item in fields if item["name"] == "exposure_time")
            self.assertEqual(exposure["normalized_value"], 7200.0)
            temperature = next(item for item in fields if item["name"] == "temperature")
            self.assertAlmostEqual(temperature["normalized_value"], 310.15)
            missing = next(item for item in fields if item["name"] == "serum_source_detail")
            self.assertIsNone(missing["normalized_value"])
            self.assertEqual(missing["status"], "MISSING")
            self.assertEqual(missing["missingness"], "MISSING")
            features = payload["protocols"][0]["severity_features"]
            self.assertEqual(features["wash_count"], 3)
            self.assertEqual(features["centrifugation_xg"], 1200.0)
            self.assertEqual(features["replicate_count"], 3)
            self.assertEqual(features["missing_field_count"], 1)

    def test_cluster_and_review_ledger_are_stable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            resolver = self._resolver(Path(temporary))
            first = resolver.run()
            second = resolver.run()
            self.assertEqual(first.clusters_path.read_bytes(), second.clusters_path.read_bytes())
            AppendOnlyJSONL(first.review_path).validate()
            self.assertEqual(first.review_path.read_text(), "")

    def test_invalid_fixture_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "bad.json"
            path.write_text(json.dumps({"schema_version": 2}), encoding="utf-8")
            resolver = ProtocolResolver(self.project_root, fixture_path=path)
            with self.assertRaisesRegex(ProtocolResolutionError, "envelope"):
                resolver.run()


if __name__ == "__main__":
    unittest.main()
