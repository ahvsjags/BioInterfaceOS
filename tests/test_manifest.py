"""Tests for the strict source manifest registry."""

from __future__ import annotations

import hashlib
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from biointerfaceos.cli import main
from biointerfaceos.manifest import (
    MANIFEST_FIELDS,
    ManifestError,
    ManifestPathError,
    ManifestRegistry,
    SourceRecord,
)


def _record(
    *,
    source_id: str = "fixture-source",
    url: str = "https://example.org/asset-a",
    sha256: str | None = None,
    status: str = "admitted",
    access: str = "admitted",
    license: str | None = "CC-BY-4.0",
    redistribution: str | None = "allowed",
    rejection_reason: str | None = None,
    retrieved_at: str | None = None,
) -> SourceRecord:
    return SourceRecord.create(
        source_id=source_id,
        source_name="Fixture Public Source",
        url=url,
        access=access,
        status=status,
        accession="ACC-001",
        publication_date="2024-01-02",
        retrieved_at=retrieved_at or datetime.now(UTC).isoformat(),
        sha256=sha256,
        size_bytes=12,
        license=license,
        redistribution=redistribution,
        download_status="downloaded" if sha256 else "pending",
        rejection_reason=rejection_reason,
    )


class ManifestRegistryTests(unittest.TestCase):
    def test_atomic_parquet_round_trip_and_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            registry = ManifestRegistry(root)
            registry.write([_record()])
            summary = registry.validate()
            self.assertEqual(summary.rows, 1)
            self.assertEqual(summary.admitted, 1)
            self.assertEqual(registry.records()[0].source_id, "fixture-source")
            self.assertEqual(tuple(registry._read_table().column_names), MANIFEST_FIELDS)

    def test_rejected_and_quarantined_records_require_explicit_reason(self) -> None:
        with self.assertRaises(ManifestError):
            _record(status="quarantined", rejection_reason=None)
        rejected = _record(
            status="rejected",
            access="rejected",
            license=None,
            redistribution=None,
            rejection_reason="registration required",
        )
        self.assertEqual(rejected.status, "rejected")

    def test_admission_requires_explicit_license_and_redistribution(self) -> None:
        with self.assertRaises(ManifestError):
            _record(license=None)
        with self.assertRaises(ManifestError):
            _record(redistribution=None)

    def test_identical_content_hash_is_deduplicated(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            registry = ManifestRegistry(Path(temporary))
            digest = hashlib.sha256(b"same bytes").hexdigest()
            first = registry.register(_record(sha256=digest))
            second = registry.register(
                _record(
                    source_id="another-source",
                    url="https://other.example/asset",
                    sha256=digest,
                )
            )
            self.assertTrue(first.inserted)
            self.assertFalse(second.inserted)
            self.assertEqual(second.duplicate_of, first.record.asset_id)
            self.assertEqual(registry.validate().rows, 1)

    def test_conflicting_same_source_url_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            registry = ManifestRegistry(Path(temporary))
            registry.register(_record())
            with self.assertRaises(ManifestError):
                registry.register(
                    _record(
                        url="https://example.org/asset-a",
                        sha256=hashlib.sha256(b"different").hexdigest(),
                    )
                )

    def test_url_hash_time_and_path_constraints_are_enforced(self) -> None:
        with self.assertRaises(ManifestError):
            _record(url="ftp://example.org/asset")
        with self.assertRaises(ManifestError):
            _record(url="https://user:pass@example.org/asset")
        with self.assertRaises(ManifestError):
            _record(sha256="not-a-hash")
        with self.assertRaises(ManifestError):
            _record(retrieved_at="2024-01-01")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.assertRaises(ManifestPathError):
                ManifestRegistry(root, root.parent / "outside.parquet")

    def test_cli_validates_repository_manifest(self) -> None:
        output_path = Path(__file__).resolve().parents[1] / "registry" / "SOURCE_MANIFEST.parquet"
        original = output_path.read_bytes() if output_path.exists() else None
        registry = ManifestRegistry(Path(__file__).resolve().parents[1])
        registry.write([])
        try:
            self.assertEqual(main(["source", "manifest", "validate"]), 0)
        finally:
            if original is None:
                output_path.unlink(missing_ok=True)
            else:
                output_path.write_bytes(original)


if __name__ == "__main__":
    unittest.main()
