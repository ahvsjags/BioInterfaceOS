"""Execute the T249 four-source paper-data common-target analysis."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from biointerfaceos.r3_uniprot_mapping import _mapping, _string
from biointerfaceos.r4_t193_three_lab_prefrozen_execution import (
    R4T193ThreeLabExecutionSummary,
    R4T193ThreeLabPrefrozenExecutionWorkflow,
)
from biointerfaceos.r4_t195_three_lab_common_target_execution import (
    R4T195CommonTargetExecutionError,
    R4T195ThreeLabCommonTargetExecutionWorkflow,
)
from biointerfaceos.r4_t249_four_lab_common_target import R4T249FourLabCommonTargetWorkflow


class R4T250FourLabCommonTargetExecutionError(R4T195CommonTargetExecutionError):
    """Raised when the frozen T250 execution cannot close."""


class R4T250FourLabCommonTargetExecutionWorkflow(R4T195ThreeLabCommonTargetExecutionWorkflow):
    """Run the four-source T249 common-target execution."""

    AUDIT_ID = "bioif-r4-t250-four-lab-common-target-execution-v1.0.0"
    STATUS = "T250_FOUR_LAB_COMMON_TARGET_EXECUTION_COMPLETED_EXPLORATORY"
    PROTOCOL_RELATIVE = "docs/data/R4_T250_FOUR_LAB_COMMON_TARGET_EXECUTION_PROTOCOL.json"
    REGISTRY_RELATIVE = "docs/data/R4_T250_FOUR_LAB_COMMON_TARGET_EXECUTION_REGISTRY.json"
    OUTPUT_RELATIVE = "reports/review_round_4/t250_four_lab_common_target_execution/v1.0.0"
    REPORT_NAME = "t250_four_lab_execution_report.json"
    RECEIPT_NAME = "t250_four_lab_execution_receipt.json"
    TARGET_SOURCE = "R4_T249_FOUR_LAB_COMMON_TARGET_REGISTRY"
    TARGET_COUNT = 7
    FOLD_PREFIX = "T250"
    OBSERVATION_PREFIX = "T250"

    def _registry(
        self,
    ) -> tuple[dict[str, Any], dict[str, Any], dict[str, Path], list[dict[str, Any]]]:
        registry = self._json(self.root / self.REGISTRY_RELATIVE, "T250 registry")
        required = {
            "schema_version",
            "audit_id",
            "protocol_id",
            "status",
            "evidence_class",
            "allowed_claim_level",
            "protocol",
            "t249_source_registry",
            "t249_common_target_ledger",
            "r3_common_rank_target_ledger",
            "r3_sequence_feature_table",
            "target_universe",
            "sources",
            "expected_accounting",
            "output_contract",
            "claim_boundary",
            "scientific_submission_ready",
        }
        if set(registry) != required or registry.get("schema_version") != 1:
            raise R4T250FourLabCommonTargetExecutionError("T250 registry fields are invalid")
        if (
            registry.get("audit_id") != self.AUDIT_ID
            or registry.get("protocol_id") != self.AUDIT_ID
            or registry.get("status") != "T250_FOUR_LAB_COMMON_TARGET_EXECUTION_REGISTERED"
            or registry.get("evidence_class") != "DEVELOPMENT_OBSERVATION"
            or registry.get("allowed_claim_level") != "EXPLORATORY"
            or registry.get("scientific_submission_ready") is not False
        ):
            raise R4T250FourLabCommonTargetExecutionError("T250 registry identity or boundary is invalid")
        protocol_path = self._reference(registry["protocol"], "T250 protocol")
        protocol = self._json(protocol_path, "T250 protocol")
        if (
            protocol.get("protocol_id") != self.AUDIT_ID
            or protocol.get("status") != "FROZEN_BEFORE_T250_EXECUTION"
            or protocol.get("scientific_submission_ready") is not False
        ):
            raise R4T250FourLabCommonTargetExecutionError("T250 protocol identity or boundary is invalid")
        refs = {
            "t192_source_registry": self._reference(registry["t249_source_registry"], "T249 source registry"),
            "t249_common_target_ledger": self._reference(
                registry["t249_common_target_ledger"], "T249 common-target ledger"
            ),
            "r3_common_target_ledger": self._reference(
                registry["r3_common_rank_target_ledger"], "R3 common-target ledger"
            ),
            "r3_sequence_feature_table": self._reference(
                registry["r3_sequence_feature_table"], "R3 sequence feature table"
            ),
        }
        targets = _mapping(protocol["target_universe"], "T250 target universe")
        common_targets = targets.get("common_targets")
        if (
            not isinstance(common_targets, list)
            or len(common_targets) != self.TARGET_COUNT
            or len(set(common_targets)) != self.TARGET_COUNT
            or any(not isinstance(item, str) or not item for item in common_targets)
        ):
            raise R4T250FourLabCommonTargetExecutionError("T250 common target set is invalid")
        sources = registry.get("sources")
        if not isinstance(sources, list) or len(sources) != 4:
            raise R4T250FourLabCommonTargetExecutionError("T250 requires exactly four source summaries")
        source_ids = [
            _string(_mapping(source, "T250 source summary")["source_id"], "T250 source ID") for source in sources
        ]
        if len(set(source_ids)) != 4:
            raise R4T250FourLabCommonTargetExecutionError("T250 source IDs are not unique")
        expected = _mapping(registry["expected_accounting"], "T250 expected accounting")
        if (
            expected.get("source_count") != 4
            or expected.get("laboratory_anchor_count") != 4
            or expected.get("target_universe_count") != self.TARGET_COUNT
            or expected.get("observation_count") != 783
            or expected.get("outer_fold_count") != 4
        ):
            raise R4T250FourLabCommonTargetExecutionError("T250 expected accounting is invalid")
        t249 = R4T249FourLabCommonTargetWorkflow(self.root, registry_path=refs["t192_source_registry"])
        _, _, t249_sources = t249._documents()
        if {str(source["source_id"]) for source in t249_sources} != set(source_ids):
            raise R4T250FourLabCommonTargetExecutionError("T250 sources do not close T249 source registry")
        return registry, protocol, refs, t249_sources

    def _features_and_targets(
        self, refs: Mapping[str, Path], protocol: Mapping[str, Any]
    ) -> tuple[dict[str, tuple[float, ...]], set[str]]:
        features, _ = R4T193ThreeLabPrefrozenExecutionWorkflow._features_and_targets(
            self,
            refs,
            {"prefrozen_target_universe": {"expected_target_count": 99}},
        )
        common_targets = set(_mapping(protocol["target_universe"], "T250 target universe")["common_targets"])
        missing = common_targets - set(features)
        if missing:
            raise R4T250FourLabCommonTargetExecutionError(
                f"T250 common targets have no sequence features: {sorted(missing)}"
            )
        return {accession: features[accession] for accession in common_targets}, common_targets

    def _source_workflow(self, refs: Mapping[str, Path]) -> R4T249FourLabCommonTargetWorkflow:
        return R4T249FourLabCommonTargetWorkflow(self.root, registry_path=refs["t192_source_registry"])

    def run(self, *, strict: bool = False) -> R4T193ThreeLabExecutionSummary:
        if not strict:
            raise R4T250FourLabCommonTargetExecutionError("T250 execution requires --strict")
        summary = super().run(strict=True)
        return summary

    def verify(self, *, strict: bool = True) -> R4T193ThreeLabExecutionSummary:
        if not strict:
            raise R4T250FourLabCommonTargetExecutionError("T250 verification requires --strict")
        return super().verify(strict=True)
