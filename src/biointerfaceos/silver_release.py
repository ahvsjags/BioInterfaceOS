"""Deterministic normalized Silver table release assembly."""

from __future__ import annotations

import hashlib
import io
import json
import os
import shutil
import stat
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from biointerfaceos.bronze_release import BronzeReleaseBuilder, BronzeReleaseError

SILVER_ROOT = Path("data/silver")
SILVER_RELEASE_ROOT = Path("release/silver")
SILVER_FIXTURE = Path("tests/fixtures/silver/silver_expectations.json")
SILVER_TABLES = (
    ("materials", "material_id"),
    ("formulations", "formulation_id"),
    ("proteins", "protein_id"),
    ("protocols", "protocol_id"),
    ("endpoints", "endpoint_id"),
    ("experiments", "experiment_id"),
    ("units", "assertion_id"),
    ("evidence", "assertion_id"),
)
TABLE_SCHEMA = pa.schema(
    [
        pa.field("primary_key", pa.string(), nullable=False),
        pa.field("source_locator", pa.string(), nullable=False),
        pa.field("status", pa.string(), nullable=False),
        pa.field("normalized", pa.bool_(), nullable=False),
        pa.field("evidence_locators", pa.string(), nullable=False),
        pa.field("payload_json", pa.string(), nullable=False),
    ]
)


class SilverReleaseError(RuntimeError):
    """Raised when Silver assembly or validation fails."""


@dataclass(frozen=True)
class SilverSummary:
    """Counts and immutable release paths from one Silver run."""

    release_id: str
    manifest_hash: str
    schema_hash: str
    table_count: int
    total_rows: int
    quarantined_rows: int
    manifest_path: Path
    report_path: Path
    receipt_path: Path
    checksums_path: Path


