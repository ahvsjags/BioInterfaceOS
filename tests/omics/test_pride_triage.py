"""PRIDE project-card and sample-plan triage tests."""

from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from biointerfaceos import cli
from biointerfaceos.pride_triage import PrideTriage, PrideTriageError


class PrideTriageTests(unittest.TestCase):
    project_root: Path

    @classmethod
    def setUpClass(cls) -> None:
        cls.project_root = Path(__file__).resolve().parents[2]

    def test_project_cards_sample_maps_and_split_decisions(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            summary = PrideTriage(self.project_root, output_root=Path(temporary)).run()
            self.assertEqual(summary.projects, 3)
            self.assertEqual(summary.eligible_projects, 1)
            self.assertEqual(summary.review_projects, 1)
            self.assertEqual(summary.metadata_only_projects, 1)
            self.assertEqual(summary.sample_rows, 8)
            cards = json.loads(summary.outputs["project_cards.json"].read_text(encoding="utf-8"))
            self.assertEqual(len(cards["cards"]), 3)
            self.assertTrue(cards["cards"][0]["sample_plan_valid"])
            self.assertTrue(cards["cards"][0]["no_raw_download"])
            eligibility = json.loads(
                summary.outputs["split_eligibility.json"].read_text(encoding="utf-8")
            )
            self.assertEqual(
                {row["split_decision"] for row in eligibility["projects"]},
                {"ELIGIBLE", "PARK_REVIEW", "METADATA_ONLY"},
            )
            queue = json.loads(summary.outputs["review_queue.json"].read_text(encoding="utf-8"))
            self.assertEqual(len(queue["queue"]), 2)
            receipt = json.loads(summary.outputs["triage_receipt.json"].read_text(encoding="utf-8"))
            self.assertTrue(receipt["no_raw_download"])
            self.assertTrue(receipt["locked_payload_accessed"] is False)

    def test_invalid_fixture_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = Path(temporary) / "bad.json"
            fixture.write_text(json.dumps({"schema_version": 2}), encoding="utf-8")
            triage = PrideTriage(self.project_root, fixture_path=fixture)
            with self.assertRaisesRegex(PrideTriageError, "envelope"):
                triage.run()

    def test_cli_pride_triage_command(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = cli.main(["omics", "pride", "triage", "--scope", "development"])
        self.assertEqual(exit_code, 0)
        self.assertIn("PRIDE_TRIAGE_VALID projects=3", output.getvalue())


if __name__ == "__main__":
    unittest.main()
