"""Tests for immutable release receipts and checksums."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from biointerfaceos.release import RELEASE_INPUTS, ReleaseError, ReleaseManager


def make_inputs(root: Path) -> None:
    for relative in RELEASE_INPUTS:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(("fixture:" + relative.as_posix()).encode("utf-8"))


class ReleaseTests(unittest.TestCase):
    def test_freeze_verify_and_repeatability(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            make_inputs(root)
            manager = ReleaseManager(root)
            now = datetime(2026, 8, 12, 12, 0, tzinfo=UTC)
            summary = manager.freeze(fixture=True, git_commit="a" * 40, now=now)
            self.assertEqual(manager.verify(summary.release_id), summary)
            receipt = json.loads((root / "release/fixtures" / summary.release_id / "release_receipt.json").read_text())
            self.assertTrue(receipt["frozen"])
            with self.assertRaises(ReleaseError):
                manager.freeze(fixture=True, git_commit="a" * 40, now=now)

    def test_tamper_and_input_change_fail_verification(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            make_inputs(root)
            manager = ReleaseManager(root)
            summary = manager.freeze(
                fixture=True,
                git_commit="b" * 40,
                now=datetime(2026, 8, 12, tzinfo=UTC),
            )
            release_dir = root / "release/fixtures" / summary.release_id
            checksums = release_dir / "checksums.txt"
            checksums.chmod(0o644)
            with checksums.open("a", encoding="utf-8") as stream:
                stream.write("tampered\n")
            checksums.chmod(0o444)
            with self.assertRaises(ReleaseError):
                manager.verify(summary.release_id)

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            make_inputs(root)
            manager = ReleaseManager(root)
            summary = manager.freeze(
                fixture=True,
                git_commit="c" * 40,
                now=datetime(2026, 8, 12, tzinfo=UTC),
            )
            (root / RELEASE_INPUTS[0]).write_bytes(b"changed")
            with self.assertRaises(ReleaseError):
                manager.verify(summary.release_id)

    def test_non_fixture_freeze_and_outside_release_are_denied(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            make_inputs(root)
            manager = ReleaseManager(root)
            with self.assertRaises(ReleaseError):
                manager.freeze()
            with self.assertRaises(ReleaseError):
                ReleaseManager(root, root.parent / "outside")

    def test_receipt_contains_all_input_hashes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            make_inputs(root)
            summary = ReleaseManager(root).freeze(
                fixture=True,
                git_commit="d" * 40,
                now=datetime(2026, 8, 12, tzinfo=UTC),
            )
            manifest_path = root / "release/fixtures" / summary.release_id / "release_manifest.json"
            manifest = json.loads(manifest_path.read_text())
            self.assertEqual(len(manifest["files"]), len(RELEASE_INPUTS))
            self.assertEqual(manifest["manifest_hash"], summary.manifest_hash)


if __name__ == "__main__":
    unittest.main()
