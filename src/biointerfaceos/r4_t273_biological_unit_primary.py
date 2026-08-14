"""Run the T273 biological-unit-primary reanalysis.

T265 demonstrated that the source maps contain explicit biological units, but
its inherited model engine selected alpha and computed the negative control at
measurement-batch level.  T273 keeps the frozen source maps and target panel,
while making biological-unit grouping the primary estimand throughout nested
selection, uncertainty, ablation, and the permutation null.
"""

from __future__ import annotations

import csv
from collections import defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np

from biointerfaceos.r3_model_evaluation import R3ModelEvaluationWorkflow, _Observation
from biointerfaceos.r3_uniprot_mapping import _sha256
from biointerfaceos.r4_t193_three_lab_prefrozen_execution import (
    R4T193ThreeLabExecutionSummary,
)
from biointerfaceos.r4_t265_biological_common_target import (
    R4T265BiologicalCommonTargetError,
    R4T265BiologicalCommonTargetWorkflow,
)


class R4T273BiologicalUnitPrimaryError(R4T265BiologicalCommonTargetError):
    """Raised when the T273 primary-estimand contract is violated."""


class R4T273BiologicalUnitPrimaryWorkflow(R4T265BiologicalCommonTargetWorkflow):
    """Execute a grouped, biological-unit-primary T265 reanalysis."""

    AUDIT_ID = "bioif-r4-t273-biological-unit-primary-execution-v2.0.0"
    STATUS = "T273_BIOLOGICAL_UNIT_PRIMARY_EXECUTION_COMPLETED_EXPLORATORY"
    PROTOCOL_RELATIVE = "docs/data/R4_T273_BIOLOGICAL_UNIT_PRIMARY_PROTOCOL.json"
    REGISTRY_RELATIVE = "docs/data/R4_T273_BIOLOGICAL_UNIT_PRIMARY_REGISTRY.json"
    OUTPUT_RELATIVE = "reports/review_round_4/t273_biological_unit_primary/v2.0.0"
    REPORT_NAME = "t273_biological_unit_primary_report.json"
    RECEIPT_NAME = "t273_biological_unit_primary_receipt.json"
    REGISTRY_STATUS = "T273_BIOLOGICAL_UNIT_PRIMARY_REGISTERED"
    PROTOCOL_STATUS = "FROZEN_BEFORE_T273_EXECUTION"
    OBSERVATION_PREFIX = "T273"
    FOLD_PREFIX = "T273"
    TARGET_SOURCE = "T273_fixed_five_target_panel_conditional_common_target_universe"

    def __init__(self, root: Path, *, output_root: Path | None = None) -> None:
        super().__init__(root, output_root=output_root)
        self._unit_by_observation: dict[str, str] = {}
        self._accounting: dict[str, dict[str, Any]] = {}
        self._last_primary: dict[str, Any] = {}

    def _source_observations(
        self,
        unused_source_workflow: Any,
        sources: Sequence[Mapping[str, Any]],
        features: Mapping[str, tuple[float, ...]],
        target_universe: set[str],
        registry: Mapping[str, Any],
    ) -> tuple[list[_Observation], list[dict[str, Any]], dict[str, dict[str, Any]]]:
        observations, ledger, accounting = super()._source_observations(
            unused_source_workflow, sources, features, target_universe, registry
        )
        model_observation_ids = {row.target_observation_id for row in observations}
        unit_map: dict[str, str] = {}
        for row in ledger:
            observation_id = str(row["target_observation_id"])
            if observation_id not in model_observation_ids:
                continue
            source_id = str(row["source_id"])
            biological_unit_id = str(row["biological_unit_id"]).strip()
            if not biological_unit_id:
                raise R4T273BiologicalUnitPrimaryError("T273 biological unit ID is empty")
            unit_key = f"{source_id}::{biological_unit_id}"
            previous = unit_map.setdefault(observation_id, unit_key)
            if previous != unit_key:
                raise R4T273BiologicalUnitPrimaryError("T273 observation maps to multiple biological units")
        if set(unit_map) != model_observation_ids:
            raise R4T273BiologicalUnitPrimaryError("T273 unit map does not cover every model observation")
        self._unit_by_observation = unit_map
        self._accounting = accounting
        return observations, ledger, accounting

    def _unit(self, observation: _Observation) -> str:
        try:
            return self._unit_by_observation[observation.target_observation_id]
        except KeyError as exc:
            raise R4T273BiologicalUnitPrimaryError("T273 observation has no biological unit") from exc

    @staticmethod
    def _clone_targets(
        observations: Sequence[_Observation], target_overrides: Mapping[str, float] | None = None
    ) -> list[_Observation]:
        overrides = target_overrides or {}
        return [
            _Observation(
                target_observation_id=row.target_observation_id,
                source_id=row.source_id,
                canonical_accession=row.canonical_accession,
                laboratory_anchor=row.laboratory_anchor,
                measurement_batch_id=row.measurement_batch_id,
                target=float(overrides.get(row.target_observation_id, row.target)),
                feature_values=row.feature_values,
            )
            for row in observations
        ]

    def _batch_and_unit_metrics(
        self,
        observations: Sequence[_Observation],
        predictions: Sequence[float] | np.ndarray[Any, Any],
        *,
        minimum_proteins: int,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        if len(observations) != len(predictions):
            raise R4T273BiologicalUnitPrimaryError("T273 prediction accounting differs from observations")
        grouped: dict[tuple[str, str], list[tuple[_Observation, float]]] = defaultdict(list)
        for row, prediction in zip(observations, predictions, strict=True):
            grouped[(row.source_id, row.measurement_batch_id)].append((row, float(prediction)))
        batch_rows: list[dict[str, Any]] = []
        unit_batches: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for (source_id, batch_id), pairs in sorted(grouped.items()):
            if len(pairs) < minimum_proteins:
                raise R4T273BiologicalUnitPrimaryError(
                    f"T273 batch {source_id}/{batch_id} has fewer than {minimum_proteins} targets"
                )
            units = {self._unit(row) for row, _ in pairs}
            if len(units) != 1:
                raise R4T273BiologicalUnitPrimaryError("T273 measurement batch spans multiple biological units")
            observed = np.asarray([row.target for row, _ in pairs], dtype=float)
            predicted = np.asarray([value for _, value in pairs], dtype=float)
            metric = {
                "source_id": source_id,
                "measurement_batch_id": batch_id,
                "biological_unit_id": next(iter(units)),
                "protein_count": len(pairs),
                "spearman": R3ModelEvaluationWorkflow._spearman(observed, predicted),
                "mae": float(np.mean(np.abs(observed - predicted))),
                "rmse": float(np.sqrt(np.mean(np.square(observed - predicted)))),
            }
            batch_rows.append(metric)
            unit_batches[metric["biological_unit_id"]].append(metric)
        unit_rows: list[dict[str, Any]] = []
        for unit_id, rows in sorted(unit_batches.items()):
            spearman_values = [row["spearman"] for row in rows]
            unit_rows.append(
                {
                    "biological_unit_id": unit_id,
                    "source_id": unit_id.split("::", 1)[0],
                    "measurement_batch_count": len(rows),
                    "protein_count": sum(int(row["protein_count"]) for row in rows),
                    "spearman": None
                    if any(value is None for value in spearman_values)
                    else float(np.mean(np.asarray(spearman_values, dtype=float))),
                    "mae": float(np.mean([float(row["mae"]) for row in rows])),
                    "rmse": float(np.mean([float(row["rmse"]) for row in rows])),
                }
            )
        if not unit_rows:
            raise R4T273BiologicalUnitPrimaryError("T273 produced no biological-unit metrics")
        return batch_rows, unit_rows

    @staticmethod
    def _unit_summary(unit_rows: Sequence[Mapping[str, Any]]) -> dict[str, float | None]:
        if not unit_rows:
            raise R4T273BiologicalUnitPrimaryError("T273 unit summary is empty")
        spearman = [row["spearman"] for row in unit_rows]
        return {
            "mean_spearman": None
            if any(value is None for value in spearman)
            else float(np.mean(np.asarray(spearman, dtype=float))),
            "mean_mae": float(np.mean([float(row["mae"]) for row in unit_rows])),
            "mean_rmse": float(np.mean([float(row["rmse"]) for row in unit_rows])),
        }

    @staticmethod
    def _bootstrap_metric(
        values: Sequence[float] | Sequence[None], *, resamples: int, seed: int
    ) -> dict[str, Any] | None:
        if not values or any(value is None for value in values):
            return None
        array = np.asarray([float(value) for value in values], dtype=float)
        rng = np.random.default_rng(seed)
        means = array[rng.integers(0, len(array), size=(resamples, len(array)))].mean(axis=1)
        interval = np.quantile(means, [0.025, 0.975], method="linear")
        return {
            "lower_95": float(interval[0]),
            "upper_95": float(interval[1]),
            "resamples": int(resamples),
            "seed": int(seed),
            "cluster_count": int(len(array)),
        }

    def _group_folds(self, development: Sequence[_Observation], n_splits: int) -> list[tuple[str, set[str]]]:
        units = sorted({self._unit(row) for row in development})
        if len(units) < n_splits:
            raise R4T273BiologicalUnitPrimaryError("T273 development has fewer units than inner folds")
        return [(f"T273_INNER_UNIT_GROUP_{index + 1:02d}", set(units[index::n_splits])) for index in range(n_splits)]

    def _select_alpha_grouped(
        self,
        development: Sequence[_Observation],
        feature_indices: Sequence[int],
        *,
        minimum_proteins: int,
        n_splits: int,
        target_overrides: Mapping[str, float] | None = None,
    ) -> tuple[float, list[dict[str, Any]], dict[str, Any]]:
        helper = R3ModelEvaluationWorkflow(
            self.root, self.root / "data/raw", self.root / "data/raw/r3_uniprot_sequence_features"
        )
        folds = self._group_folds(development, n_splits)
        selection_rows: list[dict[str, Any]] = []
        means: dict[float, float] = {}
        for alpha in helper.ALPHA_GRID:
            fold_scores: list[float] = []
            for inner_fold_id, validation_units in folds:
                training = [row for row in development if self._unit(row) not in validation_units]
                validation = [row for row in development if self._unit(row) in validation_units]
                training_targets = None
                if target_overrides is not None:
                    training_targets = np.asarray(
                        [float(target_overrides[row.target_observation_id]) for row in training], dtype=float
                    )
                model = helper._fit_ridge(training, feature_indices, alpha, targets=training_targets)
                predicted = helper._predict_ridge(model, validation)
                validation_rows = self._clone_targets(validation, target_overrides)
                _, unit_rows = self._batch_and_unit_metrics(
                    validation_rows, predicted, minimum_proteins=minimum_proteins
                )
                summary = self._unit_summary(unit_rows)
                if summary["mean_spearman"] is None:
                    raise R4T273BiologicalUnitPrimaryError("T273 grouped inner Spearman is undefined")
                score = float(summary["mean_spearman"])
                fold_scores.append(score)
                selection_rows.append(
                    {
                        "alpha": float(alpha),
                        "held_out_inner_batch_id": inner_fold_id,
                        "spearman": score,
                        "inner_validation_unit_count": len(validation_units),
                        "inner_validation_observation_count": len(validation),
                        "inner_split_unit_disjoint": True,
                    }
                )
            means[float(alpha)] = float(np.mean(np.asarray(fold_scores, dtype=float)))
            selection_rows.append(
                {
                    "alpha": float(alpha),
                    "held_out_inner_batch_id": "__MEAN_UNIT_GROUPED__",
                    "spearman": means[float(alpha)],
                    "inner_validation_unit_count": sum(len(units) for _, units in folds),
                    "inner_validation_observation_count": len(development),
                    "inner_split_unit_disjoint": True,
                }
            )
        selected = min(means, key=lambda alpha: (-means[alpha], alpha))
        return (
            selected,
            selection_rows,
            {
                "split_method": "deterministic_group_kfold_by_source_local_biological_unit",
                "fold_count": n_splits,
                "unit_count": len({self._unit(row) for row in development}),
                "unit_disjoint": True,
                "alpha_means": means,
                "selected_alpha": selected,
                "target_permutation_selection_recomputed": target_overrides is not None,
            },
        )

    def _execute_models(
        self, observations: Sequence[_Observation], protocol: Mapping[str, Any]
    ) -> tuple[dict[str, Any], dict[str, list[dict[str, Any]]]]:
        helper = R3ModelEvaluationWorkflow(
            self.root, self.root / "data/raw", self.root / "data/raw/r3_uniprot_sequence_features"
        )
        outer = sorted({row.laboratory_anchor for row in observations})
        nested = dict(protocol["nested_selection"])
        uncertainty = dict(protocol["uncertainty"])
        negative = dict(protocol["negative_control"])
        minimum = int(nested["minimum_proteins_per_selection_batch"])
        inner_folds = int(nested["biological_unit_group_folds"])
        bootstrap_resamples = int(uncertainty["resamples"])
        bootstrap_seed = int(uncertainty["random_seed"])
        negative_resamples = int(negative["resamples"])
        negative_seed = int(negative["random_seed"])
        full_indices = tuple(range(len(helper.FEATURE_NAMES)))
        composition_indices = tuple(helper.FEATURE_NAMES.index(name) for name in helper.COMPOSITION_FEATURE_NAMES)
        predictions: list[dict[str, Any]] = []
        batch_metrics: list[dict[str, Any]] = []
        fold_metrics: list[dict[str, Any]] = []
        selections: list[dict[str, Any]] = []
        ablations: list[dict[str, Any]] = []
        negative_rows: list[dict[str, Any]] = []
        unit_metrics: list[dict[str, Any]] = []
        parameters: dict[str, Any] = {}
        for fold_index, held_out_lab in enumerate(outer, start=1):
            fold_id = f"{self.FOLD_PREFIX}_OUTER_{fold_index:02d}"
            development = [row for row in observations if row.laboratory_anchor != held_out_lab]
            testing = sorted(
                [row for row in observations if row.laboratory_anchor == held_out_lab],
                key=lambda row: (row.source_id, row.measurement_batch_id, row.target_observation_id),
            )
            full_alpha, full_selection, full_selection_audit = self._select_alpha_grouped(
                development, full_indices, minimum_proteins=minimum, n_splits=inner_folds
            )
            composition_alpha, composition_selection, composition_selection_audit = self._select_alpha_grouped(
                development, composition_indices, minimum_proteins=minimum, n_splits=inner_folds
            )
            for model_id, rows, selected_alpha in (
                ("SEQUENCE_RIDGE_FULL", full_selection, full_alpha),
                ("SEQUENCE_RIDGE_COMPOSITION_ONLY", composition_selection, composition_alpha),
            ):
                selections.extend(
                    {
                        "outer_fold_id": fold_id,
                        "held_out_laboratory_anchor": held_out_lab,
                        "model_id": model_id,
                        **row,
                        "selected_alpha": selected_alpha,
                    }
                    for row in rows
                )
            constant_mean = float(np.mean([row.target for row in development]))
            full_model = helper._fit_ridge(development, full_indices, full_alpha)
            composition_model = helper._fit_ridge(development, composition_indices, composition_alpha)
            predictions_by_model = {
                "CONSTANT_TRAINING_MEAN": np.full(len(testing), constant_mean, dtype=float),
                "SEQUENCE_RIDGE_FULL": helper._predict_ridge(full_model, testing),
                "SEQUENCE_RIDGE_COMPOSITION_ONLY": helper._predict_ridge(composition_model, testing),
            }
            parameters[fold_id] = {
                "held_out_laboratory_anchor": held_out_lab,
                "development_observation_count": len(development),
                "held_out_observation_count": len(testing),
                "primary_estimand": "equal_mean_over_biological_units_of_within_unit_batch_metric",
                "CONSTANT_TRAINING_MEAN": {"development_target_mean": constant_mean},
                "SEQUENCE_RIDGE_FULL": {
                    **helper._ridge_parameters(full_model, helper.FEATURE_NAMES),
                    "grouped_selection": full_selection_audit,
                },
                "SEQUENCE_RIDGE_COMPOSITION_ONLY": {
                    **helper._ridge_parameters(composition_model, helper.COMPOSITION_FEATURE_NAMES),
                    "grouped_selection": composition_selection_audit,
                },
            }
            metric_by_model: dict[str, tuple[list[dict[str, Any]], list[dict[str, Any]]]] = {}
            for model_index, model_id in enumerate(self.MODEL_IDS, start=1):
                predicted = predictions_by_model[model_id]
                batch_rows, unit_rows = self._batch_and_unit_metrics(testing, predicted, minimum_proteins=minimum)
                metric_by_model[model_id] = (batch_rows, unit_rows)
                summary = self._unit_summary(unit_rows)
                ci = {
                    name: self._bootstrap_metric(
                        [row[name] for row in unit_rows],
                        resamples=bootstrap_resamples,
                        seed=bootstrap_seed + fold_index * 100 + model_index * 10 + offset,
                    )
                    for name, offset in (("spearman", 0), ("mae", 10), ("rmse", 20))
                }
                status = "UNDEFINED_CONSTANT_PREDICTION" if model_id == "CONSTANT_TRAINING_MEAN" else "DEFINED"
                fold_metrics.append(
                    {
                        "outer_fold_id": fold_id,
                        "held_out_laboratory_anchor": held_out_lab,
                        "model_id": model_id,
                        "held_out_observation_count": len(testing),
                        "held_out_measurement_batch_count": len(batch_rows),
                        "primary_metric_status": status,
                        "primary_cluster_count": len(unit_rows),
                        **summary,
                        "mean_spearman_lower_95": None if ci["spearman"] is None else ci["spearman"]["lower_95"],
                        "mean_spearman_upper_95": None if ci["spearman"] is None else ci["spearman"]["upper_95"],
                        "mean_mae_lower_95": None if ci["mae"] is None else ci["mae"]["lower_95"],
                        "mean_mae_upper_95": None if ci["mae"] is None else ci["mae"]["upper_95"],
                        "mean_rmse_lower_95": None if ci["rmse"] is None else ci["rmse"]["lower_95"],
                        "mean_rmse_upper_95": None if ci["rmse"] is None else ci["rmse"]["upper_95"],
                    }
                )
                for metric in batch_rows:
                    batch_metrics.append(
                        {
                            "outer_fold_id": fold_id,
                            "held_out_laboratory_anchor": held_out_lab,
                            "model_id": model_id,
                            **metric,
                            "spearman_status": status if metric["spearman"] is None else "DEFINED",
                        }
                    )
                for unit in unit_rows:
                    unit_metrics.append(
                        {
                            "outer_fold_id": fold_id,
                            "held_out_laboratory_anchor": held_out_lab,
                            "model_id": model_id,
                            **unit,
                        }
                    )
                for observation, value in zip(testing, predicted, strict=True):
                    predictions.append(
                        {
                            "outer_fold_id": fold_id,
                            "held_out_laboratory_anchor": held_out_lab,
                            "model_id": model_id,
                            "target_observation_id": observation.target_observation_id,
                            "source_id": observation.source_id,
                            "canonical_accession": observation.canonical_accession,
                            "measurement_batch_id": observation.measurement_batch_id,
                            "observed_rank_percentile_descending": observation.target,
                            "predicted_rank_percentile_descending": float(value),
                        }
                    )
            full_units = {row["biological_unit_id"]: row for row in metric_by_model["SEQUENCE_RIDGE_FULL"][1]}
            composition_units = {
                row["biological_unit_id"]: row for row in metric_by_model["SEQUENCE_RIDGE_COMPOSITION_ONLY"][1]
            }
            common_units = sorted(set(full_units) & set(composition_units))
            ablation_diffs = {
                metric: [
                    float(full_units[unit][metric]) - float(composition_units[unit][metric]) for unit in common_units
                ]
                for metric in ("spearman", "mae", "rmse")
            }
            ablation = {
                "outer_fold_id": fold_id,
                "held_out_laboratory_anchor": held_out_lab,
                "paired_measurement_batch_count": len(metric_by_model["SEQUENCE_RIDGE_FULL"][0]),
                "paired_biological_unit_count": len(common_units),
                "full_minus_composition_mean_spearman": float(np.mean(ablation_diffs["spearman"])),
                "full_minus_composition_mean_mae": float(np.mean(ablation_diffs["mae"])),
                "full_minus_composition_mean_rmse": float(np.mean(ablation_diffs["rmse"])),
                "resamples": bootstrap_resamples,
                "seed": bootstrap_seed + fold_index * 1000 + 701,
                "lower_95": self._bootstrap_metric(
                    ablation_diffs["spearman"],
                    resamples=bootstrap_resamples,
                    seed=bootstrap_seed + fold_index * 1000 + 701,
                )["lower_95"],
                "upper_95": self._bootstrap_metric(
                    ablation_diffs["spearman"],
                    resamples=bootstrap_resamples,
                    seed=bootstrap_seed + fold_index * 1000 + 701,
                )["upper_95"],
            }
            ablations.append(ablation)
            observed = next(
                row
                for row in fold_metrics
                if row["outer_fold_id"] == fold_id and row["model_id"] == "SEQUENCE_RIDGE_FULL"
            )["mean_spearman"]
            if observed is None:
                raise R4T273BiologicalUnitPrimaryError("T273 full-model primary metric is undefined")
            development_targets_by_batch: dict[tuple[str, str], list[str]] = defaultdict(list)
            for row in development:
                development_targets_by_batch[(row.source_id, row.measurement_batch_id)].append(
                    row.target_observation_id
                )
            rng = np.random.default_rng(negative_seed + fold_index)
            null_values: list[float] = []
            for resample in range(1, negative_resamples + 1):
                permuted = {row.target_observation_id: row.target for row in development}
                for ids in development_targets_by_batch.values():
                    shuffled = rng.permutation([permuted[item] for item in ids])
                    for observation_id, value in zip(ids, shuffled, strict=True):
                        permuted[observation_id] = float(value)
                selected_null_alpha, _, null_selection_audit = self._select_alpha_grouped(
                    development,
                    full_indices,
                    minimum_proteins=minimum,
                    n_splits=inner_folds,
                    target_overrides=permuted,
                )
                null_model = helper._fit_ridge(
                    development,
                    full_indices,
                    selected_null_alpha,
                    targets=np.asarray([permuted[row.target_observation_id] for row in development], dtype=float),
                )
                null_predictions = helper._predict_ridge(null_model, testing)
                _, null_units = self._batch_and_unit_metrics(testing, null_predictions, minimum_proteins=minimum)
                null_score = self._unit_summary(null_units)["mean_spearman"]
                if null_score is None:
                    raise R4T273BiologicalUnitPrimaryError("T273 selection-aware null metric is undefined")
                null_values.append(float(null_score))
                negative_rows.append(
                    {
                        "outer_fold_id": fold_id,
                        "held_out_laboratory_anchor": held_out_lab,
                        "selected_alpha": selected_null_alpha,
                        "resample": resample,
                        "null_mean_spearman": float(null_score),
                        "null_primary_cluster": "biological_unit_id",
                        "alpha_selection_recomputed": True,
                        "null_inner_unit_fold_count": null_selection_audit["fold_count"],
                    }
                )
            parameters[fold_id]["SEQUENCE_RIDGE_FULL"]["negative_control"] = {
                "resamples": negative_resamples,
                "random_seed": negative_seed + fold_index,
                "observed_mean_spearman": observed,
                "null_mean_spearman_mean": float(np.mean(null_values)),
                "null_mean_spearman_lower_95": float(np.quantile(null_values, 0.025)),
                "null_mean_spearman_upper_95": float(np.quantile(null_values, 0.975)),
                "one_sided_upper_tail_p": float(
                    (1 + sum(value >= observed for value in null_values)) / (1 + negative_resamples)
                ),
                "alpha_selection_recomputed_per_permutation": True,
                "primary_cluster": "biological_unit_id",
            }
        primary_artifacts = {
            "unit_metrics": unit_metrics,
            "ablations": ablations,
            "negative_rows": negative_rows,
            "parameters": parameters,
            "coverage": [
                {
                    "source_id": source_id,
                    **values,
                    "model_metric_eligible_rows": sum(1 for row in observations if row.source_id == source_id),
                    "raw_to_rank_eligible_exclusion_is_not_missingness_model": True,
                }
                for source_id, values in sorted(self._accounting.items())
            ],
        }
        self._last_primary = self._round_numbers(primary_artifacts)
        artifacts = {
            "predictions": predictions,
            "batch_metrics": batch_metrics,
            "fold_metrics": fold_metrics,
            "selections": selections,
            "ablations": ablations,
            "negative_rows": negative_rows,
            "parameters": parameters,
        }
        fold_contract = {
            "outer_labs": [
                {"held_out_laboratory_anchor": lab, "fold_id": f"{self.FOLD_PREFIX}_OUTER_{index:02d}"}
                for index, lab in enumerate(outer, start=1)
            ],
            "inner_split": "biological_unit_grouped_kfold",
            "primary_cluster": "biological_unit_id",
        }
        return self._round_numbers(artifacts), self._round_numbers(fold_contract)

    @staticmethod
    def _write_csv(path: Path, fields: Sequence[str], rows: Sequence[Mapping[str, Any]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
            writer.writeheader()
            for row in rows:
                writer.writerow({field: "" if row.get(field) is None else row.get(field) for field in fields})

    def _augment_cluster_artifact(self) -> None:
        if not self._last_primary:
            raise R4T273BiologicalUnitPrimaryError("T273 primary artifacts are missing")
        unit_path = self.output_root / "biological_unit_primary_metrics.csv"
        self._write_csv(
            unit_path,
            [
                "outer_fold_id",
                "held_out_laboratory_anchor",
                "model_id",
                "biological_unit_id",
                "source_id",
                "measurement_batch_count",
                "protein_count",
                "spearman",
                "mae",
                "rmse",
            ],
            self._last_primary["unit_metrics"],
        )
        ablation_path = self.output_root / "biological_unit_paired_ablation.csv"
        self._write_csv(
            ablation_path,
            [
                "outer_fold_id",
                "held_out_laboratory_anchor",
                "paired_biological_unit_count",
                "full_minus_composition_mean_spearman",
                "full_minus_composition_mean_mae",
                "full_minus_composition_mean_rmse",
                "lower_95",
                "upper_95",
                "resamples",
                "seed",
            ],
            self._last_primary["ablations"],
        )
        coverage_path = self.output_root / "coverage_missingness_flow.csv"
        self._write_csv(
            coverage_path,
            [
                "source_id",
                "laboratory_anchor",
                "license",
                "access_condition",
                "biological_unit_semantics",
                "raw_map_rows",
                "rank_eligible_rows",
                "rank_eligible_target_count",
                "rank_eligible_batch_count",
                "common_rows",
                "common_target_batch_pairs",
                "biological_unit_count",
                "qualified_measurement_batch_count",
                "qualified_biological_unit_count",
                "model_metric_eligible_rows",
                "raw_to_rank_eligible_exclusion_is_not_missingness_model",
            ],
            self._last_primary["coverage"],
        )
        audit_path = self.output_root / "grouped_selection_audit.json"
        self._write_json(
            audit_path,
            {
                "schema_version": 1,
                "primary_cluster": "biological_unit_id",
                "inner_selection": "biological_unit_grouped_kfold",
                "all_outer_test_units_disjoint_from_inner_selection": True,
                "negative_control_reselects_alpha_per_permutation": True,
                "paired_ablation_primary_unit_level": True,
                "batch_level_metrics_are_secondary": True,
            },
        )
        report_path = self.output_root / self.REPORT_NAME
        receipt_path = self.output_root / self.RECEIPT_NAME
        report = self._json(report_path, "T273 report")
        receipt = self._json(receipt_path, "T273 receipt")
        report.setdefault("artifacts", {})["biological_unit_primary_metrics"] = {
            "relative_path": unit_path.relative_to(self.root).as_posix(),
            "sha256": _sha256(unit_path),
        }
        report["artifacts"]["biological_unit_paired_ablation"] = {
            "relative_path": ablation_path.relative_to(self.root).as_posix(),
            "sha256": _sha256(ablation_path),
        }
        report["artifacts"]["coverage_missingness_flow"] = {
            "relative_path": coverage_path.relative_to(self.root).as_posix(),
            "sha256": _sha256(coverage_path),
        }
        report["artifacts"]["grouped_selection_audit"] = {
            "relative_path": audit_path.relative_to(self.root).as_posix(),
            "sha256": _sha256(audit_path),
        }
        report["primary_estimand"] = {
            "cluster_key": "biological_unit_id",
            "unit_metric": "within_unit_mean_across_qualified_measurement_batch_metrics",
            "estimand": "equal_mean_over_biological_units",
            "batch_metrics_are_secondary": True,
        }
        report["statistics_contract"] = {
            "target_universe_fixed_before_outer_split": True,
            "inner_selection_unit_grouped": True,
            "negative_control_alpha_selection_recomputed": True,
            "paired_ablation_unit_grouped": True,
            "coverage_flow_recorded": True,
        }
        self._write_json(report_path, report)
        receipt["report_sha256"] = _sha256(report_path)
        receipt["primary_estimand"] = report["primary_estimand"]
        receipt["statistics_contract"] = report["statistics_contract"]
        self._write_json(receipt_path, receipt)

    def run(self, *, strict: bool = False) -> R4T193ThreeLabExecutionSummary:
        if not strict:
            raise R4T273BiologicalUnitPrimaryError("T273 execution requires --strict")
        summary = super(R4T265BiologicalCommonTargetWorkflow, self).run(strict=True)
        self._augment_cluster_artifact()
        return summary

    def verify(self, *, strict: bool = True) -> R4T193ThreeLabExecutionSummary:
        if not strict:
            raise R4T273BiologicalUnitPrimaryError("T273 verification requires --strict")
        summary = super(R4T265BiologicalCommonTargetWorkflow, self).verify(strict=True)
        report = self._json(self.output_root / self.REPORT_NAME, "T273 report")
        required = {
            "biological_unit_primary_metrics",
            "biological_unit_paired_ablation",
            "coverage_missingness_flow",
            "grouped_selection_audit",
        }
        if not required.issubset(set(report.get("artifacts", {}))):
            raise R4T273BiologicalUnitPrimaryError("T273 primary artifacts are incomplete")
        estimand = report.get("primary_estimand", {})
        contract = report.get("statistics_contract", {})
        if (
            estimand.get("cluster_key") != "biological_unit_id"
            or estimand.get("batch_metrics_are_secondary") is not True
            or contract.get("inner_selection_unit_grouped") is not True
            or contract.get("negative_control_alpha_selection_recomputed") is not True
            or contract.get("paired_ablation_unit_grouped") is not True
        ):
            raise R4T273BiologicalUnitPrimaryError("T273 primary estimand contract is invalid")
        return summary
