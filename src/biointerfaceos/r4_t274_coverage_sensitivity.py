"""Audit coverage and common-target availability sensitivity for T273."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from biointerfaceos.r3_uniprot_mapping import _canonical, _sha256


class R4T274CoverageSensitivityError(RuntimeError):
    """Raised when the coverage sensitivity input contract is invalid."""


class R4T274CoverageSensitivityWorkflow:
    """Compute pre-model coverage sensitivity without assuming a missingness mechanism."""

    PROTOCOL = "docs/data/R4_T273_BIOLOGICAL_UNIT_PRIMARY_PROTOCOL.json"
    REGISTRY = "docs/data/R4_T273_BIOLOGICAL_UNIT_PRIMARY_REGISTRY.json"
    OUTPUT = "reports/review_round_4/t274_coverage_sensitivity/v1.0.0"

    def __init__(self, root: Path, *, output_root: Path | None = None) -> None:
        self.root = root.resolve(strict=True)
        self.output_root = (output_root or self.root / self.OUTPUT).resolve(strict=False)
        if not self.output_root.is_relative_to(self.root):
            raise R4T274CoverageSensitivityError("T274 output escapes repository root")

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def _positive_candidate(row: dict[str, str]) -> bool:
        if row.get("rank_target_eligible", "").strip().lower() != "true":
            return False
        if row.get("analysis_candidate_eligible", "true").strip().lower() != "true":
            return False
        try:
            value = float(row.get("author_numeric_value", ""))
        except (TypeError, ValueError):
            return False
        return value > 0.0

    def run(self, *, strict: bool = False) -> dict[str, Any]:
        if not strict:
            raise R4T274CoverageSensitivityError("T274 coverage sensitivity requires --strict")
        if self.output_root.exists():
            raise R4T274CoverageSensitivityError("T274 output already exists")
        registry = self._read_json(self.root / self.REGISTRY)
        protocol = self._read_json(self.root / self.PROTOCOL)
        targets = set(protocol["target_freeze"]["common_targets"])
        thresholds = [3, 4, 5]
        rows: list[dict[str, Any]] = []
        source_summaries: list[dict[str, Any]] = []
        for source in registry["sources"]:
            map_path = self.root / source["source_cell_map"]["relative_path"]
            with map_path.open(encoding="utf-8", newline="") as stream:
                raw_rows = list(csv.DictReader(stream))
            eligible = [row for row in raw_rows if self._positive_candidate(row)]
            common = [row for row in eligible if row.get("canonical_accession") in targets]
            by_batch: dict[str, list[dict[str, str]]] = defaultdict(list)
            for row in common:
                by_batch[row["measurement_batch_id"]].append(row)
            source_summary: dict[str, Any] = {
                "source_id": source["source_id"],
                "laboratory_anchor": source["laboratory_anchor"],
                "raw_map_rows": len(raw_rows),
                "rank_eligible_rows": len(eligible),
                "common_rows": len(common),
                "fixed_target_count": len(targets),
                "fixed_target_panel": sorted(targets),
                "coverage_rule_is_descriptive_not_mcar_mar_mnar": True,
                "thresholds": {},
            }
            for threshold in thresholds:
                qualified = {
                    batch_id: batch_rows for batch_id, batch_rows in by_batch.items() if len(batch_rows) >= threshold
                }
                qualified_rows = [row for batch_rows in qualified.values() for row in batch_rows]
                units = {row["biological_unit_id"] for row in qualified_rows}
                value = {
                    "minimum_targets_per_batch": threshold,
                    "qualified_batch_count": len(qualified),
                    "qualified_common_rows": len(qualified_rows),
                    "qualified_biological_unit_count": len(units),
                    "retained_common_row_fraction": len(qualified_rows) / len(common) if common else None,
                }
                source_summary["thresholds"][str(threshold)] = value
                rows.append({**source_summary, "threshold": threshold, **value})
            source_summaries.append(source_summary)
        self.output_root.mkdir(parents=True, exist_ok=False)
        flow_path = self.output_root / "coverage_sensitivity.csv"
        with flow_path.open("w", encoding="utf-8", newline="") as stream:
            fields = [
                "source_id",
                "laboratory_anchor",
                "raw_map_rows",
                "rank_eligible_rows",
                "common_rows",
                "fixed_target_count",
                "threshold",
                "qualified_batch_count",
                "qualified_common_rows",
                "qualified_biological_unit_count",
                "retained_common_row_fraction",
            ]
            writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
            writer.writeheader()
            for row in rows:
                writer.writerow({field: row.get(field, "") for field in fields})
        report = {
            "schema_version": 1,
            "audit_id": "bioif-r4-t274-coverage-sensitivity-v1.0.0",
            "status": "T274_COVERAGE_SENSITIVITY_COMPLETED_DESCRIPTIVE",
            "protocol": {"relative_path": self.PROTOCOL, "sha256": _sha256(self.root / self.PROTOCOL)},
            "registry": {"relative_path": self.REGISTRY, "sha256": _sha256(self.root / self.REGISTRY)},
            "fixed_target_panel": sorted(targets),
            "thresholds": thresholds,
            "source_summaries": source_summaries,
            "coverage_sensitivity_csv": {
                "relative_path": flow_path.relative_to(self.root).as_posix(),
                "sha256": _sha256(flow_path),
            },
            "missingness_claim_boundary": (
                "This is availability/exclusion accounting only and does not identify MCAR, MAR or MNAR mechanisms."
            ),
            "scientific_submission_ready": False,
        }
        report_path = self.output_root / "t274_coverage_sensitivity_report.json"
        report_path.write_bytes(_canonical(report))
        return report

    def verify(self, *, strict: bool = True) -> dict[str, Any]:
        if not strict:
            raise R4T274CoverageSensitivityError("T274 verification requires --strict")
        report_path = self.output_root / "t274_coverage_sensitivity_report.json"
        flow_path = self.output_root / "coverage_sensitivity.csv"
        report = self._read_json(report_path)
        if _sha256(flow_path) != report["coverage_sensitivity_csv"]["sha256"]:
            raise R4T274CoverageSensitivityError("T274 coverage sensitivity hash differs")
        if report.get("scientific_submission_ready") is not False:
            raise R4T274CoverageSensitivityError("T274 gate boundary is invalid")
        return report
