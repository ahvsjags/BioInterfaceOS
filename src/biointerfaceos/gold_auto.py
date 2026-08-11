"""Audited Gold-auto subset selection from Silver and consensus evidence."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from biointerfaceos.silver_release import SilverReleaseBuilder, SilverReleaseError

GOLD_AUTO_ROOT = Path("data/gold_auto")
GOLD_AUTO_RELEASE_ROOT = Path("release/gold_auto")
GOLD_AUTO_FIXTURE = Path("tests/fixtures/gold_auto/gold_auto_expectations.json")


class GoldAutoError(RuntimeError):
    """Raised when Gold-auto selection or verification fails."""


@dataclass(frozen=True)
class GoldAutoSummary:
    """Counts and immutable release paths from one Gold-auto run."""

    release_id: str
    manifest_hash: str
    admitted_fields: int
    excluded_fields: int
    agreement_fields: int
    disagreement_fields: int
    reverse_traces: int
    manifest_path: Path
    agreement_report_path: Path
    exclusions_path: Path
    receipt_path: Path
    checksums_path: Path


def _canonical(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")


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
        raise GoldAutoError(f"path escapes repository: {candidate}")
    if "locked_test" in resolved.parts:
        raise GoldAutoError("locked-test paths are forbidden")
    return resolved


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise GoldAutoError(f"invalid Gold-auto JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise GoldAutoError(f"Gold-auto JSON must be an object: {path}")
    return value


class GoldAutoBuilder:
    """Select only high-confidence, consensus-backed, reverse-traceable fields."""

    def __init__(
        self,
        root: Path,
        *,
        fixture_path: Path | None = None,
        release_root: Path | str = GOLD_AUTO_RELEASE_ROOT,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.fixture_path = fixture_path or self.root / GOLD_AUTO_FIXTURE
        candidate = Path(release_root)
        self.release_root = _contained(
            self.root,
            candidate if candidate.is_absolute() else self.root / candidate,
        )
        if self.release_root == self.root:
            raise GoldAutoError("Gold-auto release root cannot be repository root")

    def _load_fixture(self) -> tuple[float, int, int]:
        try:
            value = json.loads(self.fixture_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise GoldAutoError(f"cannot load Gold-auto fixture: {exc}") from exc
        if not isinstance(value, Mapping) or set(value) != {
            "schema_version",
            "minimum_confidence",
            "expected_admitted_fields",
            "expected_excluded_fields",
        }:
            raise GoldAutoError("Gold-auto fixture envelope is invalid")
        threshold = value["minimum_confidence"]
        if (
            value["schema_version"] != 1
            or not isinstance(threshold, int | float)
            or isinstance(threshold, bool)
            or not 0.0 <= float(threshold) <= 1.0
            or not isinstance(value["expected_admitted_fields"], int)
            or not isinstance(value["expected_excluded_fields"], int)
        ):
            raise GoldAutoError("Gold-auto fixture schema is invalid")
        return (
            float(threshold),
            int(value["expected_admitted_fields"]),
            int(value["expected_excluded_fields"]),
        )

    def _prepare(self) -> tuple[dict[str, bytes], dict[str, Any]]:
        threshold, expected_admitted, expected_excluded = self._load_fixture()
        try:
            SilverReleaseBuilder(self.root).validate()
        except (SilverReleaseError, OSError) as exc:
            raise GoldAutoError(f"Silver prerequisite is invalid: {exc}") from exc
        consensus = _read_json(self.root / "registry/experiment_consensus.json")
        evidence = _read_json(self.root / "registry/evidence_table.json")
        conflicts = _read_json(self.root / "registry/evidence_conflict_graph.json")
        quarantine = _read_json(self.root / "registry/qc_quarantine.json")
        fields = [dict(field) for record in consensus["records"] for field in record["fields"]]
        evidence_by_key: dict[tuple[str, str], list[dict[str, Any]]] = {}
        for row in evidence["rows"]:
            if row["resolution_status"] == "RESOLVED":
                key = (str(row["record_id"]), str(row["field_name"]))
                evidence_by_key.setdefault(key, []).append(dict(row))
        conflict_keys = {
            (str(edge["record_id"]), str(edge["field_name"])) for edge in conflicts["edges"]
        }
        quarantine_ids = {str(item["record_id"]) for item in quarantine["quarantine"]}
        admitted: list[dict[str, Any]] = []
        excluded: list[dict[str, Any]] = []
        reverse_trace: list[dict[str, Any]] = []
        for field in sorted(fields, key=lambda item: (item["record_id"], item["field_name"])):
            key = (str(field["record_id"]), str(field["field_name"]))
            reasons: list[str] = []
            matching = evidence_by_key.get(key, [])
            if field["status"] != "AGREED":
                reasons.append("CONSENSUS_DISAGREEMENT_OR_REVIEW")
            if float(field["confidence"]) < threshold:
                reasons.append("CONFIDENCE_BELOW_THRESHOLD")
            if key in conflict_keys:
                reasons.append("EVIDENCE_VALUE_CONFLICT")
            if not matching:
                reasons.append("NO_RESOLVED_EVIDENCE_ASSERTION")
            if key[0] in quarantine_ids:
                reasons.append("CRITICAL_QC_QUARANTINED")
            if not reasons:
                evidence_ids = sorted(str(row["assertion_id"]) for row in matching)
                locators = sorted(str(row["locator"]) for row in matching)
                gold_id = f"gold-auto:{field['record_id']}:{field['field_name']}"
                row = {
                    "gold_id": gold_id,
                    "record_id": field["record_id"],
                    "field_name": field["field_name"],
                    "accepted_value": field["accepted_value"],
                    "accepted_unit": field["accepted_unit"],
                    "confidence": field["confidence"],
                    "source_paths": field["source_paths"],
                    "consensus_evidence_locators": field["evidence_locators"],
                    "evidence_assertion_ids": evidence_ids,
                    "evidence_locators": locators,
                    "status": "GOLD_AUTO_ADMITTED",
                }
                admitted.append(row)
                reverse_trace.append(
                    {
                        "gold_id": gold_id,
                        "record_id": field["record_id"],
                        "field_name": field["field_name"],
                        "evidence_assertion_ids": evidence_ids,
                        "evidence_locators": locators,
                        "trace_passed": bool(locators),
                    }
                )
            else:
                excluded.append(
                    {
                        "record_id": field["record_id"],
                        "field_name": field["field_name"],
                        "consensus_status": field["status"],
                        "confidence": field["confidence"],
                        "reasons": sorted(set(reasons)),
                        "evidence_locators": field["evidence_locators"],
                        "status": "RETAIN_IN_SILVER",
                    }
                )
        if len(admitted) != expected_admitted or len(excluded) != expected_excluded:
            raise GoldAutoError(
                f"Gold-auto expectations differ: admitted={len(admitted)} excluded={len(excluded)}"
            )
        if not all(item["trace_passed"] for item in reverse_trace):
            raise GoldAutoError("Gold-auto reverse trace is incomplete")
        agreement_fields = sum(field["status"] == "AGREED" for field in fields)
        disagreement_fields = len(fields) - agreement_fields
        report = {
            "schema_version": 1,
            "minimum_confidence": threshold,
            "consensus_fields": len(fields),
            "agreement_fields": agreement_fields,
            "disagreement_fields": disagreement_fields,
            "admitted_fields": len(admitted),
            "excluded_fields": len(excluded),
            "reverse_traces": len(reverse_trace),
            "expert_gold_admitted": 0,
            "exclusion_reason_counts": {
                reason: sum(reason in item["reasons"] for item in excluded)
                for reason in sorted({reason for item in excluded for reason in item["reasons"]})
            },
        }
        manifest_rows = [
            {
                "gold_id": row["gold_id"],
                "record_id": row["record_id"],
                "field_name": row["field_name"],
                "confidence": row["confidence"],
                "evidence_assertion_ids": row["evidence_assertion_ids"],
                "status": row["status"],
            }
            for row in admitted
        ]
        manifest_hash = _sha256_bytes(_canonical(manifest_rows))
        manifest = {
            "schema_version": 1,
            "fixture": True,
            "manifest_hash": manifest_hash,
            "admission_policy": {
                "minimum_confidence": threshold,
                "requires_consensus_agreement": True,
                "requires_resolved_evidence": True,
                "requires_reverse_trace": True,
                "expert_gold_admitted": False,
            },
            "rows": manifest_rows,
        }
        payloads = {
            "gold_auto_records.json": _canonical({"schema_version": 1, "rows": admitted}),
            "gold_auto_exclusions.json": _canonical({"schema_version": 1, "rows": excluded}),
            "agreement_report.json": _canonical(report),
            "reverse_trace.json": _canonical({"schema_version": 1, "traces": reverse_trace}),
            "gold_auto_manifest.json": _canonical(manifest),
        }
        metadata = {
            "manifest": manifest,
            "report": report,
            "admitted": admitted,
            "excluded": excluded,
            "reverse_trace": reverse_trace,
        }
        return payloads, metadata

    @staticmethod
    def _read_only(directory: Path) -> None:
        for path in sorted(directory.rglob("*"), key=lambda item: len(item.parts), reverse=True):
            path.chmod(0o555 if path.is_dir() else 0o444)
        directory.chmod(0o555)

    @staticmethod
    def _is_read_only(directory: Path) -> bool:
        return all(
            not bool(path.stat().st_mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))
            for path in (directory, *directory.rglob("*"))
        )

    def build(self, *, fixture: bool = False) -> GoldAutoSummary:
        """Build one immutable Gold-auto release."""
        if not fixture:
            raise GoldAutoError("only explicit fixture Gold-auto builds are enabled")
        payloads, metadata = self._prepare()
        manifest = metadata["manifest"]
        release_id = f"bioif-gold-auto-{manifest['manifest_hash'][:16]}"
        target = self.release_root / release_id
        if target.exists():
            self.validate(release_id)
            return self._summary(target, manifest)
        self.release_root.mkdir(parents=True, exist_ok=True)
        temporary = self.release_root / f".{release_id}.{uuid.uuid4().hex}.tmp"
        temporary.mkdir()
        try:
            for relative, content in payloads.items():
                (temporary / relative).write_bytes(content)
            checksum_text = "".join(
                f"{_sha256_path(temporary / relative)}  {relative}\n"
                for relative in sorted(payloads)
            )
            (temporary / "checksums.txt").write_text(checksum_text, encoding="utf-8")
            receipt = {
                "schema_version": 1,
                "release_id": release_id,
                "fixture": True,
                "frozen": True,
                "exact_rebuild": True,
                "manifest_hash": manifest["manifest_hash"],
                "checksums_sha256": _sha256_bytes(checksum_text.encode("utf-8")),
                "admitted_fields": len(metadata["admitted"]),
                "excluded_fields": len(metadata["excluded"]),
                "reverse_traces": len(metadata["reverse_trace"]),
                "expert_gold_admitted": 0,
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
        destination = self.root / GOLD_AUTO_ROOT
        destination.mkdir(parents=True, exist_ok=True)
        for name in (
            "gold_auto_records.json",
            "gold_auto_exclusions.json",
            "agreement_report.json",
            "reverse_trace.json",
            "gold_auto_manifest.json",
            "rebuild_receipt.json",
        ):
            (destination / name).write_bytes((target / name).read_bytes())

    def _resolve(self, release_id: str | None) -> Path:
        if release_id is not None:
            target = self.release_root / release_id
            if not target.is_dir():
                raise GoldAutoError(f"Gold-auto release does not exist: {release_id}")
            return _contained(self.root, target)
        if not self.release_root.is_dir():
            raise GoldAutoError("no Gold-auto release directory exists")
        candidates = sorted(
            path
            for path in self.release_root.iterdir()
            if path.is_dir() and not path.name.startswith(".")
        )
        if not candidates:
            raise GoldAutoError("no Gold-auto release exists")
        if len(candidates) > 1:
            raise GoldAutoError("multiple Gold-auto releases exist; specify release_id")
        return candidates[0]

    def _summary(self, target: Path, manifest: Mapping[str, Any]) -> GoldAutoSummary:
        report = _read_json(target / "agreement_report.json")
        return GoldAutoSummary(
            release_id=target.name,
            manifest_hash=str(manifest["manifest_hash"]),
            admitted_fields=int(report["admitted_fields"]),
            excluded_fields=int(report["excluded_fields"]),
            agreement_fields=int(report["agreement_fields"]),
            disagreement_fields=int(report["disagreement_fields"]),
            reverse_traces=int(report["reverse_traces"]),
            manifest_path=target / "gold_auto_manifest.json",
            agreement_report_path=target / "agreement_report.json",
            exclusions_path=target / "gold_auto_exclusions.json",
            receipt_path=target / "rebuild_receipt.json",
            checksums_path=target / "checksums.txt",
        )

    def validate(self, release_id: str | None = None, *, fixture: bool = True) -> GoldAutoSummary:
        """Validate exact rebuild, exclusion rules, reverse traces, and read-only bytes."""
        if not fixture:
            raise GoldAutoError("only explicit fixture Gold-auto validation is enabled")
        target = self._resolve(release_id)
        if not self._is_read_only(target):
            raise GoldAutoError("Gold-auto release directory is writable")
        payloads, metadata = self._prepare()
        manifest = metadata["manifest"]
        expected_release_id = f"bioif-gold-auto-{manifest['manifest_hash'][:16]}"
        if target.name != expected_release_id:
            raise GoldAutoError("Gold-auto release identity mismatch")
        receipt = _read_json(target / "rebuild_receipt.json")
        if receipt.get("frozen") is not True or receipt.get("exact_rebuild") is not True:
            raise GoldAutoError("Gold-auto receipt is not immutable")
        if receipt.get("manifest_hash") != manifest["manifest_hash"]:
            raise GoldAutoError("Gold-auto receipt hash mismatch")
        for relative, content in payloads.items():
            path = target / relative
            if not path.is_file() or path.read_bytes() != content:
                raise GoldAutoError(f"Gold-auto payload differs: {relative}")
        actual_paths: set[str] = set()
        for line in (target / "checksums.txt").read_text(encoding="utf-8").splitlines():
            parts = line.split("  ", 1)
            if len(parts) != 2 or len(parts[0]) != 64:
                raise GoldAutoError("invalid Gold-auto checksum line")
            path = _contained(target, target / parts[1])
            if path == target or not path.is_file() or _sha256_path(path) != parts[0]:
                raise GoldAutoError(f"Gold-auto checksum mismatch: {parts[1]}")
            actual_paths.add(parts[1])
        if actual_paths != set(payloads):
            raise GoldAutoError("Gold-auto checksum inventory differs from release")
        if metadata["report"]["expert_gold_admitted"] != 0:
            raise GoldAutoError("expert gold was admitted into Gold-auto")
        return self._summary(target, manifest)
