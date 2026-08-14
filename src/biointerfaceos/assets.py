"""Content-addressed local asset store with provenance and atomic promotion."""

from __future__ import annotations

import hashlib
import os
import tempfile
import uuid
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from biointerfaceos.manifest import ManifestRegistry, SourceRecord

CAS_ROOT = Path("data/cas/sha256")
QUARANTINE_ROOT = Path("data/quarantine")
INDEX_PATH = Path("registry/ASSET_INDEX.parquet")
INDEX_FIELDS = (
    "asset_id",
    "source_id",
    "url",
    "sha256",
    "size_bytes",
    "relative_path",
    "stored_at",
)
INDEX_SCHEMA = pa.schema(
    [
        pa.field("asset_id", pa.string(), nullable=False),
        pa.field("source_id", pa.string(), nullable=False),
        pa.field("url", pa.string(), nullable=False),
        pa.field("sha256", pa.string(), nullable=False),
        pa.field("size_bytes", pa.int64(), nullable=False),
        pa.field("relative_path", pa.string(), nullable=False),
        pa.field("stored_at", pa.string(), nullable=False),
    ]
)


class AssetStoreError(ValueError):
    """Base error for asset storage and verification failures."""


class AssetPathError(AssetStoreError):
    """Raised when a path leaves the repository or CAS namespace."""


class AssetHashMismatch(AssetStoreError):
    """Raised when staged bytes do not match the manifest SHA-256."""


class AssetIntegrityError(AssetStoreError):
    """Raised when a promoted blob or provenance index is inconsistent."""


