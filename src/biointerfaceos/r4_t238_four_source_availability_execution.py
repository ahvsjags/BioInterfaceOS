"""Execute the four-source development-only target-membership sensitivity route."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from biointerfaceos.r3_uniprot_mapping import _mapping, _string
from biointerfaceos.r4_t197_source_availability_execution import (
    R4T197SourceAvailabilityError,
    R4T197SourceAvailabilitySummary,
    R4T197SourceAvailabilityWorkflow,
)
from biointerfaceos.r4_t249_four_lab_common_target import R4T249FourLabCommonTargetWorkflow


class R4T238FourSourceAvailabilityWorkflow(R4T197SourceAvailabilityWorkflow):
    """Run T238 against the four public T249 source maps."""

    AUDIT_ID = "bioif-r4-t238-four-source-availability-execution-v1.0.0"
    STATUS = "T238_FOUR_SOURCE_AVAILABILITY_EXECUTION_COMPLETED_EXPLORATORY"
    PROTOCOL_RELATIVE = "docs/data/R4_T238_FOUR_SOURCE_AVAILABILITY_EXECUTION_PROTOCOL.json"
    REGISTRY_RELATIVE = "docs/data/R4_T238_FOUR_SOURCE_AVAILABILITY_EXECUTION_REGISTRY.json"
    T249_REGISTRY_RELATIVE = "docs/data/R4_T249_FOUR_LAB_COMMON_TARGET_REGISTRY.json"
    OUTPUT_RELATIVE = "reports/review_round_4/t238_four_source_availability_execution/v1.0.0"
    REPORT_NAME = "t238_four_source_availability_execution_report.json"
    RECEIPT_NAME = "t238_four_source_availability_execution_receipt.json"
    REGISTRY_STATUS = "T238_FOUR_SOURCE_AVAILABILITY_EXECUTION_REGISTERED"
    PROTOCOL_STATUS = "FROZEN_BEFORE_T238_EXECUTION"
    SOURCE_COUNT = 4
    FOLD_PREFIX = "T238"
    OBSERVATION_PREFIX = "T238"
    SEED_OFFSET_BY_FOLD = True

    def _registry(self) -> tuple[dict[str, Any], dict[str, Any], dict[str, Path]]:
        registry = self._json(self.root / self.REGISTRY_RELATIVE, "T238 registry")
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
            "r3_sequence_feature_table",
            "sources",
            "expected_accounting",
            "output_contract",
            "claim_boundary",
            "scientific_submission_ready",
        }
        if set(registry) != required or registry.get("schema_version") != 1:
            raise R4T197SourceAvailabilityError("T238 registry fields are invalid")
        if (
            registry.get("audit_id") != self.AUDIT_ID
            or registry.get("protocol_id") != self.AUDIT_ID
            or registry.get("status") != self.REGISTRY_STATUS
            or registry.get("evidence_class") != "DEVELOPMENT_OBSERVATION"
            or registry.get("allowed_claim_level") != "EXPLORATORY"
            or registry.get("scientific_submission_ready") is not False
        ):
            raise R4T197SourceAvailabilityError("T238 registry identity or boundary is invalid")
        protocol_path = self._reference(registry["protocol"], "T238 protocol")
        protocol = self._json(protocol_path, "T238 protocol")
        if (
            protocol.get("protocol_id") != self.AUDIT_ID
            or protocol.get("status") != self.PROTOCOL_STATUS
            or protocol.get("scientific_submission_ready") is not False
        ):
            raise R4T197SourceAvailabilityError("T238 protocol identity or boundary is invalid")
        refs = {
            "protocol": protocol_path,
            "t249_source_registry": self._reference(registry["t249_source_registry"], "T249 source registry"),
            "t249_common_target_ledger": self._reference(
                registry["t249_common_target_ledger"], "T249 common-target ledger"
            ),
            "r3_sequence_feature_table": self._reference(
                registry["r3_sequence_feature_table"], "R3 sequence feature table"
            ),
        }
        if refs["t249_source_registry"] != self.root / self.T249_REGISTRY_RELATIVE:
            raise R4T197SourceAvailabilityError("T238 does not use the release-fixed T249 registry")
        expected = _mapping(registry["expected_accounting"], "T238 expected accounting")
        if (
            expected.get("source_count") != self.SOURCE_COUNT
            or expected.get("outer_fold_count") != self.SOURCE_COUNT
            or expected.get("minimum_development_only_target_count") != 9
            or expected.get("minimum_held_out_available_target_count") != 7
        ):
            raise R4T197SourceAvailabilityError("T238 expected accounting is invalid")
        source_ids = registry.get("sources")
        protocol_sources = _mapping(protocol["outer_split"], "T238 outer split").get("source_ids")
        if (
            not isinstance(source_ids, list)
            or len(source_ids) != self.SOURCE_COUNT
            or len(set(source_ids)) != self.SOURCE_COUNT
            or source_ids != protocol_sources
        ):
            raise R4T197SourceAvailabilityError("T238 source IDs are invalid")
        t249 = R4T249FourLabCommonTargetWorkflow(self.root, registry_path=refs["t249_source_registry"])
        _, _, t249_sources = t249._documents()
        if {str(source["source_id"]) for source in t249_sources} != set(source_ids):
            raise R4T197SourceAvailabilityError("T238 sources do not close T249 source registry")
        if not refs["t249_common_target_ledger"].is_file():
            raise R4T197SourceAvailabilityError("T249 common-target ledger is missing")
        return registry, protocol, refs

    def _source_rows(
        self, refs: Mapping[str, Path]
    ) -> tuple[
        R4T249FourLabCommonTargetWorkflow,
        dict[str, dict[str, Any]],
        dict[str, list[tuple[dict[str, str], float, int]]],
    ]:
        t249 = R4T249FourLabCommonTargetWorkflow(self.root, registry_path=refs["t249_source_registry"])
        try:
            _, _, sources = t249._documents()
            rows: dict[str, list[tuple[dict[str, str], float, int]]] = {}
            source_meta: dict[str, dict[str, Any]] = {}
            for source in sources:
                source_id = _string(source["source_id"], "T249 source ID")
                _, eligible = t249._validate_source_metadata(source)
                ranks = t249._rank_rows(eligible)
                rows[source_id] = [(row, ranks[index][0], ranks[index][1]) for index, row in enumerate(eligible)]
                source_meta[source_id] = source
        except Exception as exc:
            raise R4T197SourceAvailabilityError("T249 source admission does not verify") from exc
        return t249, source_meta, rows

    def run(self, *, strict: bool = False) -> R4T197SourceAvailabilitySummary:
        return super().run(strict=strict)

    def verify(self, *, strict: bool = True) -> R4T197SourceAvailabilitySummary:
        return super().verify(strict=strict)
