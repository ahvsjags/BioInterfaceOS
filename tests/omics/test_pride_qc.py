from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from biointerfaceos.pride_qc import PrideQCError, PrideQCWorkflow


class PrideQCWorkflowTests(unittest.TestCase):
    project_root: Path

    @classmethod
    def setUpClass(cls) -> None:
        cls.project_root = Path(__file__).resolve().parents[2]

    def test_three_projects_qc_and_concordance_are_quantified(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            summary = PrideQCWorkflow(
                self.project_root,
                output_root=Path(temporary),
            ).run(fixture=True)
            self.assertEqual(summary.attempted_projects, 3)
            self.assertEqual(summary.processed_qc_passed, 1)
            self.assertEqual(summary.failed_projects, 2)
            self.assertEqual(summary.claims, 3)
            self.assertEqual(summary.concordant, 1)
            self.assertEqual(summary.discrepant, 1)
            self.assertEqual(summary.unavailable, 1)
            concordance = json.loads((Path(temporary) / "author_concordance.json").read_text())
            self.assertEqual(
                {row["concordance"] for row in concordance["claims"]},
                {"CONCORDANT", "DISCREPANT", "UNAVAILABLE"},
            )
            failures = json.loads((Path(temporary) / "failure_ledger.json").read_text())
            self.assertTrue(failures["append_only"])
            self.assertEqual(len(failures["entries"]), 2)

    def test_identical_rerun_resumes_without_receipt_change(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workflow = PrideQCWorkflow(self.project_root, output_root=Path(temporary))
            first = workflow.run(fixture=True)
            before = first.receipt_path.read_bytes()
            second = workflow.run(fixture=True)
            self.assertEqual(first.resumed, 0)
            self.assertEqual(second.resumed, 1)
            self.assertEqual(before, second.receipt_path.read_bytes())

    def test_three_project_attempt_gate_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = json.loads((self.project_root / "tests/fixtures/omics/pride_qc_fixture.json").read_text())
            fixture["projects"] = fixture["projects"][:2]
            bad_fixture = Path(temporary) / "bad_qc_fixture.json"
            bad_fixture.write_text(json.dumps(fixture), encoding="utf-8")
            workflow = PrideQCWorkflow(
                self.project_root,
                fixture_path=bad_fixture,
                output_root=Path(temporary) / "output",
            )
            with self.assertRaisesRegex(PrideQCError, "three"):
                workflow.run(fixture=True)


if __name__ == "__main__":
    unittest.main()
