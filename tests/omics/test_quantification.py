from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from biointerfaceos.quantification_workflow import QuantificationError, QuantificationWorkflow


class QuantificationWorkflowTests(unittest.TestCase):
    project_root: Path

    @classmethod
    def setUpClass(cls) -> None:
        cls.project_root = Path(__file__).resolve().parents[2]

    def test_lfq_replicates_missingness_groups_and_ratio_recovery(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            summary = QuantificationWorkflow(
                self.project_root,
                output_root=Path(temporary),
            ).run(fixture=True)
            self.assertEqual(summary.runs, 4)
            self.assertEqual(summary.samples, 2)
            self.assertEqual(summary.quantifiable_proteins, 2)
            self.assertEqual(summary.groups, 4)
            self.assertEqual(summary.missing_cells, 1)
            self.assertEqual(summary.contaminant_groups, 1)
            self.assertEqual(summary.ratios_passed, 2)
            self.assertEqual(summary.ratios_total, 2)
            ratios = json.loads((Path(temporary) / "ratio_recovery.json").read_text())
            self.assertTrue(ratios["passed"])
            self.assertEqual(ratios["results"][1]["numerator_observations"], 1)
            missing = json.loads((Path(temporary) / "missingness_report.json").read_text())
            self.assertTrue(missing["no_imputation"])
            self.assertEqual(missing["missing_cells"], 1)
            groups = json.loads((Path(temporary) / "protein_groups.json").read_text())
            self.assertTrue(any(not row["quantifiable"] for row in groups["groups"]))

    def test_identical_rerun_resumes_without_receipt_change(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workflow = QuantificationWorkflow(self.project_root, output_root=Path(temporary))
            first = workflow.run(fixture=True)
            before = first.receipt_path.read_bytes()
            second = workflow.run(fixture=True)
            self.assertEqual(first.resumed, 0)
            self.assertEqual(second.resumed, 1)
            self.assertEqual(before, second.receipt_path.read_bytes())

    def test_search_receipt_checksum_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = json.loads(
                (self.project_root / "tests/fixtures/omics/quantification_fixture.json").read_text()
            )
            fixture["search"]["receipt_sha256"] = "0" * 64
            bad_fixture = Path(temporary) / "bad_quantification_fixture.json"
            bad_fixture.write_text(json.dumps(fixture), encoding="utf-8")
            workflow = QuantificationWorkflow(
                self.project_root,
                fixture_path=bad_fixture,
                output_root=Path(temporary) / "output",
            )
            with self.assertRaisesRegex(QuantificationError, "checksum"):
                workflow.run(fixture=True)


if __name__ == "__main__":
    unittest.main()
