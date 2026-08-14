"""Fixture-backed public GEO/SRA discovery and eligibility workflow."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import yaml  # type: ignore[import-untyped]


class GeoDiscoveryError(RuntimeError):
    """Raised when GEO/SRA discovery metadata is invalid or unsafe."""


@dataclass(frozen=True)
class GeoDiscoverySummary:
    """Summary of one bounded GEO/SRA discovery run."""

    candidates: int
    eligible: int
    restricted_rejected: int
    metadata_only: int
    coverage_gaps: int
    resumed: int
    receipt_path: Path


def _canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_path(path: Path) -> str:
    return _sha256(path.read_bytes())


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise GeoDiscoveryError(f"{label} must be an object")
    return dict(value)


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise GeoDiscoveryError(f"{label} must be a non-empty string")
    return value.strip()


def _optional_string(value: Any, label: str) -> str | None:
    if value is None:
        return None
    return _string(value, label)


class GeoDiscoveryWorkflow:
    """Discover sanitized GEO/SRA candidates without contacting endpoints."""

    def __init__(
        self,
        root: Path,
        *,
        fixture_path: Path | None = None,
        output_root: Path | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.fixture_path = fixture_path or (self.root / "tests/fixtures/omics/geo_discovery_fixture.json")
        self.output_root = output_root or self.root / "reports/omics/geo_discovery"

    def _load_fixture(self) -> dict[str, Any]:
        try:
            fixture = json.loads(self.fixture_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise GeoDiscoveryError(f"cannot load GEO discovery fixture: {exc}") from exc
        data = _mapping(fixture, "GEO discovery fixture")
        if data.get("schema_version") != 1 or data.get("scope") != "development":
            raise GeoDiscoveryError("GEO discovery fixture schema or scope is invalid")
        for key in ("inputs", "query_blocks", "candidates"):
            if key not in data:
                raise GeoDiscoveryError(f"GEO discovery fixture missing {key}")
        if not isinstance(data["query_blocks"], list) or not isinstance(data["candidates"], list):
            raise GeoDiscoveryError("query_blocks and candidates must be lists")
        return data

    def _verify_inputs(self, data: dict[str, Any]) -> str:
        inputs = _mapping(data["inputs"], "inputs")
        matrix_relative = _string(inputs.get("search_matrix_path"), "search_matrix_path")
        matrix_path = (self.root / matrix_relative).resolve(strict=True)
        if _sha256_path(matrix_path) != _string(inputs.get("search_matrix_sha256"), "search_matrix_sha256"):
            raise GeoDiscoveryError("search matrix checksum differs from fixture")
        try:
            matrix = yaml.safe_load(matrix_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, yaml.YAMLError) as exc:
            raise GeoDiscoveryError(f"cannot load search matrix: {exc}") from exc
        queries = matrix.get("queries") if isinstance(matrix, dict) else None
        if not isinstance(queries, list):
            raise GeoDiscoveryError("search matrix has no queries")
        train_geo = {
            str(query.get("id"))
            for query in queries
            if isinstance(query, dict) and query.get("scope") == "train" and query.get("source") == "geo"
        }
        for report_key in ("geo_adapter_report", "query_matrix_report", "coverage_report"):
            relative = _string(inputs.get(f"{report_key}_path"), f"{report_key}_path")
            path = (self.root / relative).resolve(strict=True)
            if _sha256_path(path) != _string(inputs.get(f"{report_key}_sha256"), f"{report_key}_sha256"):
                raise GeoDiscoveryError(f"{report_key} checksum differs from fixture")
        query_blocks = cast(list[Any], data["query_blocks"])
        for value in query_blocks:
            block = _mapping(value, "query block")
            query_id = _string(block.get("query_id"), "query_id")
            if query_id not in train_geo:
                raise GeoDiscoveryError(f"query block is not a development GEO query: {query_id}")
        return _sha256_path(matrix_path)

    @staticmethod
    def _validate_files(value: Any, label: str) -> tuple[dict[str, Any], ...]:
        if not isinstance(value, list):
            raise GeoDiscoveryError(f"{label} must be a list")
        files: list[dict[str, Any]] = []
        for item in value:
            file = _mapping(item, "public file")
            kind = _string(file.get("kind"), "public file kind")
            access = _string(file.get("access"), "public file access").upper()
            checksum = _string(file.get("sha256"), "public file sha256").lower()
            if len(checksum) != 64 or any(char not in "0123456789abcdef" for char in checksum):
                raise GeoDiscoveryError(f"public file checksum is invalid: {kind}")
            files.append(
                {
                    "kind": kind,
                    "access": access,
                    "url": _string(file.get("url"), "public file url"),
                    "sha256": checksum,
                    "checksum_status": _string(file.get("checksum_status"), "checksum_status"),
                    "credential_required": bool(file.get("credential_required", False)),
                }
            )
        return tuple(files)

    def _discover(
        self, data: dict[str, Any], matrix_sha256: str
    ) -> tuple[
        list[dict[str, Any]],
        list[dict[str, Any]],
        list[dict[str, Any]],
        list[dict[str, Any]],
    ]:
        candidates: list[dict[str, Any]] = []
        cards: list[dict[str, Any]] = []
        rejections: list[dict[str, Any]] = []
        gaps: list[dict[str, Any]] = []
        block_hashes = {
            _string(_mapping(block, "query block").get("query_id"), "query_id"): _sha256(
                _canonical(_mapping(block, "query block").get("response"))
            )
            for block in cast(list[Any], data["query_blocks"])
        }
        for value in cast(list[Any], data["candidates"]):
            candidate = _mapping(value, "GEO candidate")
            candidate_id = _string(candidate.get("candidate_id"), "candidate_id")
            accession = _string(candidate.get("accession"), "accession").upper()
            source = _string(candidate.get("source"), "source").upper()
            query_id = _string(candidate.get("query_id"), "query_id")
            if query_id not in block_hashes:
                raise GeoDiscoveryError(f"candidate query block is missing: {query_id}")
            family_id = _optional_string(candidate.get("paper_family_id"), "paper_family_id")
            material = _optional_string(candidate.get("material"), "material")
            biological_system = _optional_string(candidate.get("biological_system"), "biological_system")
            dose = _optional_string(candidate.get("dose"), "dose")
            timepoint = _optional_string(candidate.get("time"), "time")
            restricted = bool(candidate.get("restricted", False))
            credential_required = bool(candidate.get("credential_required", False))
            files = self._validate_files(candidate.get("public_files"), "public_files")
            public_files = [file for file in files if file["access"] == "PUBLIC" and not file["credential_required"]]
            reasons: list[str] = []
            if (
                restricted
                or credential_required
                or any(file["access"] != "PUBLIC" or file["credential_required"] for file in files)
            ):
                decision = "REJECTED_RESTRICTED"
                reasons.append("CREDENTIAL_OR_RESTRICTED_ACCESS")
            else:
                missing_fields = [
                    field
                    for field, field_value in (
                        ("material", material),
                        ("biological_system", biological_system),
                        ("dose", dose),
                        ("time", timepoint),
                        ("paper_family_id", family_id),
                    )
                    if field_value is None
                ]
                if not public_files:
                    reasons.append("PUBLIC_FILE_UNVERIFIED")
                reasons.extend(f"{field.upper()}_MISSING" for field in missing_fields)
                decision = "ELIGIBLE" if not reasons else "METADATA_ONLY"
            record = {
                "candidate_id": candidate_id,
                "accession": accession,
                "source": source,
                "query_id": query_id,
                "response_sha256": block_hashes[query_id],
                "search_matrix_sha256": matrix_sha256,
                "title": _string(candidate.get("title"), "title"),
                "paper_family_id": family_id,
                "publication_date": _string(candidate.get("publication_date"), "publication_date"),
                "material": material,
                "biological_system": biological_system,
                "dose": dose,
                "time": timepoint,
                "public_files": list(files),
                "raw_access": _string(candidate.get("raw_access"), "raw_access"),
                "restricted": restricted,
                "credential_required": credential_required,
                "decision": decision,
                "reasons": reasons,
                "evidence_locator": _string(candidate.get("evidence_locator"), "evidence_locator"),
                "raw_downloaded": False,
                "locked_payload_accessed": False,
            }
            candidates.append(record)
            cards.append(
                {
                    "accession": accession,
                    "decision": decision,
                    "material": material,
                    "biological_system": biological_system,
                    "dose": dose,
                    "time": timepoint,
                    "paper_family_id": family_id,
                    "public_file_count": len(public_files),
                    "reasons": reasons,
                    "evidence_locator": record["evidence_locator"],
                }
            )
            if decision != "ELIGIBLE":
                rejections.append(
                    {
                        "candidate_id": candidate_id,
                        "accession": accession,
                        "decision": decision,
                        "reasons": reasons,
                        "evidence_locator": record["evidence_locator"],
                    }
                )
            for reason in reasons:
                if reason.endswith("_MISSING") or reason == "PUBLIC_FILE_UNVERIFIED":
                    gaps.append({"accession": accession, "field": reason, "candidate_id": candidate_id})
        if not candidates:
            raise GeoDiscoveryError("no GEO/SRA candidates discovered")
        return (
            sorted(candidates, key=lambda row: row["accession"]),
            sorted(cards, key=lambda row: row["accession"]),
            sorted(rejections, key=lambda row: row["accession"]),
            sorted(gaps, key=lambda row: (row["accession"], row["field"])),
        )

    def run(self, *, fixture: bool = False, scope: str = "development") -> GeoDiscoverySummary:
        """Run GEO/SRA discovery and resume identical outputs."""
        if not fixture or scope != "development":
            raise GeoDiscoveryError("development fixture scope is required")
        data = self._load_fixture()
        matrix_sha256 = self._verify_inputs(data)
        candidates, cards, rejections, gaps = self._discover(data, matrix_sha256)
        eligible = sum(row["decision"] == "ELIGIBLE" for row in candidates)
        restricted = sum(row["decision"] == "REJECTED_RESTRICTED" for row in candidates)
        metadata_only = sum(row["decision"] == "METADATA_ONLY" for row in candidates)
        query_receipt = {
            "schema_version": 1,
            "scope": scope,
            "query_blocks": [
                {
                    "query_id": _string(_mapping(block, "query block").get("query_id"), "query_id"),
                    "response_sha256": _sha256(_canonical(_mapping(block, "query block").get("response"))),
                    "candidate_count": sum(
                        _string(candidate.get("query_id"), "query_id")
                        == _string(_mapping(block, "query block").get("query_id"), "query_id")
                        for candidate in candidates
                    ),
                }
                for block in cast(list[Any], data["query_blocks"])
            ],
            "search_matrix_sha256": matrix_sha256,
            "real_network_accessed": False,
        }
        resume_material = {
            "candidates": candidates,
            "cards": cards,
            "rejections": rejections,
            "gaps": gaps,
            "query_receipt": query_receipt,
        }
        resume_key = _sha256(_canonical(resume_material))
        self.output_root.mkdir(parents=True, exist_ok=True)
        paths = {
            "query": self.output_root / "query_receipt.json",
            "candidates": self.output_root / "candidate_registry.json",
            "cards": self.output_root / "eligibility_cards.json",
            "rejections": self.output_root / "rejection_ledger.json",
            "gaps": self.output_root / "coverage_gaps.json",
            "receipt": self.output_root / "geo_discovery_receipt.json",
            "log": self.output_root / "geo_discovery_log.json",
            "manifest": self.output_root / "geo_discovery_manifest.json",
        }
        raw_payloads = {
            "query": query_receipt,
            "candidates": {"schema_version": 1, "candidates": candidates},
            "cards": {"schema_version": 1, "cards": cards},
            "rejections": {"schema_version": 1, "append_only": True, "entries": rejections},
            "gaps": {
                "schema_version": 1,
                "gap_count": len(gaps),
                "gaps": gaps,
                "no_imputation": True,
            },
        }
        payload_bytes = {name: _canonical(value) for name, value in raw_payloads.items()}
        artifact_records = {
            name: {
                "path": str(path.relative_to(self.root)) if path.is_relative_to(self.root) else str(path),
                "sha256": _sha256(payload_bytes[name]),
                "bytes": len(payload_bytes[name]),
            }
            for name, path in paths.items()
            if name in payload_bytes
        }
        receipt = {
            "schema_version": 1,
            "status": "COMPLETED",
            "scope": scope,
            "candidates": len(candidates),
            "eligible": eligible,
            "restricted_rejected": restricted,
            "metadata_only": metadata_only,
            "coverage_gaps": len(gaps),
            "raw_downloaded": False,
            "locked_payload_accessed": False,
            "real_network_accessed": False,
            "resume_key": resume_key,
            "artifacts": artifact_records,
        }
        payload_bytes["receipt"] = _canonical(receipt)
        log = {
            "schema_version": 1,
            "resume_key": resume_key,
            "events": [
                {"event": "query_matrix_verified", "sha256": matrix_sha256},
                {"event": "candidate_registry_written", "candidates": len(candidates)},
                {"event": "restricted_access_rejected", "projects": restricted},
                {"event": "coverage_gaps_recorded", "gaps": len(gaps)},
            ],
        }
        payload_bytes["log"] = _canonical(log)
        manifest = {
            "schema_version": 1,
            "status": "COMPLETED",
            "resume_supported": True,
            "resume_key": resume_key,
            "scope": scope,
            "candidates": len(candidates),
            "eligible": eligible,
            "restricted_rejected": restricted,
            "metadata_only": metadata_only,
            "coverage_gaps": len(gaps),
            "artifacts": {
                name: {
                    "path": str(path.relative_to(self.root)) if path.is_relative_to(self.root) else str(path),
                    "sha256": _sha256(payload_bytes[name]),
                    "bytes": len(payload_bytes[name]),
                }
                for name, path in paths.items()
                if name in payload_bytes
            },
        }
        payload_bytes["manifest"] = _canonical(manifest)
        existing_receipt = paths["receipt"].read_bytes() if paths["receipt"].exists() else None
        if existing_receipt is not None:
            if existing_receipt != payload_bytes["receipt"]:
                raise GeoDiscoveryError("existing GEO discovery receipt differs from rerun")
            for name, payload in payload_bytes.items():
                if paths[name].read_bytes() != payload:
                    raise GeoDiscoveryError(f"existing GEO discovery artifact differs: {name}")
            resumed = 1
        else:
            for name, payload in payload_bytes.items():
                paths[name].write_bytes(payload)
            resumed = 0
        return GeoDiscoverySummary(
            candidates=len(candidates),
            eligible=eligible,
            restricted_rejected=restricted,
            metadata_only=metadata_only,
            coverage_gaps=len(gaps),
            resumed=resumed,
            receipt_path=paths["receipt"],
        )
