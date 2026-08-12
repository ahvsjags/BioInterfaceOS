from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from biointerfaceos.geo_discovery import GeoDiscoveryError, GeoDiscoveryWorkflow


class GeoDiscoveryWorkflowTests(unittest.TestCase):
    project_root: Path

    @classmethod
    def setUpClass(cls) -> None:
        cls.project_root = Path(__file__).resolve().parents[2]

    def test_candidate_eligibility_and_coverage_gaps(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            summary = GeoDiscoveryWorkflow(
                self.project_root,
                output_root=Path(temporary),
            ).run(fixture=True)
            self.assertEqual(summary.candidates, 4)
            self.assertEqual(summary.eligible, 2)
            self.assertEqual(summary.restricted_rejected, 1)
            self.assertEqual(summary.metadata_only, 1)
            self.assertEqual(summary.coverage_gaps, 3)
            registry = json.loads((Path(temporary) / "candidate_registry.json").read_text())
            self.assertEqual(
                {row["decision"] for row in registry["candidates"]},
                {"ELIGIBLE", "REJECTED_RESTRICTED", "METADATA_ONLY"},
            )
            rejections = json.loads((Path(temporary) / "rejection_ledger.json").read_text())
            self.assertTrue(rejections["append_only"])
            self.assertEqual(len(rejections["entries"]), 2)

    def test_identical_rerun_resumes_without_receipt_change(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workflow = GeoDiscoveryWorkflow(self.project_root, output_root=Path(temporary))
            first = workflow.run(fixture=True)
            before = first.receipt_path.read_bytes()
            second = workflow.run(fixture=True)
            self.assertEqual(first.resumed, 0)
            self.assertEqual(second.resumed, 1)
            self.assertEqual(before, second.receipt_path.read_bytes())

    def test_non_development_scope_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workflow = GeoDiscoveryWorkflow(self.project_root, output_root=Path(temporary))
            with self.assertRaisesRegex(GeoDiscoveryError, "development"):
                workflow.run(fixture=True, scope="validation")


if __name__ == "__main__":
    unittest.main()
