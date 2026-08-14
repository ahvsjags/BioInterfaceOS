"""Run the preregistered author-run technical OOD analysis for PMC13106918."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import numpy as np

from biointerfaceos.r3_analysis_protocol import R3AnalysisProtocolError, R3AnalysisProtocolWorkflow
from biointerfaceos.r3_model_evaluation import (
    R3ModelEvaluationError,
    R3ModelEvaluationWorkflow,
    _Observation,
)
from biointerfaceos.r3_uniprot_mapping import _checksum, _mapping, _sha256, _string
from biointerfaceos.r4_pmc13106918_source_audit import (
    R4PMC13106918SourceAuditError,
    R4PMC13106918SourceAuditWorkflow,
)
from biointerfaceos.r4_small_molecule_corona_ood import (
    R4SmallMoleculeCoronaOODError,
    R4SmallMoleculeCoronaOODSummary,
    R4SmallMoleculeCoronaOODWorkflow,
)


class R4PMC13106918TechnicalOODError(R4SmallMoleculeCoronaOODError):
    """Raised when the frozen PMC13106918 technical OOD cannot run safely."""


class R4PMC13106918TechnicalOODWorkflow(R4SmallMoleculeCoronaOODWorkflow):
    """Fit only on frozen R3 and score source-local PMC13106918 ranks."""

    AUDIT_ID = "bioif-r4-pmc13106918-technical-ood-v1.0.0"
    PROTOCOL_RELATIVE = "docs/data/R4_T177_PMC13106918_TECHNICAL_OOD_PROTOCOL.json"
    OUTPUT_RELATIVE = "reports/review_round_4/pmc13106918_technical_ood/v1.0.0"
    STATUS = "R4_PMC13106918_TECHNICAL_OOD_EXECUTED_EXPLORATORY"

    def _protocol(self) -> tuple[dict[str, Any], dict[str, Path]]:
        protocol = self._json(self.protocol_path, "PMC13106918 technical OOD protocol")
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
            raise R4PMC13106918TechnicalOODError("technical OOD protocol fields are invalid")
        if (
            protocol.get("protocol_id") != "bioif-r4-pmc13106918-technical-ood-protocol-v1.0.0"
            or protocol.get("evidence_class") != "DEVELOPMENT_OBSERVATION"
            or protocol.get("allowed_claim_level") != "EXPLORATORY"
        ):
            raise R4PMC13106918TechnicalOODError("technical OOD protocol identity is invalid")
        refs = _mapping(protocol.get("references"), "technical OOD references")
        expected_refs = {
            "r3_analysis_protocol_receipt",
            "r3_common_target_ledger",
            "r3_sequence_feature_table",
            "r4_source_audit_receipt",
            "r4_source_cell_map",
        }
        if set(refs) != expected_refs:
            raise R4PMC13106918TechnicalOODError("technical OOD references are invalid")
        paths = {key: self._reference(value, key) for key, value in refs.items()}
        if (
            self.output_data_root != (self.root / "data/raw").resolve(strict=False)
            or self.feature_root != (self.root / "data/raw/r3_uniprot_sequence_features").resolve(strict=False)
            or self.source_assets_root != (self.root / "data/raw/r4_candidate_pmc13106918").resolve(strict=False)
        ):
            raise R4PMC13106918TechnicalOODError("technical OOD requires fixed repository data roots")
        external = _mapping(protocol.get("external_evaluation"), "technical external evaluation")
        if external != {
            "source_id": "PMC13106918_RCSI_DCU_SILICA_CORONA",
            "laboratory_anchor": "Royal College of Surgeons in Ireland and Dublin City University",
            "analysis_population": "source-cell rows with analysis_candidate_eligible=true, rank_target_eligible=true and canonical accession present in the frozen R3 feature table",  # noqa: E501
            "minimum_proteins_per_measurement_batch": 10,
            "expected_measurement_batch_count": 16,
            "expected_shared_canonical_protein_count_at_least": 36,
            "biological_unit_count": 1,
            "access_condition": "public CC-BY-4.0 Zenodo package; author-run technical OOD candidate; one pooled material with technical replicates; not a protected lockbox and not an independent evaluator",  # noqa: E501
        }:
            raise R4PMC13106918TechnicalOODError("technical external evaluation contract is invalid")
        if protocol["models"] != [
            {"model_id": "CONSTANT_TRAINING_MEAN", "hyperparameters": {}},
            {
                "model_id": "SEQUENCE_RIDGE_FULL",
                "hyperparameters": {"alpha_grid": [0.01, 0.1, 1.0, 10.0, 100.0]},
            },
            {
                "model_id": "SEQUENCE_RIDGE_COMPOSITION_ONLY",
                "hyperparameters": {"alpha_grid": [0.01, 0.1, 1.0, 10.0, 100.0]},
            },
        ]:
            raise R4PMC13106918TechnicalOODError("technical model contract is invalid")
        return protocol, paths

    def _external_observations(
        self,
        source_map_path: Path,
        feature_values: Mapping[str, tuple[float, ...]],
        protocol: Mapping[str, Any],
    ) -> tuple[list[_Observation], list[dict[str, Any]], set[str]]:
        rows = self._read_csv(source_map_path, "PMC13106918 source cell map")
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
            raise R4PMC13106918TechnicalOODError("technical source cell map schema is invalid")
        external = protocol["external_evaluation"]
        if any(
            row.get("source_id") != external["source_id"]
            or row.get("laboratory_anchor") != external["laboratory_anchor"]
            for row in rows
        ):
            raise R4PMC13106918TechnicalOODError("technical source map identity differs")
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
            if batch_id not in eligible_batches:
                continue
            identity = f"{batch_id}:{row['source_coordinate']}"
            rank = ranks.get(identity)
            accession = row.get("canonical_accession", "")
            if rank is None or accession not in feature_values:
                continue
            percentile, positive_count = rank
            target_id = f"R4PMC13106918:{row['source_row']}:{row['source_coordinate']}:{batch_id}"
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
            or any(
                len(values) < external["minimum_proteins_per_measurement_batch"]
                for values in by_batch.values()
                if values[0]["measurement_batch_id"] in eligible_batches
            )
        ):
            raise R4PMC13106918TechnicalOODError("technical source does not meet frozen OOD coverage")
        return (
            sorted(observations, key=lambda row: (row.measurement_batch_id, row.target_observation_id)),
            target_rows,
            accessions,
        )

    def run(self, *, strict: bool = False) -> R4SmallMoleculeCoronaOODSummary:
        if not strict:
            raise R4PMC13106918TechnicalOODError("PMC13106918 technical OOD requires --strict")
        if self.output_root.exists():
            raise R4PMC13106918TechnicalOODError("PMC13106918 technical OOD already executed")
        protocol, paths = self._protocol()
        try:
            R3AnalysisProtocolWorkflow(self.root, self.output_data_root).verify()
            R4PMC13106918SourceAuditWorkflow(self.root, self.source_assets_root).verify()
        except (R4PMC13106918SourceAuditError, R3AnalysisProtocolError, OSError) as exc:
            raise R4PMC13106918TechnicalOODError("a frozen R3/T176 input receipt does not verify") from exc
        helper = R3ModelEvaluationWorkflow(self.root, self.output_data_root, self.feature_root)
        try:
            development, development_accessions = helper._observations(
                paths["r3_common_target_ledger"], paths["r3_sequence_feature_table"]
            )
        except R3ModelEvaluationError as exc:
            raise R4PMC13106918TechnicalOODError("frozen R3 development data is invalid") from exc
        if len(development) != 2724 or len(development_accessions) != 99:
            raise R4PMC13106918TechnicalOODError("frozen R3 development cohort differs")
        feature_values = {row.canonical_accession: row.feature_values for row in development}
        external, target_rows, accessions = self._external_observations(
            paths["r4_source_cell_map"], feature_values, protocol
        )
        full_indices = tuple(range(len(helper.FEATURE_NAMES)))
        composition_indices = tuple(helper.FEATURE_NAMES.index(name) for name in helper.COMPOSITION_FEATURE_NAMES)
        full_alpha, full_selection = helper._select_alpha(development, full_indices, minimum_proteins=10)
        composition_alpha, composition_selection = helper._select_alpha(
            development, composition_indices, minimum_proteins=10
        )
        constant_mean = float(np.mean([row.target for row in development]))
        full_model = helper._fit_ridge(development, full_indices, full_alpha)
        composition_model = helper._fit_ridge(development, composition_indices, composition_alpha)
        predictions = {
            "CONSTANT_TRAINING_MEAN": np.full(len(external), constant_mean, dtype=float),
            "SEQUENCE_RIDGE_FULL": helper._predict_ridge(full_model, external),
            "SEQUENCE_RIDGE_COMPOSITION_ONLY": helper._predict_ridge(composition_model, external),
        }
        uncertainty = protocol["uncertainty"]
        negative = protocol["negative_control"]
        prediction_rows: list[dict[str, Any]] = []
        batch_rows: list[dict[str, Any]] = []
        model_rows: list[dict[str, Any]] = []
        metric_by_model_batch: dict[tuple[str, str], dict[str, Any]] = {}
        full_primary: float | None = None
        for model_index, model_id in enumerate(helper.MODEL_IDS, start=1):
            metrics = helper._batch_metrics(external, predictions[model_id], minimum_proteins=10)
            aggregate = helper._aggregate(metrics)
            status = "UNDEFINED_CONSTANT_PREDICTION" if model_id == "CONSTANT_TRAINING_MEAN" else "DEFINED"
            intervals: dict[str, dict[str, float | int] | None] = {}
            for metric_name, key in (
                ("spearman", "mean_spearman"),
                ("mae", "mean_mae"),
                ("rmse", "mean_rmse"),
            ):
                values = [metric[metric_name] for metric in metrics]
                intervals[key] = (
                    None
                    if any(value is None for value in values)
                    else helper._bootstrap(
                        [float(value) for value in values],
                        resamples=uncertainty["resamples"],
                        seed=uncertainty["random_seed"] + model_index * 100,
                    )
                )
            if model_id == "SEQUENCE_RIDGE_FULL":
                full_primary = aggregate["mean_spearman"]
            mean_mae_interval = intervals["mean_mae"]
            mean_rmse_interval = intervals["mean_rmse"]
            model_rows.append(
                {
                    "model_id": model_id,
                    "external_observation_count": len(external),
                    "external_measurement_batch_count": len(metrics),
                    "primary_metric_status": status,
                    **aggregate,
                    "mean_spearman_lower_95": None
                    if intervals["mean_spearman"] is None
                    else intervals["mean_spearman"]["lower_95"],
                    "mean_spearman_upper_95": None
                    if intervals["mean_spearman"] is None
                    else intervals["mean_spearman"]["upper_95"],
                    "mean_mae_lower_95": None if mean_mae_interval is None else mean_mae_interval["lower_95"],
                    "mean_mae_upper_95": None if mean_mae_interval is None else mean_mae_interval["upper_95"],
                    "mean_rmse_lower_95": None if mean_rmse_interval is None else mean_rmse_interval["lower_95"],
                    "mean_rmse_upper_95": None if mean_rmse_interval is None else mean_rmse_interval["upper_95"],
                }
            )
            for metric in metrics:
                metric_by_model_batch[(model_id, metric["measurement_batch_id"])] = metric
                batch_rows.append(
                    {
                        "model_id": model_id,
                        **metric,
                        "spearman_status": status if metric["spearman"] is None else "DEFINED",
                    }
                )
            for observation, value in zip(external, predictions[model_id], strict=True):
                prediction_rows.append(
                    {
                        "model_id": model_id,
                        "external_target_observation_id": observation.target_observation_id,
                        "canonical_accession": observation.canonical_accession,
                        "measurement_batch_id": observation.measurement_batch_id,
                        "observed_rank_percentile_descending": observation.target,
                        "predicted_rank_percentile_descending": float(value),
                    }
                )
        if full_primary is None:
            raise R4PMC13106918TechnicalOODError("technical OOD primary metric is undefined")
        paired_batches = sorted(
            {batch for model_id, batch in metric_by_model_batch if model_id == "SEQUENCE_RIDGE_FULL"}
        )
        paired_difference = [
            float(metric_by_model_batch[("SEQUENCE_RIDGE_FULL", batch)]["spearman"])
            - float(metric_by_model_batch[("SEQUENCE_RIDGE_COMPOSITION_ONLY", batch)]["spearman"])
            for batch in paired_batches
        ]
        ablation = {
            "paired_measurement_batch_count": len(paired_difference),
            "full_minus_composition_mean_spearman": float(np.mean(paired_difference)),
            **helper._bootstrap(
                paired_difference,
                resamples=uncertainty["resamples"],
                seed=uncertainty["random_seed"] + 701,
            ),
        }
        by_development_batch: dict[str, list[int]] = defaultdict(list)
        for index, observation in enumerate(development):
            by_development_batch[observation.measurement_batch_id].append(index)
        observed_targets = np.asarray([row.target for row in development], dtype=float)
        rng = np.random.default_rng(negative["random_seed"])
        null_rows: list[dict[str, Any]] = []
        null_primary: list[float] = []
        for resample in range(1, negative["resamples"] + 1):
            permuted = observed_targets.copy()
            for indices in by_development_batch.values():
                permuted[indices] = rng.permutation(permuted[indices])
            null_model = helper._fit_ridge(development, full_indices, full_alpha, targets=permuted)
            score = helper._aggregate(
                helper._batch_metrics(external, helper._predict_ridge(null_model, external), minimum_proteins=10)
            )["mean_spearman"]
            if score is None:
                raise R4PMC13106918TechnicalOODError("technical permutation control has undefined metric")
            null_primary.append(float(score))
            null_rows.append({"resample": resample, "null_mean_spearman": float(score)})
        negative_summary = {
            "selected_alpha": full_alpha,
            "resamples": negative["resamples"],
            "random_seed": negative["random_seed"],
            "observed_mean_spearman": full_primary,
            "null_mean_spearman_mean": float(np.mean(null_primary)),
            "null_mean_spearman_lower_95": float(np.quantile(null_primary, 0.025)),
            "null_mean_spearman_upper_95": float(np.quantile(null_primary, 0.975)),
            "one_sided_upper_tail_p": float(
                (1 + sum(value >= full_primary for value in null_primary)) / (1 + len(null_primary))
            ),
        }
        selection_rows = [
            {"model_id": "SEQUENCE_RIDGE_FULL", **row, "selected_alpha": full_alpha} for row in full_selection
        ] + [
            {
                "model_id": "SEQUENCE_RIDGE_COMPOSITION_ONLY",
                **row,
                "selected_alpha": composition_alpha,
            }
            for row in composition_selection
        ]
        self.output_root.mkdir(parents=True, exist_ok=False)
        output_paths = {
            "external_target_ledger": self.output_root / "r4_pmc13106918_rank_target_ledger.csv",
            "predictions": self.output_root / "r4_pmc13106918_ood_predictions.csv",
            "batch_metrics": self.output_root / "r4_pmc13106918_measurement_batch_metrics.csv",
            "model_metrics": self.output_root / "r4_pmc13106918_ood_model_metrics.csv",
            "selection": self.output_root / "r4_pmc13106918_nested_selection.csv",
            "negative_control": self.output_root / "r4_pmc13106918_within_batch_permutation.csv",
            "parameters": self.output_root / "r4_pmc13106918_model_parameters.json",
        }
        self._write_csv(output_paths["external_target_ledger"], self.TARGET_FIELDS, target_rows)
        self._write_csv(
            output_paths["predictions"],
            [
                "model_id",
                "external_target_observation_id",
                "canonical_accession",
                "measurement_batch_id",
                "observed_rank_percentile_descending",
                "predicted_rank_percentile_descending",
            ],
            prediction_rows,
        )
        self._write_csv(
            output_paths["batch_metrics"],
            [
                "model_id",
                "measurement_batch_id",
                "protein_count",
                "spearman",
                "spearman_status",
                "mae",
                "rmse",
            ],
            batch_rows,
        )
        self._write_csv(
            output_paths["model_metrics"],
            [
                "model_id",
                "external_observation_count",
                "external_measurement_batch_count",
                "primary_metric_status",
                "mean_spearman",
                "mean_spearman_lower_95",
                "mean_spearman_upper_95",
                "mean_mae",
                "mean_mae_lower_95",
                "mean_mae_upper_95",
                "mean_rmse",
                "mean_rmse_lower_95",
                "mean_rmse_upper_95",
            ],
            model_rows,
        )
        self._write_csv(
            output_paths["selection"],
            ["model_id", "alpha", "held_out_inner_batch_id", "spearman", "selected_alpha"],
            selection_rows,
        )
        self._write_csv(output_paths["negative_control"], ["resample", "null_mean_spearman"], null_rows)
        self._write_json(
            output_paths["parameters"],
            {
                "development_observation_count": len(development),
                "external_observation_count": len(external),
                "CONSTANT_TRAINING_MEAN": {"development_target_mean": constant_mean},
                "SEQUENCE_RIDGE_FULL": {
                    **helper._ridge_parameters(full_model, helper.FEATURE_NAMES),
                    "negative_control": negative_summary,
                },
                "SEQUENCE_RIDGE_COMPOSITION_ONLY": helper._ridge_parameters(
                    composition_model, helper.COMPOSITION_FEATURE_NAMES
                ),
            },
        )
        artifacts = {
            name: {"relative_path": path.relative_to(self.root).as_posix(), "sha256": _sha256(path)}
            for name, path in output_paths.items()
        }
        report = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "protocol_id": protocol["protocol_id"],
            "protocol_sha256": _sha256(self.protocol_path),
            "execution_module_sha256": _sha256(Path(__file__).resolve(strict=True)),
            "numpy_version": np.__version__,
            "status": self.STATUS,
            "evidence_class": protocol["evidence_class"],
            "allowed_claim_level": protocol["allowed_claim_level"],
            "input_references": {
                name: {
                    "relative_path": path.relative_to(self.root).as_posix(),
                    "sha256": _sha256(path),
                }
                for name, path in paths.items()
            },
            "development_observation_count": len(development),
            "development_canonical_protein_count": len(development_accessions),
            "external_observation_count": len(external),
            "external_shared_canonical_protein_count": len(accessions),
            "external_measurement_batch_count": len({row.measurement_batch_id for row in external}),
            "biological_unit_count": 1,
            "model_results": model_rows,
            "paired_composition_ablation": ablation,
            "negative_control_summary": negative_summary,
            "external_access_condition": protocol["external_evaluation"]["access_condition"],
            "artifacts": artifacts,
            "claim_boundary": protocol["claim_boundary"],
            "independent_validation": False,
            "external_scientific_reproduction": False,
            "scientific_submission_ready": False,
        }
        report_path = self.output_root / "r4_pmc13106918_technical_ood_report.json"
        self._write_json(report_path, report)
        receipt = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "status": self.STATUS,
            "report_sha256": _sha256(report_path),
            "development_observation_count": len(development),
            "external_observation_count": len(external),
            "external_shared_canonical_protein_count": len(accessions),
            "external_measurement_batch_count": len({row.measurement_batch_id for row in external}),
            "biological_unit_count": 1,
            "model_count": len(helper.MODEL_IDS),
            "model_fitted": True,
            "independent_validation": False,
            "external_scientific_reproduction": False,
            "scientific_submission_ready": False,
        }
        receipt_path = self.output_root / "r4_pmc13106918_technical_ood_receipt.json"
        self._write_json(receipt_path, receipt)
        return R4SmallMoleculeCoronaOODSummary(
            len(development),
            len(external),
            len(accessions),
            len({row.measurement_batch_id for row in external}),
            len(helper.MODEL_IDS),
            receipt_path,
        )

    def verify(self) -> R4SmallMoleculeCoronaOODSummary:
        report_path = self.output_root / "r4_pmc13106918_technical_ood_report.json"
        receipt_path = self.output_root / "r4_pmc13106918_technical_ood_receipt.json"
        report = self._json(report_path, "PMC13106918 technical OOD report")
        receipt = self._json(receipt_path, "PMC13106918 technical OOD receipt")
        artifacts = _mapping(report.get("artifacts"), "technical OOD artifacts")
        valid = bool(artifacts)
        for value in artifacts.values():
            item = _mapping(value, "technical OOD artifact")
            if set(item) != self.REQUIRED_REFERENCE:
                valid = False
                break
            try:
                path = self._root_file(_string(item.get("relative_path"), "artifact path"), "artifact")
                valid = valid and _sha256(path) == _checksum(item.get("sha256"), "artifact")
            except Exception:
                valid = False
                break
        if (
            report.get("audit_id") != self.AUDIT_ID
            or receipt.get("audit_id") != self.AUDIT_ID
            or report.get("status") != self.STATUS
            or receipt.get("status") != self.STATUS
            or receipt.get("report_sha256") != _sha256(report_path)
            or receipt.get("model_fitted") is not True
            or receipt.get("independent_validation") is not False
            or receipt.get("external_scientific_reproduction") is not False
            or receipt.get("scientific_submission_ready") is not False
            or not valid
        ):
            raise R4PMC13106918TechnicalOODError("technical OOD receipt is invalid")
        return R4SmallMoleculeCoronaOODSummary(
            int(receipt["development_observation_count"]),
            int(receipt["external_observation_count"]),
            int(receipt["external_shared_canonical_protein_count"]),
            int(receipt["external_measurement_batch_count"]),
            int(receipt["model_count"]),
            receipt_path,
        )
