"""Run a source-availability-aware leave-one-laboratory-out sensitivity analysis.

T195 is deliberately retained as a strict-common-target sensitivity, but its nine
targets are defined from all three source maps.  T197 addresses the corresponding
reviewer concern by deriving each outer-fold target set from the two development
sources only.  The held-out source contributes observations only after the target
set and nested hyperparameters have been frozen.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

import numpy as np

from biointerfaceos.r3_model_evaluation import R3ModelEvaluationWorkflow, _Observation
from biointerfaceos.r3_uniprot_mapping import _canonical, _checksum, _mapping, _sha256, _string
from biointerfaceos.r4_t192_three_lab_common_target import (
    R4T192ThreeLabCommonTargetError,
    R4T192ThreeLabCommonTargetWorkflow,
)


class R4T197SourceAvailabilityError(RuntimeError):
    """Raised when the T197 sensitivity cannot close its frozen inputs or outputs."""


@dataclass(frozen=True)
class R4T197SourceAvailabilitySummary:
    observation_count: int
    outer_fold_count: int
    target_count_minimum: int
    measurement_batch_count: int
    model_count: int
    receipt_path: Path


class R4T197SourceAvailabilityWorkflow:
    """Execute target selection using development sources only in every outer fold."""

    AUDIT_ID = "bioif-r4-t197-source-availability-execution-v1.0.0"
    STATUS = "T197_SOURCE_AVAILABILITY_EXECUTION_COMPLETED_EXPLORATORY"
    PROTOCOL_RELATIVE = "docs/data/R4_T197_SOURCE_AVAILABILITY_EXECUTION_PROTOCOL.json"
    REGISTRY_RELATIVE = "docs/data/R4_T197_SOURCE_AVAILABILITY_EXECUTION_REGISTRY.json"
    T192_REGISTRY_RELATIVE = "docs/data/R4_T192_THREE_LAB_REDISTRIBUTABLE_COMMON_TARGET_REGISTRY.json"
    FEATURE_RELATIVE = (
        "data/raw/r3_uniprot_sequence_features/uniprot_sequence_features/R3_uniprot_sequence_features.csv"
    )
    OUTPUT_RELATIVE = "reports/review_round_4/t197_source_availability_execution/v1.0.0"
    REPORT_NAME = "t197_source_availability_execution_report.json"
    RECEIPT_NAME = "t197_source_availability_execution_receipt.json"
    REGISTRY_STATUS = "T197_SOURCE_AVAILABILITY_EXECUTION_REGISTERED"
    PROTOCOL_STATUS = "FROZEN_BEFORE_T197_EXECUTION"
    SOURCE_COUNT = 3
    FOLD_PREFIX = "T197"
    OBSERVATION_PREFIX = "T197"
    SEED_OFFSET_BY_FOLD = False
    REQUIRED_REFERENCE = {"relative_path", "sha256"}
    MODEL_IDS = R3ModelEvaluationWorkflow.MODEL_IDS

    def __init__(self, root: Path, *, output_root: Path | None = None) -> None:
        self.root = root.resolve(strict=True)
        candidate = (output_root or self.root / self.OUTPUT_RELATIVE).resolve(strict=False)
        if not candidate.is_relative_to(self.root):
            raise R4T197SourceAvailabilityError("T197 output must remain under repository root")
        self.output_root = candidate

    @staticmethod
    def _write_json(path: Path, value: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(_canonical(value))

    @staticmethod
    def _write_csv(path: Path, fields: Sequence[str], rows: Sequence[Mapping[str, Any]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
            writer.writeheader()
            for row in rows:
                writer.writerow({field: "" if row.get(field) is None else row.get(field) for field in fields})

    @staticmethod
    def _json(path: Path, label: str) -> dict[str, Any]:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            return _mapping(value, label)
        except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
            raise R4T197SourceAvailabilityError(f"cannot parse {label}") from exc

    def _root_file(self, relative_path: str, label: str) -> Path:
        if "\\" in relative_path:
            raise R4T197SourceAvailabilityError(f"{label} must use POSIX separators")
        pure = PurePosixPath(relative_path)
        if pure.is_absolute() or not pure.parts or ".." in pure.parts:
            raise R4T197SourceAvailabilityError(f"{label} escapes repository root")
        path = (self.root / Path(*pure.parts)).resolve(strict=False)
        if not path.is_relative_to(self.root) or not path.is_file():
            raise R4T197SourceAvailabilityError(f"{label} is missing or outside repository root")
        return path

    def _reference(self, value: Any, label: str) -> Path:
        reference = _mapping(value, label)
        if set(reference) != self.REQUIRED_REFERENCE:
            raise R4T197SourceAvailabilityError(f"{label} reference fields are invalid")
        path = self._root_file(_string(reference["relative_path"], label), label)
        if _sha256(path) != _checksum(reference["sha256"], label):
            raise R4T197SourceAvailabilityError(f"{label} checksum differs")
        return path

    @staticmethod
    def _read_csv(path: Path, label: str) -> list[dict[str, str]]:
        try:
            with path.open("r", encoding="utf-8", newline="") as stream:
                rows = list(csv.DictReader(stream))
        except OSError as exc:
            raise R4T197SourceAvailabilityError(f"cannot read {label}") from exc
        if not rows or not rows[0]:
            raise R4T197SourceAvailabilityError(f"{label} is empty")
        return rows

    def _registry(self) -> tuple[dict[str, Any], dict[str, Any], dict[str, Path]]:
        registry = self._json(self.root / self.REGISTRY_RELATIVE, "T197 registry")
        required = {
            "schema_version",
            "audit_id",
            "protocol_id",
            "status",
            "evidence_class",
            "allowed_claim_level",
            "protocol",
            "t192_source_registry",
            "r3_sequence_feature_table",
            "sources",
            "expected_accounting",
            "output_contract",
            "claim_boundary",
            "scientific_submission_ready",
        }
        if set(registry) != required or registry.get("schema_version") != 1:
            raise R4T197SourceAvailabilityError("T197 registry fields are invalid")
        if (
            registry.get("audit_id") != self.AUDIT_ID
            or registry.get("protocol_id") != self.AUDIT_ID
            or registry.get("status") != self.REGISTRY_STATUS
            or registry.get("evidence_class") != "DEVELOPMENT_OBSERVATION"
            or registry.get("allowed_claim_level") != "EXPLORATORY"
            or registry.get("scientific_submission_ready") is not False
        ):
            raise R4T197SourceAvailabilityError("T197 registry identity or boundary is invalid")
        protocol_path = self._reference(registry["protocol"], "T197 protocol")
        protocol = self._json(protocol_path, "T197 protocol")
        if (
            protocol.get("protocol_id") != self.AUDIT_ID
            or protocol.get("status") != self.PROTOCOL_STATUS
            or protocol.get("scientific_submission_ready") is not False
        ):
            raise R4T197SourceAvailabilityError("T197 protocol identity or boundary is invalid")
        refs = {
            "protocol": protocol_path,
            "t192_source_registry": self._reference(registry["t192_source_registry"], "T192 registry"),
            "r3_sequence_feature_table": self._reference(registry["r3_sequence_feature_table"], "R3 feature table"),
        }
        if refs["t192_source_registry"] != self.root / self.T192_REGISTRY_RELATIVE:
            raise R4T197SourceAvailabilityError("T197 does not use the release-fixed T192 registry")
        if refs["r3_sequence_feature_table"] != self.root / self.FEATURE_RELATIVE:
            raise R4T197SourceAvailabilityError("T197 does not use the release-fixed feature table")
        source_ids = registry.get("sources")
        if (
            not isinstance(source_ids, list)
            or len(source_ids) != self.SOURCE_COUNT
            or len(set(source_ids)) != self.SOURCE_COUNT
        ):
            raise R4T197SourceAvailabilityError("T197 requires three unique source IDs")
        protocol_sources = _mapping(protocol["outer_split"], "T197 outer split").get("source_ids")
        if protocol_sources != source_ids:
            raise R4T197SourceAvailabilityError("T197 protocol and registry source IDs differ")
        return registry, protocol, refs

    def _features(self, path: Path) -> dict[str, tuple[float, ...]]:
        rows = self._read_csv(path, "R3 feature table")
        expected = {"canonical_accession", *R3ModelEvaluationWorkflow.FEATURE_NAMES}
        if set(rows[0]) != expected:
            raise R4T197SourceAvailabilityError("R3 feature table schema differs")
        features: dict[str, tuple[float, ...]] = {}
        for row in rows:
            accession = _string(row.get("canonical_accession"), "feature accession")
            if accession in features:
                raise R4T197SourceAvailabilityError("R3 feature table repeats an accession")
            try:
                values = tuple(float(row[name]) for name in R3ModelEvaluationWorkflow.FEATURE_NAMES)
            except (TypeError, ValueError) as exc:
                raise R4T197SourceAvailabilityError("R3 feature value is invalid") from exc
            if not all(math.isfinite(value) for value in values):
                raise R4T197SourceAvailabilityError("R3 feature value is not finite")
            features[accession] = values
        return features

    def _source_rows(
        self, refs: Mapping[str, Path]
    ) -> tuple[
        R4T192ThreeLabCommonTargetWorkflow,
        dict[str, dict[str, Any]],
        dict[str, list[tuple[dict[str, str], float, int]]],
    ]:
        t192 = R4T192ThreeLabCommonTargetWorkflow(self.root, registry_path=refs["t192_source_registry"])
        try:
            _, _, sources = t192._documents()
            rows: dict[str, list[tuple[dict[str, str], float, int]]] = {}
            source_meta: dict[str, dict[str, Any]] = {}
            for source in sources:
                source_id = _string(source["source_id"], "T192 source ID")
                _, eligible = t192._validate_source_metadata(source)
                ranks = t192._rank_rows(eligible)
                rows[source_id] = [(row, ranks[index][0], ranks[index][1]) for index, row in enumerate(eligible)]
                source_meta[source_id] = source
        except R4T192ThreeLabCommonTargetError as exc:
            raise R4T197SourceAvailabilityError("T192 source admission does not verify") from exc
        return t192, source_meta, rows

    @classmethod
    def _make_observations(
        cls,
        source_id: str,
        fold_id: str,
        rows: Sequence[tuple[dict[str, str], float, int]],
        targets: set[str],
        features: Mapping[str, tuple[float, ...]],
    ) -> tuple[list[_Observation], list[dict[str, Any]]]:
        observations: list[_Observation] = []
        ledger: list[dict[str, Any]] = []
        for row, percentile, positive_count in rows:
            accession = row["canonical_accession"]
            if accession not in targets:
                continue
            if accession not in features:
                raise R4T197SourceAvailabilityError(f"T197 target {accession} lacks a feature")
            identity = f"{fold_id}|{source_id}|{row['source_coordinate']}|{accession}"
            observation_id = cls.OBSERVATION_PREFIX + "_" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:20]
            observations.append(
                _Observation(
                    observation_id,
                    source_id,
                    accession,
                    row["laboratory_anchor"],
                    row["measurement_batch_id"],
                    percentile,
                    features[accession],
                )
            )
            ledger.append(
                {
                    "target_observation_id": observation_id,
                    "outer_fold_id": fold_id,
                    "split_role": "TEST" if row.get("split_role") == "TEST" else "DEVELOPMENT",
                    "source_id": source_id,
                    "laboratory_anchor": row["laboratory_anchor"],
                    "canonical_accession": accession,
                    "measurement_batch_id": row["measurement_batch_id"],
                    "biological_unit_id": row.get("biological_unit_id", ""),
                    "source_asset_id": row["source_asset_id"],
                    "source_row": row["source_row"],
                    "source_coordinate": row["source_coordinate"],
                    "source_identifier": row["source_identifier"],
                    "author_numeric_value": row["author_numeric_value"],
                    "source_local_rank_percentile": format(percentile, ".17g"),
                    "source_batch_positive_count": positive_count,
                    "target_membership_basis": "DEVELOPMENT_SOURCES_ONLY",
                    "cross_source_scale_use": "PROHIBITED",
                }
            )
        return sorted(observations, key=lambda item: item.target_observation_id), sorted(
            ledger, key=lambda item: item["target_observation_id"]
        )

    @staticmethod
    def _permuted_observations(observations: Sequence[_Observation], targets: np.ndarray) -> list[_Observation]:
        return [
            _Observation(
                row.target_observation_id,
                row.source_id,
                row.canonical_accession,
                row.laboratory_anchor,
                row.measurement_batch_id,
                float(target),
                row.feature_values,
            )
            for row, target in zip(observations, targets, strict=True)
        ]

    def _run_models(
        self,
        helper: R3ModelEvaluationWorkflow,
        development: Sequence[_Observation],
        testing: Sequence[_Observation],
        protocol: Mapping[str, Any],
        fold_id: str,
        held_out_source: str,
    ) -> dict[str, Any]:
        nested = _mapping(protocol["nested_selection"], "T197 nested selection")
        minimum = int(nested["minimum_proteins_per_batch"])
        full_indices = tuple(range(len(helper.FEATURE_NAMES)))
        composition_indices = tuple(helper.FEATURE_NAMES.index(name) for name in helper.COMPOSITION_FEATURE_NAMES)
        full_alpha, full_selection = helper._select_alpha(development, full_indices, minimum_proteins=minimum)
        composition_alpha, composition_selection = helper._select_alpha(
            development, composition_indices, minimum_proteins=minimum
        )
        constant_mean = float(np.mean([row.target for row in development]))
        full_model = helper._fit_ridge(development, full_indices, full_alpha)
        composition_model = helper._fit_ridge(development, composition_indices, composition_alpha)
        predictions = {
            "CONSTANT_TRAINING_MEAN": np.full(len(testing), constant_mean, dtype=float),
            "SEQUENCE_RIDGE_FULL": helper._predict_ridge(full_model, testing),
            "SEQUENCE_RIDGE_COMPOSITION_ONLY": helper._predict_ridge(composition_model, testing),
        }
        model_rows: list[dict[str, Any]] = []
        batch_rows: list[dict[str, Any]] = []
        prediction_rows: list[dict[str, Any]] = []
        metric_by_model: dict[str, list[dict[str, Any]]] = {}
        for model_id in self.MODEL_IDS:
            metrics = helper._batch_metrics(testing, predictions[model_id], minimum_proteins=minimum)
            metric_by_model[model_id] = metrics
            aggregate = helper._aggregate(metrics)
            model_rows.append(
                {
                    "outer_fold_id": fold_id,
                    "held_out_source_id": held_out_source,
                    "model_id": model_id,
                    "target_count": len({row.canonical_accession for row in testing}),
                    "observation_count": len(testing),
                    "measurement_batch_count": len(metrics),
                    "primary_metric_status": "UNDEFINED_CONSTANT_PREDICTION"
                    if model_id == "CONSTANT_TRAINING_MEAN"
                    else "DEFINED",
                    **aggregate,
                }
            )
            for metric in metrics:
                batch_rows.append(
                    {
                        "outer_fold_id": fold_id,
                        "held_out_source_id": held_out_source,
                        "model_id": model_id,
                        **metric,
                        "spearman_status": (
                            "UNDEFINED_CONSTANT_PREDICTION"
                            if model_id == "CONSTANT_TRAINING_MEAN" and metric["spearman"] is None
                            else "DEFINED"
                        ),
                    }
                )
            for observation, prediction in zip(testing, predictions[model_id], strict=True):
                prediction_rows.append(
                    {
                        "outer_fold_id": fold_id,
                        "held_out_source_id": held_out_source,
                        "model_id": model_id,
                        "target_observation_id": observation.target_observation_id,
                        "canonical_accession": observation.canonical_accession,
                        "measurement_batch_id": observation.measurement_batch_id,
                        "observed_rank_percentile_descending": observation.target,
                        "predicted_rank_percentile_descending": float(prediction),
                    }
                )
        full_metrics = metric_by_model["SEQUENCE_RIDGE_FULL"]
        composition_metrics = metric_by_model["SEQUENCE_RIDGE_COMPOSITION_ONLY"]
        differences = [
            float(full["spearman"]) - float(composition["spearman"])
            for full, composition in zip(full_metrics, composition_metrics, strict=True)
            if full["spearman"] is not None and composition["spearman"] is not None
        ]
        uncertainty = _mapping(protocol["uncertainty"], "T197 uncertainty")
        seed_offset = int(fold_id.rsplit("_", maxsplit=1)[-1]) if self.SEED_OFFSET_BY_FOLD else len(fold_id)
        paired_interval: dict[str, float | int | None] = {}
        if differences:
            paired_interval.update(
                helper._bootstrap(
                    differences,
                    resamples=int(uncertainty["resamples"]),
                    seed=int(uncertainty["random_seed"]) + seed_offset,
                )
            )
        else:
            paired_interval.update(
                {
                    "resamples": int(uncertainty["resamples"]),
                    "seed": int(uncertainty["random_seed"]) + seed_offset,
                    "lower_95": None,
                    "upper_95": None,
                }
            )
        paired = {
            "outer_fold_id": fold_id,
            "held_out_source_id": held_out_source,
            "paired_measurement_batch_count": len(differences),
            "full_minus_composition_mean_spearman": float(np.mean(differences)) if differences else None,
            **paired_interval,
        }
        negative = _mapping(protocol["negative_control"], "T197 negative control")
        development_targets = np.asarray([row.target for row in development], dtype=float)
        by_batch: dict[str, list[int]] = defaultdict(list)
        for index, row in enumerate(development):
            by_batch[row.measurement_batch_id].append(index)
        rng = np.random.default_rng(int(negative["random_seed"]) + seed_offset)
        null_rows: list[dict[str, Any]] = []
        null_scores: list[float] = []
        for resample in range(1, int(negative["resamples"]) + 1):
            permuted = development_targets.copy()
            for positions in by_batch.values():
                permuted[positions] = rng.permutation(permuted[positions])
            permuted_development = self._permuted_observations(development, permuted)
            null_alpha, _ = helper._select_alpha(permuted_development, full_indices, minimum_proteins=minimum)
            null_model = helper._fit_ridge(permuted_development, full_indices, null_alpha, targets=permuted)
            null_metrics = helper._batch_metrics(
                testing, helper._predict_ridge(null_model, testing), minimum_proteins=minimum
            )
            score = helper._aggregate(null_metrics)["mean_spearman"]
            if score is None:
                raise R4T197SourceAvailabilityError("T197 negative-control Spearman is undefined")
            null_scores.append(float(score))
            null_rows.append(
                {
                    "outer_fold_id": fold_id,
                    "held_out_source_id": held_out_source,
                    "resample": resample,
                    "selected_alpha": null_alpha,
                    "null_mean_spearman": float(score),
                }
            )
        observed = next(row["mean_spearman"] for row in model_rows if row["model_id"] == "SEQUENCE_RIDGE_FULL")
        negative_summary = {
            "resamples": int(negative["resamples"]),
            "random_seed": int(negative["random_seed"]) + seed_offset,
            "selection_reexecuted_per_resample": True,
            "observed_mean_spearman": observed,
            "null_mean_spearman_mean": float(np.mean(null_scores)),
            "null_mean_spearman_lower_95": float(np.quantile(null_scores, 0.025)),
            "null_mean_spearman_upper_95": float(np.quantile(null_scores, 0.975)),
            "one_sided_upper_tail_p": float(
                (1 + sum(value >= observed for value in null_scores)) / (1 + len(null_scores))
            ),
        }
        return {
            "model_rows": model_rows,
            "batch_rows": batch_rows,
            "prediction_rows": prediction_rows,
            "selection_rows": [
                {
                    "outer_fold_id": fold_id,
                    "held_out_source_id": held_out_source,
                    "model_id": "SEQUENCE_RIDGE_FULL",
                    **row,
                    "selected_alpha": full_alpha,
                }
                for row in full_selection
            ]
            + [
                {
                    "outer_fold_id": fold_id,
                    "held_out_source_id": held_out_source,
                    "model_id": "SEQUENCE_RIDGE_COMPOSITION_ONLY",
                    **row,
                    "selected_alpha": composition_alpha,
                }
                for row in composition_selection
            ],
            "paired": paired,
            "negative_rows": null_rows,
            "negative_summary": negative_summary,
            "parameters": {
                "full_selected_alpha": full_alpha,
                "composition_selected_alpha": composition_alpha,
                "development_observation_count": len(development),
                "test_observation_count": len(testing),
                "full_model": helper._ridge_parameters(full_model, helper.FEATURE_NAMES),
                "composition_model": helper._ridge_parameters(composition_model, helper.COMPOSITION_FEATURE_NAMES),
            },
        }

    def run(self, *, strict: bool = False) -> R4T197SourceAvailabilitySummary:
        if not strict:
            raise R4T197SourceAvailabilityError("T197 execution requires --strict")
        if self.output_root.exists():
            raise R4T197SourceAvailabilityError("T197 execution already exists")
        registry, protocol, refs = self._registry()
        features = self._features(refs["r3_sequence_feature_table"])
        _, source_meta, source_rows = self._source_rows(refs)
        source_ids = list(registry["sources"])
        if set(source_ids) != set(source_rows):
            raise R4T197SourceAvailabilityError("T197 registry does not close T192 sources")
        source_target_sets = {
            source_id: {row[0]["canonical_accession"] for row in rows} for source_id, rows in source_rows.items()
        }
        helper = R3ModelEvaluationWorkflow(
            self.root,
            self.root / "data/raw",
            self.root / "data/raw/r3_uniprot_sequence_features",
            output_root=self.root / "reports/review_round_4/t197_helper_unused",
        )
        split_cfg = _mapping(protocol["outer_split"], "T197 outer split")
        minimum_target_count = int(split_cfg["minimum_development_target_count"])
        all_ledger: list[dict[str, Any]] = []
        all_model_rows: list[dict[str, Any]] = []
        all_batch_rows: list[dict[str, Any]] = []
        all_prediction_rows: list[dict[str, Any]] = []
        all_selection_rows: list[dict[str, Any]] = []
        all_paired: list[dict[str, Any]] = []
        all_negative_rows: list[dict[str, Any]] = []
        fold_targets: list[dict[str, Any]] = []
        parameters: dict[str, Any] = {}
        for fold_index, held_out_source in enumerate(sorted(source_ids), start=1):
            fold_id = f"{self.FOLD_PREFIX}_OUTER_{fold_index:02d}"
            development_sources = sorted(source_id for source_id in source_ids if source_id != held_out_source)
            target_set = set.intersection(*(source_target_sets[source_id] for source_id in development_sources))
            if len(target_set) < minimum_target_count:
                raise R4T197SourceAvailabilityError(f"T197 fold {fold_id} has too few development-only targets")
            development: list[_Observation] = []
            testing: list[_Observation] = []
            fold_ledger: list[dict[str, Any]] = []
            for source_id in development_sources:
                rows = [
                    (dict(row, split_role="DEVELOPMENT"), percentile, count)
                    for row, percentile, count in source_rows[source_id]
                ]
                observations, ledger = self._make_observations(source_id, fold_id, rows, target_set, features)
                development.extend(observations)
                fold_ledger.extend(ledger)
            rows = [
                (dict(row, split_role="TEST"), percentile, count)
                for row, percentile, count in source_rows[held_out_source]
            ]
            testing, test_ledger = self._make_observations(held_out_source, fold_id, rows, target_set, features)
            fold_ledger.extend(test_ledger)
            minimum = int(_mapping(protocol["nested_selection"], "T197 nested selection")["minimum_proteins_per_batch"])
            if not development or not testing:
                raise R4T197SourceAvailabilityError(f"T197 fold {fold_id} has no observations")
            if any(
                len([row for row in development if row.measurement_batch_id == batch_id]) < minimum
                for batch_id in {row.measurement_batch_id for row in development}
            ):
                raise R4T197SourceAvailabilityError(f"T197 fold {fold_id} has an under-covered development batch")
            fold_result = self._run_models(helper, development, testing, protocol, fold_id, held_out_source)
            for item in fold_ledger:
                item["target_universe_count"] = len(target_set)
            all_ledger.extend(fold_ledger)
            all_model_rows.extend(fold_result["model_rows"])
            all_batch_rows.extend(fold_result["batch_rows"])
            all_prediction_rows.extend(fold_result["prediction_rows"])
            all_selection_rows.extend(fold_result["selection_rows"])
            all_paired.append(fold_result["paired"])
            all_negative_rows.extend(fold_result["negative_rows"])
            parameters[fold_id] = fold_result["parameters"] | {
                "held_out_source_id": held_out_source,
                "development_source_ids": development_sources,
                "development_only_target_set": sorted(target_set),
                "test_available_target_count": len(target_set & source_target_sets[held_out_source]),
                "negative_control": fold_result["negative_summary"],
            }
            fold_targets.append(
                {
                    "outer_fold_id": fold_id,
                    "held_out_source_id": held_out_source,
                    "development_source_ids": development_sources,
                    "development_only_target_count": len(target_set),
                    "test_available_target_count": len(target_set & source_target_sets[held_out_source]),
                    "test_observation_count": len(testing),
                    "test_measurement_batch_count": len({row.measurement_batch_id for row in testing}),
                }
            )
        output = self.output_root
        output.mkdir(parents=True, exist_ok=False)
        paths = {
            "target_ledger": output / "source_availability_target_ledger.csv",
            "model_metrics": output / "outer_fold_model_metrics.csv",
            "batch_metrics": output / "outer_fold_batch_metrics.csv",
            "predictions": output / "outer_fold_predictions.csv",
            "nested_selection": output / "nested_selection.csv",
            "paired_ablation": output / "paired_composition_ablation.csv",
            "negative_control": output / "nested_selection_aware_permutation.csv",
            "parameters": output / "outer_fold_model_parameters.json",
            "fold_targets": output / "outer_fold_target_sets.json",
        }
        self._write_csv(paths["target_ledger"], list(all_ledger[0]), all_ledger)
        self._write_csv(paths["model_metrics"], list(all_model_rows[0]), all_model_rows)
        self._write_csv(paths["batch_metrics"], list(all_batch_rows[0]), all_batch_rows)
        self._write_csv(paths["predictions"], list(all_prediction_rows[0]), all_prediction_rows)
        self._write_csv(paths["nested_selection"], list(all_selection_rows[0]), all_selection_rows)
        self._write_csv(paths["paired_ablation"], list(all_paired[0]), all_paired)
        self._write_csv(paths["negative_control"], list(all_negative_rows[0]), all_negative_rows)
        self._write_json(paths["parameters"], parameters)
        self._write_json(paths["fold_targets"], fold_targets)
        artifacts = {
            name: {"relative_path": path.relative_to(self.root).as_posix(), "sha256": _sha256(path)}
            for name, path in paths.items()
        }
        report = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "protocol_id": protocol["protocol_id"],
            "protocol_sha256": _sha256(refs["protocol"]),
            "execution_module_sha256": _sha256(Path(__file__).resolve(strict=True)),
            "status": self.STATUS,
            "evidence_class": protocol["evidence_class"],
            "allowed_claim_level": protocol["allowed_claim_level"],
            "source_meta": {
                source_id: {
                    "laboratory_anchor": source_meta[source_id]["laboratory_anchor"],
                    "license": source_meta[source_id]["license"],
                    "rank_eligible_target_count": len(source_target_sets[source_id]),
                }
                for source_id in sorted(source_meta)
            },
            "fold_targets": fold_targets,
            "accounting": {
                "fold_ledger_row_count": len(all_ledger),
                "development_observation_count": sum(
                    int(values["development_observation_count"]) for values in parameters.values()
                ),
                "held_out_test_observation_count": sum(
                    int(values["test_observation_count"]) for values in parameters.values()
                ),
                "counting_rule": (
                    "fold ledger rows include development and held-out rows repeated by outer fold; "
                    "held_out_test_observation_count is the non-repeated test-only total"
                ),
            },
            "model_results": all_model_rows,
            "paired_composition_ablation": all_paired,
            "negative_control_summary": [
                {
                    "outer_fold_id": fold_id,
                    "held_out_source_id": values["held_out_source_id"],
                    **values["negative_control"],
                }
                for fold_id, values in sorted(parameters.items())
            ],
            "artifacts": artifacts,
            "claim_boundary": protocol["claim_boundary"],
            "independent_validation": False,
            "external_scientific_reproduction": False,
            "scientific_submission_ready": False,
        }
        report_path = output / self.REPORT_NAME
        self._write_json(report_path, report)
        receipt = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "status": self.STATUS,
            "report_sha256": _sha256(report_path),
            "observation_count": len(all_ledger),
            "fold_ledger_row_count": len(all_ledger),
            "development_observation_count": sum(
                int(values["development_observation_count"]) for values in parameters.values()
            ),
            "held_out_test_observation_count": sum(
                int(values["test_observation_count"]) for values in parameters.values()
            ),
            "counting_rule": (
                "observation_count is the fold ledger row count; held_out_test_observation_count is the test-only total"
            ),
            "outer_fold_count": len(fold_targets),
            "target_count_minimum": min(item["development_only_target_count"] for item in fold_targets),
            "measurement_batch_count": len({item["measurement_batch_id"] for item in all_ledger}),
            "model_count": len(self.MODEL_IDS),
            "nested_selection": True,
            "selection_reexecuted_in_negative_control": True,
            "independent_validation": False,
            "external_scientific_reproduction": False,
            "scientific_submission_ready": False,
        }
        receipt_path = output / self.RECEIPT_NAME
        self._write_json(receipt_path, receipt)
        return R4T197SourceAvailabilitySummary(
            len(all_ledger),
            len(fold_targets),
            int(receipt["target_count_minimum"]),
            int(receipt["measurement_batch_count"]),
            len(self.MODEL_IDS),
            receipt_path,
        )

    def verify(self, *, strict: bool = True) -> R4T197SourceAvailabilitySummary:
        if not strict:
            raise R4T197SourceAvailabilityError("T197 verification requires --strict")
        _, protocol, _ = self._registry()
        report_path = self.output_root / self.REPORT_NAME
        receipt_path = self.output_root / self.RECEIPT_NAME
        report = self._json(report_path, "T197 report")
        receipt = self._json(receipt_path, "T197 receipt")
        artifacts = _mapping(report.get("artifacts"), "T197 artifacts")
        for value in artifacts.values():
            item = _mapping(value, "T197 artifact")
            if set(item) != self.REQUIRED_REFERENCE:
                raise R4T197SourceAvailabilityError("T197 artifact reference fields are invalid")
            path = self._root_file(_string(item["relative_path"], "T197 artifact path"), "T197 artifact")
            if _sha256(path) != _checksum(item["sha256"], "T197 artifact checksum"):
                raise R4T197SourceAvailabilityError("T197 artifact checksum differs")
        if (
            report.get("audit_id") != self.AUDIT_ID
            or report.get("protocol_id") != protocol["protocol_id"]
            or report.get("status") != self.STATUS
            or report.get("scientific_submission_ready") is not False
            or receipt.get("audit_id") != self.AUDIT_ID
            or receipt.get("status") != self.STATUS
            or receipt.get("report_sha256") != _sha256(report_path)
            or receipt.get("nested_selection") is not True
            or receipt.get("selection_reexecuted_in_negative_control") is not True
            or receipt.get("scientific_submission_ready") is not False
        ):
            raise R4T197SourceAvailabilityError("T197 receipt is invalid")
        return R4T197SourceAvailabilitySummary(
            int(receipt["observation_count"]),
            int(receipt["outer_fold_count"]),
            int(receipt["target_count_minimum"]),
            int(receipt["measurement_batch_count"]),
            int(receipt["model_count"]),
            receipt_path,
        )
