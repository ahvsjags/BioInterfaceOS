"""Tests for the rebuildable Parquet-backed DuckDB catalog."""

from __future__ import annotations

import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from biointerfaceos.assets import AssetStore
from biointerfaceos.catalog import Catalog, CatalogError
from biointerfaceos.manifest import ManifestRegistry, SourceRecord
from biointerfaceos.policy import RejectionRegistry


def record(data: bytes) -> SourceRecord:
    import hashlib

    digest = hashlib.sha256(data).hexdigest()
    return SourceRecord.create(
        source_id="catalog-source",
        source_name="Catalog Fixture",
        url="https://example.org/catalog",
        access="admitted",
        status="admitted",
        accession="CAT-001",
        publication_date="2024-01-01",
        retrieved_at=datetime.now(UTC).isoformat(),
        sha256=digest,
        size_bytes=len(data),
        license="CC-BY-4.0",
        redistribution="allowed",
        download_status="downloaded",
    )


def empty_inputs(root: Path) -> None:
    ManifestRegistry(root).write([])
    AssetStore(root).initialize()
    RejectionRegistry(root).write([])


class CatalogTests(unittest.TestCase):
    def test_build_check_and_rebuild_are_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            empty_inputs(root)
            catalog = Catalog(root)
            first = catalog.build()
            second = catalog.build()
            self.assertEqual(first, second)
            self.assertEqual(first.schema_version, 1)
            self.assertEqual(first.source_rows, 0)
            self.assertEqual(catalog.query("SELECT value FROM catalog_meta WHERE key='schema_version'"), [("1",)])

    def test_core_join_reads_parquet_backed_rows(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            data = b"catalog asset"
            source_record = record(data)
            ManifestRegistry(root).write([source_record])
            store = AssetStore(root)
            store.put_bytes(data, source_record)
            RejectionRegistry(root).write([])
            summary = Catalog(root).build()
            self.assertEqual(summary.source_rows, 1)
            self.assertEqual(summary.asset_rows, 1)
            self.assertEqual(summary.join_rows, 1)
            self.assertEqual(Catalog(root).query("SELECT count(*) FROM asset_provenance"), [(1,)])

    def test_missing_or_changed_authoritative_input_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            empty_inputs(root)
            catalog = Catalog(root)
            catalog.build()
            (root / "registry/ASSET_INDEX.parquet").unlink()
            with self.assertRaises(CatalogError):
                catalog.check()

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            empty_inputs(root)
            catalog = Catalog(root)
            catalog.build()
            with (root / "registry/SOURCE_MANIFEST.parquet").open("ab") as stream:
                stream.write(b"tamper")
            with self.assertRaises(CatalogError):
                catalog.check()

    def test_query_rejects_writes_and_paths_leave_repository(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            empty_inputs(root)
            catalog = Catalog(root)
            catalog.build()
            with self.assertRaises(CatalogError):
                catalog.query("DELETE FROM source_manifest")
            with self.assertRaises(CatalogError):
                Catalog(root, root.parent / "outside.duckdb")


if __name__ == "__main__":
    unittest.main()