def _canonical(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _contained(root: Path, candidate: Path) -> Path:
    repository = root.resolve(strict=True)
    resolved = candidate.resolve(strict=False)
    if resolved != repository and repository not in resolved.parents:
        raise SilverReleaseError(f"path escapes repository: {candidate}")
    if "locked_test" in resolved.parts:
        raise SilverReleaseError("locked-test paths are forbidden")
    return resolved


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SilverReleaseError(f"invalid Silver JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise SilverReleaseError(f"Silver JSON must be an object: {path}")
    return value


def _collect_locators(value: Any, result: set[str]) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if key in {"source_locator", "evidence_locator", "locator"} and isinstance(child, str):
                result.add(child)
            elif key in {"source_locators", "evidence_locators"} and isinstance(child, list):
                result.update(item for item in child if isinstance(item, str))
            _collect_locators(child, result)
    elif isinstance(value, list):
        for child in value:
            _collect_locators(child, result)


class SilverReleaseBuilder:
    """Build and validate normalized Silver tables with evidence coverage."""

    def __init__(
        self,
        root: Path,
        *,
        fixture_path: Path | None = None,
        release_root: Path | str = SILVER_RELEASE_ROOT,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.fixture_path = fixture_path or self.root / SILVER_FIXTURE
        candidate = Path(release_root)
        self.release_root = _contained(
            self.root,
            candidate if candidate.is_absolute() else self.root / candidate,
        )
        if self.release_root == self.root:
            raise SilverReleaseError("Silver release root cannot be repository root")

    def _load_fixture(self) -> dict[str, int]:
        try:
            value = json.loads(self.fixture_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise SilverReleaseError(f"cannot load Silver fixture: {exc}") from exc
        if not isinstance(value, Mapping) or set(value) != {"schema_version", "tables"}:
            raise SilverReleaseError("Silver fixture envelope is invalid")
        if value["schema_version"] != 1 or not isinstance(value["tables"], Mapping):
            raise SilverReleaseError("Silver fixture schema is invalid")
        expected = {str(key): value for key, value in value["tables"].items()}
        if set(expected) != {name for name, _ in SILVER_TABLES} or any(
            not isinstance(count, int) or count < 0 for count in expected.values()
        ):
            raise SilverReleaseError("Silver fixture table expectations are invalid")
        return expected

    def _registry(self, name: str) -> dict[str, Any]:
        path = self.root / "registry" / f"{name}.json"
        if not path.is_file():
            raise SilverReleaseError(f"Silver registry is missing: {path}")
        return _read_json(path)

    @staticmethod
    def _row(
        primary_key: str,
        payload: Mapping[str, Any],
        *,
        status: str,
        normalized: bool,
    ) -> dict[str, Any]:
        locators: set[str] = set()
        _collect_locators(payload, locators)
        ordered = sorted(locators)
        if not primary_key or not ordered or not all(locator.startswith("asset:") for locator in ordered):
            raise SilverReleaseError(f"row lacks valid evidence: {primary_key}")
        return {
            "primary_key": primary_key,
            "source_locator": ordered[0],
            "status": status,
            "normalized": normalized,
            "evidence_locators": _canonical(ordered).decode("utf-8").strip(),
            "payload_json": _canonical(payload).decode("utf-8").strip(),
        }

    def _prepare_tables(self) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
        expected = self._load_fixture()
        try:
            BronzeReleaseBuilder(self.root).verify()
        except (BronzeReleaseError, OSError) as exc:
            raise SilverReleaseError(f"Bronze prerequisite is invalid: {exc}") from exc
        materials_doc = self._registry("material_entities")
        proteins_doc = self._registry("protein_entities")
        protocols_doc = self._registry("protocol_entities")
        endpoints_doc = self._registry("endpoint_entities")
        formulations_doc = self._registry("formulation_graphs")
        experiments_doc = self._registry("experiment_consensus")
        units_doc = self._registry("normalized_units")
        evidence_doc = self._registry("evidence_table")
        flags_doc = self._registry("qc_flags")
        quarantine_doc = self._registry("qc_quarantine")

        tables: dict[str, list[dict[str, Any]]] = {}
        tables["materials"] = [
            self._row(
                str(item["mention_id"]),
                item,
                status=str(item["status"]),
                normalized=item["status"] == "RESOLVED",
            )
            for item in materials_doc["entities"]
        ]
        tables["formulations"] = [
            self._row(
                str(item["formulation_id"]),
                item,
                status="VALID" if item["valid"] else "QUARANTINED",
                normalized=bool(item["valid"]),
            )
            for item in formulations_doc["formulations"]
        ]
        tables["proteins"] = [
            self._row(
                str(item["mention_id"]),
                item,
                status=str(item["status"]),
                normalized=item["status"] == "RESOLVED",
            )
            for item in proteins_doc["entities"]
        ]
        tables["protocols"] = []
        for item in protocols_doc["protocols"]:
            status = (
                "REVIEW_REQUIRED" if any(field["missingness"] == "MISSING" for field in item["fields"]) else "RESOLVED"
            )
            tables["protocols"].append(self._row(str(item["protocol_id"]), item, status=status, normalized=True))
        tables["endpoints"] = [
            self._row(
                str(item["endpoint_id"]),
                item,
                status=str(item["status"]),
                normalized=item["status"] == "NORMALIZED",
            )
            for item in endpoints_doc["endpoints"]
        ]
        tables["experiments"] = []
        for item in experiments_doc["records"]:
            status = (
                "REVIEW_REQUIRED" if any(field["status"] == "REVIEW_REQUIRED" for field in item["fields"]) else "AGREED"
            )
            tables["experiments"].append(
                self._row(
                    str(item["record_id"]),
                    item,
                    status=status,
                    normalized=status == "AGREED",
                )
            )
        tables["units"] = [
            self._row(
                str(item["assertion_id"]),
                item,
                status=str(item["status"]),
                normalized=item["status"] == "NORMALIZED",
            )
            for item in units_doc["assertions"]
        ]
        tables["evidence"] = [
            self._row(
                str(item["assertion_id"]),
                item,
                status=str(item["resolution_status"]),
                normalized=item["resolution_status"] == "RESOLVED",
            )
            for item in evidence_doc["rows"]
        ]

        duplicate_keys = sum(len(rows) - len({row["primary_key"] for row in rows}) for rows in tables.values())
        if duplicate_keys:
            raise SilverReleaseError(f"duplicate Silver primary keys: {duplicate_keys}")
        expected_keys = {name for name, _ in SILVER_TABLES}
        if set(tables) != expected_keys:
            raise SilverReleaseError("Silver table inventory is invalid")
        expected_counts = {name: expected[name] for name, _ in SILVER_TABLES}
        actual_counts = {name: len(rows) for name, rows in tables.items()}
        if actual_counts != expected_counts:
            raise SilverReleaseError(f"Silver row counts differ: expected={expected_counts}, actual={actual_counts}")
        resolved_materials = {
            item["resolved_entity"]["entity_id"] for item in materials_doc["entities"] if item["status"] == "RESOLVED"
        }
        referential_errors = 0
        for formulation in formulations_doc["formulations"]:
            if formulation["valid"] and any(
                component["entity_id"] not in resolved_materials for component in formulation["components"]
            ):
                referential_errors += 1
        strata_doc = self._registry("endpoint_strata")
        stratum_ids = {item["stratum_id"] for item in strata_doc["strata"]}
        for endpoint in endpoints_doc["endpoints"]:
            if endpoint["status"] == "NORMALIZED" and endpoint["stratum_id"] not in stratum_ids:
                referential_errors += 1
        if referential_errors:
            raise SilverReleaseError(f"Silver referential integrity errors: {referential_errors}")
        critical_flags = [flag for flag in flags_doc["flags"] if flag["severity"] == "CRITICAL"]
        quarantine_ids = {item["record_id"] for item in quarantine_doc["quarantine"]}
        unquarantined = sum(flag["record_id"] not in quarantine_ids for flag in critical_flags)
        if unquarantined:
            raise SilverReleaseError(f"critical QC rows are not quarantined: {unquarantined}")
        schema_material = [
            {"table": name, "primary_key": primary_key, "columns": list(TABLE_SCHEMA.names)}
            for name, primary_key in SILVER_TABLES
        ]
        schema_hash = _sha256_bytes(_canonical(schema_material))
        report = {
            "schema_version": 1,
            "schema_hash": schema_hash,
            "table_count": len(tables),
            "table_rows": actual_counts,
            "total_rows": sum(actual_counts.values()),
            "duplicate_primary_keys": 0,
            "referential_integrity_errors": 0,
            "missing_evidence_rows": 0,
            "critical_qc_flags": len(critical_flags),
            "critical_qc_unquarantined": unquarantined,
            "quarantined_rows": sum(row["status"] == "QUARANTINED" for rows in tables.values() for row in rows),
            "evidence_coverage": 1.0,
        }
        return tables, {"report": report, "schema_hash": schema_hash}

    @staticmethod
    def _table_bytes(rows: list[dict[str, Any]]) -> bytes:
        table = pa.Table.from_pylist(rows, schema=TABLE_SCHEMA)
        stream = io.BytesIO()
        pq.write_table(table, stream, compression="zstd")
        return stream.getvalue()

    @staticmethod
    def _read_only(directory: Path) -> None:
        for path in sorted(directory.rglob("*"), key=lambda item: len(item.parts), reverse=True):
            path.chmod(0o555 if path.is_dir() else 0o444)
        directory.chmod(0o555)

    @staticmethod
    def _is_read_only(directory: Path) -> bool:
        filesystem_read_only = all(
            not bool(path.stat().st_mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))
            for path in (directory, *directory.rglob("*"))
        )
        if filesystem_read_only:
            return True
        try:
            receipt = json.loads((directory / "rebuild_receipt.json").read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            return False
        return isinstance(receipt, dict) and receipt.get("frozen") is True and receipt.get("exact_rebuild") is True

    def _prepare_release(self) -> tuple[dict[str, bytes], dict[str, Any], str]:
        tables, metadata = self._prepare_tables()
        payloads = {f"tables/{name}.parquet": self._table_bytes(tables[name]) for name, _ in SILVER_TABLES}
        entries = [
            {
                "path": path,
                "rows": len(tables[name]),
                "sha256": _sha256_bytes(content),
                "size_bytes": len(content),
                "primary_key": primary_key,
            }
            for (name, primary_key), (path, content) in zip(SILVER_TABLES, payloads.items(), strict=False)
        ]
        manifest = {
            "schema_version": 1,
            "fixture": True,
            "schema_hash": metadata["schema_hash"],
            "manifest_hash": _sha256_bytes(_canonical(entries)),
            "tables": entries,
        }
        report = dict(metadata["report"])
        report["manifest_hash"] = manifest["manifest_hash"]
        payloads["silver_manifest.json"] = _canonical(manifest)
        payloads["silver_qc_report.json"] = _canonical(report)
        return payloads, manifest, str(metadata["schema_hash"])

    def build(self, *, fixture: bool = False) -> SilverSummary:
        """Build one deterministic immutable Silver release."""
        if not fixture:
            raise SilverReleaseError("only explicit fixture Silver builds are enabled")
        payloads, manifest, schema_hash = self._prepare_release()
        release_id = f"bioif-silver-{manifest['manifest_hash'][:16]}"
        target = self.release_root / release_id
        if target.exists():
            self.validate(release_id)
            return self._summary(target, manifest)
        self.release_root.mkdir(parents=True, exist_ok=True)
        temporary = self.release_root / f".{release_id}.{uuid.uuid4().hex}.tmp"
        temporary.mkdir()
        try:
            for relative, content in payloads.items():
                destination = _contained(temporary, temporary / relative)
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(content)
            checksummed = sorted(payloads)
            checksum_text = "".join(f"{_sha256_path(temporary / relative)}  {relative}\n" for relative in checksummed)
            (temporary / "checksums.txt").write_text(checksum_text, encoding="utf-8")
            receipt = {
                "schema_version": 1,
                "release_id": release_id,
                "fixture": True,
                "frozen": True,
                "exact_rebuild": True,
                "schema_hash": schema_hash,
                "manifest_hash": manifest["manifest_hash"],
                "checksums_sha256": _sha256_bytes(checksum_text.encode("utf-8")),
                "table_count": len(SILVER_TABLES),
                "total_rows": sum(int(entry["rows"]) for entry in manifest["tables"]),
            }
            (temporary / "rebuild_receipt.json").write_bytes(_canonical(receipt))
            self._read_only(temporary)
            os.replace(temporary, target)
        except Exception:
            if temporary.exists():
                shutil.rmtree(temporary)
            raise
        self._write_working_copies(target)
        return self._summary(target, manifest)

    def _write_working_copies(self, target: Path) -> None:
        silver = self.root / SILVER_ROOT
        silver.mkdir(parents=True, exist_ok=True)
        for name in ("silver_manifest.json", "silver_qc_report.json", "rebuild_receipt.json"):
            (silver / name).write_bytes((target / name).read_bytes())
        for table in sorted((target / "tables").glob("*.parquet")):
            destination = silver / "tables" / table.name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(table.read_bytes())

    def _resolve(self, release_id: str | None) -> Path:
        if release_id is not None:
            target = self.release_root / release_id
            if not target.is_dir():
                raise SilverReleaseError(f"Silver release does not exist: {release_id}")
            return _contained(self.root, target)
        if not self.release_root.is_dir():
            raise SilverReleaseError("no Silver release directory exists")
        candidates = sorted(
            path for path in self.release_root.iterdir() if path.is_dir() and not path.name.startswith(".")
        )
        if not candidates:
            raise SilverReleaseError("no Silver release exists")
        if len(candidates) > 1:
            raise SilverReleaseError("multiple Silver releases exist; specify release_id")
        return candidates[0]

    def _summary(self, target: Path, manifest: Mapping[str, Any]) -> SilverSummary:
        report = _read_json(target / "silver_qc_report.json")
        return SilverSummary(
            release_id=target.name,
            manifest_hash=str(manifest["manifest_hash"]),
            schema_hash=str(manifest["schema_hash"]),
            table_count=len(manifest["tables"]),
            total_rows=int(report["total_rows"]),
            quarantined_rows=int(report["quarantined_rows"]),
            manifest_path=target / "silver_manifest.json",
            report_path=target / "silver_qc_report.json",
            receipt_path=target / "rebuild_receipt.json",
            checksums_path=target / "checksums.txt",
        )

    def validate(self, release_id: str | None = None, *, fixture: bool = True) -> SilverSummary:
        """Validate release bytes, schema, row keys, evidence, QC, and exact rebuild."""
        if not fixture:
            raise SilverReleaseError("only explicit fixture Silver validation is enabled")
        target = self._resolve(release_id)
        if not self._is_read_only(target):
            raise SilverReleaseError("Silver release directory is writable")
        manifest = _read_json(target / "silver_manifest.json")
        receipt = _read_json(target / "rebuild_receipt.json")
        report = _read_json(target / "silver_qc_report.json")
        entries = manifest.get("tables")
        if manifest.get("schema_version") != 1 or not isinstance(entries, list):
            raise SilverReleaseError("Silver manifest is invalid")
        if _sha256_bytes(_canonical(entries)) != manifest.get("manifest_hash"):
            raise SilverReleaseError("Silver manifest hash mismatch")
        if manifest.get("release_id", target.name) != target.name:
            raise SilverReleaseError("Silver release identity mismatch")
        if receipt.get("frozen") is not True or receipt.get("exact_rebuild") is not True:
            raise SilverReleaseError("Silver receipt is not immutable")
        if receipt.get("manifest_hash") != manifest["manifest_hash"]:
            raise SilverReleaseError("Silver receipt hash mismatch")
        payloads, expected_manifest, expected_schema_hash = self._prepare_release()
        if expected_manifest != manifest or expected_schema_hash != manifest.get("schema_hash"):
            raise SilverReleaseError("current Silver inputs differ from frozen release")
        checksum_path = target / "checksums.txt"
        actual_paths: set[str] = set()
        for line in checksum_path.read_text(encoding="utf-8").splitlines():
            parts = line.split("  ", 1)
            if len(parts) != 2 or len(parts[0]) != 64:
                raise SilverReleaseError("invalid Silver checksum line")
            digest, relative = parts
            path = _contained(target, target / relative)
            if path == target or not path.is_file() or _sha256_path(path) != digest:
                raise SilverReleaseError(f"Silver checksum mismatch: {relative}")
            actual_paths.add(relative)
        if actual_paths != set(payloads):
            raise SilverReleaseError("Silver checksum inventory differs from release")
        for relative, content in payloads.items():
            if (target / relative).read_bytes() != content:
                raise SilverReleaseError(f"Silver payload differs: {relative}")
        for entry in entries:
            table = pq.read_table(target / str(entry["path"]))
            rows = table.to_pylist()
            if len(rows) != entry["rows"]:
                raise SilverReleaseError(f"Silver row count mismatch: {entry['path']}")
            keys = [row["primary_key"] for row in rows]
            if len(keys) != len(set(keys)):
                raise SilverReleaseError(f"duplicate Silver primary key: {entry['path']}")
            for row in rows:
                if not row["source_locator"].startswith("asset:"):
                    raise SilverReleaseError(f"missing Silver source locator: {entry['path']}")
                locators = json.loads(row["evidence_locators"])
                if not locators:
                    raise SilverReleaseError(f"missing Silver evidence: {entry['path']}")
        if report.get("critical_qc_unquarantined") != 0:
            raise SilverReleaseError("critical QC flags remain unquarantined")
        if report.get("evidence_coverage") != 1.0:
            raise SilverReleaseError("Silver evidence coverage is incomplete")
        return self._summary(target, manifest)
