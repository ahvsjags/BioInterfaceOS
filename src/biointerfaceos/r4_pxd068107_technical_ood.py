"""Run the frozen author-side technical OOD on paper source data PXD068107."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from biointerfaceos.r3_analysis_protocol import R3AnalysisProtocolError
from biointerfaceos.r3_model_evaluation import R3ModelEvaluationError, _Observation
from biointerfaceos.r3_uniprot_mapping import _mapping
from biointerfaceos.r4_pmc13106918_technical_ood import R4PMC13106918TechnicalOODWorkflow
from biointerfaceos.r4_pxd068107_source_audit import (
    R4PXD068107SourceAuditError,
    R4PXD068107SourceAuditWorkflow,
)
from biointerfaceos.r4_small_molecule_corona_ood import R4SmallMoleculeCoronaOODSummary


class R4PXD068107TechnicalOODError(RuntimeError):
    """Raised when the frozen PXD068107 technical OOD cannot run safely."""


class R4PXD068107TechnicalOODWorkflow(R4PMC13106918TechnicalOODWorkflow):
    """Fit only on frozen R3 and score PXD068107 source-local ranks."""

    AUDIT_ID = "bioif-r4-pxd068107-technical-ood-v1.0.0"
    PROTOCOL_RELATIVE = "docs/data/R4_T264_PXD068107_TECHNICAL_OOD_PROTOCOL.json"
    OUTPUT_RELATIVE = "reports/review_round_4/pxd068107_technical_ood/v1.0.0"
    STATUS = "R4_PXD068107_TECHNICAL_OOD_EXECUTED_EXPLORATORY"
    FILE_PREFIX = "r4_pxd068107"
    SOURCE_AUDIT_WORKFLOW = R4PXD068107SourceAuditWorkflow
    SOURCE_AUDIT_ERROR = R4PXD068107SourceAuditError

    def _protocol(self) -> tuple[dict[str, Any], dict[str, Path]]:
        protocol = self._json(self.protocol_path, "PXD068107 technical OOD protocol")
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
            raise R4PXD068107TechnicalOODError("technical OOD protocol fields are invalid")
        if (
            protocol.get("protocol_id") != "bioif-r4-pxd068107-technical-ood-protocol-v1.0.0"
            or protocol.get("evidence_class") != "DEVELOPMENT_OBSERVATION"
            or protocol.get("allowed_claim_level") != "EXPLORATORY"
        ):
            raise R4PXD068107TechnicalOODError("technical OOD protocol identity is invalid")
        refs = _mapping(protocol.get("references"), "technical OOD references")
        expected_refs = {
            "r3_analysis_protocol_receipt",
            "r3_common_target_ledger",
            "r3_sequence_feature_table",
            "r4_source_audit_receipt",
            "r4_source_cell_map",
        }
        if set(refs) != expected_refs:
            raise R4PXD068107TechnicalOODError("technical OOD references are invalid")
        paths = {key: self._reference(value, key) for key, value in refs.items()}
        if (
            self.output_data_root != (self.root / "data/raw").resolve(strict=False)
            or self.feature_root != (self.root / "data/raw/r3_uniprot_sequence_features").resolve(strict=False)
            or self.source_assets_root != (self.root / "data/raw/r4_candidate_pxd068107").resolve(strict=False)
        ):
            raise R4PXD068107TechnicalOODError("PXD068107 technical OOD requires fixed repository roots")
        external = _mapping(protocol.get("external_evaluation"), "technical external evaluation")
        if external != {
            "source_id": "PXD068107_WESTLAKE_OMNIPROT_TECHNICAL",
            "laboratory_anchor": "Westlake University",
            "analysis_population": (
                "source-cell rows with analysis_candidate_eligible=true, rank_target_eligible=true "
                "and canonical accession present in the frozen R3 feature table"
            ),
            "minimum_proteins_per_measurement_batch": 10,
            "expected_measurement_batch_count": 21,
            "expected_shared_canonical_protein_count_at_least": 98,
            "biological_unit_count": 1,
            "access_condition": (
                "public CC0 paper-attached BioStudies source; author-run technical OOD candidate; "
                "one pooled technical source; not a protected lockbox and not an independent evaluator"
            ),
        }:
            raise R4PXD068107TechnicalOODError("technical external evaluation contract is invalid")
        if protocol["models"] != [
            {"model_id": "CONSTANT_TRAINING_MEAN", "hyperparameters": {}},
            {"model_id": "SEQUENCE_RIDGE_FULL", "hyperparameters": {"alpha_grid": [0.01, 0.1, 1.0, 10.0, 100.0]}},
            {
                "model_id": "SEQUENCE_RIDGE_COMPOSITION_ONLY",
                "hyperparameters": {"alpha_grid": [0.01, 0.1, 1.0, 10.0, 100.0]},
            },
        ]:
            raise R4PXD068107TechnicalOODError("technical model contract is invalid")
        return protocol, paths

    def _external_observations(
        self,
        source_map_path: Path,
        feature_values: Mapping[str, tuple[float, ...]],
        protocol: Mapping[str, Any],
    ) -> tuple[list[_Observation], list[dict[str, Any]], set[str]]:
        rows = self._read_csv(source_map_path, "PXD068107 source cell map")
        required = {
            "source_id",
            "laboratory_anchor",
            "source_worksheet",
            "source_row",
            "source_coordinate",
            "measurement_batch_id",
            "canonical_accession",
            "author_quantity_type",
            "author_numeric_value",
            "analysis_candidate_eligible",
            "rank_target_eligible",
        }
        if not required.issubset(rows[0]):
            raise R4PXD068107TechnicalOODError("technical source cell map schema is invalid")
        external = protocol["external_evaluation"]
        if any(
            row.get("source_id") != external["source_id"]
            or row.get("laboratory_anchor") != external["laboratory_anchor"]
            for row in rows
        ):
            raise R4PXD068107TechnicalOODError("technical source map identity differs")
        ranks = self._rank_percentiles(rows)
        by_batch: dict[str, list[dict[str, str]]] = defaultdict(list)
        for row in rows:
            identity = f"{row['measurement_batch_id']}:{row['source_coordinate']}"
            if identity in ranks:
                by_batch[row["measurement_batch_id"]].append(row)
        eligible_batches = {
            batch
            for batch, values in by_batch.items()
            if len(values) >= external["minimum_proteins_per_measurement_batch"]
        }
        observations: list[_Observation] = []
        target_rows: list[dict[str, Any]] = []
        accessions: set[str] = set()
        for row in rows:
            batch_id = row["measurement_batch_id"]
            identity = f"{batch_id}:{row['source_coordinate']}"
            rank = ranks.get(identity)
            accession = row.get("canonical_accession", "")
            if batch_id not in eligible_batches or rank is None or accession not in feature_values:
                continue
            percentile, positive_count = rank
            target_id = f"R4PXD068107:{row['source_row']}:{row['source_coordinate']}:{batch_id}"
            observations.append(
                _Observation(
                    target_id,
                    external["source_id"],
                    accession,
                    external["laboratory_anchor"],
                    batch_id,
                    percentile,
                    feature_values[accession],
                )
            )
            target_rows.append(
                {
                    "external_target_observation_id": target_id,
                    "source_id": external["source_id"],
                    "laboratory_anchor": external["laboratory_anchor"],
                    "canonical_accession": accession,
                    "measurement_batch_id": batch_id,
                    "source_worksheet": row["source_worksheet"],
                    "source_row": row["source_row"],
                    "source_coordinate": row["source_coordinate"],
                    "author_quantity_type": row["author_quantity_type"],
                    "author_numeric_value": float(row["author_numeric_value"]),
                    "rank_percentile_descending": percentile,
                    "measurement_batch_positive_protein_count": positive_count,
                }
            )
            accessions.add(accession)
        if (
            len(eligible_batches) != external["expected_measurement_batch_count"]
            or len(accessions) < external["expected_shared_canonical_protein_count_at_least"]
        ):
            raise R4PXD068107TechnicalOODError("PXD068107 source does not meet frozen OOD coverage")
        return (
            sorted(observations, key=lambda row: (row.measurement_batch_id, row.target_observation_id)),
            target_rows,
            accessions,
        )

    def run(self, *, strict: bool = False) -> R4SmallMoleculeCoronaOODSummary:
        if not strict:
            raise R4PXD068107TechnicalOODError("PXD068107 technical OOD requires --strict")
        try:
            return super().run(strict=True)
        except (R4PXD068107SourceAuditError, R3AnalysisProtocolError, R3ModelEvaluationError, OSError) as exc:
            raise R4PXD068107TechnicalOODError("PXD068107 technical OOD input receipt is invalid") from exc
