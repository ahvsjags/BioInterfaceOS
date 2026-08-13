"""Audit effective sampling units and missingness for the R4 OOD candidate."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class R4OODEffectiveNAuditError(RuntimeError):
    """Raised when the frozen R4 effective-n audit cannot run safely."""


@dataclass(frozen=True)
class R4OODEffectiveNAuditSummary:
    """Summary of the aggregate effective-n and missingness audit."""

    status: str
    source_row_count: int
    measurement_batch_count: int
    primary_rank_eligible_batch_count: int
    biological_unit_count: int
    laboratory_count: int
    report_path: Path


class R4OODEffectiveNAuditWorkflow:
    """Run a non-promoting effective-n and missingness audit on a frozen source map."""

    PROTOCOL_RELATIVE = "docs/data/R4_T174_OOD_EFFECTIVE_N_MISSINGNESS_PROTOCOL.json"
    DEFAULT_SOURCE_MAP = (
        "data/raw/r4_candidate_pmc11544298/derived/"
        "R4_PMC11544298_small_molecule_corona_source_cell_map.csv"
    )
    DEFAULT_OUTPUT = "reports/review_round_4/small_molecule_corona_effective_n/v1.0.0"
    AUDIT_ID = "bioif-r4-ood-effective-n-missingness-v1.0.0"
    STATUS = "R4_OOD_EFFECTIVE_N_MISSINGNESS_AUDITED_EXPLORATORY"
    REQUIRED_COLUMNS = {
        "source_id",
        "laboratory_anchor",
        "source_asset_id",
        "measurement_batch_id",
        "biological_unit_id",
        "condition_label",
        "analysis_candidate_eligible",
        "author_value_state",
        "rank_target_eligible",
    }

    def __init__(
        self,
        root: Path,
        *,
        source_map_path: Path | None = None,
        protocol_path: Path | None = None,
        output_root: Path | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.source_map_path = (source_map_path or self.root / self.DEFAULT_SOURCE_MAP).resolve(
            strict=False
        )
        self.protocol_path = protocol_path or self.root / self.PROTOCOL_RELATIVE
        self.output_root = output_root or self.root / self.DEFAULT_OUTPUT

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()

    @staticmethod
    def _json(path: Path, label: str) -> dict[str, Any]:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise R4OODEffectiveNAuditError(f"cannot parse {label}") from exc
        if not isinstance(value, dict):
            raise R4OODEffectiveNAuditError(f"{label} must be an object")
        return value

    @staticmethod
    def _checksum(value: Any, label: str) -> str:
        if not isinstance(value, str) or len(value) != 64:
            raise R4OODEffectiveNAuditError(f"{label} must be a SHA-256 digest")
        if any(character not in "0123456789abcdef" for character in value):
            raise R4OODEffectiveNAuditError(f"{label} must be lowercase hexadecimal")
        return value

    def _root_file(self, relative_path: str, label: str) -> Path:
        path = (self.root / Path(*Path(relative_path).parts)).resolve(strict=False)
        if Path(relative_path).is_absolute() or ".." in Path(relative_path).parts:
            raise R4OODEffectiveNAuditError(f"{label} must be a safe relative path")
        if not path.is_relative_to(self.root) or not path.is_file():
            raise R4OODEffectiveNAuditError(f"{label} is missing or outside the repository")
        return path

    def _protocol(self) -> dict[str, Any]:
        protocol = self._json(self.protocol_path, "R4 effective-n protocol")
        required = {
            "schema_version",
            "protocol_id",
            "frozen_at",
            "evidence_class",
            "allowed_claim_level",
            "source_map",
            "upstream_ood_protocol",
            "eligibility",
            "effective_n_groups",
            "pooled_unit_rule",
            "threshold_sensitivity",
            "missingness_outputs",
            "claim_boundary",
        }
        if set(protocol) != required or protocol["schema_version"] != 1:
            raise R4OODEffectiveNAuditError("R4 effective-n protocol fields are invalid")
        if (
            protocol["protocol_id"] != self.AUDIT_ID
            or protocol["evidence_class"] != "DEVELOPMENT_OBSERVATION"
            or protocol["allowed_claim_level"] != "EXPLORATORY"
        ):
            raise R4OODEffectiveNAuditError("R4 effective-n protocol identity is invalid")
        source_ref = protocol["source_map"]
        if not isinstance(source_ref, dict) or set(source_ref) != {"relative_path", "sha256"}:
            raise R4OODEffectiveNAuditError("R4 effective-n source reference is invalid")
        source_path = self._root_file(source_ref["relative_path"], "R4 source map")
        if source_path != self.source_map_path:
            raise R4OODEffectiveNAuditError("R4 source map path differs from frozen protocol")
        if self._sha256(source_path) != self._checksum(source_ref["sha256"], "R4 source map"):
            raise R4OODEffectiveNAuditError("R4 source map checksum differs")
        upstream_ref = protocol["upstream_ood_protocol"]
        if not isinstance(upstream_ref, dict) or set(upstream_ref) != {"relative_path", "sha256"}:
            raise R4OODEffectiveNAuditError("R4 upstream protocol reference is invalid")
        upstream_path = self._root_file(upstream_ref["relative_path"], "R4 upstream protocol")
        if self._sha256(upstream_path) != self._checksum(
            upstream_ref["sha256"], "R4 upstream protocol"
        ):
            raise R4OODEffectiveNAuditError("R4 upstream protocol checksum differs")
        eligibility = protocol["eligibility"]
        if not isinstance(eligibility, dict) or set(eligibility) != {
            "analysis_candidate_flag",
            "rank_target_flag",
            "source_na_policy",
            "primary_minimum_rank_eligible_proteins_per_batch",
        }:
            raise R4OODEffectiveNAuditError("R4 eligibility contract is invalid")
        if eligibility["primary_minimum_rank_eligible_proteins_per_batch"] != 10:
            raise R4OODEffectiveNAuditError("R4 primary minimum batch threshold changed")
        thresholds = protocol["threshold_sensitivity"]
        if not isinstance(thresholds, dict) or thresholds != {
            "minimum_rank_eligible_proteins_per_batch": [1, 10, 20, 40, 50, 60, 70, 80]
        }:
            raise R4OODEffectiveNAuditError("R4 threshold sensitivity contract is invalid")
        return protocol

    def _rows(self) -> list[dict[str, str]]:
        if not self.source_map_path.is_file():
            raise R4OODEffectiveNAuditError("R4 source map is missing")
        try:
            with self.source_map_path.open("r", encoding="utf-8", newline="") as stream:
                rows = list(csv.DictReader(stream))
        except OSError as exc:
            raise R4OODEffectiveNAuditError("cannot read R4 source map") from exc
        if not rows or not self.REQUIRED_COLUMNS.issubset(rows[0]):
            raise R4OODEffectiveNAuditError("R4 source map schema is incomplete")
        return rows

    @staticmethod
    def _unit_class(unit_id: str) -> str:
        return "POOLED" if "POOLED" in unit_id.upper() else "DONOR_LABELLED"

    @staticmethod
    def _rate(numerator: int, denominator: int) -> float | None:
        return None if denominator == 0 else numerator / denominator

    @staticmethod
    def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
        with path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fieldnames, extrasaction="raise")
            writer.writeheader()
            writer.writerows(rows)

    @staticmethod
    def _write_json(path: Path, value: Any) -> None:
        path.write_text(
            json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )

    def run(self, *, strict: bool = False) -> R4OODEffectiveNAuditSummary:
        if not strict:
            raise R4OODEffectiveNAuditError("R4 effective-n audit requires --strict")
        if self.output_root.exists():
            raise R4OODEffectiveNAuditError("R4 effective-n audit already executed")
        protocol = self._protocol()
        rows = self._rows()
        by_batch: dict[str, list[dict[str, str]]] = defaultdict(list)
        by_unit: dict[str, list[dict[str, str]]] = defaultdict(list)
        for row in rows:
            by_batch[row["measurement_batch_id"]].append(row)
            by_unit[row["biological_unit_id"]].append(row)
        primary_threshold = protocol["eligibility"][
            "primary_minimum_rank_eligible_proteins_per_batch"
        ]
        batch_summary: list[dict[str, Any]] = []
        for batch_id in sorted(by_batch):
            batch = by_batch[batch_id]
            rank_count = sum(row["rank_target_eligible"] == "true" for row in batch)
            analysis_count = sum(row["analysis_candidate_eligible"] == "true" for row in batch)
            source_na_count = sum(row["author_value_state"] == "SOURCE_NA" for row in batch)
            batch_summary.append(
                {
                    "measurement_batch_id": batch_id,
                    "biological_unit_id": sorted({row["biological_unit_id"] for row in batch}),
                    "condition_labels": sorted({row["condition_label"] for row in batch}),
                    "source_asset_ids": sorted({row["source_asset_id"] for row in batch}),
                    "raw_row_count": len(batch),
                    "analysis_candidate_row_count": analysis_count,
                    "rank_target_eligible_row_count": rank_count,
                    "source_na_row_count": source_na_count,
                    "primary_rank_eligible": rank_count >= primary_threshold,
                    "rank_retention_rate": self._rate(rank_count, analysis_count),
                }
            )
        unit_summary: list[dict[str, Any]] = []
        for unit_id in sorted(by_unit):
            unit = by_unit[unit_id]
            unit_batches = [item for item in batch_summary if unit_id in item["biological_unit_id"]]
            analysis_count = sum(row["analysis_candidate_eligible"] == "true" for row in unit)
            rank_count = sum(row["rank_target_eligible"] == "true" for row in unit)
            source_na_count = sum(row["author_value_state"] == "SOURCE_NA" for row in unit)
            unit_summary.append(
                {
                    "biological_unit_id": unit_id,
                    "unit_class": self._unit_class(unit_id),
                    "laboratory_count": len({row["laboratory_anchor"] for row in unit}),
                    "source_asset_count": len({row["source_asset_id"] for row in unit}),
                    "condition_count": len({row["condition_label"] for row in unit}),
                    "measurement_batch_count": len(unit_batches),
                    "primary_rank_eligible_batch_count": sum(
                        item["primary_rank_eligible"] for item in unit_batches
                    ),
                    "raw_row_count": len(unit),
                    "analysis_candidate_row_count": analysis_count,
                    "rank_target_eligible_row_count": rank_count,
                    "source_na_row_count": source_na_count,
                    "rank_retention_rate": self._rate(rank_count, analysis_count),
                }
            )
        thresholds = protocol["threshold_sensitivity"]["minimum_rank_eligible_proteins_per_batch"]
        threshold_summary: list[dict[str, Any]] = []
        for threshold in thresholds:
            retained = [
                item for item in batch_summary
                if item["rank_target_eligible_row_count"] >= threshold
            ]
            threshold_summary.append(
                {
                    "minimum_rank_eligible_proteins_per_batch": threshold,
                    "measurement_batch_count": len(retained),
                    "rank_target_eligible_row_count": sum(
                        item["rank_target_eligible_row_count"] for item in retained
                    ),
                    "biological_unit_count": len({
                        unit for item in retained for unit in item["biological_unit_id"]
                    }),
                    "laboratory_count": len({
                        lab for item in retained for row in by_batch[item["measurement_batch_id"]]
                        for lab in [row["laboratory_anchor"]]
                    }),
                }
            )
        state_counts = Counter(row["author_value_state"] for row in rows)
        analysis_counts = Counter(row["analysis_candidate_eligible"] for row in rows)
        rank_counts = Counter(row["rank_target_eligible"] for row in rows)
        primary_batches = [item for item in batch_summary if item["primary_rank_eligible"]]
        laboratories = {row["laboratory_anchor"] for row in rows}
        units = {row["biological_unit_id"] for row in rows}
        pooled_units = {unit for unit in units if self._unit_class(unit) == "POOLED"}
        donor_units = units - pooled_units
        effective_n = {
            "raw_source_row_count": len(rows),
            "analysis_candidate_row_count": analysis_counts["true"],
            "rank_target_eligible_row_count": rank_counts["true"],
            "measurement_batch_count": len(by_batch),
            "primary_rank_eligible_batch_count": len(primary_batches),
            "laboratory_count": len(laboratories),
            "biological_unit_count": len(units),
            "pooled_unit_count": len(pooled_units),
            "donor_labelled_unit_count": len(donor_units),
            "condition_label_count": len({row["condition_label"] for row in rows}),
            "unit_condition_stratum_count": len({
                (row["biological_unit_id"], row["condition_label"]) for row in rows
            }),
            "primary_rank_eligible_biological_unit_count": len({
                unit for item in primary_batches for unit in item["biological_unit_id"]
            }),
            "primary_rank_eligible_laboratory_count": len(laboratories),
            "pooled_primary_batch_count": sum(
                any(self._unit_class(unit) == "POOLED" for unit in item["biological_unit_id"])
                for item in primary_batches
            ),
            "donor_primary_batch_count": sum(
                any(
                    self._unit_class(unit) == "DONOR_LABELLED"
                    for unit in item["biological_unit_id"]
                )
                for item in primary_batches
            ),
        }
        output_rows = [
            {
                "biological_unit_id": item["biological_unit_id"],
                "unit_class": item["unit_class"],
                "laboratory_count": item["laboratory_count"],
                "source_asset_count": item["source_asset_count"],
                "condition_count": item["condition_count"],
                "measurement_batch_count": item["measurement_batch_count"],
                "primary_rank_eligible_batch_count": item["primary_rank_eligible_batch_count"],
                "raw_row_count": item["raw_row_count"],
                "analysis_candidate_row_count": item["analysis_candidate_row_count"],
                "rank_target_eligible_row_count": item["rank_target_eligible_row_count"],
                "source_na_row_count": item["source_na_row_count"],
                "rank_retention_rate": item["rank_retention_rate"],
            }
            for item in unit_summary
        ]
        batch_output_rows = [
            {
                **item,
                "biological_unit_id": "|".join(item["biological_unit_id"]),
                "condition_labels": "|".join(item["condition_labels"]),
                "source_asset_ids": "|".join(item["source_asset_ids"]),
            }
            for item in batch_summary
        ]
        self.output_root.mkdir(parents=True)
        unit_path = self.output_root / "r4_external_effective_n_by_unit.csv"
        batch_path = self.output_root / "r4_external_batch_missingness.csv"
        self._write_csv(unit_path, list(output_rows[0]), output_rows)
        self._write_csv(batch_path, list(batch_output_rows[0]), batch_output_rows)
        report = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "protocol_id": protocol["protocol_id"],
            "protocol_sha256": self._sha256(self.protocol_path),
            "source_map_sha256": self._sha256(self.source_map_path),
            "status": self.STATUS,
            "evidence_class": protocol["evidence_class"],
            "allowed_claim_level": protocol["allowed_claim_level"],
            "effective_n": effective_n,
            "source_value_state_counts": dict(sorted(state_counts.items())),
            "analysis_candidate_flag_counts": dict(sorted(analysis_counts.items())),
            "rank_target_flag_counts": dict(sorted(rank_counts.items())),
            "unit_summary": unit_summary,
            "threshold_sensitivity": threshold_summary,
            "batch_summary": batch_summary,
            "artifacts": {
                "effective_n_by_unit": {
                    "relative_path": unit_path.relative_to(self.root).as_posix(),
                    "sha256": self._sha256(unit_path),
                },
                "batch_missingness": {
                    "relative_path": batch_path.relative_to(self.root).as_posix(),
                    "sha256": self._sha256(batch_path),
                },
            },
            "independent_validation": False,
            "external_scientific_reproduction": False,
            "scientific_submission_ready": False,
            "claim_boundary": protocol["claim_boundary"],
        }
        report_path = self.output_root / "r4_external_effective_n_missingness_report.json"
        self._write_json(report_path, report)
        receipt = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "status": self.STATUS,
            "report_sha256": self._sha256(report_path),
            "source_row_count": len(rows),
            "measurement_batch_count": len(by_batch),
            "primary_rank_eligible_batch_count": len(primary_batches),
            "biological_unit_count": len(units),
            "laboratory_count": len(laboratories),
            "independent_validation": False,
            "external_scientific_reproduction": False,
            "scientific_submission_ready": False,
        }
        self._write_json(
            self.output_root / "r4_external_effective_n_missingness_receipt.json", receipt
        )
        return R4OODEffectiveNAuditSummary(
            self.STATUS,
            len(rows),
            len(by_batch),
            len(primary_batches),
            len(units),
            len(laboratories),
            report_path,
        )

    def verify(self) -> R4OODEffectiveNAuditSummary:
        """Verify the aggregate report, receipt and two CSV artifact hashes."""
        protocol = self._protocol()
        report_path = self.output_root / "r4_external_effective_n_missingness_report.json"
        receipt_path = self.output_root / "r4_external_effective_n_missingness_receipt.json"
        report = self._json(report_path, "R4 effective-n report")
        receipt = self._json(receipt_path, "R4 effective-n receipt")
        artifacts = report.get("artifacts")
        if not isinstance(artifacts, dict) or set(artifacts) != {
            "effective_n_by_unit",
            "batch_missingness",
        }:
            raise R4OODEffectiveNAuditError("R4 effective-n artifacts are invalid")
        for item in artifacts.values():
            if not isinstance(item, dict) or set(item) != {"relative_path", "sha256"}:
                raise R4OODEffectiveNAuditError("R4 effective-n artifact reference is invalid")
            path = self._root_file(item["relative_path"], "R4 effective-n artifact")
            if self._sha256(path) != self._checksum(item["sha256"], "R4 effective-n artifact"):
                raise R4OODEffectiveNAuditError("R4 effective-n artifact checksum differs")
        effective_n = report.get("effective_n")
        if not isinstance(effective_n, dict):
            raise R4OODEffectiveNAuditError("R4 effective-n summary is missing")
        if (
            report.get("audit_id") != self.AUDIT_ID
            or report.get("protocol_id") != protocol["protocol_id"]
            or report.get("status") != self.STATUS
            or report.get("scientific_submission_ready") is not False
            or report.get("independent_validation") is not False
            or report.get("external_scientific_reproduction") is not False
            or receipt.get("audit_id") != self.AUDIT_ID
            or receipt.get("status") != self.STATUS
            or receipt.get("report_sha256") != self._sha256(report_path)
            or receipt.get("scientific_submission_ready") is not False
        ):
            raise R4OODEffectiveNAuditError("R4 effective-n receipt is invalid")
        return R4OODEffectiveNAuditSummary(
            self.STATUS,
            int(receipt["source_row_count"]),
            int(receipt["measurement_batch_count"]),
            int(receipt["primary_rank_eligible_batch_count"]),
            int(receipt["biological_unit_count"]),
            int(receipt["laboratory_count"]),
            report_path,
        )
