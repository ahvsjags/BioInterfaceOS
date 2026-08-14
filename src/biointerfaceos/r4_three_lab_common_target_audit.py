"""Verify the three-laboratory, row-traceable common-target admission.

This audit binds the three already published CC-BY source-cell maps to the
current common-rank ledger.  It makes the cross-laboratory evidence explicit
without converting development sources into a protected lockbox or biological
replication claim.
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from biointerfaceos.r3_uniprot_mapping import _canonical, _checksum, _mapping, _sha256, _string


class R4ThreeLabCommonTargetAuditError(RuntimeError):
    """Raised when the three-laboratory common-target evidence is not closed."""


@dataclass(frozen=True)
class R4ThreeLabCommonTargetAuditSummary:
    source_count: int
    laboratory_anchor_count: int
    common_target_count: int
    common_rank_observation_count: int
    selected_source_row_count: int
    measurement_batch_count: int
    source_cell_count: int
    receipt_path: Path


class R4ThreeLabCommonTargetAuditWorkflow:
    """Recompute and verify the cross-laboratory common-target receipt."""

    AUDIT_ID = "bioif-r4-three-lab-common-target-admission-v1.0.0"
    REGISTRY_RELATIVE = "docs/data/R4_T178_THREE_LAB_COMMON_TARGET_ADMISSION.json"
    OUTPUT_RELATIVE = "reports/review_round_4/three_lab_common_target/v1.0.0"
    STATUS = "THREE_INDEPENDENT_LABORATORY_COMMON_TARGET_VERIFIED_DEVELOPMENT_ONLY"
    REQUIRED_TOP_LEVEL = {
        "schema_version",
        "audit_id",
        "evaluated_at",
        "evidence_class",
        "allowed_claim_level",
        "status",
        "target_definition",
        "common_rank_ledger",
        "sources",
        "claim_boundary",
        "scientific_submission_ready",
    }
    REQUIRED_LEDGER_FIELDS = {
        "target_observation_id",
        "source_id",
        "canonical_accession",
        "laboratory_anchor",
        "measurement_batch_id",
        "source_analysis_unit_id",
        "source_measurement_id",
        "source_identifier",
        "source_asset_id",
        "source_worksheet",
        "source_row",
        "source_coordinate",
        "author_quantity_type",
        "author_numeric_value",
        "author_value_state",
        "rank_percentile_descending",
        "measurement_batch_positive_protein_count",
        "rank_target_eligible",
        "common_rank_target_member",
    }
    REQUIRED_MAP_FIELDS = {
        "analysis_unit_id",
        "source_article_doi",
        "source_pmcid",
        "source_license",
        "source_asset_id",
        "source_worksheet",
        "source_row",
    }

    def __init__(self, root: Path, *, registry_path: Path | None = None, output_root: Path | None = None) -> None:
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
            raise R4ThreeLabCommonTargetAuditError(f"cannot parse {label}") from exc

    def _root_file(self, relative_path: str, label: str) -> Path:
        if "\\" in relative_path:
            raise R4ThreeLabCommonTargetAuditError(f"{label} must use POSIX path separators")
        pure = PurePosixPath(relative_path)
        if pure.is_absolute() or not pure.parts or ".." in pure.parts:
            raise R4ThreeLabCommonTargetAuditError(f"{label} escapes repository root")
        path = (self.root / Path(*pure.parts)).resolve(strict=False)
        if not path.is_relative_to(self.root) or not path.is_file():
            raise R4ThreeLabCommonTargetAuditError(f"{label} is missing or outside repository root")
        return path

    def _reference(self, value: Any, label: str) -> tuple[Path, dict[str, Any]]:
        item = _mapping(value, label)
        if set(item) != {"relative_path", "sha256"}:
            raise R4ThreeLabCommonTargetAuditError(f"{label} fields are invalid")
        path = self._root_file(_string(item["relative_path"], label), label)
        if _sha256(path) != _checksum(item["sha256"], label):
            raise R4ThreeLabCommonTargetAuditError(f"{label} checksum differs")
        return path, item

    def _registry(self) -> tuple[dict[str, Any], Path, list[dict[str, Any]]]:
        registry = self._json(self.registry_path, "T178 registry")
        if set(registry) != self.REQUIRED_TOP_LEVEL or registry.get("schema_version") != 1:
            raise R4ThreeLabCommonTargetAuditError("registry fields are invalid")
        if registry.get("audit_id") != self.AUDIT_ID or registry.get("status") != self.STATUS:
            raise R4ThreeLabCommonTargetAuditError("registry identity is invalid")
        if (
            registry.get("evidence_class") != "DEVELOPMENT_OBSERVATION"
            or registry.get("allowed_claim_level") != "EXPLORATORY"
            or registry.get("scientific_submission_ready") is not False
        ):
            raise R4ThreeLabCommonTargetAuditError("registry evidence boundary is invalid")
        ledger_item = _mapping(registry.get("common_rank_ledger"), "common rank ledger")
        if not {"relative_path", "sha256"}.issubset(ledger_item):
            raise R4ThreeLabCommonTargetAuditError("common rank ledger reference is incomplete")
        ledger = self._root_file(_string(ledger_item["relative_path"], "common rank ledger"), "common rank ledger")
        if _sha256(ledger) != _checksum(ledger_item["sha256"], "common rank ledger"):
            raise R4ThreeLabCommonTargetAuditError("common rank ledger checksum differs")
        sources = registry.get("sources")
        if not isinstance(sources, list) or len(sources) != 3:
            raise R4ThreeLabCommonTargetAuditError("registry must contain exactly three sources")
        return registry, ledger, [_mapping(item, "source admission entry") for item in sources]

    def _source_inputs(self, entry: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any], Path, Path]:
        expected = {
            "source_id",
            "laboratory_anchor",
            "article",
            "source_registry",
            "source_audit_report",
            "source_audit_receipt",
            "source_cell_map",
            "expected_common_rank_observations",
            "expected_common_target_count",
            "expected_measurement_batch_count",
            "source_unit_boundary",
        }
        if set(entry) != expected:
            raise R4ThreeLabCommonTargetAuditError("source admission fields are invalid")
        article = _mapping(entry.get("article"), "source article")
        if set(article) != {"doi", "pmcid", "license", "locator"} or article.get("license") != "CC-BY-4.0":
            raise R4ThreeLabCommonTargetAuditError("source article license is not explicit CC-BY-4.0")
        registry_path, _ = self._reference(entry["source_registry"], f"{entry['source_id']} registry")
        report_path, _ = self._reference(entry["source_audit_report"], f"{entry['source_id']} audit report")
        receipt_path, _ = self._reference(entry["source_audit_receipt"], f"{entry['source_id']} audit receipt")
        map_path, _ = self._reference(entry["source_cell_map"], f"{entry['source_id']} source-cell map")
        source_registry = self._json(registry_path, f"{entry['source_id']} source registry")
        source = _mapping(source_registry.get("source"), f"{entry['source_id']} source")
        if source.get("license") != "CC-BY-4.0":
            raise R4ThreeLabCommonTargetAuditError(f"{entry['source_id']} source registry license differs")
        if source.get("doi") != article["doi"] or source.get("pmcid") != article["pmcid"]:
            raise R4ThreeLabCommonTargetAuditError(f"{entry['source_id']} source article identity differs")
        report = self._json(report_path, f"{entry['source_id']} source audit report")
        receipt = self._json(receipt_path, f"{entry['source_id']} source audit receipt")
        if (
            report.get("scientific_submission_ready") is not False
            or receipt.get("scientific_submission_ready") is not False
        ):
            raise R4ThreeLabCommonTargetAuditError(f"{entry['source_id']} readiness boundary differs")
        if receipt.get("report_sha256") != _sha256(report_path):
            raise R4ThreeLabCommonTargetAuditError(f"{entry['source_id']} audit receipt does not close report")
        map_info = _mapping(report.get("source_to_cell_map"), f"{entry['source_id']} report source map")
        if map_info.get("sha256") != _sha256(map_path):
            raise R4ThreeLabCommonTargetAuditError(f"{entry['source_id']} report map hash differs")
        return source_registry, report, map_path, receipt_path

    def _read_map(self, path: Path, source_id: str, laboratory_anchor: str, article: Mapping[str, Any]) -> int:
        with path.open(newline="", encoding="utf-8") as stream:
            reader = csv.DictReader(stream)
            if reader.fieldnames is None or not self.REQUIRED_MAP_FIELDS.issubset(reader.fieldnames):
                raise R4ThreeLabCommonTargetAuditError(f"{source_id} source map schema is invalid")
            coordinate_field = "source_cell" if "source_cell" in reader.fieldnames else "source_cell_range"
            identifier_field = (
                "protein_source_identifier"
                if "protein_source_identifier" in reader.fieldnames
                else "protein_ids"
                if "protein_ids" in reader.fieldnames
                else None
            )
            if identifier_field is None:
                raise R4ThreeLabCommonTargetAuditError(f"{source_id} source map identifier field is missing")
            count = 0
            for row in reader:
                count += 1
                for field in self.REQUIRED_MAP_FIELDS:
                    if not str(row.get(field, "")).strip():
                        raise R4ThreeLabCommonTargetAuditError(f"{source_id} source map has blank {field}")
                if (
                    row["source_article_doi"] != article["doi"]
                    or row["source_pmcid"] != article["pmcid"]
                    or row["source_license"] != article["license"]
                ):
                    raise R4ThreeLabCommonTargetAuditError(f"{source_id} source map identity differs")
                if not row.get(coordinate_field, "").strip() or not row.get(identifier_field, "").strip():
                    raise R4ThreeLabCommonTargetAuditError(f"{source_id} source map provenance is incomplete")
        if count == 0:
            raise R4ThreeLabCommonTargetAuditError(f"{source_id} source map is empty")
        return count

    def _ledger_counts(self, path: Path, entries: list[dict[str, Any]]) -> dict[str, Any]:
        declared = {entry["source_id"]: entry for entry in entries}
        with path.open(newline="", encoding="utf-8") as stream:
            reader = csv.DictReader(stream)
            if reader.fieldnames is None or set(reader.fieldnames) != self.REQUIRED_LEDGER_FIELDS:
                raise R4ThreeLabCommonTargetAuditError("common rank ledger schema is invalid")
            rows = list(reader)
        by_source: dict[str, list[dict[str, str]]] = defaultdict(list)
        for row in rows:
            source_id = row["source_id"]
            if source_id not in declared:
                raise R4ThreeLabCommonTargetAuditError("ledger contains an undeclared source")
            if row["laboratory_anchor"] != declared[source_id]["laboratory_anchor"]:
                raise R4ThreeLabCommonTargetAuditError("ledger laboratory anchor differs")
            if row["common_rank_target_member"] == "true" and row["rank_target_eligible"] == "true":
                try:
                    rank = float(row["rank_percentile_descending"])
                except ValueError as exc:
                    raise R4ThreeLabCommonTargetAuditError("common rank percentile is not numeric") from exc
                if not 0.0 <= rank <= 1.0:
                    continue
                for field in (
                    "source_coordinate",
                    "source_worksheet",
                    "source_row",
                    "canonical_accession",
                    "measurement_batch_id",
                ):
                    if not row[field].strip():
                        raise R4ThreeLabCommonTargetAuditError(f"ledger common row has blank {field}")
                by_source[source_id].append(row)
        if set(by_source) != set(declared):
            raise R4ThreeLabCommonTargetAuditError("ledger does not contain all declared sources")
        target_sets = {
            source_id: {row["canonical_accession"] for row in values} for source_id, values in by_source.items()
        }
        intersection = set.intersection(*target_sets.values())
        batch_counts = {
            source_id: len({row["measurement_batch_id"] for row in values}) for source_id, values in by_source.items()
        }
        observation_counts = {source_id: len(values) for source_id, values in by_source.items()}
        expected = _mapping(json.loads(self.registry_path.read_text(encoding="utf-8")), "T178 registry")
        ledger_contract = _mapping(expected["common_rank_ledger"], "common rank ledger")
        if (
            len(rows) != ledger_contract["expected_selected_source_row_count"]
            or len(intersection) != ledger_contract["expected_common_target_count"]
        ):
            raise R4ThreeLabCommonTargetAuditError("common ledger total accounting differs")
        for source_id, entry in declared.items():
            if (
                observation_counts[source_id] != entry["expected_common_rank_observations"]
                or len(target_sets[source_id]) != entry["expected_common_target_count"]
                or batch_counts[source_id] != entry["expected_measurement_batch_count"]
            ):
                raise R4ThreeLabCommonTargetAuditError(f"{source_id} common ledger accounting differs")
        if (
            sum(observation_counts.values()) != ledger_contract["expected_common_rank_observation_count"]
            or sum(batch_counts.values()) != ledger_contract["expected_measurement_batch_count"]
        ):
            raise R4ThreeLabCommonTargetAuditError("common ledger aggregate accounting differs")
        return {
            "selected_source_row_count": len(rows),
            "common_rank_observation_count": sum(observation_counts.values()),
            "common_target_count": len(intersection),
            "measurement_batch_count": sum(batch_counts.values()),
            "source_observation_counts": observation_counts,
            "source_target_counts": {key: len(value) for key, value in target_sets.items()},
            "source_batch_counts": batch_counts,
            "laboratory_anchor_count": len({entry["laboratory_anchor"] for entry in entries}),
            "source_count": len(entries),
        }

    def _execute(self) -> tuple[dict[str, Any], dict[str, Any]]:
        registry, ledger_path, entries = self._registry()
        source_reports: dict[str, Any] = {}
        source_cell_counts: dict[str, int] = {}
        for entry in entries:
            _, report, map_path, _ = self._source_inputs(entry)
            source_cell_counts[entry["source_id"]] = self._read_map(
                map_path, entry["source_id"], entry["laboratory_anchor"], entry["article"]
            )
            source_reports[entry["source_id"]] = {
                "laboratory_anchor": entry["laboratory_anchor"],
                "article": entry["article"],
                "audit_id": report["audit_id"],
                "source_cell_count": source_cell_counts[entry["source_id"]],
            }
        totals = self._ledger_counts(ledger_path, entries)
        report = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "status": self.STATUS,
            "evidence_class": "DEVELOPMENT_OBSERVATION",
            "allowed_claim_level": "EXPLORATORY",
            "scientific_submission_ready": False,
            "input_references": {
                "registry": {
                    "relative_path": self.registry_path.relative_to(self.root).as_posix(),
                    "sha256": _sha256(self.registry_path),
                },
                "common_rank_ledger": {
                    "relative_path": ledger_path.relative_to(self.root).as_posix(),
                    "sha256": _sha256(ledger_path),
                },
            },
            "sources": source_reports,
            "source_cell_count_by_source": source_cell_counts,
            **totals,
            "claim_boundary": registry["claim_boundary"],
        }
        return report, registry

    def run(self, *, strict: bool = False) -> R4ThreeLabCommonTargetAuditSummary:
        if not strict:
            raise R4ThreeLabCommonTargetAuditError("T178 three-laboratory audit requires --strict")
        if self.output_root.exists():
            raise R4ThreeLabCommonTargetAuditError("T178 audit already executed")
        report, _ = self._execute()
        self.output_root.mkdir(parents=True, exist_ok=False)
        report_path = self.output_root / "three_lab_common_target_report.json"
        self._write(report_path, report)
        receipt = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "status": self.STATUS,
            "report_sha256": _sha256(report_path),
            "source_count": report["source_count"],
            "laboratory_anchor_count": report["laboratory_anchor_count"],
            "common_target_count": report["common_target_count"],
            "common_rank_observation_count": report["common_rank_observation_count"],
            "selected_source_row_count": report["selected_source_row_count"],
            "measurement_batch_count": report["measurement_batch_count"],
            "source_cell_count_by_source": report["source_cell_count_by_source"],
            "scientific_submission_ready": False,
        }
        receipt_path = self.output_root / "three_lab_common_target_receipt.json"
        self._write(receipt_path, receipt)
        return R4ThreeLabCommonTargetAuditSummary(
            report["source_count"],
            report["laboratory_anchor_count"],
            report["common_target_count"],
            report["common_rank_observation_count"],
            report["selected_source_row_count"],
            report["measurement_batch_count"],
            sum(report["source_cell_count_by_source"].values()),
            receipt_path,
        )

    def verify(self) -> R4ThreeLabCommonTargetAuditSummary:
        report_path = self.output_root / "three_lab_common_target_report.json"
        receipt_path = self.output_root / "three_lab_common_target_receipt.json"
        report = self._json(report_path, "T178 report")
        receipt = self._json(receipt_path, "T178 receipt")
        if (
            report.get("audit_id") != self.AUDIT_ID
            or report.get("status") != self.STATUS
            or receipt.get("audit_id") != self.AUDIT_ID
            or receipt.get("status") != self.STATUS
            or receipt.get("report_sha256") != _sha256(report_path)
            or receipt.get("scientific_submission_ready") is not False
        ):
            raise R4ThreeLabCommonTargetAuditError("T178 receipt identity or report hash differs")
        recomputed, _ = self._execute()
        comparable = (
            "source_count",
            "laboratory_anchor_count",
            "common_target_count",
            "common_rank_observation_count",
            "selected_source_row_count",
            "measurement_batch_count",
            "source_cell_count_by_source",
        )
        if any(report.get(key) != recomputed.get(key) or receipt.get(key) != recomputed.get(key) for key in comparable):
            raise R4ThreeLabCommonTargetAuditError("T178 accounting differs from current inputs")
        return R4ThreeLabCommonTargetAuditSummary(
            recomputed["source_count"],
            recomputed["laboratory_anchor_count"],
            recomputed["common_target_count"],
            recomputed["common_rank_observation_count"],
            recomputed["selected_source_row_count"],
            recomputed["measurement_batch_count"],
            sum(recomputed["source_cell_count_by_source"].values()),
            receipt_path,
        )