@dataclass(frozen=True)
class AssetReference:
    """One provenance reference to a content-addressed blob."""

    asset_id: str
    source_id: str
    url: str
    sha256: str
    size_bytes: int
    relative_path: str
    stored_at: str

    def to_mapping(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AssetVerification:
    """Verification totals for the CAS and its index."""

    references: int
    unique_blobs: int
    bytes: int

    @property
    def valid(self) -> bool:
        return True


def _contained(root: Path, candidate: Path) -> Path:
    repository = root.resolve(strict=True)
    resolved = candidate.resolve(strict=False)
    if resolved != repository and repository not in resolved.parents:
        raise AssetPathError(f"path escapes repository: {candidate}")
    if "locked_test" in resolved.parts:
        raise AssetPathError("locked-test paths are forbidden")
    return resolved


def _sha256_file(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


class AssetStore:
    """Atomic SHA-256 content store with a fixed Parquet provenance index."""

    def __init__(
        self,
        root: Path,
        *,
        cas_root: Path | str = CAS_ROOT,
        quarantine_root: Path | str = QUARANTINE_ROOT,
        index_path: Path | str = INDEX_PATH,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.cas_root = _contained(
            self.root,
            (Path(cas_root) if Path(cas_root).is_absolute() else self.root / cas_root),
        )
        self.quarantine_root = _contained(
            self.root,
            (Path(quarantine_root) if Path(quarantine_root).is_absolute() else self.root / quarantine_root),
        )
        self.index_path = _contained(
            self.root,
            (Path(index_path) if Path(index_path).is_absolute() else self.root / index_path),
        )
        if self.cas_root == self.root or self.quarantine_root == self.root:
            raise AssetPathError("asset roots cannot be repository root")

    @staticmethod
    def _validate_digest(value: str) -> str:
        if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
            raise AssetStoreError("sha256 must be lowercase hexadecimal with 64 characters")
        return value

    def _blob_path(self, digest: str) -> Path:
        normalized = self._validate_digest(digest)
        path = self.cas_root / normalized[:2] / normalized[2:]
        resolved = _contained(self.root, path)
        if self.cas_root not in resolved.parents:
            raise AssetPathError("blob path escapes CAS root")
        return resolved

    def _staging_dir(self) -> Path:
        path = self.cas_root / ".staging"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _quarantine(self, staged: Path, digest: str, suffix: str) -> Path:
        self.quarantine_root.mkdir(parents=True, exist_ok=True)
        target = self.quarantine_root / f"{digest}.{suffix}.{uuid.uuid4().hex}.part"
        os.replace(staged, target)
        return target

    def _index(self) -> tuple[AssetReference, ...]:
        if not self.index_path.exists():
            return ()
        try:
            table = pq.read_table(self.index_path)
        except Exception as exc:
            raise AssetIntegrityError(f"cannot read asset index: {exc}") from exc
        if tuple(table.column_names) != INDEX_FIELDS:
            raise AssetIntegrityError("asset index columns mismatch")
        references = tuple(AssetReference(**row) for row in table.to_pylist())
        seen: set[tuple[str, str]] = set()
        for reference in references:
            self._validate_digest(reference.sha256)
            key = (reference.asset_id, reference.sha256)
            if key in seen:
                raise AssetIntegrityError(f"duplicate asset reference: {key}")
            seen.add(key)
        return references

    def _write_index(self, references: Sequence[AssetReference]) -> None:
        normalized = [reference.to_mapping() for reference in references]
        table = pa.Table.from_pylist(normalized, schema=INDEX_SCHEMA)
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_name: str | None = None
        try:
            descriptor, temporary_name = tempfile.mkstemp(
                prefix=f".{self.index_path.name}.",
                suffix=".tmp",
                dir=self.index_path.parent,
            )
            os.close(descriptor)
            pq.write_table(table, temporary_name, compression="zstd")
            os.replace(temporary_name, self.index_path)
            temporary_name = None
        except Exception as exc:
            raise AssetStoreError(f"cannot write asset index: {exc}") from exc
        finally:
            if temporary_name is not None:
                Path(temporary_name).unlink(missing_ok=True)

    def initialize(self) -> None:
        """Create empty CAS namespaces and a valid empty index."""
        self.cas_root.mkdir(parents=True, exist_ok=True)
        self.quarantine_root.mkdir(parents=True, exist_ok=True)
        if not self.index_path.exists():
            self._write_index(())

    def _require_manifest_record(self, record: SourceRecord) -> None:
        if record.status != "admitted" or record.sha256 is None:
            raise AssetStoreError("only admitted records with SHA-256 may enter CAS")
        manifest_records = ManifestRegistry(self.root).records()
        by_asset = {item.asset_id: item for item in manifest_records}
        linked = by_asset.get(record.asset_id)
        if linked is None or linked.sha256 != record.sha256 or linked.status != "admitted":
            raise AssetStoreError("asset provenance is absent or does not match source manifest")

    def _commit_staged(self, staged: Path, record: SourceRecord) -> AssetReference:
        self._require_manifest_record(record)
        assert record.sha256 is not None
        actual, size = _sha256_file(staged)
        if actual != record.sha256 or (record.size_bytes is not None and size != record.size_bytes):
            quarantine = self._quarantine(staged, actual, "hash-mismatch")
            raise AssetHashMismatch(f"staged bytes do not match {record.sha256}; preserved at {quarantine}")
        target = self._blob_path(actual)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            existing, existing_size = _sha256_file(target)
            if existing != actual or existing_size != size:
                quarantine = self._quarantine(staged, actual, "cas-conflict")
                raise AssetIntegrityError(f"CAS path is corrupt; staged bytes preserved at {quarantine}")
            staged.unlink(missing_ok=True)
        else:
            os.replace(staged, target)
        relative_path = target.relative_to(self.root).as_posix()
        references = list(self._index())
        for reference in references:
            if reference.asset_id == record.asset_id and reference.sha256 == actual:
                return reference
        reference = AssetReference(
            asset_id=record.asset_id,
            source_id=record.source_id,
            url=record.url,
            sha256=actual,
            size_bytes=size,
            relative_path=relative_path,
            stored_at=datetime.now(UTC).isoformat(),
        )
        references.append(reference)
        self._write_index(references)
        return reference

    def put_bytes(self, data: bytes, record: SourceRecord) -> AssetReference:
        """Stage bytes, verify them, and atomically promote one asset."""
        self.initialize()
        staging = self._staging_dir()
        descriptor, name = tempfile.mkstemp(prefix=".asset.", suffix=".part", dir=staging)
        staged = Path(name)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
        except Exception:
            staged.unlink(missing_ok=True)
            raise
        return self._commit_staged(staged, record)

    def put_file(self, source: Path, record: SourceRecord) -> AssetReference:
        """Copy a repository-contained file into CAS after provenance/hash checks."""
        source_path = _contained(self.root, source if source.is_absolute() else self.root / source)
        if not source_path.is_file():
            raise AssetStoreError(f"source file is not a regular file: {source}")
        self.initialize()
        staging = self._staging_dir()
        descriptor, name = tempfile.mkstemp(prefix=".asset.", suffix=".part", dir=staging)
        staged = Path(name)
        try:
            with source_path.open("rb") as origin, os.fdopen(descriptor, "wb") as target:
                for chunk in iter(lambda: origin.read(1024 * 1024), b""):
                    target.write(chunk)
                target.flush()
                os.fsync(target.fileno())
        except Exception:
            staged.unlink(missing_ok=True)
            raise
        return self._commit_staged(staged, record)

    def verify(self) -> AssetVerification:
        """Verify index rows, CAS hashes, and source-manifest provenance."""
        references = self._index()
        manifest = {record.asset_id: record for record in ManifestRegistry(self.root).records()}
        physical_paths: set[Path] = set()
        total_bytes = 0
        for reference in references:
            record = manifest.get(reference.asset_id)
            if record is None or record.sha256 != reference.sha256 or record.status != "admitted":
                raise AssetIntegrityError(f"missing or mismatched provenance: {reference.asset_id}")
            path = _contained(self.root, self.root / reference.relative_path)
            if path != self._blob_path(reference.sha256):
                raise AssetIntegrityError(f"non-canonical blob path: {reference.relative_path}")
            if not path.is_file():
                raise AssetIntegrityError(f"missing CAS blob: {path}")
            actual, size = _sha256_file(path)
            if actual != reference.sha256 or size != reference.size_bytes:
                raise AssetIntegrityError(f"CAS hash mismatch: {path}")
            physical_paths.add(path)
            total_bytes += size
        if self.cas_root.exists():
            for path in self.cas_root.rglob("*"):
                if not path.is_file() or ".staging" in path.parts:
                    continue
                if path.resolve() not in physical_paths:
                    raise AssetIntegrityError(f"orphan CAS blob: {path}")
        return AssetVerification(
            references=len(references),
            unique_blobs=len(physical_paths),
            bytes=total_bytes,
        )
