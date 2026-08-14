"""Strict Parquet source and asset manifest registry."""

from __future__ import annotations

import hashlib
import os
import re
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import pyarrow as pa
import pyarrow.parquet as pq

MANIFEST_PATH = Path("registry/SOURCE_MANIFEST.parquet")
MANIFEST_FIELDS = (
    "asset_id",
    "source_id",
    "source_name",
    "url",
    "access",
    "status",
    "accession",
    "publication_date",
    "retrieved_at",
    "sha256",
    "size_bytes",
    "license",
    "redistribution",
    "download_status",
    "duplicate_of",
    "rejection_reason",
)
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_ALLOWED_ACCESS = frozenset({"admitted", "rejected"})
_ALLOWED_STATUS = frozenset({"admitted", "rejected", "quarantined"})
_ALLOWED_REDISTRIBUTION = frozenset({"allowed", "noncommercial", "manifest_only"})
_ALLOWED_DOWNLOAD_STATUS = frozenset({"pending", "downloaded", "failed", "rejected", "quarantined"})

MANIFEST_SCHEMA = pa.schema(
    [
        pa.field("asset_id", pa.string(), nullable=False),
        pa.field("source_id", pa.string(), nullable=False),
        pa.field("source_name", pa.string(), nullable=False),
        pa.field("url", pa.string(), nullable=False),
        pa.field("access", pa.string(), nullable=False),
        pa.field("status", pa.string(), nullable=False),
        pa.field("accession", pa.string(), nullable=True),
        pa.field("publication_date", pa.string(), nullable=True),
        pa.field("retrieved_at", pa.string(), nullable=False),
        pa.field("sha256", pa.string(), nullable=True),
        pa.field("size_bytes", pa.int64(), nullable=True),
        pa.field("license", pa.string(), nullable=True),
        pa.field("redistribution", pa.string(), nullable=True),
        pa.field("download_status", pa.string(), nullable=False),
        pa.field("duplicate_of", pa.string(), nullable=True),
        pa.field("rejection_reason", pa.string(), nullable=True),
    ]
)


class ManifestError(ValueError):
    """Base error for manifest validation and storage."""


class ManifestPathError(ManifestError):
    """Raised when a manifest path escapes the repository."""


class ManifestConflictError(ManifestError):
    """Raised when a source identity conflicts with an existing record."""


