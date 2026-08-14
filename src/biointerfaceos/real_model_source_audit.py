"""Strict source-candidate audit for the R2 real-model target.

The audit records promising public raw-data packages without silently promoting
them to a common prediction target.  In particular, a shared unit (``nm``) is
not evidence that differently named DLS size statistics are interchangeable.
"""

from __future__ import annotations

import hashlib
import io
import json
import stat
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from openpyxl import load_workbook


class RealModelSourceAuditError(RuntimeError):
    """Raised when a T123 source candidate cannot be audited safely."""


def _canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise RealModelSourceAuditError(f"{label} must be an object")
    return value


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RealModelSourceAuditError(f"{label} must be a non-empty string")
    return value.strip()


def _integer(value: Any, label: str, *, minimum: int = 0) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        raise RealModelSourceAuditError(f"{label} must be an integer >= {minimum}")
    return value


@dataclass(frozen=True)
class RealModelSourceAuditSummary:
    """Compact accounting for the source-candidate qualification result."""

    source_count: int
    distinct_measurement_definitions: int
    admissible_target_count: int
    receipt_path: Path


class RealModelSourceAudit:
    """Audit raw files and preserve a non-admission decision for T123."""

    AUDIT_ID = "bioif-r2-real-model-source-candidate-audit-v1.1.0"
    EVALUATED_AT = "2026-08-12T00:00:00+00:00"
    REGISTRY_RELATIVE = "data/empirical/R2_T123_REAL_MODEL_SOURCE_CANDIDATES.json"
    OUTPUT_RELATIVE = "reports/review_round_2/real_model_source_candidates/v1.1.0"
    ALLOWED_LICENSES = frozenset({"CC-BY-4.0", "CC0-1.0", "PDDL-1.0"})
    REQUIRED_REGISTRY_FIELDS = {
        "schema_version",
        "audit_id",
        "evidence_class",
        "allowed_claim_level",
        "sources",
        "excluded_sources",
    }
    REQUIRED_SOURCE_FIELDS = {
        "source_id",
        "study_id",
        "laboratory",
        "affiliation_status",
        "doi",
        "landing_url",
        "license_id",
        "access",
        "biological_system",
        "protocol_id",
        "asset",
        "worksheet",
        "header_cells",
        "declared_measurement_definition_id",
        "declared_measurement_definition",
        "endpoint_family_id",
        "unit",
        "biological_condition_status",
        "observation_granularity",
    }
    REQUIRED_ASSET_FIELDS = {
        "path",
        "download_url",
        "sha256",
        "bytes",
        "content_type",
        "archive_member",
    }
    REQUIRED_HEADER_FIELDS = {"cell", "expected"}

    def __init__(
        self,
        root: Path,
        *,
        registry_path: Path | None = None,
        output_root: Path | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.registry_path = registry_path or self.root / self.REGISTRY_RELATIVE
        self.output_root = output_root or self.root / self.OUTPUT_RELATIVE

    @staticmethod
    def _write(path: Path, value: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(_canonical(value))

    @staticmethod
    def _json(path: Path, label: str) -> dict[str, Any]:
        try:
            return _mapping(json.loads(path.read_text(encoding="utf-8")), label)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise RealModelSourceAuditError(f"cannot parse {label}") from exc

    def _registry(self) -> dict[str, Any]:
        registry = self._json(self.registry_path, "T123 source-candidate registry")
        if set(registry) != self.REQUIRED_REGISTRY_FIELDS or registry.get("schema_version") != 1:
            raise RealModelSourceAuditError("source-candidate registry fields or schema are invalid")
        if registry.get("audit_id") != self.AUDIT_ID:
            raise RealModelSourceAuditError("source-candidate registry identity is invalid")
        if registry.get("evidence_class") != "DEVELOPMENT_OBSERVATION":
            raise RealModelSourceAuditError("source-candidate evidence class is unsafe")
        if registry.get("allowed_claim_level") != "EXPLORATORY":
            raise RealModelSourceAuditError("source-candidate claim level is unsafe")
        if not isinstance(registry["sources"], list) or len(registry["sources"]) < 3:
            raise RealModelSourceAuditError("source-candidate audit requires at least three sources")
        if not isinstance(registry["excluded_sources"], list):
            raise RealModelSourceAuditError("source-candidate exclusions are invalid")
        return registry

    def _workbook_bytes(self, asset: dict[str, Any]) -> tuple[bytes, dict[str, Any]]:
        if set(asset) != self.REQUIRED_ASSET_FIELDS:
            raise RealModelSourceAuditError("source-candidate asset fields are invalid")
        relative = _string(asset.get("path"), "source-candidate asset path")
        path = (self.root / relative).resolve(strict=False)
        if not path.is_relative_to(self.root) or not path.is_file():
            raise RealModelSourceAuditError(f"source-candidate asset is missing: {relative}")
        if any(token in relative.lower() for token in ("fixture", "synthetic", "mock")):
            raise RealModelSourceAuditError("fixture-like material crossed into source candidates")
        expected_hash = _string(asset.get("sha256"), "source-candidate asset SHA-256").lower()
        if len(expected_hash) != 64 or any(char not in "0123456789abcdef" for char in expected_hash):
            raise RealModelSourceAuditError("source-candidate asset checksum is invalid")
        if _sha256(path) != expected_hash:
            raise RealModelSourceAuditError("source-candidate asset checksum differs")
        if path.stat().st_size != _integer(asset.get("bytes"), "source-candidate asset bytes"):
            raise RealModelSourceAuditError("source-candidate asset size differs")
        if not _string(asset.get("download_url"), "source-candidate asset URL").startswith("https://"):
            raise RealModelSourceAuditError("source-candidate asset needs an HTTPS URL")
        member = asset["archive_member"]
        if member is None:
            if asset.get("content_type") != ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"):
                raise RealModelSourceAuditError("direct source-candidate asset must be XLSX")
            return path.read_bytes(), {
                "path": relative,
                "sha256": expected_hash,
                "bytes": path.stat().st_size,
                "archive_member": None,
            }
        if asset.get("content_type") != "application/zip":
            raise RealModelSourceAuditError("archived source-candidate asset must be ZIP")
        member_text = _string(member, "source-candidate archive member")
        try:
            with zipfile.ZipFile(path) as archive:
                names = archive.namelist()
                if names.count(member_text) != 1:
                    raise RealModelSourceAuditError("source-candidate archive member is missing")
                return archive.read(member_text), {
                    "path": relative,
                    "sha256": expected_hash,
                    "bytes": path.stat().st_size,
                    "archive_member": member_text,
                }
        except (OSError, zipfile.BadZipFile) as exc:
            raise RealModelSourceAuditError("cannot read source-candidate ZIP") from exc

    def _admit_sources(self) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        registry = self._registry()
        source_ids: set[str] = set()
        studies: set[str] = set()
        laboratories: set[str] = set()
        admitted: list[dict[str, Any]] = []
        for value in registry["sources"]:
            source = _mapping(value, "source-candidate source")
            if set(source) != self.REQUIRED_SOURCE_FIELDS:
                raise RealModelSourceAuditError("source-candidate source fields are invalid")
            for field in self.REQUIRED_SOURCE_FIELDS - {"asset", "header_cells"}:
                _string(source.get(field), f"source-candidate {field}")
            if source["license_id"] not in self.ALLOWED_LICENSES:
                raise RealModelSourceAuditError("source-candidate licence is not reusable")
            if source["access"] != "ANONYMOUS_PUBLIC":
                raise RealModelSourceAuditError("source-candidate access is restricted")
            if not source["doi"].startswith("10.") or not source["landing_url"].startswith("https://"):
                raise RealModelSourceAuditError("source-candidate DOI or landing URL is invalid")
            source_id = source["source_id"]
            if source_id in source_ids:
                raise RealModelSourceAuditError("source-candidate source ID is duplicated")
            source_ids.add(source_id)
            studies.add(source["study_id"])
            laboratories.add(source["laboratory"])
            workbook_bytes, asset_record = self._workbook_bytes(_mapping(source["asset"], "source-candidate asset"))
            header_cells = source["header_cells"]
            if not isinstance(header_cells, list) or not header_cells:
                raise RealModelSourceAuditError("source-candidate headers are missing")
            workbook: Any | None = None
            try:
                workbook = load_workbook(io.BytesIO(workbook_bytes), data_only=True, read_only=True)
                worksheet = workbook[_string(source["worksheet"], "source-candidate worksheet")]
                verified_headers: list[dict[str, str]] = []
                for header_value in header_cells:
                    header = _mapping(header_value, "source-candidate header")
                    if set(header) != self.REQUIRED_HEADER_FIELDS:
                        raise RealModelSourceAuditError("source-candidate header fields are invalid")
                    cell = _string(header.get("cell"), "source-candidate header cell")
                    expected = _string(header.get("expected"), "source-candidate header expected value")
                    observed = worksheet[cell].value
                    if observed != expected:
                        raise RealModelSourceAuditError(
                            f"source-candidate header differs from source: {source_id}:{cell}"
                        )
                    verified_headers.append({"cell": cell, "expected": expected})
            except (KeyError, OSError, ValueError) as exc:
                raise RealModelSourceAuditError("cannot open source-candidate workbook") from exc
            finally:
                if workbook is not None:
                    workbook.close()
            admitted.append(
                {
                    "source_id": source_id,
                    "study_id": source["study_id"],
                    "laboratory": source["laboratory"],
                    "affiliation_status": source["affiliation_status"],
                    "doi": source["doi"],
                    "landing_url": source["landing_url"],
                    "license_id": source["license_id"],
                    "biological_system": source["biological_system"],
                    "protocol_id": source["protocol_id"],
                    "asset": asset_record,
                    "worksheet": source["worksheet"],
                    "header_cells": verified_headers,
                    "declared_measurement_definition_id": source["declared_measurement_definition_id"],
                    "declared_measurement_definition": source["declared_measurement_definition"],
                    "endpoint_family_id": source["endpoint_family_id"],
                    "unit": source["unit"],
                    "biological_condition_status": source["biological_condition_status"],
                    "observation_granularity": source["observation_granularity"],
                }
            )
        if len(source_ids) < 3 or len(studies) < 3 or len(laboratories) < 3:
            raise RealModelSourceAuditError(
                "source candidates require three distinct sources, studies and laboratories"
            )
        return registry, sorted(admitted, key=lambda row: str(row["source_id"]))

    def run(self, *, strict: bool = False) -> RealModelSourceAuditSummary:
        """Write one immutable source-candidate decision in strict mode."""

        if not strict:
            raise RealModelSourceAuditError("T123 source-candidate audit requires --strict")
        if self.output_root.exists():
            raise RealModelSourceAuditError("real-model source-candidate audit already executed")
        registry, sources = self._admit_sources()
        definitions = sorted({str(source["declared_measurement_definition_id"]) for source in sources})
        blocked_reasons = [
            "The three source workbooks use different declared DLS size statistics: "
            + ", ".join(definitions)
            + ". A shared nm unit does not establish an identical endpoint.",
            "One candidate record does not state an institutional laboratory affiliation in its "
            "landing-page metadata; author names are not substituted for laboratory provenance.",
            "Candidate rows include source-level summaries or missing biological-condition "
            "metadata; "
            "they are not silently recast as matched biological replicate records.",
        ]
        decision = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "evaluated_at": self.EVALUATED_AT,
            "registry_sha256": _sha256(self.registry_path),
            "evidence_class": "DEVELOPMENT_OBSERVATION",
            "allowed_claim_level": "EXPLORATORY",
            "source_count": len(sources),
            "study_count": len({source["study_id"] for source in sources}),
            "laboratory_count": len({source["laboratory"] for source in sources}),
            "candidate_endpoint_family": "DLS_HYDRODYNAMIC_DIMENSION_NM",
            "declared_measurement_definition_ids": definitions,
            "sources": sources,
            "excluded_sources": registry["excluded_sources"],
            "status": "BLOCKED_SOURCE_CANDIDATES_NOT_ADMISSIBLE_AS_COMMON_TARGET",
            "admissible_target_count": 0,
            "blocked_reasons": blocked_reasons,
            "next_required_evidence": (
                "Admit at least three independently generated datasets that explicitly name the "
                "same DLS statistic, unit and biological-condition protocol, retain source-defined "
                "independent units, and document laboratory provenance before freezing any target."
            ),
            "model_fitted": False,
            "paired_ablations_run": False,
            "external_ood_evaluated": False,
            "negative_controls_run": False,
            "independent_validation": False,
            "scientific_submission_ready": False,
        }
        self.output_root.mkdir(parents=True, exist_ok=False)
        decision_path = self.output_root / "source_candidate_decision.json"
        self._write(decision_path, decision)
        receipt = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "evaluated_at": self.EVALUATED_AT,
            "status": decision["status"],
            "source_candidate_decision_sha256": _sha256(decision_path),
            "source_count": decision["source_count"],
            "distinct_measurement_definitions": len(definitions),
            "admissible_target_count": 0,
            "model_fitted": False,
            "paired_ablations_run": False,
            "external_ood_evaluated": False,
            "negative_controls_run": False,
            "independent_validation": False,
            "scientific_submission_ready": False,
        }
        receipt_path = self.output_root / "source_candidate_receipt.json"
        self._write(receipt_path, receipt)
        for path in self.output_root.iterdir():
            path.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
        self.output_root.chmod(stat.S_IRUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
        return RealModelSourceAuditSummary(
            source_count=_integer(receipt["source_count"], "source count", minimum=3),
            distinct_measurement_definitions=_integer(
                receipt["distinct_measurement_definitions"], "measurement definitions", minimum=1
            ),
            admissible_target_count=_integer(receipt["admissible_target_count"], "admissible target count"),
            receipt_path=receipt_path,
        )

    def verify(self) -> dict[str, Any]:
        """Verify the immutable candidate decision and its evidence boundary."""

        decision_path = self.output_root / "source_candidate_decision.json"
        receipt_path = self.output_root / "source_candidate_receipt.json"
        decision = self._json(decision_path, "source-candidate decision")
        receipt = self._json(receipt_path, "source-candidate receipt")
        required_false = (
            "model_fitted",
            "paired_ablations_run",
            "external_ood_evaluated",
            "negative_controls_run",
            "independent_validation",
            "scientific_submission_ready",
        )
        if (
            receipt.get("audit_id") != self.AUDIT_ID
            or receipt.get("status") != "BLOCKED_SOURCE_CANDIDATES_NOT_ADMISSIBLE_AS_COMMON_TARGET"
            or receipt.get("source_candidate_decision_sha256") != _sha256(decision_path)
            or decision.get("status") != receipt["status"]
            or decision.get("admissible_target_count") != 0
            or receipt.get("admissible_target_count") != 0
            or receipt.get("distinct_measurement_definitions") != 3
            or any(receipt.get(field) is not False for field in required_false)
            or any(decision.get(field) is not False for field in required_false)
        ):
            raise RealModelSourceAuditError("source-candidate receipt is invalid")
        return receipt
