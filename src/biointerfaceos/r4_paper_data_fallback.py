"""Audit the published-paper data fallback used by the R4 evidence plan.

This workflow does not manufacture wet-lab observations.  It binds the public
full-text/supplementary-data routes that are actually available to the frozen
target ledger, reports and claim boundaries, while keeping external receipts
and biological replication claims closed.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any


class R4PaperDataFallbackError(RuntimeError):
    """Raised when the published-data fallback contract is not reproducible."""


@dataclass(frozen=True)
class R4PaperDataFallbackSummary:
    """Machine-readable summary of the paper-data fallback audit."""

    route_count: int
    reference_count: int
    source_registry_count: int
    source_map_count: int
    report_count: int
    external_gate_count: int
    receipt_path: Path


class R4PaperDataFallbackWorkflow:
    """Verify frozen published-data routes without promoting external claims."""

    AUDIT_ID = "bioif-r4-t222-paper-data-fallback-v1.0.0"
    LEDGER_RELATIVE = "docs/data/R4_T222_PAPER_DATA_FALLBACK_LEDGER.json"
    OUTPUT_RELATIVE = "reports/review_round_4/paper_data_fallback/v1.0.0"
    RECEIPT_NAME = "r4_t222_paper_data_fallback_receipt.json"
    REPORT_NAME = "r4_t222_paper_data_fallback_report.json"
    EVIDENCE_CLASSES = {
        "REDISTRIBUTABLE_DEVELOPMENT",
        "AUTHOR_RUN_PAPER_OOD",
        "AUTHOR_RUN_EXTERNAL_OOD",
        "EXPLORATORY_SENSITIVITY",
        "EXTERNAL_REPRODUCTION_CANDIDATE",
    }
    REQUIRED_GATE_FIELDS = {
        "independent_validation",
        "protected_lockbox_evaluator_receipt",
        "external_scientific_reproduction",
        "external_user_adoption",
        "doi_archived",
        "scientific_submission_ready",
    }

    def __init__(self, root: Path) -> None:
        self.root = root.resolve(strict=True)
        self.ledger_path = self.root / self.LEDGER_RELATIVE
        self.output_root = self.root / self.OUTPUT_RELATIVE
        self.receipt_path = self.output_root / self.RECEIPT_NAME
        self.report_path = self.output_root / self.REPORT_NAME

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()

    @staticmethod
    def _mapping(value: Any, label: str) -> dict[str, Any]:
        if not isinstance(value, Mapping):
            raise R4PaperDataFallbackError(f"{label} must be an object")
        return dict(value)

    @staticmethod
    def _string(value: Any, label: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise R4PaperDataFallbackError(f"{label} must be a non-empty string")
        return value.strip()

    @staticmethod
    def _digest(value: Any, label: str) -> str:
        result = R4PaperDataFallbackWorkflow._string(value, label)
        if len(result) != 64 or any(character not in "0123456789abcdef" for character in result):
            raise R4PaperDataFallbackError(f"{label} must be lowercase hexadecimal SHA-256")
        return result

    def _root_file(self, relative_path: Any, label: str) -> Path:
        text = self._string(relative_path, label)
        if "\\" in text:
            raise R4PaperDataFallbackError(f"{label} must use POSIX separators")
        pure = PurePosixPath(text)
        if pure.is_absolute() or not pure.parts or ".." in pure.parts:
            raise R4PaperDataFallbackError(f"{label} escapes repository root")
        path = (self.root / Path(*pure.parts)).resolve(strict=False)
        if not path.is_relative_to(self.root) or not path.is_file():
            raise R4PaperDataFallbackError(f"{label} is missing or outside repository root")
        return path

    def _reference(self, value: Any, label: str) -> tuple[Path, str]:
        reference = self._mapping(value, label)
        if set(reference) != {"relative_path", "sha256"}:
            raise R4PaperDataFallbackError(f"{label} fields are invalid")
        path = self._root_file(reference["relative_path"], label)
        expected = self._digest(reference["sha256"], f"{label} checksum")
        actual = self._sha256(path)
        if actual != expected:
            raise R4PaperDataFallbackError(f"{label} checksum differs")
        return path, actual

    @staticmethod
    def _json(path: Path, label: str) -> dict[str, Any]:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise R4PaperDataFallbackError(f"cannot parse {label}") from exc
        if not isinstance(value, Mapping):
            raise R4PaperDataFallbackError(f"{label} must be an object")
        return dict(value)

    def _ledger(self) -> dict[str, Any]:
        ledger = self._json(self.ledger_path, "T222 paper-data ledger")
        required = {
            "schema_version",
            "task_id",
            "status",
            "strategy",
            "routes",
            "claim_boundary",
            "scientific_submission_ready",
        }
        if set(ledger) != required or ledger["schema_version"] != 1:
            raise R4PaperDataFallbackError("T222 ledger fields are invalid")
        if (
            ledger["task_id"] != self.AUDIT_ID
            or ledger["status"] != "FROZEN_PUBLIC_PAPER_DATA_FALLBACK"
        ):
            raise R4PaperDataFallbackError("T222 ledger identity is invalid")
        if ledger["scientific_submission_ready"] is not False:
            raise R4PaperDataFallbackError("T222 ledger cannot claim submission readiness")
        if not isinstance(ledger["routes"], list) or not ledger["routes"]:
            raise R4PaperDataFallbackError("T222 routes must be non-empty")
        self._string(ledger["strategy"], "T222 strategy")
        self._string(ledger["claim_boundary"], "T222 claim boundary")
        return ledger

    def _audit(self) -> tuple[dict[str, Any], dict[str, Any]]:
        ledger = self._ledger()
        route_rows: list[dict[str, Any]] = []
        all_references: dict[str, str] = {}
        source_registry_count = source_map_count = report_count = external_gate_count = 0
        route_ids: set[str] = set()
        for index, value in enumerate(ledger["routes"], start=1):
            route = self._mapping(value, f"T222 route {index}")
            required = {
                "route_id",
                "source_kind",
                "evidence_class",
                "article",
                "source_registry",
                "source_maps",
                "output_reports",
                "expected_accounting",
                "license_boundary",
                "external_gate_effect",
                "claim_boundary",
            }
            if set(route) != required:
                raise R4PaperDataFallbackError(f"T222 route {index} fields are invalid")
            route_id = self._string(route["route_id"], f"T222 route {index} route_id")
            if route_id in route_ids:
                raise R4PaperDataFallbackError(f"T222 route {route_id} is duplicated")
            route_ids.add(route_id)
            self._string(route["source_kind"], f"T222 route {route_id} source_kind")
            evidence_class = self._string(
                route["evidence_class"], f"T222 route {route_id} evidence_class"
            )
            if evidence_class not in self.EVIDENCE_CLASSES:
                raise R4PaperDataFallbackError(f"T222 route {route_id} evidence class is invalid")
            article = self._mapping(route["article"], f"T222 route {route_id} article")
            for field in {"pmcid", "full_text_locator", "license"}:
                self._string(article.get(field), f"T222 route {route_id} article {field}")
            source_registry, registry_hash = self._reference(
                route["source_registry"], f"T222 route {route_id} source_registry"
            )
            source_registry_count += 1
            all_references[f"{route_id}:source_registry"] = registry_hash
            source_maps = route["source_maps"]
            if not isinstance(source_maps, list) or not source_maps:
                raise R4PaperDataFallbackError(f"T222 route {route_id} source_maps are empty")
            map_hashes: list[str] = []
            for map_index, item in enumerate(source_maps, start=1):
                _, map_hash = self._reference(
                    item, f"T222 route {route_id} source_map {map_index}"
                )
                source_map_count += 1
                map_hashes.append(map_hash)
            report_hashes: list[str] = []
            reports = route["output_reports"]
            if not isinstance(reports, list) or not reports:
                raise R4PaperDataFallbackError(f"T222 route {route_id} output_reports are empty")
            for report_index, item in enumerate(reports, start=1):
                _, report_hash = self._reference(
                    item, f"T222 route {route_id} output_report {report_index}"
                )
                report_count += 1
                report_hashes.append(report_hash)
            expected = self._mapping(
                route["expected_accounting"], f"T222 route {route_id} accounting"
            )
            if not expected or any(not isinstance(key, str) for key in expected):
                raise R4PaperDataFallbackError(f"T222 route {route_id} accounting is invalid")
            license_boundary = self._mapping(
                route["license_boundary"], f"T222 route {route_id} license boundary"
            )
            self._string(license_boundary.get("license"), f"T222 route {route_id} license")
            if license_boundary.get("public_release_asset") is not True:
                raise R4PaperDataFallbackError(
                    f"T222 route {route_id} must use a release-eligible public asset"
                )
            gates = self._mapping(
                route["external_gate_effect"], f"T222 route {route_id} external gates"
            )
            if set(gates) != self.REQUIRED_GATE_FIELDS or any(
                value is not False for value in gates.values()
            ):
                raise R4PaperDataFallbackError(
                    f"T222 route {route_id} must keep all external gates closed"
                )
            external_gate_count += len(gates)
            claim_boundary = self._string(
                route["claim_boundary"], f"T222 route {route_id} claim boundary"
            )
            route_rows.append(
                {
                    "route_id": route_id,
                    "source_kind": route["source_kind"],
                    "evidence_class": evidence_class,
                    "article": article,
                    "source_registry": {
                        "relative_path": source_registry.relative_to(self.root).as_posix(),
                        "sha256": registry_hash,
                    },
                    "source_map_sha256": map_hashes,
                    "output_report_sha256": report_hashes,
                    "expected_accounting": expected,
                    "license": license_boundary["license"],
                    "claim_boundary": claim_boundary,
                    "external_gate_effect": gates,
                }
            )
        report = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "status": "T222_PUBLISHED_PAPER_DATA_FALLBACK_AUDITED",
            "strategy": ledger["strategy"],
            "route_count": len(route_rows),
            "reference_count": source_registry_count + source_map_count + report_count,
            "source_registry_count": source_registry_count,
            "source_map_count": source_map_count,
            "report_count": report_count,
            "external_gate_count": external_gate_count,
            "routes": route_rows,
            "all_references_sha256": all_references,
            "independent_validation": False,
            "protected_lockbox_evaluator_receipt": False,
            "external_scientific_reproduction": False,
            "external_user_adoption": False,
            "doi_archived": False,
            "scientific_submission_ready": False,
            "claim_boundary": ledger["claim_boundary"],
        }
        return ledger, report

    @staticmethod
    def _write_json(path: Path, value: Mapping[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        path.write_bytes((payload + "\n").encode("utf-8"))

    def run(self, *, strict: bool = False) -> R4PaperDataFallbackSummary:
        if not strict:
            raise R4PaperDataFallbackError("T222 paper-data fallback requires --strict")
        if self.receipt_path.exists() or self.report_path.exists():
            raise R4PaperDataFallbackError("T222 output already exists")
        _, report = self._audit()
        self._write_json(self.report_path, report)
        receipt = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "report": {
                "relative_path": self.report_path.relative_to(self.root).as_posix(),
                "sha256": self._sha256(self.report_path),
            },
            "route_count": report["route_count"],
            "reference_count": report["reference_count"],
            "source_registry_count": report["source_registry_count"],
            "source_map_count": report["source_map_count"],
            "report_count": report["report_count"],
            "external_gate_count": report["external_gate_count"],
            "published_paper_data_audited": True,
            "independent_validation": False,
            "external_scientific_reproduction": False,
            "external_user_adoption": False,
            "doi_archived": False,
            "scientific_submission_ready": False,
            "claim_boundary": report["claim_boundary"],
        }
        self._write_json(self.receipt_path, receipt)
        return self._summary()

    def _summary(self) -> R4PaperDataFallbackSummary:
        receipt = self._json(self.receipt_path, "T222 receipt")
        return R4PaperDataFallbackSummary(
            route_count=int(receipt["route_count"]),
            reference_count=int(receipt["reference_count"]),
            source_registry_count=int(receipt["source_registry_count"]),
            source_map_count=int(receipt["source_map_count"]),
            report_count=int(receipt["report_count"]),
            external_gate_count=int(receipt["external_gate_count"]),
            receipt_path=self.receipt_path,
        )

    def verify(self, *, strict: bool = False) -> R4PaperDataFallbackSummary:
        if not strict:
            raise R4PaperDataFallbackError(
                "T222 paper-data fallback verification requires --strict"
            )
        _, report = self._audit()
        receipt = self._json(self.receipt_path, "T222 receipt")
        if not self.report_path.is_file() or self._sha256(self.report_path) != receipt.get(
            "report", {}
        ).get("sha256"):
            raise R4PaperDataFallbackError("T222 report checksum differs")
        if self._json(self.report_path, "T222 report") != report:
            raise R4PaperDataFallbackError("T222 report differs from the frozen ledger audit")
        if any(receipt.get(field) is not False for field in (
            "independent_validation",
            "external_scientific_reproduction",
            "external_user_adoption",
            "doi_archived",
            "scientific_submission_ready",
        )) or receipt.get("published_paper_data_audited") is not True:
            raise R4PaperDataFallbackError("T222 receipt claim boundary is invalid")
        return self._summary()
