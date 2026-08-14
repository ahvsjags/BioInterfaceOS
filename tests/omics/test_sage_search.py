from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from biointerfaceos.sage_search import SageSearchError, SageSearchWorkflow


class SageSearchWorkflowTests(unittest.TestCase):
    project_root: Path

    @classmethod
    def setUpClass(cls) -> None:
        cls.project_root = Path(__file__).resolve().parents[2]

    def test_target_decoy_fdr_and_spike_in_recovery(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            summary = SageSearchWorkflow(
                self.project_root,
                output_root=Path(temporary),
            ).run(fixture=True)
            self.assertEqual(summary.psm_rows, 3)
            self.assertEqual(summary.target_psms, 2)
            self.assertEqual(summary.decoy_psms, 1)
            self.assertEqual(summary.accepted_psms, 2)
            self.assertEqual(summary.estimated_fdr, 0.0)
            self.assertEqual(summary.recovered_spike_ins, 2)
            self.assertEqual(summary.total_spike_ins, 2)
            fdr = json.loads((Path(temporary) / "fdr_summary.json").read_text())
            self.assertEqual(fdr["accepted_decoy_psms"], 0)
            self.assertTrue(fdr["q_values_monotonic"])
            receipt = json.loads((Path(temporary) / "search_receipt.json").read_text())
            self.assertEqual(receipt["configuration"]["enzyme"], "trypsin")
            self.assertEqual(receipt["configuration"]["database_version"], "uniprot-human-fixture-2026-08")
            self.assertEqual(receipt["target_decoy"]["method"], "reverse")

    def test_identical_rerun_resumes_without_receipt_change(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workflow = SageSearchWorkflow(self.project_root, output_root=Path(temporary))
            first = workflow.run(fixture=True)
            receipt_path = Path(temporary) / "search_receipt.json"
            before = receipt_path.read_bytes()
            second = workflow.run(fixture=True)
            self.assertEqual(first.resumed, 0)
            self.assertEqual(second.resumed, 1)
            self.assertEqual(before, receipt_path.read_bytes())

    def test_input_checksum_mismatch_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = json.loads((self.project_root / "tests/fixtures/omics/search_fixture.json").read_text())
            fixture["input"]["artifact_sha256"] = "0" * 64
            bad_fixture = Path(temporary) / "bad_search_fixture.json"
            bad_fixture.write_text(json.dumps(fixture), encoding="utf-8")
            workflow = SageSearchWorkflow(
                self.project_root,
                fixture_path=bad_fixture,
                output_root=Path(temporary) / "output",
            )
            with self.assertRaisesRegex(SageSearchError, "checksum"):
                workflow.run(fixture=True)


if __name__ == "__main__":
    unittest.main()
