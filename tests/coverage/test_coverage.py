"""Data coverage and missingness audit tests."""

from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from biointerfaceos import cli
from biointerfaceos.coverage_audit import DataCoverageAuditor, DataCoverageError


class DataCoverageTests(unittest.TestCase):
    project_root: Path

    @classmethod
    def setUpClass(cls) -> None:
        cls.project_root = Path(__file__).resolve().parents[2]

    def test_independent_coverage_missingness_and_bias_warnings(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            summary = DataCoverageAuditor(
                self.project_root,
                output_root=Path(temporary),
            ).run()
            self.assertEqual(summary.independent_studies, 7)
            self.assertEqual(summary.admitted_candidates, 13)
            self.assertEqual(summary.represented_candidates, 7)
            self.assertEqual(summary.missing_values, 4)
            self.assertEqual(summary.gaps, 4)
            self.assertGreaterEqual(summary.bias_warnings, 8)
            report = json.loads(summary.coverage_path.read_text(encoding="utf-8"))
            self.assertTrue(report["no_imputation"])
            self.assertEqual(
                report["coverage"]["study"]["observed"]["study-001"]["independent_studies"],
                1,
            )
            self.assertEqual(report["search_registry"]["candidate_rows"], 14)
            missingness = json.loads(summary.missingness_path.read_text(encoding="utf-8"))
            self.assertEqual(missingness["overall"]["lab"]["missing_count"], 2)
            self.assertEqual(missingness["overall"]["species"]["missing_count"], 1)
            self.assertEqual(missingness["overall"]["publication_year"]["missing_count"], 1)
            warnings = json.loads(summary.warnings_path.read_text(encoding="utf-8"))
            warning_ids = {warning["warning_id"] for warning in warnings["warnings"]}
            self.assertIn("MISSING_LAB", warning_ids)
            self.assertIn("SEARCH_CANDIDATE_COVERAGE", warning_ids)
            self.assertIn("COVERAGE_GAP:material:silica", warning_ids)

    def test_invalid_fixture_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = Path(temporary) / "bad.json"
            fixture.write_text(json.dumps({"schema_version": 2}), encoding="utf-8")
            auditor = DataCoverageAuditor(self.project_root, fixture_path=fixture)
            with self.assertRaisesRegex(DataCoverageError, "envelope"):
                auditor.run()

    def test_cli_data_coverage_command(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = cli.main(["report", "data-coverage"])
        self.assertEqual(exit_code, 0)
        self.assertIn("DATA_COVERAGE_VALID studies=7", output.getvalue())


if __name__ == "__main__":
    unittest.main()
