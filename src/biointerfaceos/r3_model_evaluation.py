"""Execute the frozen R3 cross-laboratory sequence-only benchmark."""

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

from biointerfaceos.r3_analysis_protocol import R3AnalysisProtocolWorkflow
from biointerfaceos.r3_uniprot_mapping import _canonical, _checksum, _mapping, _sha256, _string
from biointerfaceos.r3_uniprot_sequence_features import AA_ORDER


class R3ModelEvaluationError(RuntimeError):
    """Raised when frozen R3 execution inputs or results are invalid."""


@dataclass(frozen=True)
class _Observation:
    target_observation_id: str
    source_id: str
    canonical_accession: str
    laboratory_anchor: str
    measurement_batch_id: str
    target: float
    feature_values: tuple[float, ...]


@dataclass(frozen=True)
class R3ModelEvaluationSummary:
    """Compact accounting for one immutable R3 model-evaluation release."""

    eligible_observation_count: int
    canonical_protein_count: int
    laboratory_anchor_count: int
    measurement_batch_count: int
    model_count: int
    receipt_path: Path


class R3ModelEvaluationWorkflow:
    """Run exactly the models and partitions fixed by the R3 protocol."""

    AUDIT_ID = "bioif-r3-common-rank-model-evaluation-v1.0.0"
    REGISTRY_RELATIVE = "docs/data/R3_T152_MODEL_EVALUATION_REGISTRY.json"
    PROTOCOL_OUTPUT_RELATIVE = "reports/review_round_3/analysis_protocol/v1.0.0"
    OUTPUT_RELATIVE = "reports/review_round_3/common_rank_model_evaluation/v1.0.0"
    STATUS = "R3_COMMON_RANK_MODELS_EXECUTED_EXPLORATORY"
    FEATURE_NAMES = [
        "sequence_length",
        "estimated_molecular_mass_da",
        "hydrophobic_fraction",
        "aromatic_fraction",
        "acidic_fraction",
        "basic_fraction",
        "cysteine_fraction",
        "proline_fraction",
        "mean_kyte_doolittle",
        *[f"aa_fraction_{residue}" for residue in AA_ORDER],
    ]
    COMPOSITION_FEATURE_NAMES = [f"aa_fraction_{residue}" for residue in AA_ORDER]
    ALPHA_GRID = (0.01, 0.1, 1.0, 10.0, 100.0)
    MODEL_IDS = (
        "CONSTANT_TRAINING_MEAN",
        "SEQUENCE_RIDGE_FULL",
        "SEQUENCE_RIDGE_COMPOSITION_ONLY",
    )
    REQUIRED_REGISTRY = {
        "schema_version",
        "audit_id",
        "executed_at",
        "evidence_class",
        "allowed_claim_level",
        "analysis_protocol_receipt",
        "frozen_analysis_protocol",
        "frozen_outer_split_manifest",
        "common_target_ledger",
        "sequence_feature_table",
        "execution_contract",
        "claim_boundary",
    }
    REQUIRED_REFERENCE = {"relative_path", "sha256"}
    REQUIRED_CONTRACT = {
        "full_model_feature_set",
        "ablation_feature_set",
        "ridge_intercept",
        "ridge_solver",
        "zero_variance_feature_policy",
        "constant_rank_metric_policy",
        "negative_control_hyperparameter_policy",
        "negative_control_tail",
        "significance_policy",
    }

    def __init__(
        self,
        root: Path,
        output_data_root: Path,
        feature_root: Path,
        *,
        registry_path: Path | None = None,
        output_root: Path | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.output_data_root = output_data_root.resolve(strict=False)
        self.feature_root = feature_root.resolve(strict=False)
        self.registry_path = registry_path or self.root / self.REGISTRY_RELATIVE
        self.output_root = output_root or self.root / self.OUTPUT_RELATIVE

    @staticmethod
    def _write_json(path: Path, value: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(_canonical(value))

    @staticmethod
    def _json(path: Path, label: str) -> dict[str, Any]:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise R3ModelEvaluationError(f"cannot parse {label}") from exc
        try:
            return _mapping(value, label)
        except Exception as exc:
            raise R3ModelEvaluationError(f"cannot parse {label}") from exc

    def _root_file(self, relative_path: str, label: str) -> Path:
        if "\\" in relative_path:
            raise R3ModelEvaluationError(f"{label} must use a POSIX relative path")
        pure = PurePosixPath(relative_path)
        if pure.is_absolute() or not pure.parts or ".." in pure.parts:
            raise R3ModelEvaluationError(f"{label} escapes repository root")
        path = (self.root / Path(*pure.parts)).resolve(strict=False)
        if not path.is_relative_to(self.root) or not path.is_file():
            raise R3ModelEvaluationError(f"{label} is missing or outside repository root")
        return path

    def _reference(self, value: Any, label: str) -> Path:
        reference = _mapping(value, label)
        if set(reference) != self.REQUIRED_REFERENCE:
            raise R3ModelEvaluationError(f"{label} fields are invalid")
        path = self._root_file(_string(reference.get("relative_path"), label), label)
        try:
            expected_hash = _checksum(reference.get("sha256"), label)
        except Exception as exc:
            raise R3ModelEvaluationError(f"{label} checksum is invalid") from exc
        if _sha256(path) != expected_hash:
            raise R3ModelEvaluationError(f"{label} checksum differs")
        return path

    def _registry(self) -> tuple[dict[str, Any], dict[str, Path]]:
        registry = self._json(self.registry_path, "R3 model-evaluation registry")
        if set(registry) != self.REQUIRED_REGISTRY or registry.get("schema_version") != 1:
            raise R3ModelEvaluationError("R3 model-evaluation registry fields are invalid")
        if (
            registry.get("audit_id") != self.AUDIT_ID
            or registry.get("evidence_class") != "DEVELOPMENT_OBSERVATION"
            or registry.get("allowed_claim_level") != "EXPLORATORY"
        ):
            raise R3ModelEvaluationError("R3 model-evaluation registry boundary is invalid")
        _string(registry.get("executed_at"), "R3 model-evaluation executed_at")
        _string(registry.get("claim_boundary"), "R3 model-evaluation claim boundary")
        contract = _mapping(registry.get("execution_contract"), "R3 execution contract")
        if set(contract) != self.REQUIRED_CONTRACT or contract != {
            "full_model_feature_set": "R3_UNIPROT_SEQUENCE_COMPOSITION_PHYSICOCHEMICAL_V1",
            "ablation_feature_set": "AA_FRACTION_ONLY",
            "ridge_intercept": "unpenalized",
            "ridge_solver": "numpy.linalg.solve",
            "zero_variance_feature_policy": "set development-partition standard deviation to 1.0 after centering",
            "constant_rank_metric_policy": "undefined; report MAE and RMSE only",
            "negative_control_hyperparameter_policy": (
                "hold the observed nested-selected full-model alpha fixed for each outer fold; "
                "permute development targets independently within each development measurement batch; "
                "never use held-out targets in fitting or selection"
            ),
            "negative_control_tail": "one-sided upper tail; p=(1+count(null_primary>=observed_primary))/(1+resamples)",
            "significance_policy": (
                "no unpredeclared hypothesis test is manufactured; Holm adjustment is reported as "
                "not applicable when no predeclared p-values exist"
            ),
        }:
            raise R3ModelEvaluationError("R3 execution contract is invalid")
        references = {
            name: self._reference(registry.get(name), name.replace("_", " "))
            for name in (
                "analysis_protocol_receipt",
                "frozen_analysis_protocol",
                "frozen_outer_split_manifest",
                "common_target_ledger",
                "sequence_feature_table",
            )
        }
        if references["analysis_protocol_receipt"].parent != self.root / self.PROTOCOL_OUTPUT_RELATIVE:
            raise R3ModelEvaluationError("R3 protocol receipt does not use the frozen protocol output")
        expected_data_root = (self.root / "data/raw").resolve(strict=False)
        expected_feature_root = (self.root / "data/raw/r3_uniprot_sequence_features").resolve(
            strict=False
        )
        if self.output_data_root != expected_data_root or self.feature_root != expected_feature_root:
            raise R3ModelEvaluationError("R3 evaluation requires the registry-fixed data roots")
        return registry, references

    def _validate_protocol(self, references: Mapping[str, Path]) -> dict[str, Any]:
        protocol = R3AnalysisProtocolWorkflow(self.root, self.output_data_root)
        try:
            protocol.verify()
        except Exception as exc:
            raise R3ModelEvaluationError("R3 analysis protocol verification failed") from exc
        receipt = self._json(references["analysis_protocol_receipt"], "R3 protocol receipt")
        if (
            receipt.get("status") != "FROZEN_R3_COMMON_RANK_ANALYSIS_PROTOCOL"
            or receipt.get("target_status") != "FROZEN_R3_RANK_BENCHMARK"
            or receipt.get("outcome_analysis_run") is not False
            or receipt.get("model_fitted") is not False
            or receipt.get("independent_validation") is not False
            or receipt.get("scientific_submission_ready") is not False
        ):
            raise R3ModelEvaluationError("R3 protocol receipt execution boundary is invalid")
        frozen_plan = self._json(references["frozen_analysis_protocol"], "frozen R3 analysis protocol")
        if frozen_plan.get("plan_id") != R3AnalysisProtocolWorkflow.PLAN_ID:
            raise R3ModelEvaluationError("frozen R3 analysis protocol identity is invalid")
        return frozen_plan

    @staticmethod
    def _read_csv(path: Path, label: str) -> list[dict[str, str]]:
        try:
            with path.open("r", encoding="utf-8", newline="") as stream:
                rows = list(csv.DictReader(stream))
        except OSError as exc:
            raise R3ModelEvaluationError(f"cannot read {label}") from exc
        if not rows or not rows[0]:
            raise R3ModelEvaluationError(f"{label} is empty")
        return rows

    def _observations(
        self, ledger_path: Path, feature_path: Path
    ) -> tuple[list[_Observation], list[str]]:
        feature_rows = self._read_csv(feature_path, "R3 sequence feature table")
        expected_feature_columns = {"canonical_accession", *self.FEATURE_NAMES}
        if set(feature_rows[0]) != expected_feature_columns:
            raise R3ModelEvaluationError("R3 sequence feature table schema is invalid")
        features: dict[str, tuple[float, ...]] = {}
        for feature_row in feature_rows:
            accession = _string(feature_row.get("canonical_accession"), "feature accession")
            if accession in features:
                raise R3ModelEvaluationError("R3 sequence feature table repeats an accession")
            try:
                values = tuple(float(feature_row[name]) for name in self.FEATURE_NAMES)
            except (TypeError, ValueError) as exc:
                raise R3ModelEvaluationError("R3 sequence feature is not numeric") from exc
            if not all(math.isfinite(value) for value in values):
                raise R3ModelEvaluationError("R3 sequence feature is not finite")
            features[accession] = values

        ledger_rows = self._read_csv(ledger_path, "R3 common target ledger")
        required_ledger = {
            "target_observation_id",
            "source_id",
            "canonical_accession",
            "laboratory_anchor",
            "measurement_batch_id",
            "rank_percentile_descending",
            "rank_target_eligible",
            "common_rank_target_member",
        }
        if not required_ledger.issubset(ledger_rows[0]):
            raise R3ModelEvaluationError("R3 common target ledger schema is invalid")
        observations: list[_Observation] = []
        for row in ledger_rows:
            if (
                row.get("rank_target_eligible") != "true"
                or row.get("common_rank_target_member") != "true"
            ):
                continue
            accession = _string(row.get("canonical_accession"), "common target accession")
            if accession not in features:
                raise R3ModelEvaluationError("common target lacks a sequence feature row")
            try:
                target = float(row["rank_percentile_descending"])
            except (KeyError, TypeError, ValueError) as exc:
                raise R3ModelEvaluationError("R3 rank target is invalid") from exc
            if not math.isfinite(target) or not 0.0 <= target <= 1.0:
                raise R3ModelEvaluationError("R3 rank target is outside [0, 1]")
            observations.append(
                _Observation(
                    target_observation_id=_string(row.get("target_observation_id"), "target observation"),
                    source_id=_string(row.get("source_id"), "source ID"),
                    canonical_accession=accession,
                    laboratory_anchor=_string(row.get("laboratory_anchor"), "laboratory anchor"),
                    measurement_batch_id=_string(
                        row.get("measurement_batch_id"), "measurement batch ID"
                    ),
                    target=target,
                    feature_values=features[accession],
                )
            )
        if not observations:
            raise R3ModelEvaluationError("R3 common target has no eligible observations")
        identifiers = [row.target_observation_id for row in observations]
        if len(set(identifiers)) != len(identifiers):
            raise R3ModelEvaluationError("R3 common target repeats an eligible observation")
        accessions = {row.canonical_accession for row in observations}
        if set(features) != accessions:
            raise R3ModelEvaluationError("sequence feature table does not exactly close common target")
        return sorted(observations, key=lambda row: row.target_observation_id), sorted(accessions)

    def _validate_splits(
        self, split_path: Path, observations: Sequence[_Observation]
    ) -> list[tuple[str, str]]:
        rows = self._read_csv(split_path, "frozen R3 outer split manifest")
        required = {
            "outer_fold_id",
            "held_out_laboratory_anchor",
            "target_observation_id",
            "source_id",
            "laboratory_anchor",
            "measurement_batch_id",
            "split_role",
        }
        if set(rows[0]) != required:
            raise R3ModelEvaluationError("frozen R3 outer split manifest schema is invalid")
        observation_by_id = {row.target_observation_id: row for row in observations}
        by_fold: dict[str, list[dict[str, str]]] = defaultdict(list)
        for row in rows:
            by_fold[_string(row.get("outer_fold_id"), "outer fold ID")].append(row)
        expected_ids = set(observation_by_id)
        validated: list[tuple[str, str]] = []
        for fold_id in sorted(by_fold):
            fold_rows = by_fold[fold_id]
            held_out_values = {row.get("held_out_laboratory_anchor") for row in fold_rows}
            if len(held_out_values) != 1 or not isinstance(next(iter(held_out_values)), str):
                raise R3ModelEvaluationError("outer fold must specify one held-out laboratory")
            held_out_lab = _string(next(iter(held_out_values)), "held-out laboratory anchor")
            by_identifier = {row.get("target_observation_id"): row for row in fold_rows}
            if len(by_identifier) != len(fold_rows) or set(by_identifier) != expected_ids:
                raise R3ModelEvaluationError("outer fold does not close the frozen observations")
            for identifier, split_row in by_identifier.items():
                observation = observation_by_id[identifier]
                expected_role = "TEST" if observation.laboratory_anchor == held_out_lab else "DEVELOPMENT"
                if (
                    split_row.get("split_role") != expected_role
                    or split_row.get("laboratory_anchor") != observation.laboratory_anchor
                    or split_row.get("measurement_batch_id") != observation.measurement_batch_id
                    or split_row.get("source_id") != observation.source_id
                ):
                    raise R3ModelEvaluationError("outer split manifest does not match frozen observations")
            validated.append((fold_id, held_out_lab))
        expected_labs = {row.laboratory_anchor for row in observations}
        if {held_out_lab for _, held_out_lab in validated} != expected_labs or len(validated) != 3:
            raise R3ModelEvaluationError("R3 outer folds do not leave out each laboratory exactly once")
        return validated

    @staticmethod
    def _rank(values: np.ndarray) -> np.ndarray:
        order = np.argsort(values, kind="mergesort")
        ranks = np.empty(len(values), dtype=float)
        start = 0
        while start < len(values):
            end = start + 1
            while end < len(values) and values[order[end]] == values[order[start]]:
                end += 1
            ranks[order[start:end]] = (start + end - 1) / 2.0 + 1.0
            start = end
        return ranks

    @classmethod
    def _spearman(cls, observed: Sequence[float], predicted: Sequence[float]) -> float | None:
        observed_array = np.asarray(observed, dtype=float)
        predicted_array = np.asarray(predicted, dtype=float)
        if len(observed_array) < 2 or not np.all(np.isfinite(predicted_array)):
            return None
        observed_rank = cls._rank(observed_array)
        predicted_rank = cls._rank(predicted_array)
        observed_centered = observed_rank - observed_rank.mean()
        predicted_centered = predicted_rank - predicted_rank.mean()
        denominator = math.sqrt(
            float(np.dot(observed_centered, observed_centered))
            * float(np.dot(predicted_centered, predicted_centered))
        )
        if denominator == 0.0:
            return None
        return float(np.dot(observed_centered, predicted_centered) / denominator)

    @classmethod
    def _batch_metrics(
        cls,
        observations: Sequence[_Observation],
        predictions: Sequence[float],
        *,
        minimum_proteins: int,
    ) -> list[dict[str, Any]]:
        if len(observations) != len(predictions):
            raise R3ModelEvaluationError("prediction accounting differs from observations")
        grouped: dict[str, list[tuple[float, float]]] = defaultdict(list)
        for observation, prediction in zip(observations, predictions, strict=True):
            grouped[observation.measurement_batch_id].append((observation.target, float(prediction)))
        result: list[dict[str, Any]] = []
        for batch_id in sorted(grouped):
            pairs = grouped[batch_id]
            if len(pairs) < minimum_proteins:
                raise R3ModelEvaluationError("held-out measurement batch has fewer than 10 proteins")
            observed = np.asarray([item[0] for item in pairs], dtype=float)
            predicted = np.asarray([item[1] for item in pairs], dtype=float)
            result.append(
                {
                    "measurement_batch_id": batch_id,
                    "protein_count": len(pairs),
                    "spearman": cls._spearman(observed, predicted),
                    "mae": float(np.mean(np.abs(observed - predicted))),
                    "rmse": float(np.sqrt(np.mean(np.square(observed - predicted)))),
                }
            )
        return result

    @staticmethod
    def _aggregate(metrics: Sequence[Mapping[str, Any]]) -> dict[str, float | None]:
        if not metrics:
            raise R3ModelEvaluationError("no measurement-batch metrics to aggregate")
        primary = [item["spearman"] for item in metrics]
        if any(value is None for value in primary):
            mean_spearman: float | None = None
        else:
            mean_spearman = float(np.mean(np.asarray(primary, dtype=float)))
        return {
            "mean_spearman": mean_spearman,
            "mean_mae": float(np.mean([float(item["mae"]) for item in metrics])),
            "mean_rmse": float(np.mean([float(item["rmse"]) for item in metrics])),
        }

    @staticmethod
    def _fit_ridge(
        observations: Sequence[_Observation],
        feature_indices: Sequence[int],
        alpha: float,
        *,
        targets: np.ndarray | None = None,
    ) -> dict[str, Any]:
        if not observations or alpha <= 0.0:
            raise R3ModelEvaluationError("ridge model fit inputs are invalid")
        matrix = np.asarray(
            [[row.feature_values[index] for index in feature_indices] for row in observations],
            dtype=float,
        )
        outcome = (
            np.asarray([row.target for row in observations], dtype=float)
            if targets is None
            else np.asarray(targets, dtype=float)
        )
        if len(outcome) != len(matrix) or not np.all(np.isfinite(outcome)):
            raise R3ModelEvaluationError("ridge model targets are invalid")
        means = matrix.mean(axis=0)
        standard_deviations = matrix.std(axis=0)
        standard_deviations[standard_deviations == 0.0] = 1.0
        standardized = (matrix - means) / standard_deviations
        design = np.column_stack((np.ones(len(standardized), dtype=float), standardized))
        penalty = np.diag(np.concatenate(([0.0], np.full(len(feature_indices), alpha))))
        try:
            coefficients = np.linalg.solve(design.T @ design + penalty, design.T @ outcome)
        except np.linalg.LinAlgError as exc:
            raise R3ModelEvaluationError("ridge linear system is singular") from exc
        return {
            "alpha": alpha,
            "feature_indices": tuple(feature_indices),
            "means": means,
            "standard_deviations": standard_deviations,
            "coefficients": coefficients,
        }

    @staticmethod
    def _predict_ridge(model: Mapping[str, Any], observations: Sequence[_Observation]) -> np.ndarray:
        feature_indices = model["feature_indices"]
        matrix = np.asarray(
            [[row.feature_values[index] for index in feature_indices] for row in observations],
            dtype=float,
        )
        standardized = (matrix - model["means"]) / model["standard_deviations"]
        design = np.column_stack((np.ones(len(standardized), dtype=float), standardized))
        prediction = design @ model["coefficients"]
        if not np.all(np.isfinite(prediction)):
            raise R3ModelEvaluationError("ridge prediction is not finite")
        return prediction

    def _select_alpha(
        self,
        development: Sequence[_Observation],
        feature_indices: Sequence[int],
        *,
        minimum_proteins: int,
    ) -> tuple[float, list[dict[str, Any]]]:
        by_batch: dict[str, list[_Observation]] = defaultdict(list)
        for observation in development:
            by_batch[observation.measurement_batch_id].append(observation)
        if len(by_batch) < 2:
            raise R3ModelEvaluationError("nested selection requires at least two development batches")
        selection_rows: list[dict[str, Any]] = []
        for alpha in self.ALPHA_GRID:
            batch_scores: list[float] = []
            for held_out_batch in sorted(by_batch):
                training = [
                    row for batch_id, rows in by_batch.items() if batch_id != held_out_batch for row in rows
                ]
                validation = by_batch[held_out_batch]
                model = self._fit_ridge(training, feature_indices, alpha)
                metric = self._batch_metrics(
                    validation,
                    self._predict_ridge(model, validation),
                    minimum_proteins=minimum_proteins,
                )[0]
                if metric["spearman"] is None:
                    raise R3ModelEvaluationError("nested ridge validation has undefined Spearman correlation")
                batch_scores.append(float(metric["spearman"]))
                selection_rows.append(
                    {
                        "alpha": alpha,
                        "held_out_inner_batch_id": held_out_batch,
                        "spearman": float(metric["spearman"]),
                    }
                )
            selection_rows.append(
                {
                    "alpha": alpha,
                    "held_out_inner_batch_id": "__MEAN__",
                    "spearman": float(np.mean(batch_scores)),
                }
            )
        means = {
            float(row["alpha"]): float(row["spearman"])
            for row in selection_rows
            if row["held_out_inner_batch_id"] == "__MEAN__"
        }
        selected = self.ALPHA_GRID[0]
        for alpha in self.ALPHA_GRID[1:]:
            if means[alpha] > means[selected]:
                selected = alpha
        return selected, selection_rows

    @staticmethod
    def _bootstrap(
        values: Sequence[float], *, resamples: int, seed: int
    ) -> dict[str, float | int]:
        array = np.asarray(values, dtype=float)
        if not len(array) or not np.all(np.isfinite(array)):
            raise R3ModelEvaluationError("cluster bootstrap values are invalid")
        rng = np.random.default_rng(seed)
        draw_indices = rng.integers(0, len(array), size=(resamples, len(array)))
        means = array[draw_indices].mean(axis=1)
        interval = np.quantile(means, [0.025, 0.975], method="linear")
        return {
            "resamples": resamples,
            "seed": seed,
            "lower_95": float(interval[0]),
            "upper_95": float(interval[1]),
        }

    @staticmethod
    def _format(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, float):
            return format(value, ".17g")
        return str(value)

    @classmethod
    def _write_csv(cls, path: Path, fieldnames: Sequence[str], rows: Sequence[Mapping[str, Any]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator="\n")
            writer.writeheader()
            for row in rows:
                writer.writerow({field: cls._format(row.get(field)) for field in fieldnames})

    @staticmethod
    def _ridge_parameters(model: Mapping[str, Any], feature_names: Sequence[str]) -> dict[str, Any]:
        coefficients = np.asarray(model["coefficients"], dtype=float)
        means = np.asarray(model["means"], dtype=float)
        deviations = np.asarray(model["standard_deviations"], dtype=float)
        return {
            "alpha": float(model["alpha"]),
            "intercept_standardized_scale": float(coefficients[0]),
            "feature_parameters": [
                {
                    "feature_name": name,
                    "development_mean": float(mean),
                    "development_standard_deviation": float(deviation),
                    "standardized_coefficient": float(coefficient),
                }
                for name, mean, deviation, coefficient in zip(
                    feature_names, means, deviations, coefficients[1:], strict=True
                )
            ],
        }

    def run(self, *, strict: bool = False) -> R3ModelEvaluationSummary:
        if not strict:
            raise R3ModelEvaluationError("R3 model evaluation requires --strict")
        if self.output_root.exists():
            raise R3ModelEvaluationError("R3 model evaluation already executed")
        registry, references = self._registry()
        plan = self._validate_protocol(references)
        observations, accessions = self._observations(
            references["common_target_ledger"], references["sequence_feature_table"]
        )
        folds = self._validate_splits(references["frozen_outer_split_manifest"], observations)
        if len(observations) != 2724 or len(accessions) != 99:
            raise R3ModelEvaluationError("R3 frozen effective sample differs from protocol-defined cohort")
        minimum_proteins = int(plan["metrics"]["minimum_proteins_per_metric_batch"])
        bootstrap_resamples = int(plan["uncertainty"]["resamples"])
        bootstrap_seed = int(plan["uncertainty"]["random_seed"])
        negative_config = plan["negative_controls"]["within_batch_rank_permutation"]
        negative_resamples = int(negative_config["resamples"])
        negative_seed = int(negative_config["random_seed"])
        full_indices = tuple(range(len(self.FEATURE_NAMES)))
        composition_indices = tuple(
            self.FEATURE_NAMES.index(name) for name in self.COMPOSITION_FEATURE_NAMES
        )

        predictions_rows: list[dict[str, Any]] = []
        per_batch_rows: list[dict[str, Any]] = []
        fold_rows: list[dict[str, Any]] = []
        selection_rows: list[dict[str, Any]] = []
        negative_rows: list[dict[str, Any]] = []
        ablation_rows: list[dict[str, Any]] = []
        parameters: dict[str, Any] = {}
        batch_metrics_by_key: dict[tuple[str, str, str], dict[str, Any]] = {}
        fold_primary: dict[tuple[str, str], float | None] = {}

        for fold_index, (fold_id, held_out_lab) in enumerate(folds, start=1):
            development = [row for row in observations if row.laboratory_anchor != held_out_lab]
            testing = sorted(
                [row for row in observations if row.laboratory_anchor == held_out_lab],
                key=lambda row: (row.measurement_batch_id, row.target_observation_id),
            )
            if not development or not testing:
                raise R3ModelEvaluationError("outer fold has no development or held-out observations")
            full_alpha, full_selection = self._select_alpha(
                development, full_indices, minimum_proteins=minimum_proteins
            )
            composition_alpha, composition_selection = self._select_alpha(
                development, composition_indices, minimum_proteins=minimum_proteins
            )
            for model_id, rows in (
                ("SEQUENCE_RIDGE_FULL", full_selection),
                ("SEQUENCE_RIDGE_COMPOSITION_ONLY", composition_selection),
            ):
                for row in rows:
                    selection_rows.append(
                        {
                            "outer_fold_id": fold_id,
                            "held_out_laboratory_anchor": held_out_lab,
                            "model_id": model_id,
                            **row,
                            "selected_alpha": full_alpha if model_id == "SEQUENCE_RIDGE_FULL" else composition_alpha,
                        }
                    )

            constant_mean = float(np.mean([row.target for row in development]))
            full_model = self._fit_ridge(development, full_indices, full_alpha)
            composition_model = self._fit_ridge(development, composition_indices, composition_alpha)
            model_predictions = {
                "CONSTANT_TRAINING_MEAN": np.full(len(testing), constant_mean, dtype=float),
                "SEQUENCE_RIDGE_FULL": self._predict_ridge(full_model, testing),
                "SEQUENCE_RIDGE_COMPOSITION_ONLY": self._predict_ridge(composition_model, testing),
            }
            parameters[fold_id] = {
                "held_out_laboratory_anchor": held_out_lab,
                "development_observation_count": len(development),
                "held_out_observation_count": len(testing),
                "CONSTANT_TRAINING_MEAN": {"development_target_mean": constant_mean},
                "SEQUENCE_RIDGE_FULL": self._ridge_parameters(full_model, self.FEATURE_NAMES),
                "SEQUENCE_RIDGE_COMPOSITION_ONLY": self._ridge_parameters(
                    composition_model, self.COMPOSITION_FEATURE_NAMES
                ),
            }
            for model_index, model_id in enumerate(self.MODEL_IDS, start=1):
                prediction = model_predictions[model_id]
                metrics = self._batch_metrics(
                    testing, prediction, minimum_proteins=minimum_proteins
                )
                aggregate = self._aggregate(metrics)
                fold_primary[(fold_id, model_id)] = aggregate["mean_spearman"]
                metric_status = (
                    "UNDEFINED_CONSTANT_PREDICTION"
                    if model_id == "CONSTANT_TRAINING_MEAN"
                    else "DEFINED"
                )
                uncertainty: dict[str, Any] = {}
                for metric_name, output_name in (
                    ("spearman", "mean_spearman"),
                    ("mae", "mean_mae"),
                    ("rmse", "mean_rmse"),
                ):
                    values = [item[metric_name] for item in metrics]
                    if any(value is None for value in values):
                        uncertainty[output_name] = None
                    else:
                        uncertainty[output_name] = self._bootstrap(
                            [float(value) for value in values],
                            resamples=bootstrap_resamples,
                            seed=bootstrap_seed + fold_index * 100 + model_index * 10,
                        )
                fold_rows.append(
                    {
                        "outer_fold_id": fold_id,
                        "held_out_laboratory_anchor": held_out_lab,
                        "model_id": model_id,
                        "held_out_observation_count": len(testing),
                        "held_out_measurement_batch_count": len(metrics),
                        "primary_metric_status": metric_status,
                        **aggregate,
                        "mean_spearman_lower_95": (
                            None if uncertainty["mean_spearman"] is None else uncertainty["mean_spearman"]["lower_95"]
                        ),
                        "mean_spearman_upper_95": (
                            None if uncertainty["mean_spearman"] is None else uncertainty["mean_spearman"]["upper_95"]
                        ),
                        "mean_mae_lower_95": uncertainty["mean_mae"]["lower_95"],
                        "mean_mae_upper_95": uncertainty["mean_mae"]["upper_95"],
                        "mean_rmse_lower_95": uncertainty["mean_rmse"]["lower_95"],
                        "mean_rmse_upper_95": uncertainty["mean_rmse"]["upper_95"],
                    }
                )
                for metric in metrics:
                    batch_metrics_by_key[(fold_id, model_id, metric["measurement_batch_id"])] = metric
                    per_batch_rows.append(
                        {
                            "outer_fold_id": fold_id,
                            "held_out_laboratory_anchor": held_out_lab,
                            "model_id": model_id,
                            **metric,
                            "spearman_status": metric_status if metric["spearman"] is None else "DEFINED",
                        }
                    )
                for observation, value in zip(testing, prediction, strict=True):
                    predictions_rows.append(
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

            paired_batches = sorted(
                {
                    batch_id
                    for outer_fold, model_id, batch_id in batch_metrics_by_key
                    if outer_fold == fold_id and model_id == "SEQUENCE_RIDGE_FULL"
                }
            )
            differences = [
                float(batch_metrics_by_key[(fold_id, "SEQUENCE_RIDGE_FULL", batch_id)]["spearman"])
                - float(
                    batch_metrics_by_key[(fold_id, "SEQUENCE_RIDGE_COMPOSITION_ONLY", batch_id)][
                        "spearman"
                    ]
                )
                for batch_id in paired_batches
            ]
            ablation_rows.append(
                {
                    "outer_fold_id": fold_id,
                    "held_out_laboratory_anchor": held_out_lab,
                    "paired_measurement_batch_count": len(differences),
                    "full_minus_composition_mean_spearman": float(np.mean(differences)),
                    **self._bootstrap(
                        differences,
                        resamples=bootstrap_resamples,
                        seed=bootstrap_seed + fold_index * 1000 + 701,
                    ),
                }
            )

            observed_primary = fold_primary[(fold_id, "SEQUENCE_RIDGE_FULL")]
            if observed_primary is None:
                raise R3ModelEvaluationError("full sequence model has undefined primary metric")
            development_targets = np.asarray([row.target for row in development], dtype=float)
            development_by_batch: dict[str, list[int]] = defaultdict(list)
            for position, row in enumerate(development):
                development_by_batch[row.measurement_batch_id].append(position)
            negative_rng = np.random.default_rng(negative_seed + fold_index)
            null_primary: list[float] = []
            for resample in range(1, negative_resamples + 1):
                permuted = development_targets.copy()
                for positions in development_by_batch.values():
                    permuted[positions] = negative_rng.permutation(permuted[positions])
                null_model = self._fit_ridge(
                    development, full_indices, full_alpha, targets=permuted
                )
                null_metrics = self._batch_metrics(
                    testing,
                    self._predict_ridge(null_model, testing),
                    minimum_proteins=minimum_proteins,
                )
                null_score = self._aggregate(null_metrics)["mean_spearman"]
                if null_score is None:
                    raise R3ModelEvaluationError("permutation negative control has undefined primary metric")
                null_primary.append(float(null_score))
                negative_rows.append(
                    {
                        "outer_fold_id": fold_id,
                        "held_out_laboratory_anchor": held_out_lab,
                        "selected_alpha": full_alpha,
                        "resample": resample,
                        "null_mean_spearman": float(null_score),
                    }
                )
            upper_tail_p = (1 + sum(value >= observed_primary for value in null_primary)) / (
                1 + negative_resamples
            )
            parameters[fold_id]["SEQUENCE_RIDGE_FULL"]["negative_control"] = {
                "resamples": negative_resamples,
                "random_seed": negative_seed + fold_index,
                "observed_mean_spearman": observed_primary,
                "null_mean_spearman_mean": float(np.mean(null_primary)),
                "null_mean_spearman_lower_95": float(np.quantile(null_primary, 0.025)),
                "null_mean_spearman_upper_95": float(np.quantile(null_primary, 0.975)),
                "one_sided_upper_tail_p": float(upper_tail_p),
            }

        self.output_root.mkdir(parents=True, exist_ok=False)
        paths = {
            "predictions": self.output_root / "outer_fold_predictions.csv",
            "batch_metrics": self.output_root / "measurement_batch_metrics.csv",
            "fold_metrics": self.output_root / "outer_fold_metrics.csv",
            "inner_selection": self.output_root / "nested_inner_selection.csv",
            "negative_control": self.output_root / "within_batch_rank_permutation.csv",
            "paired_ablation": self.output_root / "paired_composition_ablation.csv",
            "parameters": self.output_root / "outer_fold_model_parameters.json",
        }
        self._write_csv(
            paths["predictions"],
            [
                "outer_fold_id", "held_out_laboratory_anchor", "model_id", "target_observation_id",
                "source_id", "canonical_accession", "measurement_batch_id",
                "observed_rank_percentile_descending", "predicted_rank_percentile_descending",
            ],
            predictions_rows,
        )
        self._write_csv(
            paths["batch_metrics"],
            [
                "outer_fold_id", "held_out_laboratory_anchor", "model_id", "measurement_batch_id",
                "protein_count", "spearman", "spearman_status", "mae", "rmse",
            ],
            per_batch_rows,
        )
        self._write_csv(
            paths["fold_metrics"],
            [
                "outer_fold_id", "held_out_laboratory_anchor", "model_id",
                "held_out_observation_count", "held_out_measurement_batch_count",
                "primary_metric_status", "mean_spearman", "mean_spearman_lower_95",
                "mean_spearman_upper_95", "mean_mae", "mean_mae_lower_95", "mean_mae_upper_95",
                "mean_rmse", "mean_rmse_lower_95", "mean_rmse_upper_95",
            ],
            fold_rows,
        )
        self._write_csv(
            paths["inner_selection"],
            [
                "outer_fold_id", "held_out_laboratory_anchor", "model_id", "alpha",
                "held_out_inner_batch_id", "spearman", "selected_alpha",
            ],
            selection_rows,
        )
        self._write_csv(
            paths["negative_control"],
            [
                "outer_fold_id", "held_out_laboratory_anchor", "selected_alpha", "resample",
                "null_mean_spearman",
            ],
            negative_rows,
        )
        self._write_csv(
            paths["paired_ablation"],
            [
                "outer_fold_id", "held_out_laboratory_anchor", "paired_measurement_batch_count",
                "full_minus_composition_mean_spearman", "resamples", "seed", "lower_95", "upper_95",
            ],
            ablation_rows,
        )
        self._write_json(paths["parameters"], parameters)
        artifact_manifest = {
            name: {
                "relative_path": path.relative_to(self.root).as_posix(),
                "sha256": _sha256(path),
            }
            for name, path in paths.items()
        }
        report = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "executed_at": registry["executed_at"],
            "registry_sha256": _sha256(self.registry_path),
            "execution_module_sha256": _sha256(Path(__file__).resolve(strict=True)),
            "numpy_version": np.__version__,
            "evidence_class": registry["evidence_class"],
            "allowed_claim_level": registry["allowed_claim_level"],
            "status": self.STATUS,
            "input_references": {
                name: {
                    "relative_path": path.relative_to(self.root).as_posix(),
                    "sha256": _sha256(path),
                }
                for name, path in references.items()
            },
            "frozen_cohort": {
                "eligible_observation_count": len(observations),
                "canonical_protein_count": len(accessions),
                "laboratory_anchor_count": len({row.laboratory_anchor for row in observations}),
                "measurement_batch_count": len({row.measurement_batch_id for row in observations}),
                "outer_fold_count": len(folds),
                "model_count": len(self.MODEL_IDS),
            },
            "execution_contract": registry["execution_contract"],
            "model_results": fold_rows,
            "paired_composition_ablation": ablation_rows,
            "negative_control_summary": [
                {
                    "outer_fold_id": fold_id,
                    "held_out_laboratory_anchor": parameters[fold_id]["held_out_laboratory_anchor"],
                    **parameters[fold_id]["SEQUENCE_RIDGE_FULL"]["negative_control"],
                }
                for fold_id, _ in folds
            ],
            "multiplicity": {
                "method": "Holm step-down",
                "status": "NOT_APPLICABLE_NO_PREDECLARED_P_VALUES",
                "reason": registry["execution_contract"]["significance_policy"],
            },
            "artifacts": artifact_manifest,
            "claim_boundary": registry["claim_boundary"],
            "independent_validation": False,
            "external_scientific_reproduction": False,
            "scientific_submission_ready": False,
        }
        report_path = self.output_root / "model_evaluation_report.json"
        self._write_json(report_path, report)
        receipt = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "status": self.STATUS,
            "report_sha256": _sha256(report_path),
            "eligible_observation_count": len(observations),
            "canonical_protein_count": len(accessions),
            "laboratory_anchor_count": len({row.laboratory_anchor for row in observations}),
            "measurement_batch_count": len({row.measurement_batch_id for row in observations}),
            "outer_fold_count": len(folds),
            "model_count": len(self.MODEL_IDS),
            "outcome_analysis_run": True,
            "model_fitted": True,
            "independent_validation": False,
            "external_scientific_reproduction": False,
            "scientific_submission_ready": False,
        }
        receipt_path = self.output_root / "model_evaluation_receipt.json"
        self._write_json(receipt_path, receipt)
        return R3ModelEvaluationSummary(
            eligible_observation_count=len(observations),
            canonical_protein_count=len(accessions),
            laboratory_anchor_count=len({row.laboratory_anchor for row in observations}),
            measurement_batch_count=len({row.measurement_batch_id for row in observations}),
            model_count=len(self.MODEL_IDS),
            receipt_path=receipt_path,
        )

    def verify(self) -> R3ModelEvaluationSummary:
        report_path = self.output_root / "model_evaluation_report.json"
        receipt_path = self.output_root / "model_evaluation_receipt.json"
        report = self._json(report_path, "R3 model-evaluation report")
        receipt = self._json(receipt_path, "R3 model-evaluation receipt")
        artifacts = _mapping(report.get("artifacts"), "R3 model-evaluation artifacts")
        artifacts_valid = bool(artifacts)
        for artifact in artifacts.values():
            item = _mapping(artifact, "R3 model-evaluation artifact")
            if set(item) != self.REQUIRED_REFERENCE:
                artifacts_valid = False
                break
            try:
                path = self._root_file(_string(item.get("relative_path"), "artifact path"), "artifact")
                artifacts_valid = artifacts_valid and _sha256(path) == _checksum(
                    item.get("sha256"), "artifact"
                )
            except Exception:
                artifacts_valid = False
                break
        if (
            report.get("audit_id") != self.AUDIT_ID
            or receipt.get("audit_id") != self.AUDIT_ID
            or report.get("status") != self.STATUS
            or receipt.get("status") != self.STATUS
            or receipt.get("report_sha256") != _sha256(report_path)
            or receipt.get("outcome_analysis_run") is not True
            or receipt.get("model_fitted") is not True
            or receipt.get("independent_validation") is not False
            or receipt.get("external_scientific_reproduction") is not False
            or receipt.get("scientific_submission_ready") is not False
            or not artifacts_valid
        ):
            raise R3ModelEvaluationError("R3 model-evaluation receipt is invalid")
        return R3ModelEvaluationSummary(
            eligible_observation_count=int(receipt["eligible_observation_count"]),
            canonical_protein_count=int(receipt["canonical_protein_count"]),
            laboratory_anchor_count=int(receipt["laboratory_anchor_count"]),
            measurement_batch_count=int(receipt["measurement_batch_count"]),
            model_count=int(receipt["model_count"]),
            receipt_path=receipt_path,
        )
