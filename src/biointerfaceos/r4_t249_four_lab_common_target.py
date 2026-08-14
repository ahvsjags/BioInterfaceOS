"""Audit a four-source paper-derived common target.

T249 is an append-only extension of the frozen T192 source ledger.  The
existing three-source registry is referenced by hash and one public
PMC6592156 supplementary-data source is added.  The target is re-frozen as
the exact source intersection before any downstream model execution.
"""

from __future__ import annotations

import csv
from typing import Any

from biointerfaceos.r3_uniprot_mapping import _mapping, _sha256
from biointerfaceos.r4_t192_three_lab_common_target import (
    R4T192ThreeLabCommonTargetError,
    R4T192ThreeLabCommonTargetSummary,
    R4T192ThreeLabCommonTargetWorkflow,
)


class R4T249FourLabCommonTargetError(R4T192ThreeLabCommonTargetError):
    """Raised when the frozen T249 common-target admission cannot be reproduced."""


class R4T249FourLabCommonTargetWorkflow(R4T192ThreeLabCommonTargetWorkflow):
    """Recompute and verify the four-source T249 common-target asset."""

    AUDIT_ID = "bioif-r4-t249-four-lab-common-target-paper-data-v1.0.0"
    PROTOCOL_RELATIVE = "docs/data/R4_T249_FOUR_LAB_COMMON_TARGET_PROTOCOL.json"
    REGISTRY_RELATIVE = "docs/data/R4_T249_FOUR_LAB_COMMON_TARGET_REGISTRY.json"
    OUTPUT_RELATIVE = "reports/review_round_4/four_lab_common_target/v1.0.0"
    STATUS = "FOUR_LABORATORY_COMMON_TARGET_VERIFIED_RESTRICTED_DEVELOPMENT"

    _COMMON_ACCOUNTING_OVERRIDES = {
        "EDINBURGH_DS7545_HUMAN_PLASMA_NANOOMICS": {"common_rows": 306, "common_target_batch_pairs": 306},
        "PXD060795_DALIAN_PLA_MICRO_NANOPLASTIC_HUMAN_PLASMA_CORONA": {
            "common_rows": 40,
            "common_target_batch_pairs": 40,
        },
        "PXD064962_UCD_EVENT": {"common_rows": 244, "common_target_batch_pairs": 132},
    }

    def _documents(self) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
        registry = self._json(self.registry_path, "T249 registry")
        required = {
            "schema_version",
            "audit_id",
            "protocol_id",
            "status",
            "evidence_class",
            "allowed_claim_level",
            "protocol",
            "base_registry",
            "target_freeze",
            "additional_sources",
            "output_contract",
            "claim_boundary",
            "scientific_submission_ready",
        }
        if set(registry) != required or registry.get("schema_version") != 1:
            raise R4T249FourLabCommonTargetError("T249 registry fields are invalid")
        if (
            registry.get("audit_id") != self.AUDIT_ID
            or registry.get("protocol_id") != self.AUDIT_ID
            or registry.get("status") != self.STATUS
            or registry.get("evidence_class") != "DEVELOPMENT_OBSERVATION"
            or registry.get("allowed_claim_level") != "EXPLORATORY"
            or registry.get("scientific_submission_ready") is not False
        ):
            raise R4T249FourLabCommonTargetError("T249 registry identity or boundary is invalid")
        protocol_path = self._reference(registry["protocol"], "T249 protocol")
        protocol = self._json(protocol_path, "T249 protocol")
        if (
            protocol.get("protocol_id") != self.AUDIT_ID
            or protocol.get("status") != "FROZEN_FOR_DEVELOPMENT_ADMISSION"
            or protocol.get("scientific_submission_ready") is not False
        ):
            raise R4T249FourLabCommonTargetError("T249 protocol identity or boundary is invalid")
        base_path = self._reference(registry["base_registry"], "T192 base registry")
        base = self._json(base_path, "T192 base registry")
        if base.get("schema_version") != 1 or not isinstance(base.get("sources"), list) or len(base["sources"]) != 3:
            raise R4T249FourLabCommonTargetError("T192 base registry must contain exactly three sources")
        additional = registry.get("additional_sources")
        if not isinstance(additional, list) or len(additional) != 1:
            raise R4T249FourLabCommonTargetError("T249 registry must contain exactly one additional source")
        sources: list[dict[str, Any]] = []
        for raw in [*base["sources"], *additional]:
            source = dict(_mapping(raw, "T249 source"))
            source_id = str(source.get("source_id", ""))
            if source_id in self._COMMON_ACCOUNTING_OVERRIDES:
                expected = dict(_mapping(source["expected_accounting"], f"{source_id} expected accounting"))
                expected.update(self._COMMON_ACCOUNTING_OVERRIDES[source_id])
                source["expected_accounting"] = expected
            sources.append(source)
        source_ids = [str(source.get("source_id", "")) for source in sources]
        anchors = [str(source.get("laboratory_anchor", "")) for source in sources]
        if len(set(source_ids)) != 4 or len(set(anchors)) != 4 or any(not item for item in source_ids + anchors):
            raise R4T249FourLabCommonTargetError("T249 source IDs and laboratory anchors must be unique")
        return registry, protocol, sources

    def _execute(self) -> tuple[dict[str, Any], list[dict[str, str]], dict[str, Any]]:
        report, ledger_rows, registry = super()._execute()
        for row in ledger_rows:
            row["target_observation_id"] = row["target_observation_id"].replace("T192_", "T249_", 1)
        return report, ledger_rows, registry

    def run(self, *, strict: bool = False) -> R4T192ThreeLabCommonTargetSummary:
        if not strict:
            raise R4T249FourLabCommonTargetError("T249 audit requires --strict")
        if self.output_root.exists():
            raise R4T249FourLabCommonTargetError("T249 audit already executed")
        report, ledger_rows, _ = self._execute()
        self.output_root.mkdir(parents=True, exist_ok=False)
        ledger_path = self.output_root / "r4_t249_four_lab_common_target_ledger.csv"
        self._write_csv(ledger_path, self.LEDGER_FIELDS, ledger_rows)
        try:
            ledger_relative_path = ledger_path.relative_to(self.root).as_posix()
        except ValueError:
            ledger_relative_path = ledger_path.name
        report["ledger"] = {
            "relative_path": ledger_relative_path,
            "sha256": _sha256(ledger_path),
            "row_count": len(ledger_rows),
        }
        report_path = self.output_root / "r4_t249_four_lab_common_target_report.json"
        self._write_json(report_path, report)
        receipt = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "status": self.STATUS,
            "report_sha256": _sha256(report_path),
            "ledger_sha256": _sha256(ledger_path),
            "source_count": report["source_count"],
            "laboratory_anchor_count": report["laboratory_anchor_count"],
            "common_target_count": report["common_target_count"],
            "common_row_count": report["common_row_count"],
            "source_cell_count": report["source_cell_count"],
            "rank_eligible_cell_count": report["rank_eligible_cell_count"],
            "source_batch_counts": report["source_batch_counts"],
            "scientific_submission_ready": False,
            "independent_validation": False,
        }
        receipt_path = self.output_root / "r4_t249_four_lab_common_target_receipt.json"
        self._write_json(receipt_path, receipt)
        return R4T192ThreeLabCommonTargetSummary(
            report["source_count"],
            report["laboratory_anchor_count"],
            report["common_target_count"],
            report["common_row_count"],
            report["source_cell_count"],
            report["rank_eligible_cell_count"],
            report["source_batch_counts"],
            receipt_path,
        )

    def verify(self, *, strict: bool = True) -> R4T192ThreeLabCommonTargetSummary:
        if not strict:
            raise R4T249FourLabCommonTargetError("T249 verify requires --strict")
        ledger_path = self.output_root / "r4_t249_four_lab_common_target_ledger.csv"
        report_path = self.output_root / "r4_t249_four_lab_common_target_report.json"
        receipt_path = self.output_root / "r4_t249_four_lab_common_target_receipt.json"
        report = self._json(report_path, "T249 report")
        receipt = self._json(receipt_path, "T249 receipt")
        if (
            report.get("audit_id") != self.AUDIT_ID
            or report.get("status") != self.STATUS
            or receipt.get("audit_id") != self.AUDIT_ID
            or receipt.get("status") != self.STATUS
            or receipt.get("report_sha256") != _sha256(report_path)
            or receipt.get("ledger_sha256") != _sha256(ledger_path)
            or report.get("scientific_submission_ready") is not False
            or receipt.get("scientific_submission_ready") is not False
        ):
            raise R4T249FourLabCommonTargetError("T249 report, receipt or ledger identity differs")
        recomputed, ledger_rows, _ = self._execute()
        report_comparable = (
            "source_count",
            "laboratory_anchor_count",
            "common_target_count",
            "common_row_count",
            "source_cell_count",
            "rank_eligible_cell_count",
            "source_batch_counts",
            "common_targets",
        )
        receipt_comparable = (
            "source_count",
            "laboratory_anchor_count",
            "common_target_count",
            "common_row_count",
            "source_cell_count",
            "rank_eligible_cell_count",
            "source_batch_counts",
        )
        if any(report.get(key) != recomputed.get(key) for key in report_comparable) or any(
            receipt.get(key) != recomputed.get(key) for key in receipt_comparable
        ):
            raise R4T249FourLabCommonTargetError("T249 accounting differs from current inputs")
        with ledger_path.open(newline="", encoding="utf-8") as stream:
            current_rows = list(csv.DictReader(stream))
        expected_rows = [{field: row[field] for field in self.LEDGER_FIELDS} for row in ledger_rows]
        if current_rows != expected_rows:
            raise R4T249FourLabCommonTargetError("T249 ledger differs from current inputs")
        return R4T192ThreeLabCommonTargetSummary(
            recomputed["source_count"],
            recomputed["laboratory_anchor_count"],
            recomputed["common_target_count"],
            recomputed["common_row_count"],
            recomputed["source_cell_count"],
            recomputed["rank_eligible_cell_count"],
            recomputed["source_batch_counts"],
            receipt_path,
        )
