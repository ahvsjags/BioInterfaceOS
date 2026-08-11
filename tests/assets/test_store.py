"""File-only tests for the content-addressed asset store."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from biointerfaceos.assets import (
    AssetHashMismatch,
    AssetIntegrityError,
    AssetPathError,
    AssetStore,
    AssetStoreError,
)
from biointerfaceos.manifest import ManifestRegistry, SourceRecord


def _record(data: bytes, *, source_id: str = "asset-source") -> SourceRecord:
    import hashlib
    from datetime import UTC, datetime

    digest = hashlib.sha256(data).hexdigest()
    return SourceRecord.create(
        source_id=source_id,
        source_name="Asset Fixture",
        url="https://example.org/asset/" + source_id,
        access="admitted",
        status="admitted",
        accession="ASSET-001",
        publication_date="2024-01-02",
        retrieved_at=datetime.now(UTC).isoformat(),
        sha256=digest,
        size_bytes=len(data),
        license="CC-BY-4.0",
        redistribution="allowed",
        download_status="downloaded",
    )


def _setup(root: Path, record: SourceRecord) -> AssetStore:
    ManifestRegistry(root).write([record])
    return AssetStore(root)


class AssetStoreTests(unittest.TestCase):
    def test_identical_bytes_are_stored_once_and_indexed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            data = b"same public bytes"
            record = _record(data)
            store = _setup(root, record)
            first = store.put_bytes(data, record)
            second = store.put_bytes(data, record)
            self.assertEqual(first, second)
            summary = store.verify()
            self.assertEqual(summary.references, 1)
            self.assertEqual(summary.unique_blobs, 1)
            blobs = [path for path in (root / "data/cas/sha256").rglob("*") if path.is_file()]
            self.assertEqual(len(blobs), 1)

    def test_hash_mismatch_is_rejected_and_preserved_outside_cas(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            expected = _record(b"expected bytes")
            store = _setup(root, expected)
            with self.assertRaises(AssetHashMismatch):
                store.put_bytes(b"wrong bytes", expected)
            self.assertEqual(store.verify().references, 0)
            self.assertEqual(
                [path for path in (root / "data/cas/sha256").rglob("*") if path.is_file()],
                [],
            )
            quarantined = list((root / "data/quarantine").glob("*.part"))
            self.assertEqual(len(quarantined), 1)

    def test_file_ingest_keeps_provenance_link(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            data = b"provenance bytes"
            record = _record(data)
            source = root / "incoming.bin"
            source.write_bytes(data)
            store = _setup(root, record)
            reference = store.put_file(source, record)
            self.assertEqual(reference.asset_id, record.asset_id)
            self.assertEqual(store.verify().references, 1)

    def test_missing_provenance_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            record = _record(b"unlinked")
            store = AssetStore(root)
            with self.assertRaises(AssetStoreError):
                store.put_bytes(b"unlinked", record)

    def test_locked_test_and_outside_paths_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            record = _record(b"protected")
            store = _setup(root, record)
            locked = root / "data/locked_test/fixture.bin"
            locked.parent.mkdir(parents=True)
            locked.write_bytes(b"protected")
            with self.assertRaises(AssetPathError):
                store.put_file(locked, record)
            with self.assertRaises(AssetPathError):
                AssetStore(root, cas_root=root.parent / "cas")

    def test_tampered_promoted_blob_fails_verification(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            data = b"tamper me"
            record = _record(data)
            store = _setup(root, record)
            store.put_bytes(data, record)
            blob = next(path for path in (root / "data/cas/sha256").rglob("*") if path.is_file())
            blob.write_bytes(b"tampered")
            with self.assertRaises(AssetIntegrityError):
                store.verify()


if __name__ == "__main__":
    unittest.main()
