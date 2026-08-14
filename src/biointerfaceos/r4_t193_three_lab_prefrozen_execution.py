"""Execute the leakage-controlled T193 three-source rank portability analysis.

T193 deliberately uses the R3 common-target universe, which was frozen before
the T192 public source packages were admitted.  The new source maps therefore
contribute held-out observations only; they do not select the target universe,
the model, or the ridge hyperparameter.
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

from biointerfaceos.r3_model_evaluation import (
    R3ModelEvaluationWorkflow,
    _Observation,
)
from biointerfaceos.r3_uniprot_mapping import _canonical, _checksum, _mapping, _sha256, _string
from biointerfaceos.r4_t192_three_lab_common_target import (
    R4T192ThreeLabCommonTargetError,
    R4T192ThreeLabCommonTargetWorkflow,
)


class R4T193ThreeLabExecutionError(RuntimeError):
    """Raised when frozen T193 inputs or outputs fail validation."""


@dataclass(frozen=True)
class R4T193ThreeLabExecutionSummary:
    observation_count: int
    target_universe_count: int
    laboratory_anchor_count: int
    measurement_batch_count: int
    model_count: int
    receipt_path: Path


class R4T193ThreeLabPrefrozenExecutionWorkflow:
    """Run the pre-registered, three-anchor study-held-out execution."""

    AUDIT_ID = "bioif-r4-t193-three-lab-prefrozen-target-execution-v1.0.0"
    STATUS = "T193_PREFROZEN_TARGET_EXECUTION_COMPLETED_EXPLORATORY"
    PROTOCOL_RELATIVE = "docs/data/R4_T193_THREE_LAB_PREFROZEN_TARGET_EXECUTION_PROTOCOL.json"
    REGISTRY_RELATIVE = "docs/data/R4_T193_THREE_LAB_PREFROZEN_TARGET_EXECUTION_REGISTRY.json"
    T192_REGISTRY_RELATIVE = "docs/data/R4_T192_THREE_LAB_REDISTRIBUTABLE_COMMON_TARGET_REGISTRY.json"
    R3_LEDGER_RELATIVE = "data/raw/r3_common_rank_target/R3_common_rank_target_ledger.csv"
    FEATURE_RELATIVE = (
        "data/raw/r3_uniprot_sequence_features/uniprot_sequence_features/R3_uniprot_sequence_features.csv"
    )
    OUTPUT_RELATIVE = "reports/review_round_4/t193_three_lab_prefrozen_target_execution/v1.0.0"
    REQUIRED_REFERENCE = {"relative_path", "sha256"}
    MODEL_IDS = R3ModelEvaluationWorkflow.MODEL_IDS
    LEDGER_FIELDS = [
        "target_observation_id",
        "source_id",
        "laboratory_anchor",
        "source_license",
        "canonical_accession",
        "measurement_batch_id",
        "biological_unit_id",
        "source_asset_id",
        "source_worksheet",
        "source_row",
        "source_coordinate",
        "source_identifier",
        "source_sample",
        "condition_label",
        "technical_replicate_id",
        "author_quantity_type",
        "author_numeric_value",
        "author_value_state",
        "rank_target_eligible",
        "prefrozen_target_universe_member",
        "multi_accession_group_flag",
        "source_local_rank_percentile",
        "source_batch_positive_count",
        "cross_source_scale_use",
    ]

    def __init__(self, root: Path, *, output_root: Path | None = None) -> None:
        self.root = root.resolve(strict=True)
        candidate = (output_root or self.root / self.OUTPUT_RELATIVE).resolve(strict=False)
        if not candidate.is_relative_to(self.root):
            raise R4T193ThreeLabExecutionError("T193 output must remain under repository root")
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
            raise R4T193ThreeLabExecutionError(f"cannot parse {label}") from exc

    def _root_file(self, relative_path: str, label: str) -> Path:
        if "\\" in relative_path:
            raise R4T193ThreeLabExecutionError(f"{label} must use POSIX separators")
        pure = PurePosixPath(relative_path)
        if pure.is_absolute() or not pure.parts or ".." in pure.parts:
            raise R4T193ThreeLabExecutionError(f"{label} escapes repository root")
        path = (self.root / Path(*pure.parts)).resolve(strict=False)
        if not path.is_relative_to(self.root) or not path.is_file():
            raise R4T193ThreeLabExecutionError(f"{label} is missing or outside repository root")
        return path

    def _reference(self, value: Any, label: str) -> Path:
        reference = _mapping(value, label)
        if set(reference) != self.REQUIRED_REFERENCE:
            raise R4T193ThreeLabExecutionError(f"{label} reference fields are invalid")
        path = self._root_file(_string(reference["relative_path"], label), label)
        if _sha256(path) != _checksum(reference["sha256"], label):
            raise R4T193ThreeLabExecutionError(f"{label} checksum differs")
        return path

    def _registry(
        self,
    ) -> tuple[dict[str, Any], dict[str, Any], dict[str, Path], list[dict[str, Any]]]:
        registry = self._json(self.root / self.REGISTRY_RELATIVE, "T193 registry")
        expected = {
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
        if set(registry) != expected or registry.get("schema_version") != 1:
            raise R4T193ThreeLabExecutionError("T193 registry fields are invalid")
        if (
            registry["audit_id"] != self.AUDIT_ID
            or registry["protocol_id"] != self.AUDIT_ID
            or registry["status"] != "T193_PREFROZEN_TARGET_EXECUTION_REGISTERED"
            or registry["evidence_class"] != "DEVELOPMENT_OBSERVATION"
            or registry["allowed_claim_level"] != "EXPLORATORY"
            or registry["scientific_submission_ready"] is not False
        ):
            raise R4T193ThreeLabExecutionError("T193 registry identity or boundary is invalid")
        protocol_path = self._reference(registry["protocol"], "T193 protocol")
        protocol = self._json(protocol_path, "T193 protocol")
        if (
            protocol.get("protocol_id") != self.AUDIT_ID
            or protocol.get("status") != "FROZEN_BEFORE_T193_EXECUTION"
            or protocol.get("scientific_submission_ready") is not False
        ):
            raise R4T193ThreeLabExecutionError("T193 protocol identity or boundary is invalid")
        refs = {
            "t192_source_registry": self._reference(registry["t192_source_registry"], "T192 source registry"),
            "r3_common_target_ledger": self._reference(registry["r3_common_target_ledger"], "R3 common target ledger"),
            "r3_sequence_feature_table": self._reference(registry["r3_sequence_feature_table"], "R3 feature table"),
        }
        if refs["t192_source_registry"] != self.root / self.T192_REGISTRY_RELATIVE:
            raise R4T193ThreeLabExecutionError("T193 does not use the release-fixed T192 source registry")
        if refs["r3_common_target_ledger"] != self.root / self.R3_LEDGER_RELATIVE:
            raise R4T193ThreeLabExecutionError("T193 does not use the release-fixed R3 target ledger")
        if refs["r3_sequence_feature_table"] != self.root / self.FEATURE_RELATIVE:
            raise R4T193ThreeLabExecutionError("T193 does not use the release-fixed feature table")
        sources = registry["sources"]
        if not isinstance(sources, list) or len(sources) != 3:
            raise R4T193ThreeLabExecutionError("T193 requires exactly three sources")
        return registry, protocol, refs, [_mapping(source, "T193 source") for source in sources]

    @staticmethod
    def _read_csv(path: Path, label: str) -> list[dict[str, str]]:
        try:
            with path.open("r", encoding="utf-8", newline="") as stream:
                rows = list(csv.DictReader(stream))
        except OSError as exc:
            raise R4T193ThreeLabExecutionError(f"cannot read {label}") from exc
        if not rows or not rows[0]:
            raise R4T193ThreeLabExecutionError(f"{label} is empty")
        return rows

    def _features_and_targets(
        self, refs: Mapping[str, Path], protocol: Mapping[str, Any]
    ) -> tuple[dict[str, tuple[float, ...]], set[str]]:
        feature_rows = self._read_csv(refs["r3_sequence_feature_table"], "R3 feature table")
        expected_columns = {"canonical_accession", *R3ModelEvaluationWorkflow.FEATURE_NAMES}
        if set(feature_rows[0]) != expected_columns:
            raise R4T193ThreeLabExecutionError("R3 feature table schema differs")
        features: dict[str, tuple[float, ...]] = {}
        for row in feature_rows:
            accession = _string(row.get("canonical_accession"), "feature accession")
            if accession in features:
                raise R4T193ThreeLabExecutionError("R3 feature table repeats an accession")
            try:
                values = tuple(float(row[name]) for name in R3ModelEvaluationWorkflow.FEATURE_NAMES)
            except (TypeError, ValueError) as exc:
                raise R4T193ThreeLabExecutionError("R3 feature value is invalid") from exc
            if not all(math.isfinite(value) for value in values):
                raise R4T193ThreeLabExecutionError("R3 feature value is not finite")
            features[accession] = values
        target_rows = self._read_csv(refs["r3_common_target_ledger"], "R3 common target ledger")
        targets = {
            _string(row["canonical_accession"], "R3 target accession")
            for row in target_rows
            if row.get("common_rank_target_member") == "true"
        }
        expected_count = int(
            _mapping(protocol["prefrozen_target_universe"], "T193 target universe")["expected_target_count"]
        )
        if len(targets) != expected_count or set(features) != targets:
            raise R4T193ThreeLabExecutionError("pre-frozen R3 target universe does not close the feature table")
        return features, targets

    def _source_observations(
        self,
        t192: R4T192ThreeLabCommonTargetWorkflow,
        sources: Sequence[Mapping[str, Any]],
        features: Mapping[str, tuple[float, ...]],
        target_universe: set[str],
        registry: Mapping[str, Any],
    ) -> tuple[list[_Observation], list[dict[str, Any]], dict[str, dict[str, Any]]]:
        by_source = {str(item["source_id"]): item for item in registry["sources"]}
        observations: list[_Observation] = []
        ledger: list[dict[str, Any]] = []
        accounting: dict[str, dict[str, Any]] = {}
        for source in sources:
            source_id = _string(source["source_id"], "T193 source ID")
            source_meta = by_source.get(source_id)
            if source_meta is None:
                raise R4T193ThreeLabExecutionError(f"T193 source {source_id} is not registered")
            _, eligible = t192._validate_source_metadata(source)
            ranks = t192._rank_rows(eligible)
            selected: list[tuple[dict[str, str], float, int]] = []
            for index, row in enumerate(eligible):
                accession = row["canonical_accession"]
                if accession not in target_universe:
                    continue
                if accession not in features:
                    raise R4T193ThreeLabExecutionError(f"T193 target {accession} has no feature row")
                percentile, positive_count = ranks[index]
                selected.append((row, percentile, positive_count))
            expected_count = int(source_meta["expected_observation_count"])
            expected_targets = int(source_meta["expected_target_count"])
            expected_batches = int(source_meta["expected_batch_count"])
            if len(selected) != expected_count:
                raise R4T193ThreeLabExecutionError(f"{source_id} observation count differs")
            target_count = len({row["canonical_accession"] for row, _, _ in selected})
            batch_count = len({row["measurement_batch_id"] for row, _, _ in selected})
            if target_count != expected_targets or batch_count != expected_batches:
                raise R4T193ThreeLabExecutionError(f"{source_id} source accounting differs")
            accounting[source_id] = {
                "laboratory_anchor": source["laboratory_anchor"],
                "license": source["license"],
                "observation_count": len(selected),
                "target_count": target_count,
                "measurement_batch_count": batch_count,
                "multi_accession_group_row_count": sum(
                    ";" in row.get("source_identifier", "") for row, _, _ in selected
                ),
                "biological_unit_semantics": source["biological_unit_semantics"],
            }
            for row, percentile, positive_count in selected:
                identity = "|".join((source_id, row["source_coordinate"], row["canonical_accession"]))
                observation_id = "T193_" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:20]
                observations.append(
                    _Observation(
                        target_observation_id=observation_id,
                        source_id=source_id,
                        canonical_accession=row["canonical_accession"],
                        laboratory_anchor=row["laboratory_anchor"],
                        measurement_batch_id=row["measurement_batch_id"],
                        target=percentile,
                        feature_values=features[row["canonical_accession"]],
                    )
                )
                ledger.append(
                    {
                        "target_observation_id": observation_id,
                        "source_id": source_id,
                        "laboratory_anchor": row["laboratory_anchor"],
                        "source_license": source["license"],
                        "canonical_accession": row["canonical_accession"],
                        "measurement_batch_id": row["measurement_batch_id"],
                        "biological_unit_id": row.get("biological_unit_id", ""),
                        "source_asset_id": row["source_asset_id"],
                        "source_worksheet": row.get("source_worksheet", ""),
                        "source_row": row["source_row"],
                        "source_coordinate": row["source_coordinate"],
                        "source_identifier": row["source_identifier"],
                        "source_sample": row.get("source_sample", ""),
                        "condition_label": row.get("condition_label", ""),
                        "technical_replicate_id": row.get("technical_replicate_id", ""),
                        "author_quantity_type": row.get("author_quantity_type", ""),
                        "author_numeric_value": row["author_numeric_value"],
                        "author_value_state": row.get("author_value_state", ""),
                        "rank_target_eligible": "true",
                        "prefrozen_target_universe_member": "true",
                        "multi_accession_group_flag": "true" if ";" in row.get("source_identifier", "") else "false",
                        "source_local_rank_percentile": format(percentile, ".17g"),
                        "source_batch_positive_count": positive_count,
                        "cross_source_scale_use": "PROHIBITED",
                    }
                )
        if len(observations) != int(_mapping(registry["expected_accounting"], "T193 accounting")["observation_count"]):
            raise R4T193ThreeLabExecutionError("T193 total observation count differs")
        return (
            sorted(observations, key=lambda row: row.target_observation_id),
            sorted(ledger, key=lambda row: row["target_observation_id"]),
            accounting,
        )

    @staticmethod
    def _helper(root: Path) -> R3ModelEvaluationWorkflow:
        return R3ModelEvaluationWorkflow(
            root,
            root / "data/raw",
            root / "data/raw/r3_uniprot_sequence_features",
            output_root=root / "reports/review_round_4/t193_helper_unused",
        )

    def _execute_models(
        self, observations: Sequence[_Observation], protocol: Mapping[str, Any]
    ) -> tuple[dict[str, Any], dict[str, list[dict[str, Any]]]]:
        helper = self._helper(self.root)
        outer = sorted({row.laboratory_anchor for row in observations})
        if len(outer) != 3:
            raise R4T193ThreeLabExecutionError("T193 does not have three unique laboratory anchors")
        nested = _mapping(protocol["nested_selection"], "T193 nested selection")
        minimum_proteins = int(nested["minimum_proteins_per_selection_batch"])
        uncertainty = _mapping(protocol["uncertainty"], "T193 uncertainty")
        bootstrap_resamples = int(uncertainty["resamples"])
        bootstrap_seed = int(uncertainty["random_seed"])
        negative = _mapping(protocol["negative_control"], "T193 negative control")
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
        parameters: dict[str, Any] = {}
        for fold_index, held_out_lab in enumerate(outer, start=1):
            fold_id = f"T193_OUTER_{fold_index:02d}"
            development = [row for row in observations if row.laboratory_anchor != held_out_lab]
            testing = sorted(
                [row for row in observations if row.laboratory_anchor == held_out_lab],
                key=lambda row: (row.measurement_batch_id, row.target_observation_id),
            )
            full_alpha, full_selection = helper._select_alpha(
                development, full_indices, minimum_proteins=minimum_proteins
            )
            composition_alpha, composition_selection = helper._select_alpha(
                development, composition_indices, minimum_proteins=minimum_proteins
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
                "CONSTANT_TRAINING_MEAN": {"development_target_mean": constant_mean},
                "SEQUENCE_RIDGE_FULL": helper._ridge_parameters(full_model, helper.FEATURE_NAMES),
                "SEQUENCE_RIDGE_COMPOSITION_ONLY": helper._ridge_parameters(
                    composition_model, helper.COMPOSITION_FEATURE_NAMES
                ),
            }
            metric_by_model: dict[str, list[dict[str, Any]]] = {}
            for model_index, model_id in enumerate(self.MODEL_IDS, start=1):
                predicted = predictions_by_model[model_id]
                metrics = helper._batch_metrics(testing, predicted, minimum_proteins=minimum_proteins)
                metric_by_model[model_id] = metrics
                aggregate = helper._aggregate(metrics)
                status = "UNDEFINED_CONSTANT_PREDICTION" if model_id == "CONSTANT_TRAINING_MEAN" else "DEFINED"
                ci: dict[str, dict[str, Any] | None] = {}
                for metric_name, output_name, seed_offset in (
                    ("spearman", "mean_spearman", 0),
                    ("mae", "mean_mae", 10),
                    ("rmse", "mean_rmse", 20),
                ):
                    values = [item[metric_name] for item in metrics]
                    ci[output_name] = (
                        None
                        if any(value is None for value in values)
                        else helper._bootstrap(
                            [float(value) for value in values],
                            resamples=bootstrap_resamples,
                            seed=bootstrap_seed + fold_index * 100 + model_index * 10 + seed_offset,
                        )
                    )
                mean_mae_interval = ci["mean_mae"]
                mean_rmse_interval = ci["mean_rmse"]
                fold_metrics.append(
                    {
                        "outer_fold_id": fold_id,
                        "held_out_laboratory_anchor": held_out_lab,
                        "model_id": model_id,
                        "held_out_observation_count": len(testing),
                        "held_out_measurement_batch_count": len(metrics),
                        "primary_metric_status": status,
                        **aggregate,
                        "mean_spearman_lower_95": None
                        if ci["mean_spearman"] is None
                        else ci["mean_spearman"]["lower_95"],
                        "mean_spearman_upper_95": None
                        if ci["mean_spearman"] is None
                        else ci["mean_spearman"]["upper_95"],
                        "mean_mae_lower_95": None if mean_mae_interval is None else mean_mae_interval["lower_95"],
                        "mean_mae_upper_95": None if mean_mae_interval is None else mean_mae_interval["upper_95"],
                        "mean_rmse_lower_95": None if mean_rmse_interval is None else mean_rmse_interval["lower_95"],
                        "mean_rmse_upper_95": None if mean_rmse_interval is None else mean_rmse_interval["upper_95"],
                    }
                )
                for metric in metrics:
                    batch_metrics.append(
                        {
                            "outer_fold_id": fold_id,
                            "held_out_laboratory_anchor": held_out_lab,
                            "model_id": model_id,
                            **metric,
                            "spearman_status": status if metric["spearman"] is None else "DEFINED",
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
            full_metrics = metric_by_model["SEQUENCE_RIDGE_FULL"]
            composition_metrics = metric_by_model["SEQUENCE_RIDGE_COMPOSITION_ONLY"]
            differences = [
                float(full["spearman"]) - float(comp["spearman"])
                for full, comp in zip(full_metrics, composition_metrics, strict=True)
                if full["spearman"] is not None and comp["spearman"] is not None
            ]
            ablation: dict[str, Any] = {
                "outer_fold_id": fold_id,
                "held_out_laboratory_anchor": held_out_lab,
                "paired_measurement_batch_count": len(differences),
            }
            if differences:
                ablation.update(
                    {
                        "full_minus_composition_mean_spearman": float(np.mean(differences)),
                        **helper._bootstrap(
                            differences,
                            resamples=bootstrap_resamples,
                            seed=bootstrap_seed + fold_index * 1000 + 701,
                        ),
                    }
                )
            else:
                ablation.update(
                    {
                        "full_minus_composition_mean_spearman": None,
                        "resamples": bootstrap_resamples,
                        "seed": bootstrap_seed + fold_index * 1000 + 701,
                        "lower_95": None,
                        "upper_95": None,
                    }
                )
            ablations.append(ablation)
            observed = next(
                row
                for row in fold_metrics
                if row["outer_fold_id"] == fold_id and row["model_id"] == "SEQUENCE_RIDGE_FULL"
            )["mean_spearman"]
            if observed is None:
                raise R4T193ThreeLabExecutionError("T193 full model primary metric is undefined")
            development_targets = np.asarray([row.target for row in development], dtype=float)
            by_batch: dict[str, list[int]] = defaultdict(list)
            for position, row in enumerate(development):
                by_batch[row.measurement_batch_id].append(position)
            rng = np.random.default_rng(negative_seed + fold_index)
            null_values: list[float] = []
            for resample in range(1, negative_resamples + 1):
                permuted = development_targets.copy()
                for positions in by_batch.values():
                    permuted[positions] = rng.permutation(permuted[positions])
                null_model = helper._fit_ridge(development, full_indices, full_alpha, targets=permuted)
                null_metrics = helper._batch_metrics(
                    testing,
                    helper._predict_ridge(null_model, testing),
                    minimum_proteins=minimum_proteins,
                )
                null_score = helper._aggregate(null_metrics)["mean_spearman"]
                if null_score is None:
                    raise R4T193ThreeLabExecutionError("T193 negative-control primary metric is undefined")
                null_values.append(float(null_score))
                negative_rows.append(
                    {
                        "outer_fold_id": fold_id,
                        "held_out_laboratory_anchor": held_out_lab,
                        "selected_alpha": full_alpha,
                        "resample": resample,
                        "null_mean_spearman": float(null_score),
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
            }
        return {
            "predictions": predictions,
            "batch_metrics": batch_metrics,
            "fold_metrics": fold_metrics,
            "selections": selections,
            "ablations": ablations,
            "negative_rows": negative_rows,
            "parameters": parameters,
        }, {
            "outer_labs": [
                {"held_out_laboratory_anchor": lab, "fold_id": f"T193_OUTER_{index:02d}"}
                for index, lab in enumerate(outer, start=1)
            ]
        }

    def run(self, *, strict: bool = False) -> R4T193ThreeLabExecutionSummary:
        if not strict:
            raise R4T193ThreeLabExecutionError("T193 execution requires --strict")
        if self.output_root.exists():
            raise R4T193ThreeLabExecutionError("T193 execution already exists")
        registry, protocol, refs, sources = self._registry()
        features, targets = self._features_and_targets(refs, protocol)
        t192 = R4T192ThreeLabCommonTargetWorkflow(self.root, registry_path=refs["t192_source_registry"])
        try:
            _, _, t192_sources = t192._documents()
            observations, ledger, accounting = self._source_observations(
                t192, t192_sources, features, targets, registry
            )
        except (R4T192ThreeLabCommonTargetError, R4T193ThreeLabExecutionError) as exc:
            if isinstance(exc, R4T193ThreeLabExecutionError):
                raise
            raise R4T193ThreeLabExecutionError("T192 source closure failed during T193 admission") from exc
        artifacts, fold_contract = self._execute_models(observations, protocol)
        self.output_root.mkdir(parents=True, exist_ok=False)
        paths = {
            "ledger": self.output_root / "source_local_prefrozen_target_ledger.csv",
            "predictions": self.output_root / "outer_fold_predictions.csv",
            "batch_metrics": self.output_root / "measurement_batch_metrics.csv",
            "fold_metrics": self.output_root / "outer_fold_metrics.csv",
            "inner_selection": self.output_root / "nested_inner_selection.csv",
            "paired_ablation": self.output_root / "paired_composition_ablation.csv",
            "negative_control": self.output_root / "within_batch_rank_permutation.csv",
            "parameters": self.output_root / "outer_fold_model_parameters.json",
        }
        self._write_csv(paths["ledger"], self.LEDGER_FIELDS, ledger)
        self._write_csv(
            paths["predictions"],
            [
                "outer_fold_id",
                "held_out_laboratory_anchor",
                "model_id",
                "target_observation_id",
                "source_id",
                "canonical_accession",
                "measurement_batch_id",
                "observed_rank_percentile_descending",
                "predicted_rank_percentile_descending",
            ],
            artifacts["predictions"],
        )
        self._write_csv(
            paths["batch_metrics"],
            [
                "outer_fold_id",
                "held_out_laboratory_anchor",
                "model_id",
                "measurement_batch_id",
                "protein_count",
                "spearman",
                "spearman_status",
                "mae",
                "rmse",
            ],
            artifacts["batch_metrics"],
        )
        self._write_csv(
            paths["fold_metrics"],
            [
                "outer_fold_id",
                "held_out_laboratory_anchor",
                "model_id",
                "held_out_observation_count",
                "held_out_measurement_batch_count",
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
            artifacts["fold_metrics"],
        )
        self._write_csv(
            paths["inner_selection"],
            [
                "outer_fold_id",
                "held_out_laboratory_anchor",
                "model_id",
                "alpha",
                "held_out_inner_batch_id",
                "spearman",
                "selected_alpha",
            ],
            artifacts["selections"],
        )
        self._write_csv(
            paths["paired_ablation"],
            [
                "outer_fold_id",
                "held_out_laboratory_anchor",
                "paired_measurement_batch_count",
                "full_minus_composition_mean_spearman",
                "resamples",
                "seed",
                "lower_95",
                "upper_95",
            ],
            artifacts["ablations"],
        )
        self._write_csv(
            paths["negative_control"],
            [
                "outer_fold_id",
                "held_out_laboratory_anchor",
                "selected_alpha",
                "resample",
                "null_mean_spearman",
            ],
            artifacts["negative_rows"],
        )
        self._write_json(paths["parameters"], artifacts["parameters"])
        artifact_manifest = {
            name: {"relative_path": path.relative_to(self.root).as_posix(), "sha256": _sha256(path)}
            for name, path in paths.items()
        }
        report = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "status": self.STATUS,
            "evidence_class": registry["evidence_class"],
            "allowed_claim_level": registry["allowed_claim_level"],
            "input_references": {
                name: {
                    "relative_path": path.relative_to(self.root).as_posix(),
                    "sha256": _sha256(path),
                }
                for name, path in refs.items()
            },
            "target_universe": {
                "source": "R3_common_rank_target_ledger",
                "count": len(targets),
                "selection_after_outer_split": False,
            },
            "source_accounting": accounting,
            "fold_contract": fold_contract,
            "frozen_cohort": {
                "observation_count": len(observations),
                "target_universe_count": len(targets),
                "laboratory_anchor_count": len({row.laboratory_anchor for row in observations}),
                "measurement_batch_count": len({row.measurement_batch_id for row in observations}),
                "outer_fold_count": 3,
                "model_count": len(self.MODEL_IDS),
            },
            "model_results": artifacts["fold_metrics"],
            "paired_composition_ablation": artifacts["ablations"],
            "negative_control_summary": [
                {
                    "outer_fold_id": fold_id,
                    "held_out_laboratory_anchor": values["held_out_laboratory_anchor"],
                    **values["SEQUENCE_RIDGE_FULL"]["negative_control"],
                }
                for fold_id, values in artifacts["parameters"].items()
            ],
            "artifacts": artifact_manifest,
            "claim_boundary": protocol["claim_boundary"],
            "independent_validation": False,
            "external_scientific_reproduction": False,
            "external_user_adoption": False,
            "scientific_submission_ready": False,
        }
        report_path = self.output_root / "t193_three_lab_execution_report.json"
        self._write_json(report_path, report)
        receipt = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "status": self.STATUS,
            "report_sha256": _sha256(report_path),
            "observation_count": len(observations),
            "target_universe_count": len(targets),
            "laboratory_anchor_count": 3,
            "measurement_batch_count": len({row.measurement_batch_id for row in observations}),
            "outer_fold_count": 3,
            "model_count": len(self.MODEL_IDS),
            "outcome_analysis_run": True,
            "model_fitted": True,
            "independent_validation": False,
            "external_scientific_reproduction": False,
            "scientific_submission_ready": False,
        }
        receipt_path = self.output_root / "t193_three_lab_execution_receipt.json"
        self._write_json(receipt_path, receipt)
        return R4T193ThreeLabExecutionSummary(
            len(observations),
            len(targets),
            3,
            len({row.measurement_batch_id for row in observations}),
            len(self.MODEL_IDS),
            receipt_path,
        )

    def verify(self, *, strict: bool = True) -> R4T193ThreeLabExecutionSummary:
        if not strict:
            raise R4T193ThreeLabExecutionError("T193 verification requires --strict")
        report_path = self.output_root / "t193_three_lab_execution_report.json"
        receipt_path = self.output_root / "t193_three_lab_execution_receipt.json"
        report = self._json(report_path, "T193 report")
        receipt = self._json(receipt_path, "T193 receipt")
        artifacts = _mapping(report.get("artifacts"), "T193 artifacts")
        if not artifacts:
            raise R4T193ThreeLabExecutionError("T193 artifacts are missing")
        for item in artifacts.values():
            reference = _mapping(item, "T193 artifact")
            if set(reference) != self.REQUIRED_REFERENCE:
                raise R4T193ThreeLabExecutionError("T193 artifact reference fields are invalid")
            path = self._root_file(_string(reference["relative_path"], "T193 artifact path"), "T193 artifact")
            if _sha256(path) != _checksum(reference["sha256"], "T193 artifact checksum"):
                raise R4T193ThreeLabExecutionError("T193 artifact checksum differs")
        if (
            report.get("audit_id") != self.AUDIT_ID
            or report.get("status") != self.STATUS
            or receipt.get("audit_id") != self.AUDIT_ID
            or receipt.get("status") != self.STATUS
            or receipt.get("report_sha256") != _sha256(report_path)
            or receipt.get("outcome_analysis_run") is not True
            or receipt.get("model_fitted") is not True
            or receipt.get("independent_validation") is not False
            or receipt.get("external_scientific_reproduction") is not False
            or receipt.get("scientific_submission_ready") is not False
        ):
            raise R4T193ThreeLabExecutionError("T193 report or receipt is invalid")
        return R4T193ThreeLabExecutionSummary(
            int(receipt["observation_count"]),
            int(receipt["target_universe_count"]),
            int(receipt["laboratory_anchor_count"]),
            int(receipt["measurement_batch_count"]),
            int(receipt["model_count"]),
            receipt_path,
        )
