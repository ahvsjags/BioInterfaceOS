"""Policy-gated fixture asset downloader tests."""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from biointerfaceos.asset_downloader import AssetDownloader
from biointerfaceos.assets import AssetStore
from biointerfaceos.ledgers import AppendOnlyJSONL
from biointerfaceos.policy import SourcePolicyEngine


class AssetDownloaderTests(unittest.TestCase):
    project_root: Path

    @classmethod
    def setUpClass(cls) -> None:
        cls.project_root = Path(__file__).resolve().parents[1]

    def _root(self, temporary: str) -> Path:
        root = Path(temporary)
        shutil.copytree(self.project_root / "config", root / "config")
        shutil.copytree(self.project_root / "configs", root / "configs")
        shutil.copytree(
            self.project_root / "tests/fixtures/downloads",
            root / "tests/fixtures/downloads",
        )
        return root

    def _downloader(self, root: Path) -> AssetDownloader:
        return AssetDownloader(root, SourcePolicyEngine.from_yaml(root))

    def test_policy_gate_hash_type_and_quarantine(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = self._root(temporary)
            summary = self._downloader(root).run()
            self.assertEqual(summary.promoted, 2)
            self.assertEqual(summary.quarantined, 2)
            self.assertEqual(summary.policy_skipped, 2)
            self.assertEqual(summary.bytes, 61)
            self.assertEqual(AssetStore(root).verify().references, 2)
            receipts = [
                json.loads(line) for line in (root / "reports/download_receipts.jsonl").read_text().splitlines()
            ]
            self.assertEqual(
                {row["status"] for row in receipts},
                {
                    "PROMOTED",
                    "QUARANTINED",
                    "POLICY_SKIPPED",
                },
            )
            self.assertEqual(
                sum(row["reason"].startswith("sha256_mismatch") for row in receipts),
                1,
            )
            self.assertEqual(
                sum(row["reason"].startswith("content_type_mismatch") for row in receipts),
                1,
            )
            AppendOnlyJSONL(root / "reports/download_receipts.jsonl").validate()

    def test_rerun_resumes_without_duplicate_receipts_or_blobs(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = self._root(temporary)
            downloader = self._downloader(root)
            first = downloader.run()
            second = downloader.run()
            self.assertEqual(first.receipts, 6)
            self.assertEqual(second.resumed, 6)
            self.assertEqual(second.receipts, 6)
            self.assertEqual(
                len((root / "reports/download_receipts.jsonl").read_text().splitlines()),
                6,
            )
            self.assertEqual(AssetStore(root).verify().unique_blobs, 2)

    def test_policy_skip_does_not_require_or_read_fixture_payload(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = self._root(temporary)
            queue_path = root / "tests/fixtures/downloads/download_queue.json"
            queue = json.loads(queue_path.read_text())
            item = queue["items"][-1]
            item["fixture_path"] = "data/locked_test/forbidden.bin"
            queue_path.write_text(json.dumps(queue), encoding="utf-8")
            summary = self._downloader(root).run()
            self.assertEqual(summary.policy_skipped, 2)


if __name__ == "__main__":
    unittest.main()
