"""Execute the strict three-laboratory common-target sensitivity analysis.

T195 reuses the T193 leakage-controlled execution engine, but replaces the
pre-T192 99-accession development universe with the exact nine-accession
intersection frozen by T192.  This is deliberately a sensitivity analysis:
the common target is frozen from source availability, source-local ranks are
used within each batch, and no claim of donor-level biological independence
or external validation is promoted.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any, Mapping

from biointerfaceos.r3_uniprot_mapping import _canonical, _mapping, _sha256, _string
from biointerfaceos.r4_t193_three_lab_prefrozen_execution import (
    R4T193ThreeLabExecutionError,
    R4T193ThreeLabExecutionSummary,
    R4T193ThreeLabPrefrozenExecutionWorkflow,
)


class R4T195CommonTargetExecutionError(R4T193ThreeLabExecutionError):
    """Raised when the frozen T195 common-target execution cannot close."""


class R4T195ThreeLabCommonTargetExecutionWorkflow(
    R4T193ThreeLabPrefrozenExecutionWorkflow
):
    """Run T195 on the exact T192 common-target intersection."""

    AUDIT_ID = "bioif-r4-t195-three-lab-common-target-execution-v1.0.0"
    STATUS = "T195_COMMON_TARGET_EXECUTION_COMPLETED_EXPLORATORY"
    PROTOCOL_RELATIVE = "docs/data/R4_T195_THREE_LAB_COMMON_TARGET_EXECUTION_PROTOCOL.json"
    REGISTRY_RELATIVE = "docs/data/R4_T195_THREE_LAB_COMMON_TARGET_EXECUTION_REGISTRY.json"
    OUTPUT_RELATIVE = (
        "reports/review_round_4/t195_three_lab_common_target_execution/v1.0.0"
    )

    def _registry(self):  # type: ignore[no-untyped-def]
        """Validate the compact T195 registry and close it to T192 assets."""
        registry = self._json(self.root / self.REGISTRY_RELATIVE, "T195 registry")
        required = {
            "schema_version",
            "audit_id",
            "protocol_id",
            "status",
            "evidence_class",
            "allowed_claim_level",
            "protocol",
            "t192_source_registry",
            "r3_common_target_ledger",
            "r3_sequence_feature_table",
            "target_universe",
            "sources",
            "expected_accounting",
            "output_contract",
            "claim_boundary",
            "scientific_submission_ready",
        }
        if set(registry) != required or registry.get("schema_version") != 1:
            raise R4T195CommonTargetExecutionError("T195 registry fields are invalid")
        if (
            registry.get("audit_id") != self.AUDIT_ID
            or registry.get("protocol_id") != self.AUDIT_ID
            or registry.get("status") != "T195_COMMON_TARGET_EXECUTION_REGISTERED"
            or registry.get("evidence_class") != "DEVELOPMENT_OBSERVATION"
            or registry.get("allowed_claim_level") != "EXPLORATORY"
            or registry.get("scientific_submission_ready") is not False
        ):
            raise R4T195CommonTargetExecutionError("T195 registry identity or boundary is invalid")
        protocol_path = self._reference(registry["protocol"], "T195 protocol")
        protocol = self._json(protocol_path, "T195 protocol")
        if (
            protocol.get("protocol_id") != self.AUDIT_ID
            or protocol.get("status") != "FROZEN_BEFORE_T195_EXECUTION"
            or protocol.get("scientific_submission_ready") is not False
        ):
            raise R4T195CommonTargetExecutionError("T195 protocol identity or boundary is invalid")
        refs = {
            "t192_source_registry": self._reference(
                registry["t192_source_registry"], "T192 source registry"
            ),
            "r3_common_target_ledger": self._reference(
                registry["r3_common_target_ledger"], "R3 common target ledger"
            ),
            "r3_sequence_feature_table": self._reference(
                registry["r3_sequence_feature_table"], "R3 feature table"
            ),
        }
        targets = _mapping(protocol["target_universe"], "T195 target universe")
        common_targets = targets.get("common_targets")
        if (
            not isinstance(common_targets, list)
            or len(common_targets) != 9
            or len(set(common_targets)) != 9
            or any(not isinstance(item, str) or not item for item in common_targets)
        ):
            raise R4T195CommonTargetExecutionError("T195 common target set is invalid")
        sources = registry.get("sources")
        if not isinstance(sources, list) or len(sources) != 3:
            raise R4T195CommonTargetExecutionError("T195 requires exactly three source summaries")
        source_ids = [
            _string(_mapping(source, "T195 source summary")["source_id"], "T195 source ID")
            for source in sources
        ]
        if len(set(source_ids)) != 3:
            raise R4T195CommonTargetExecutionError("T195 source IDs are not unique")
        t192 = self._json(refs["t192_source_registry"], "T192 source registry")
        t192_sources = t192.get("sources")
        if not isinstance(t192_sources, list):
            raise R4T195CommonTargetExecutionError("T192 source registry has no sources")
        t192_by_id = {str(item.get("source_id")): item for item in t192_sources}
        for source_id in source_ids:
            if source_id not in t192_by_id:
                raise R4T195CommonTargetExecutionError(
                    f"T195 source {source_id} is not closed by T192"
                )
        return registry, protocol, refs, t192_sources

    def _features_and_targets(self, refs: Mapping[str, Path], protocol: Mapping[str, Any]):
        features, _ = super()._features_and_targets(
            refs,
            {
                "prefrozen_target_universe": {
                    "expected_target_count": 99,
                },
            },
        )
        common_targets = set(
            _mapping(protocol["target_universe"], "T195 target universe")["common_targets"]
        )
        missing = common_targets - set(features)
        if missing:
            raise R4T195CommonTargetExecutionError(
                f"T195 common targets have no sequence features: {sorted(missing)}"
            )
        return {accession: features[accession] for accession in common_targets}, common_targets

    def _rename_parent_outputs(self, *, reverse: bool = False) -> None:
        old_report = self.output_root / "t193_three_lab_execution_report.json"
        old_receipt = self.output_root / "t193_three_lab_execution_receipt.json"
        new_report = self.output_root / "t195_three_lab_execution_report.json"
        new_receipt = self.output_root / "t195_three_lab_execution_receipt.json"
        pairs = ((new_report, old_report), (new_receipt, old_receipt)) if reverse else (
            (old_report, new_report),
            (old_receipt, new_receipt),
        )
        for source, target in pairs:
            if source.is_file():
                source.replace(target)

    def run(self, *, strict: bool = False) -> R4T193ThreeLabExecutionSummary:
        if not strict:
            raise R4T195CommonTargetExecutionError("T195 execution requires --strict")
        summary = super().run(strict=True)
        self._rename_parent_outputs()
        report_path = self.output_root / "t195_three_lab_execution_report.json"
        receipt_path = self.output_root / "t195_three_lab_execution_receipt.json"
        report = self._json(report_path, "T195 report")
        report["target_universe"] = {
            "source": "R4_T192_THREE_LAB_COMMON_TARGET_REGISTRY",
            "count": 9,
            "selection_after_outer_split": False,
            "common_targets": sorted(
                _mapping(self._json(self.root / self.PROTOCOL_RELATIVE, "T195 protocol")["target_universe"], "T195 target universe")["common_targets"]
            ),
        }
        report["audit_id"] = self.AUDIT_ID
        report["status"] = self.STATUS
        report_path.write_bytes(_canonical(report))
        receipt = self._json(receipt_path, "T195 receipt")
        receipt["audit_id"] = self.AUDIT_ID
        receipt["status"] = self.STATUS
        receipt["report_sha256"] = _sha256(report_path)
        receipt["target_universe_count"] = 9
        receipt_path.write_bytes(_canonical(receipt))
        return replace(summary, receipt_path=receipt_path)

    def verify(self, *, strict: bool = True) -> R4T193ThreeLabExecutionSummary:
        if not strict:
            raise R4T195CommonTargetExecutionError("T195 verification requires --strict")
        report_path = self.output_root / "t195_three_lab_execution_report.json"
        receipt_path = self.output_root / "t195_three_lab_execution_receipt.json"
        if not report_path.is_file() or not receipt_path.is_file():
            raise R4T195CommonTargetExecutionError("T195 report or receipt is missing")
        self._rename_parent_outputs(reverse=True)
        try:
            summary = super().verify(strict=True)
        finally:
            self._rename_parent_outputs()
        return replace(summary, receipt_path=receipt_path)