@dataclass(frozen=True)
class SourceRecord:
    """One validated source asset record."""

    asset_id: str
    source_id: str
    source_name: str
    url: str
    access: str
    status: str
    accession: str | None
    publication_date: str | None
    retrieved_at: str
    sha256: str | None
    size_bytes: int | None
    license: str | None
    redistribution: str | None
    download_status: str
    duplicate_of: str | None
    rejection_reason: str | None

    def __post_init__(self) -> None:
        for field_name in ("asset_id", "source_id", "source_name", "url", "retrieved_at"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ManifestError(f"{field_name} must be a non-empty string")
        parsed = urlsplit(self.url)
        if parsed.scheme not in {"http", "https"} or parsed.hostname is None:
            raise ManifestError("url must be an absolute HTTP(S) URL")
        if parsed.username is not None or parsed.password is not None:
            raise ManifestError("url credentials are forbidden")
        if parsed.fragment:
            raise ManifestError("url fragments are not canonical")
        if self.access not in _ALLOWED_ACCESS:
            raise ManifestError(f"invalid access: {self.access}")
        if self.status not in _ALLOWED_STATUS:
            raise ManifestError(f"invalid status: {self.status}")
        if self.download_status not in _ALLOWED_DOWNLOAD_STATUS:
            raise ManifestError(f"invalid download_status: {self.download_status}")
        if self.status == "admitted" and self.access != "admitted":
            raise ManifestError("admitted status requires admitted access")
        if self.status == "admitted" and (not self.license or self.redistribution not in _ALLOWED_REDISTRIBUTION):
            raise ManifestError("admitted records require explicit license and redistribution")
        if self.access == "rejected" and self.status == "admitted":
            raise ManifestError("rejected access cannot be admitted")
        if self.redistribution is not None and self.redistribution not in _ALLOWED_REDISTRIBUTION:
            raise ManifestError(f"invalid redistribution: {self.redistribution}")
        if self.sha256 is not None and not _SHA256.fullmatch(self.sha256):
            raise ManifestError("sha256 must be lowercase hexadecimal with 64 characters")
        if self.size_bytes is not None and (
            isinstance(self.size_bytes, bool) or not isinstance(self.size_bytes, int) or self.size_bytes < 0
        ):
            raise ManifestError("size_bytes must be a non-negative integer or null")
        try:
            retrieved = datetime.fromisoformat(self.retrieved_at.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ManifestError("retrieved_at must be ISO-8601") from exc
        if retrieved.tzinfo is None:
            raise ManifestError("retrieved_at must include a timezone")
        if self.publication_date is not None:
            try:
                date.fromisoformat(self.publication_date)
            except ValueError as exc:
                raise ManifestError("publication_date must be YYYY-MM-DD") from exc
        expected = self.compute_asset_id(self.source_id, self.url, self.sha256)
        if self.asset_id != expected:
            raise ManifestError("asset_id does not match source_id, url, and sha256")
        if self.duplicate_of is not None and not self.duplicate_of.strip():
            raise ManifestError("duplicate_of cannot be empty")
        if self.status in {"rejected", "quarantined"} and not self.rejection_reason:
            raise ManifestError("rejected or quarantined records require rejection_reason")

    @staticmethod
    def compute_asset_id(source_id: str, url: str, sha256: str | None) -> str:
        """Derive the stable content/provenance identity."""
        material = "\x1f".join((source_id, url, sha256 or ""))
        return hashlib.sha256(material.encode("utf-8")).hexdigest()

    @classmethod
    def create(
        cls,
        *,
        source_id: str,
        source_name: str,
        url: str,
        access: str,
        status: str,
        retrieved_at: str,
        accession: str | None = None,
        publication_date: str | None = None,
        sha256: str | None = None,
        size_bytes: int | None = None,
        license: str | None = None,
        redistribution: str | None = None,
        download_status: str = "pending",
        duplicate_of: str | None = None,
        rejection_reason: str | None = None,
    ) -> SourceRecord:
        """Build a record with its deterministic asset ID."""
        asset_id = cls.compute_asset_id(source_id, url, sha256)
        return cls(
            asset_id=asset_id,
            source_id=source_id,
            source_name=source_name,
            url=url,
            access=access,
            status=status,
            accession=accession,
            publication_date=publication_date,
            retrieved_at=retrieved_at,
            sha256=sha256,
            size_bytes=size_bytes,
            license=license,
            redistribution=redistribution,
            download_status=download_status,
            duplicate_of=duplicate_of,
            rejection_reason=rejection_reason,
        )

    def to_mapping(self) -> dict[str, Any]:
        """Return the fixed manifest column mapping."""
        return asdict(self)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> SourceRecord:
        """Validate one mapping and reject missing or extra columns."""
        if set(value) != set(MANIFEST_FIELDS):
            missing = sorted(set(MANIFEST_FIELDS) - set(value))
            extra = sorted(set(value) - set(MANIFEST_FIELDS))
            raise ManifestError(f"record fields mismatch; missing={missing}, extra={extra}")
        return cls(**{field_name: value[field_name] for field_name in MANIFEST_FIELDS})


@dataclass(frozen=True)
class RegistrationResult:
    """Outcome of an insert attempt."""

    record: SourceRecord
    inserted: bool
    duplicate_of: str | None


@dataclass(frozen=True)
class ManifestSummary:
    """Deterministic manifest validation summary."""

    rows: int
    unique_content_hashes: int
    admitted: int
    rejected: int
    quarantined: int


def _contained(root: Path, candidate: Path) -> Path:
    repository = root.resolve(strict=True)
    resolved = candidate.resolve(strict=False)
    if resolved != repository and repository not in resolved.parents:
        raise ManifestPathError(f"path escapes repository: {candidate}")
    return resolved


class ManifestRegistry:
    """Atomic, fixed-schema Parquet manifest registry."""

    def __init__(self, root: Path, path: Path | str = MANIFEST_PATH) -> None:
        self.root = root.resolve(strict=True)
        candidate = Path(path)
        resolved = _contained(self.root, candidate if candidate.is_absolute() else self.root / candidate)
        if resolved == self.root:
            raise ManifestPathError("manifest path cannot be repository root")
        self.path = resolved

    def _read_table(self) -> Any:
        if not self.path.exists():
            return pa.Table.from_pylist([], schema=MANIFEST_SCHEMA)
        try:
            table = pq.read_table(self.path)
        except Exception as exc:
            raise ManifestError(f"cannot read manifest {self.path}: {exc}") from exc
        if tuple(table.column_names) != MANIFEST_FIELDS:
            raise ManifestError(
                f"manifest columns mismatch: expected {MANIFEST_FIELDS}, got {tuple(table.column_names)}"
            )
        return table

    def records(self) -> tuple[SourceRecord, ...]:
        """Read and validate all manifest rows."""
        rows = self._read_table().to_pylist()
        records = tuple(SourceRecord.from_mapping(row) for row in rows)
        self._check_uniqueness(records)
        return records

    @staticmethod
    def _check_uniqueness(records: Sequence[SourceRecord]) -> None:
        asset_ids: set[str] = set()
        content_hashes: set[str] = set()
        for record in records:
            if record.asset_id in asset_ids:
                raise ManifestError(f"duplicate asset_id: {record.asset_id}")
            asset_ids.add(record.asset_id)
            if record.sha256 is not None:
                if record.sha256 in content_hashes:
                    raise ManifestError(f"duplicate content hash: {record.sha256}")
                content_hashes.add(record.sha256)

    def write(self, records: Sequence[SourceRecord]) -> None:
        """Atomically write a validated fixed-schema Parquet table."""
        normalized = tuple(records)
        self._check_uniqueness(normalized)
        for record in normalized:
            SourceRecord.from_mapping(record.to_mapping())
        self.path.parent.mkdir(parents=True, exist_ok=True)
        table = pa.Table.from_pylist(
            [record.to_mapping() for record in normalized],
            schema=MANIFEST_SCHEMA,
        )
        temporary_name: str | None = None
        try:
            descriptor, temporary_name = tempfile.mkstemp(
                prefix=f".{self.path.name}.",
                suffix=".tmp",
                dir=self.path.parent,
            )
            os.close(descriptor)
            pq.write_table(table, temporary_name, compression="zstd")
            os.replace(temporary_name, self.path)
            temporary_name = None
        except Exception as exc:
            raise ManifestError(f"cannot write manifest {self.path}: {exc}") from exc
        finally:
            if temporary_name is not None:
                Path(temporary_name).unlink(missing_ok=True)

    def register(self, record: SourceRecord) -> RegistrationResult:
        """Insert one record or return the existing row for an identical content hash."""
        SourceRecord.from_mapping(record.to_mapping())
        records = list(self.records())
        if record.sha256 is not None:
            for existing in records:
                if existing.sha256 == record.sha256:
                    return RegistrationResult(existing, False, existing.asset_id)
        for existing in records:
            if existing.asset_id == record.asset_id:
                if existing != record:
                    raise ManifestConflictError(f"asset_id already exists: {record.asset_id}")
                return RegistrationResult(existing, False, existing.asset_id)
            if existing.source_id == record.source_id and existing.url == record.url:
                raise ManifestConflictError("source_id and url already exist with different content")
        records.append(record)
        self.write(records)
        return RegistrationResult(record, True, None)

    def register_mapping(self, value: Mapping[str, Any]) -> RegistrationResult:
        """Validate and register a mapping."""
        return self.register(SourceRecord.from_mapping(value))

    def validate(self) -> ManifestSummary:
        """Validate the Parquet file and return counts."""
        records = self.records()
        hashes = {record.sha256 for record in records if record.sha256 is not None}
        return ManifestSummary(
            rows=len(records),
            unique_content_hashes=len(hashes),
            admitted=sum(record.status == "admitted" for record in records),
            rejected=sum(record.status == "rejected" for record in records),
            quarantined=sum(record.status == "quarantined" for record in records),
        )
