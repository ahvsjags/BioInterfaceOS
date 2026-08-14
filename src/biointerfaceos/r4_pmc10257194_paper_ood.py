"""Execute the frozen R3-target, paper-attached PMC10257194 analysis-only OOD."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any, ClassVar

from biointerfaceos.r3_uniprot_mapping import _mapping
from biointerfaceos.r4_pmc10257194_paper_source_audit import (
    R4PMC10257194PaperSourceAuditError,
    R4PMC10257194PaperSourceAuditWorkflow,
)
from biointerfaceos.r4_small_molecule_corona_ood import (
    R4SmallMoleculeCoronaOODError,
    R4SmallMoleculeCoronaOODWorkflow,
)


class R4PMC10257194PaperOODError(R4SmallMoleculeCoronaOODError):
    """Raised when the PMC10257194 OOD contract is violated."""


class R4PMC10257194PaperOODWorkflow(R4SmallMoleculeCoronaOODWorkflow):
    AUDIT_ID = "bioif-r4-pmc10257194-paper-ood-v1.0.0"
    PROTOCOL_RELATIVE = "docs/data/R4_T203_PMC10257194_NAY_LUAD_PAPER_OOD_PROTOCOL.json"
    OUTPUT_RELATIVE = "reports/review_round_4/pmc10257194_paper_ood/v1.0.0"
    STATUS = "R4_PMC10257194_PAPER_OOD_EXECUTED_EXPLORATORY"
    SOURCE_AUDIT_WORKFLOW: ClassVar[type[Any]] = R4PMC10257194PaperSourceAuditWorkflow
    SOURCE_AUDIT_ERROR: ClassVar[type[Exception]] = R4PMC10257194PaperSourceAuditError

    def _protocol(self) -> tuple[dict[str, Any], dict[str, Path]]:
        protocol = self._json(self.protocol_path, "PMC10257194 paper OOD protocol")
        expected_top = {
            "schema_version",
            "protocol_id",
            "frozen_at",
            "evidence_class",
            "allowed_claim_level",
            "references",
            "target",
            "development_selection",
            "external_evaluation",
            "feature_policy",
            "models",
            "metrics",
            "uncertainty",
            "negative_control",
            "claim_boundary",
        }
        if set(protocol) != expected_top or protocol.get("schema_version") != 1:
            raise R4PMC10257194PaperOODError("PMC10257194 protocol fields are invalid")
        if (
            protocol.get("protocol_id") != "bioif-r4-pmc10257194-paper-ood-protocol-v1.0.0"
            or protocol.get("evidence_class") != "DEVELOPMENT_OBSERVATION"
            or protocol.get("allowed_claim_level") != "EXPLORATORY"
        ):
            raise R4PMC10257194PaperOODError("PMC10257194 protocol identity is invalid")
        refs = _mapping(protocol["references"], "PMC10257194 references")
        expected_refs = {
            "r3_analysis_protocol_receipt",
            "r3_common_target_ledger",
            "r3_sequence_feature_table",
            "r4_source_audit_receipt",
            "r4_source_cell_map",
        }
        if set(refs) != expected_refs:
            raise R4PMC10257194PaperOODError("PMC10257194 references are invalid")
        paths = {key: self._reference(value, key) for key, value in refs.items()}
        if (
            self.output_data_root != (self.root / "data/raw").resolve(strict=False)
            or self.feature_root != (self.root / "data/raw/r3_uniprot_sequence_features").resolve(strict=False)
            or self.source_assets_root != (self.root / "data/raw/r4_candidate_pmc10257194").resolve(strict=False)
        ):
            raise R4PMC10257194PaperOODError("PMC10257194 requires fixed repository data roots")
        external = _mapping(protocol["external_evaluation"], "PMC10257194 external evaluation")
        if external != {
            "source_id": "PMC10257194_NAY_LUAD_PLASMA_CORONA",
            "laboratory_anchor": "Tianjin University / Tianjin Medical University",
            "analysis_population": "45 paper-attached NaY-PPC subject columns with exact frozen R3 target accession mapping and strictly positive finite values",  # noqa: E501
            "minimum_proteins_per_measurement_batch": 10,
            "expected_measurement_batch_count": 45,
            "expected_shared_canonical_protein_count_at_least": 97,
            "biological_unit_count": 45,
            "access_condition": "CC-BY-NC-ND-4.0 paper supplementary workbook; analysis-only local acquisition; not redistributable and not a protected lockbox",  # noqa: E501
        }:
            raise R4PMC10257194PaperOODError("PMC10257194 external evaluation contract is invalid")
        return protocol, paths

    def _external_observations(
        self,
        source_map_path: Path,
        feature_values: Mapping[str, tuple[float, ...]],
        protocol: Mapping[str, Any],
    ) -> tuple[list[Any], list[dict[str, Any]], set[str]]:
        observations, target_rows, accessions = super()._external_observations(
            source_map_path, feature_values, protocol
        )
        external = protocol["external_evaluation"]
        if (
            len({row.measurement_batch_id for row in observations}) != external["expected_measurement_batch_count"]
            or len({row.canonical_accession for row in observations})
            < external["expected_shared_canonical_protein_count_at_least"]
        ):
            raise R4PMC10257194PaperOODError("PMC10257194 coverage is below the frozen contract")
        return observations, target_rows, accessions
