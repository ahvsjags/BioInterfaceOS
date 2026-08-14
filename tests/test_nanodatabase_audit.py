"""Offline validation tests for the specialized nanodatabase audit."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from biointerfaceos.nanodatabase_audit import NanodatabaseAuditError, load_audit, validate_audit


class NanodatabaseAuditTests(unittest.TestCase):
    def test_fixture_has_decisions_for_specialized_sources_and_substitutes(self) -> None:
        root = Path(__file__).resolve().parents[1]
        summary = load_audit(root / "tests/fixtures/nanodatabases/admission_decisions.json")
        self.assertEqual(summary.candidates, 6)
        self.assertEqual(summary.admitted_substitutes, 2)
        self.assertEqual(summary.metadata_only, 2)
        self.assertEqual(summary.quarantined, 1)
        self.assertEqual(summary.rejected, 1)

    def test_audit_rejects_duplicate_or_missing_evidence(self) -> None:
        root = Path(__file__).resolve().parents[1]
        value = json.loads((root / "tests/fixtures/nanodatabases/admission_decisions.json").read_text(encoding="utf-8"))
        value["decisions"][1]["id"] = value["decisions"][0]["id"]
        with self.assertRaises(NanodatabaseAuditError):
            validate_audit(value)
        value["decisions"][1]["id"] = "unique"
        value["decisions"][1]["evidence_urls"] = []
        with self.assertRaises(NanodatabaseAuditError):
            validate_audit(value)

    def test_audit_file_errors_are_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "bad.json"
            path.write_text("[]", encoding="utf-8")
            with self.assertRaises(NanodatabaseAuditError):
                load_audit(path)


if __name__ == "__main__":
    unittest.main()
