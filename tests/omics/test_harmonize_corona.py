from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from biointerfaceos.harmonize_corona import HarmonizationError, HarmonizationWorkflow


class HarmonizationWorkflowTests(unittest.TestCase):
    project_root: Path

    @classmethod
    def setUpClass(cls) -> None:
        cls.project_root = Path(__file__).resolve().parents[2]

    def test_project_scales_composition_and_modules_are_auditable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            summary = HarmonizationWorkflow(
                self.project_root,
                output_root=Path(temporary),
            ).run(fixture=True)
            self.assertEqual(summary.projects, 2)
            self.assertEqual(summary.samples, 4)
            self.assertEqual(summary.proteins, 2)
            self.assertEqual(summary.modules, 2)
            self.assertEqual(summary.missing_cells, 1)
            self.assertEqual(summary.mapping_rows, 2)
            matrix = json.loads((Path(temporary) / "project_matrix.json").read_text())
            self.assertTrue(
                all(
                    abs(
                        sum(
                            value
                            for value in row["composition_values"].values()
                            if value is not None
                        )
                        - 1.0
                    )
                    < 1e-7
                    for row in matrix["rows"]
                )
            )
            qc = json.loads((Path(temporary) / "harmonization_qc.json").read_text())
            self.assertTrue(qc["project_scale_preserved"])
            self.assertTrue(qc["no_combat"])
            self.assertTrue(qc["no_outcome_leakage"])

    def test_identical_rerun_resumes_without_receipt_change(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workflow = HarmonizationWorkflow(self.project_root, output_root=Path(temporary))
            first = workflow.run(fixture=True)
            before = first.receipt_path.read_bytes()
            second = workflow.run(fixture=True)
            self.assertEqual(first.resumed, 0)
            self.assertEqual(second.resumed, 1)
            self.assertEqual(before, second.receipt_path.read_bytes())

    def test_combat_policy_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = json.loads(
                (
                    self.project_root / "tests/fixtures/omics/harmonize_corona_fixture.json"
                ).read_text()
            )
            fixture["policy"]["batch_correction"] = "ComBat"
            bad_fixture = Path(temporary) / "bad_harmonize_fixture.json"
            bad_fixture.write_text(json.dumps(fixture), encoding="utf-8")
            workflow = HarmonizationWorkflow(
                self.project_root,
                fixture_path=bad_fixture,
                output_root=Path(temporary) / "output",
            )
            with self.assertRaisesRegex(HarmonizationError, "ComBat"):
                workflow.run(fixture=True)


if __name__ == "__main__":
    unittest.main()
