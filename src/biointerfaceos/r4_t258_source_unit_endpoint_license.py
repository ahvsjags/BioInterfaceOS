"""Audit biological-unit semantics, endpoint compatibility and license reuse.

T258 is a bounded accounting audit over the frozen T249 four-source paper-data
asset.  It deliberately separates laboratory/source provenance from biological
independence and separates a source-local rank endpoint from a calibrated
cross-source biological effect endpoint.
"""

from __future__ import annotations

import csv
import hashlib
import itertools
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class R4T258SourceUnitEndpointLicenseError(RuntimeError):
    """Raised when the frozen T258 accounting cannot be reproduced."""


@dataclass(frozen=True)
class R4T258SourceUnitEndpointLicenseSummary:
    """Summary returned by the T258 run and verify operations."""

    source_count: int
    source_cell_count: int
    rank_eligible_cell_count: int
    encoded_biological_unit_count: int
    source_unit_ledger_path: Path
    endpoint_matrix_path: Path
    receipt_path: Path


class R4T258SourceUnitEndpointLicenseWorkflow:
    """Recompute and verify the source-unit and endpoint accounting."""

    AUDIT_ID = "bioif-r4-t258-source-unit-endpoint-license-v1.0.0"
    PROTOCOL_RELATIVE = "docs/data/R4_T258_SOURCE_UNIT_ENDPOINT_LICENSE_PROTOCOL.json"
    OUTPUT_RELATIVE = "reports/review_round_4/source_unit_endpoint_license/v1.0.0"
    STATUS = "SOURCE_UNIT_ENDPOINT_LICENSE_AUDIT_VERIFIED_RESTRICTED_DEVELOPMENT"
    LEDGER_FIELDS = (
        "source_id",
        "laboratory_anchor",
        "license",
        "source_locator",
        "license_status",
        "redistribution_class",
        "biological_unit_semantics",
        "reported_biological_unit_count",
        "reported_biological_unit_type",
        "encoded_biological_unit_count",
        "measurement_unit_count",
        "technical_replicate_count",
        "rank_eligible_row_count",
        "rank_eligible_target_count",
        "biological_unit_crosswalk_status",
        "rank_endpoint_status",
        "biological_effect_endpoint_status",
        "source_cell_map_sha256",
    )
    MATRIX_FIELDS = (
        "source_id_a",
        "source_id_b",
        "pair_common_target_count",
        "rank_endpoint_compatibility",
        "biological_effect_endpoint_compatibility",
        "cross_source_calibration",
        "interpretation",
    )

    def __init__(self, root: Path, *, output_root: Path | None = None) -> None:
        self.root = root.resolve()
        self.protocol_path = self.root / self.PROTOCOL_RELATIVE
        self.output_root = output_root.resolve() if output_root is not None else self.root / self.OUTPUT_RELATIVE

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()

    @staticmethod
    def _json(path: Path, label: str) -> dict[str, Any]:
        if not path.is_file():
            raise R4T258SourceUnitEndpointLicenseError(f"{label} is missing: {path}")
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise R4T258SourceUnitEndpointLicenseError(f"{label} must be a JSON object")
        return value

    @staticmethod
    def _relative(path: Path, root: Path) -> str:
        try:
            return path.relative_to(root).as_posix()
        except ValueError:
            # Tests may place the output contract in an isolated temporary
            # directory.  Source inputs are always required to remain under
            # the project root; generated output may be external by design.
            return path.as_posix()

    @staticmethod
    def _as_csv_value(value: Any) -> str:
        if value is None:
            return "UNKNOWN"
        if isinstance(value, bool):
            return "true" if value else "false"
        return str(value)

    def _protocol(self) -> dict[str, Any]:
        protocol = self._json(self.protocol_path, "T258 protocol")
        required = {
            "schema_version",
            "audit_id",
            "protocol_id",
            "status",
            "evidence_class",
            "allowed_claim_level",
            "input_t249",
            "sources",
            "endpoint_rules",
            "claim_boundary",
            "scientific_submission_ready",
        }
        if set(protocol) != required or protocol.get("schema_version") != 1:
            raise R4T258SourceUnitEndpointLicenseError("T258 protocol fields are invalid")
        if (
            protocol.get("audit_id") != self.AUDIT_ID
            or protocol.get("protocol_id") != self.AUDIT_ID
            or protocol.get("status") != "FROZEN_FOR_SOURCE_UNIT_ENDPOINT_LICENSE_AUDIT"
            or protocol.get("scientific_submission_ready") is not False
        ):
            raise R4T258SourceUnitEndpointLicenseError("T258 protocol identity or boundary is invalid")
        sources = protocol.get("sources")
        if not isinstance(sources, list) or len(sources) != 4:
            raise R4T258SourceUnitEndpointLicenseError("T258 protocol must contain exactly four sources")
        ids = [str(source.get("source_id", "")) for source in sources if isinstance(source, dict)]
        if len(ids) != 4 or len(set(ids)) != 4 or any(not source_id for source_id in ids):
            raise R4T258SourceUnitEndpointLicenseError("T258 source IDs must be unique and non-empty")
        return protocol

    def _validate_t249_input(self, protocol: dict[str, Any]) -> dict[str, Any]:
        input_t249 = protocol["input_t249"]
        if not isinstance(input_t249, dict):
            raise R4T258SourceUnitEndpointLicenseError("T249 input declaration is invalid")
        paths: dict[str, Path] = {}
        for key in ("report", "receipt", "ledger"):
            declaration = input_t249.get(key)
            if not isinstance(declaration, dict):
                raise R4T258SourceUnitEndpointLicenseError(f"T249 {key} declaration is invalid")
            path = self.root / str(declaration["relative_path"])
            expected_sha = str(declaration["sha256"])
            if self._sha256(path) != expected_sha:
                raise R4T258SourceUnitEndpointLicenseError(f"T249 {key} hash differs from frozen protocol")
            paths[key] = path
        report = self._json(paths["report"], "T249 report")
        receipt = self._json(paths["receipt"], "T249 receipt")
        if (
            report.get("source_count") != 4
            or report.get("laboratory_anchor_count") != 4
            or report.get("source_cell_count") != 15971
            or report.get("rank_eligible_cell_count") != 10852
            or report.get("common_target_count") != 7
            or report.get("scientific_submission_ready") is not False
            or receipt.get("scientific_submission_ready") is not False
        ):
            raise R4T258SourceUnitEndpointLicenseError("T249 accounting or claim boundary is invalid")
        return {"paths": paths, "report": report, "receipt": receipt}

    def _read_source_rows(self, source: dict[str, Any]) -> tuple[list[dict[str, str]], Path, str]:
        source_map = source.get("source_cell_map")
        if not isinstance(source_map, dict):
            raise R4T258SourceUnitEndpointLicenseError("source-cell-map declaration is invalid")
        path = self.root / str(source_map["relative_path"])
        observed_sha = self._sha256(path)
        if observed_sha != str(source_map["sha256"]):
            raise R4T258SourceUnitEndpointLicenseError(f"source-cell-map hash differs: {path}")
        with path.open(newline="", encoding="utf-8") as stream:
            rows = list(csv.DictReader(stream))
        if not rows:
            raise R4T258SourceUnitEndpointLicenseError(f"source-cell-map is empty: {path}")
        source_id = str(source["source_id"])
        if any(row.get("source_id") != source_id for row in rows):
            raise R4T258SourceUnitEndpointLicenseError(f"source-cell-map source IDs differ: {path}")
        if any(row.get("laboratory_anchor") != str(source["laboratory_anchor"]) for row in rows):
            raise R4T258SourceUnitEndpointLicenseError(f"laboratory anchors differ: {path}")
        return rows, path, observed_sha

    def _summarize_source(self, source: dict[str, Any]) -> tuple[dict[str, str], set[str]]:
        rows, path, map_sha = self._read_source_rows(source)
        eligible = [row for row in rows if row.get("rank_target_eligible", "").lower() == "true"]
        targets = {row.get("canonical_accession", "") for row in eligible}
        targets.discard("")
        batches = {row.get("measurement_batch_id", "") for row in eligible}
        batches.discard("")
        unit_field = source.get("biological_unit_field")
        placeholders = {str(value) for value in source.get("biological_unit_placeholders", [])}
        if unit_field is None:
            encoded_units: set[str] = set()
        else:
            encoded_units = {
                row.get(str(unit_field), "")
                for row in rows
                if row.get(str(unit_field), "") and row.get(str(unit_field), "") not in placeholders
            }
        technical_field = source.get("technical_replicate_field")
        technical_replicates = (
            {row.get(str(technical_field), "") for row in rows if row.get(str(technical_field), "")}
            if technical_field is not None
            else set()
        )
        expected = {
            "expected_row_count": len(rows),
            "expected_rank_eligible_row_count": len(eligible),
            "expected_rank_eligible_target_count": len(targets),
            "expected_rank_eligible_measurement_unit_count": len(batches),
            "expected_encoded_biological_unit_count": len(encoded_units),
            "expected_technical_replicate_count": len(technical_replicates) if technical_field is not None else None,
        }
        for key, observed in expected.items():
            declared = source.get(key)
            if observed != declared:
                raise R4T258SourceUnitEndpointLicenseError(
                    f"{source['source_id']} {key} differs: declared={declared!r} observed={observed!r}"
                )
        if source.get("license") not in {"CC-BY-3.0", "CC-BY-4.0", "CC0"}:
            raise R4T258SourceUnitEndpointLicenseError(f"unsupported T258 license: {source['license']}")
        ledger_row = {
            "source_id": str(source["source_id"]),
            "laboratory_anchor": str(source["laboratory_anchor"]),
            "license": str(source["license"]),
            "source_locator": str(source["source_locator"]),
            "license_status": "VERIFIED_PUBLIC_SOURCE_DECLARATION",
            "redistribution_class": str(source["redistribution_class"]),
            "biological_unit_semantics": str(source["biological_unit_semantics"]),
            "reported_biological_unit_count": self._as_csv_value(source.get("reported_biological_unit_count")),
            "reported_biological_unit_type": str(source["reported_biological_unit_type"]),
            "encoded_biological_unit_count": str(len(encoded_units)),
            "measurement_unit_count": str(len(batches)),
            "technical_replicate_count": self._as_csv_value(
                len(technical_replicates) if technical_field is not None else None
            ),
            "rank_eligible_row_count": str(len(eligible)),
            "rank_eligible_target_count": str(len(targets)),
            "biological_unit_crosswalk_status": str(source["biological_unit_crosswalk_status"]),
            "rank_endpoint_status": "COMPATIBLE_FOR_SOURCE_LOCAL_RANK_ANALYSIS",
            "biological_effect_endpoint_status": (
                "NOT_COMPARABLE_WITHOUT_EXPLICIT_HIERARCHICAL_MATERIAL_ASSAY_CONDITION_MODEL"
            ),
            "source_cell_map_sha256": map_sha,
        }
        return ledger_row, targets

    def _compute(self) -> tuple[dict[str, Any], list[dict[str, str]], list[dict[str, str]]]:
        protocol = self._protocol()
        t249 = self._validate_t249_input(protocol)
        source_rows: list[dict[str, str]] = []
        source_targets: dict[str, set[str]] = {}
        for source in protocol["sources"]:
            if not isinstance(source, dict):
                raise R4T258SourceUnitEndpointLicenseError("T258 source declaration is invalid")
            ledger_row, targets = self._summarize_source(source)
            source_rows.append(ledger_row)
            source_targets[str(source["source_id"])] = targets
        source_rows.sort(key=lambda row: row["source_id"])
        matrix_rows: list[dict[str, str]] = []
        for source_a, source_b in itertools.combinations(sorted(source_targets), 2):
            pair_targets = sorted(source_targets[source_a] & source_targets[source_b])
            matrix_rows.append(
                {
                    "source_id_a": source_a,
                    "source_id_b": source_b,
                    "pair_common_target_count": str(len(pair_targets)),
                    "rank_endpoint_compatibility": "CONDITIONALLY_COMPARABLE_AFTER_SOURCE_LOCAL_RANKING",
                    "biological_effect_endpoint_compatibility": (
                        "NOT_COMPARABLE_WITHOUT_EXPLICIT_HIERARCHICAL_MATERIAL_ASSAY_CONDITION_MODEL"
                    ),
                    "cross_source_calibration": "false",
                    "interpretation": (
                        "Portable source-local rank endpoint only; no pooled magnitude or "
                        "common biological-effect claim."
                    ),
                }
            )
        source_cell_count = sum(int(row["rank_eligible_row_count"]) for row in source_rows)
        full_source_cell_count = sum(
            int(source["expected_row_count"]) for source in protocol["sources"] if isinstance(source, dict)
        )
        encoded_units = sum(int(row["encoded_biological_unit_count"]) for row in source_rows)
        report = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "status": self.STATUS,
            "evidence_class": protocol["evidence_class"],
            "allowed_claim_level": protocol["allowed_claim_level"],
            "source_count": len(source_rows),
            "laboratory_anchor_count": len(source_rows),
            "source_cell_count": full_source_cell_count,
            "rank_eligible_cell_count": source_cell_count,
            "encoded_biological_unit_count": encoded_units,
            "reported_biological_unit_counts_are_not_additive": True,
            "source_unit_accounting": source_rows,
            "endpoint_compatibility": {
                "within_source_endpoint": protocol["endpoint_rules"]["within_source_endpoint"],
                "within_source_status": protocol["endpoint_rules"]["within_source_status"],
                "cross_source_rank_status": protocol["endpoint_rules"]["cross_source_rank_status"],
                "cross_source_biological_effect_status": protocol["endpoint_rules"][
                    "cross_source_biological_effect_status"
                ],
                "cross_source_calibration": False,
                "technical_replicates_as_independent_units": False,
                "pair_count": len(matrix_rows),
            },
            "license_accounting": {
                "all_sources_have_project_declared_reuse_class": True,
                "redistributable_source_count": len(source_rows),
                "cc_by_source_count": sum(row["license"].startswith("CC-BY") for row in source_rows),
                "cc0_source_count": sum(row["license"] == "CC0" for row in source_rows),
            },
            "input_references": {
                "protocol": {
                    "relative_path": self._relative(self.protocol_path, self.root),
                    "sha256": self._sha256(self.protocol_path),
                },
                "t249_report": {
                    "relative_path": self._relative(t249["paths"]["report"], self.root),
                    "sha256": self._sha256(t249["paths"]["report"]),
                },
                "t249_receipt": {
                    "relative_path": self._relative(t249["paths"]["receipt"], self.root),
                    "sha256": self._sha256(t249["paths"]["receipt"]),
                },
                "t249_ledger": {
                    "relative_path": self._relative(t249["paths"]["ledger"], self.root),
                    "sha256": self._sha256(t249["paths"]["ledger"]),
                },
            },
            "claim_boundary": protocol["claim_boundary"],
            "independent_validation": False,
            "external_scientific_reproduction": False,
            "external_user_adoption": False,
            "scientific_submission_ready": False,
        }
        return report, source_rows, matrix_rows

    @staticmethod
    def _write_json(path: Path, value: dict[str, Any]) -> None:
        path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")

    @staticmethod
    def _write_csv(path: Path, fieldnames: tuple[str, ...], rows: list[dict[str, str]]) -> None:
        with path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=fieldnames, extrasaction="raise")
            writer.writeheader()
            writer.writerows(rows)

    def run(self, *, strict: bool = False) -> R4T258SourceUnitEndpointLicenseSummary:
        if not strict:
            raise R4T258SourceUnitEndpointLicenseError("T258 audit requires --strict")
        if self.output_root.exists():
            raise R4T258SourceUnitEndpointLicenseError("T258 audit already executed")
        report, source_rows, matrix_rows = self._compute()
        self.output_root.mkdir(parents=True, exist_ok=False)
        ledger_path = self.output_root / "r4_t258_source_unit_endpoint_ledger.csv"
        matrix_path = self.output_root / "r4_t258_endpoint_compatibility_matrix.csv"
        report_path = self.output_root / "r4_t258_source_unit_endpoint_license_report.json"
        receipt_path = self.output_root / "r4_t258_source_unit_endpoint_license_receipt.json"
        self._write_csv(ledger_path, self.LEDGER_FIELDS, source_rows)
        self._write_csv(matrix_path, self.MATRIX_FIELDS, matrix_rows)
        report["output_contract"] = {
            "source_unit_ledger_relative_path": self._relative(ledger_path, self.root),
            "endpoint_matrix_relative_path": self._relative(matrix_path, self.root),
            "report_relative_path": self._relative(report_path, self.root),
            "receipt_relative_path": self._relative(receipt_path, self.root),
            "source_unit_ledger_sha256": self._sha256(ledger_path),
            "endpoint_matrix_sha256": self._sha256(matrix_path),
        }
        self._write_json(report_path, report)
        receipt = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "status": self.STATUS,
            "protocol_sha256": self._sha256(self.protocol_path),
            "report_sha256": self._sha256(report_path),
            "source_unit_ledger_sha256": self._sha256(ledger_path),
            "endpoint_matrix_sha256": self._sha256(matrix_path),
            "source_count": report["source_count"],
            "source_cell_count": report["source_cell_count"],
            "rank_eligible_cell_count": report["rank_eligible_cell_count"],
            "encoded_biological_unit_count": report["encoded_biological_unit_count"],
            "endpoint_pair_count": report["endpoint_compatibility"]["pair_count"],
            "independent_validation": False,
            "external_scientific_reproduction": False,
            "external_user_adoption": False,
            "scientific_submission_ready": False,
        }
        self._write_json(receipt_path, receipt)
        return R4T258SourceUnitEndpointLicenseSummary(
            report["source_count"],
            report["source_cell_count"],
            report["rank_eligible_cell_count"],
            report["encoded_biological_unit_count"],
            ledger_path,
            matrix_path,
            receipt_path,
        )

    def verify(self, *, strict: bool = True) -> R4T258SourceUnitEndpointLicenseSummary:
        if not strict:
            raise R4T258SourceUnitEndpointLicenseError("T258 verify requires --strict")
        ledger_path = self.output_root / "r4_t258_source_unit_endpoint_ledger.csv"
        matrix_path = self.output_root / "r4_t258_endpoint_compatibility_matrix.csv"
        report_path = self.output_root / "r4_t258_source_unit_endpoint_license_report.json"
        receipt_path = self.output_root / "r4_t258_source_unit_endpoint_license_receipt.json"
        report = self._json(report_path, "T258 report")
        receipt = self._json(receipt_path, "T258 receipt")
        if (
            report.get("audit_id") != self.AUDIT_ID
            or report.get("status") != self.STATUS
            or receipt.get("audit_id") != self.AUDIT_ID
            or receipt.get("status") != self.STATUS
            or receipt.get("protocol_sha256") != self._sha256(self.protocol_path)
            or receipt.get("report_sha256") != self._sha256(report_path)
            or receipt.get("source_unit_ledger_sha256") != self._sha256(ledger_path)
            or receipt.get("endpoint_matrix_sha256") != self._sha256(matrix_path)
            or report.get("scientific_submission_ready") is not False
            or receipt.get("scientific_submission_ready") is not False
        ):
            raise R4T258SourceUnitEndpointLicenseError("T258 report, receipt or artifact hash is invalid")
        recomputed, source_rows, matrix_rows = self._compute()
        stable_keys = (
            "schema_version",
            "audit_id",
            "status",
            "evidence_class",
            "allowed_claim_level",
            "source_count",
            "laboratory_anchor_count",
            "source_cell_count",
            "rank_eligible_cell_count",
            "encoded_biological_unit_count",
            "reported_biological_unit_counts_are_not_additive",
            "source_unit_accounting",
            "endpoint_compatibility",
            "license_accounting",
            "input_references",
            "claim_boundary",
            "independent_validation",
            "external_scientific_reproduction",
            "external_user_adoption",
            "scientific_submission_ready",
        )
        if any(report.get(key) != recomputed.get(key) for key in stable_keys):
            raise R4T258SourceUnitEndpointLicenseError("T258 report differs from current frozen inputs")
        with ledger_path.open(newline="", encoding="utf-8") as stream:
            current_ledger = list(csv.DictReader(stream))
        with matrix_path.open(newline="", encoding="utf-8") as stream:
            current_matrix = list(csv.DictReader(stream))
        if current_ledger != source_rows or current_matrix != matrix_rows:
            raise R4T258SourceUnitEndpointLicenseError("T258 derived artifacts differ from current inputs")
        return R4T258SourceUnitEndpointLicenseSummary(
            recomputed["source_count"],
            recomputed["source_cell_count"],
            recomputed["rank_eligible_cell_count"],
            recomputed["encoded_biological_unit_count"],
            ledger_path,
            matrix_path,
            receipt_path,
        )
