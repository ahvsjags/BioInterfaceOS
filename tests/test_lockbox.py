"""Tests for lockbox firewall and contamination scanning."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from biointerfaceos.lockbox import (
    LockboxAccessError,
    LockboxFirewall,
    LockboxPolicy,
)


def policy(root: Path) -> LockboxPolicy:
    return LockboxPolicy(
        locked_root=root / "data/locked_test",
        metadata_whitelist=frozenset({"metadata.json", "README.md"}),
        forbidden_fields=("outcome", "label", "sample_id", "locked_test"),
    )


class LockboxTests(unittest.TestCase):
    def test_development_reads_are_blocked_and_metadata_is_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            locked = root / "data/locked_test"
            locked.mkdir(parents=True)
            (locked / "metadata.json").write_text('{"date_start": "2025-01-01"}\n')
            (locked / "payload.json").write_text('{"outcome": "hidden"}\n')
            firewall = LockboxFirewall(root, policy(root))
            with self.assertRaises(LockboxAccessError):
                firewall.open_development(locked / "payload.json")
            with self.assertRaises(LockboxAccessError):
                firewall.read_metadata(locked / "payload.json")
            metadata = firewall.read_metadata(locked / "metadata.json")
            self.assertIsInstance(metadata, dict)
            assert isinstance(metadata, dict)
            self.assertEqual(metadata["date_start"], "2025-01-01")

    def test_scanner_detects_forbidden_field_and_exact_hash(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fixture = root / "artifact.json"
            fixture.write_text('{"outcome": "hidden"}\n')
            firewall = LockboxFirewall(root, policy(root))
            digest = hashlib.sha256(fixture.read_bytes()).hexdigest()
            report = firewall.scan([fixture], forbidden_hashes=[digest])
            self.assertFalse(report.clean)
            self.assertEqual(len(report.findings), 2)
            with self.assertRaises(LockboxAccessError):
                firewall.scan([root / "data/locked_test/payload.bin"])

    def test_clean_scan_and_audit_receipt_are_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fixture_dir = root / "fixtures"
            fixture_dir.mkdir()
            (fixture_dir / "clean.json").write_text('{"run_id": "clean"}\n')
            (fixture_dir / "contaminated.json").write_text('{"label": "bad"}\n')
            firewall = LockboxFirewall(root, policy(root))
            audit = firewall.self_test(fixture_dir)
            self.assertTrue(audit["passed"])
            report_path = firewall.write_audit(audit, root / "reports/audit.json")
            self.assertTrue(report_path.is_file())
            stored = json.loads(report_path.read_text())
            self.assertTrue(stored["passed"])

    def test_configured_project_lockbox_has_no_payload_access(self) -> None:
        root = Path(__file__).resolve().parents[1]
        firewall = LockboxFirewall(root)
        with self.assertRaises(LockboxAccessError):
            firewall.assert_development_read_allowed(root / "data/locked_test/payload.bin")
        self.assertTrue((root / "data/locked_test").is_dir())


if __name__ == "__main__":
    unittest.main()
