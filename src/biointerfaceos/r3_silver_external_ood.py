"""Run the frozen author-run external-laboratory OOD check for the silver source."""

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
from biointerfaceos.r3_model_evaluation import (
    R3ModelEvaluationError,
    R3ModelEvaluationWorkflow,
    _Observation,
)
from biointerfaceos.r3_silver_plasma_source_audit import R3SilverPlasmaSourceAuditWorkflow
from biointerfaceos.r3_uniprot_mapping import _canonical, _checksum, _mapping, _sha256, _string


class R3SilverExternalOODerror(RuntimeError):
    """Raised when the frozen external OOD protocol cannot be executed safely."""


@dataclass(frozen=True)
class R3SilverExternalOODSummary:
    """Compact accounting for the external-laboratory R3 OOD run."""

    development_observation_count: int
    external_observation_count: int
    shared_canonical_protein_count: int
    external_measurement_batch_count: int
    model_count: int
    receipt_path: Path


class R3SilverExternalOODWorkflow:
    """Fit only on frozen R3 and score one byte-verified external lab source."""

    AUDIT_ID = "bioif-r3-silver-external-ood-v1.0.0"
    PROTOCOL_RELATIVE = "docs/data/R3_T155_SILVER_EXTERNAL_OOD_PROTOCOL.json"
    OUTPUT_RELATIVE = "reports/review_round_3/silver_external_ood/v1.0.0"
    STATUS = "R3_SILVER_EXTERNAL_LAB_OOD_EXECUTED_EXPLORATORY"
    REQUIRED_TOP_LEVEL = {
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
    REQUIRED_REFERENCE = {"relative_path", "sha256"}
    REQUIRED_REFERENCES = {
        "r3_analysis_protocol_receipt",
        "r3_common_target_ledger",
        "r3_sequence_feature_table",
        "silver_source_audit_receipt",
        "silver_source_cell_map",
    }
    REQUIRED_TARGET = {
        "target_id",
        "development_target",
        "external_target",
        "cross_study_raw_scale",
    }
    REQUIRED_SELECTION = {
        "population",
        "method",
        "tuning_metric",
        "tie_breaker",
        "final_refit",
    }
    REQUIRED_EXTERNAL = {
        "source_id",
        "laboratory_anchor",
        "analysis_population",
        "minimum_proteins_per_measurement_batch",
        "expected_measurement_batch_count",
        "expected_shared_canonical_protein_count_at_least",
        "access_condition",
    }
    REQUIRED_FEATURES = {"allowed_feature_set", "feature_standardization", "prohibited_features"}
    REQUIRED_METRICS = {"primary", "secondary", "constant_rank_metric_policy"}
    REQUIRED_UNCERTAINTY = {"method", "resamples", "random_seed"}
    REQUIRED_NEGATIVE = {"method", "resamples", "random_seed", "tail"}
    TARGET_FIELDS = [
        "external_target_observation_id",
        "source_id",
        "laboratory_anchor",
        "canonical_accession",
        "measurement_batch_id",
        "source_worksheet",
        "source_row",
        "source_coordinate",
        "author_quantity_type",
        "author_numeric_value",
        "rank_percentile_descending",
        "measurement_batch_positive_protein_count",
    ]

    def __init__(
        self,
        root: Path,
        output_data_root: Path,
        feature_root: Path,
        silver_assets_root: Path,
        *,
        protocol_path: Path | None = None,
        output_root: Path | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.output_data_root = output_data_root.resolve(strict=False)
        self.feature_root = feature_root.resolve(strict=False)
        self.silver_assets_root = silver_assets_root.resolve(strict=False)
        self.protocol_path = protocol_path or self.root / self.PROTOCOL_RELATIVE
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
            raise R3SilverExternalOODerror(f"cannot parse {label}") from exc
        try:
            return _mapping(value, label)
        except Exception as exc:
            raise R3SilverExternalOODerror(f"cannot parse {label}") from exc

    def _root_file(self, relative_path: str, label: str) -> Path:
        if "\\" in relative_path:
            raise R3SilverExternalOODerror(f"{label} must use a POSIX relative path")
        pure = PurePosixPath(relative_path)
        if pure.is_absolute() or not pure.parts or ".." in pure.parts:
            raise R3SilverExternalOODerror(f"{label} escapes repository root")
        path = (self.root / Path(*pure.parts)).resolve(strict=False)
        if not path.is_relative_to(self.root) or not path.is_file():
            raise R3SilverExternalOODerror(f"{label} is missing or outside repository root")
        return path

    def _reference(self, value: Any, label: str) -> Path:
        item = _mapping(value, label)
        if set(item) != self.REQUIRED_REFERENCE:
            raise R3SilverExternalOODerror(f"{label} fields are invalid")
        path = self._root_file(_string(item.get("relative_path"), label), label)
        try:
            expected = _checksum(item.get("sha256"), label)
        except Exception as exc:
            raise R3SilverExternalOODerror(f"{label} checksum is invalid") from exc
        if _sha256(path) != expected:
            raise R3SilverExternalOODerror(f"{label} checksum differs")
        return path

    def _protocol(self) -> tuple[dict[str, Any], dict[str, Path]]:
        protocol = self._json(self.protocol_path, "R3 silver external OOD protocol")
        if set(protocol) != self.REQUIRED_TOP_LEVEL or protocol.get("schema_version") != 1:
            raise R3SilverExternalOODerror("R3 silver external OOD protocol fields are invalid")
        if (
            protocol.get("protocol_id") != "bioif-r3-silver-external-ood-protocol-v1.0.0"
            or protocol.get("evidence_class") != "DEVELOPMENT_OBSERVATION"
            or protocol.get("allowed_claim_level") != "EXPLORATORY"
        ):
            raise R3SilverExternalOODerror("R3 silver external OOD protocol identity is invalid")
        _string(protocol.get("frozen_at"), "R3 silver external OOD frozen_at")
        _string(protocol.get("claim_boundary"), "R3 silver external OOD claim boundary")
        references = _mapping(protocol.get("references"), "R3 silver external OOD references")
        if set(references) != self.REQUIRED_REFERENCES:
            raise R3SilverExternalOODerror("R3 silver external OOD references are invalid")
        paths = {key: self._reference(value, key.replace("_", " ")) for key, value in references.items()}
        if self.output_data_root != (self.root / "data/raw").resolve(strict=False):
            raise R3SilverExternalOODerror("R3 silver external OOD requires the fixed data/raw root")
        if self.feature_root != (self.root / "data/raw/r3_uniprot_sequence_features").resolve(strict=False):
            raise R3SilverExternalOODerror("R3 silver external OOD requires the fixed feature root")
        if self.silver_assets_root != (self.root / "data/raw/r3_candidate_pmc6592156").resolve(strict=False):
            raise R3SilverExternalOODerror("R3 silver external OOD requires the fixed silver asset root")
        if _mapping(protocol.get("target"), "R3 silver external OOD target") != {
            "target_id": "R3_WITHIN_MEASUREMENT_BATCH_POSITIVE_QUANTIFICATION_RANK_PERCENTILE",
            "development_target": "the frozen R3 source-local descending midrank percentile",
            "external_target": "descending midrank percentile among all strictly positive finite author-reported LOG_CONVERTED_LFQ_ABUNDANCE values in the same silver-source measurement batch",
            "cross_study_raw_scale": "PROHIBITED",
        }:
            raise R3SilverExternalOODerror("R3 silver external OOD target is invalid")
        selection = _mapping(protocol.get("development_selection"), "R3 silver external OOD selection")
        if set(selection) != self.REQUIRED_SELECTION or selection != {
            "population": "all 2,724 frozen R3 eligible observations from the three original laboratory anchors",
            "method": "LEAVE_ONE_R3_DEVELOPMENT_MEASUREMENT_BATCH_OUT_NESTED_SELECTION",
            "tuning_metric": "mean development measurement-batch Spearman correlation",
            "tie_breaker": "smaller regularization then lexical model identifier",
            "final_refit": "fit the selected configuration on all frozen R3 development observations",
        }:
            raise R3SilverExternalOODerror("R3 silver external OOD selection is invalid")
        external = _mapping(protocol.get("external_evaluation"), "R3 silver external OOD external evaluation")
        if set(external) != self.REQUIRED_EXTERNAL or external != {
            "source_id": "PMC6592156_SILVER_NANOPARTICLE_HUMAN_PLASMA",
            "laboratory_anchor": "University of Southern Denmark / Russian Academy of Sciences study",
            "analysis_population": "strictly positive source rows whose direct UniProt accession exists in the frozen R3 sequence-feature table",
            "minimum_proteins_per_measurement_batch": 10,
            "expected_measurement_batch_count": 30,
            "expected_shared_canonical_protein_count_at_least": 45,
            "access_condition": "public author-accessible source; not a protected lockbox and not an independent evaluator",
        }:
            raise R3SilverExternalOODerror("R3 silver external OOD external evaluation is invalid")
        features = _mapping(protocol.get("feature_policy"), "R3 silver external OOD feature policy")
        prohibited = [
            "protein identity", "source identity", "laboratory identity", "worksheet", "condition",
            "replicate", "source coordinate", "author quantification value", "author rank",
        ]
        if set(features) != self.REQUIRED_FEATURES or features != {
            "allowed_feature_set": "R3_UNIPROT_SEQUENCE_COMPOSITION_PHYSICOCHEMICAL_V1",
            "feature_standardization": "fit only on all frozen R3 development observations",
            "prohibited_features": prohibited,
        }:
            raise R3SilverExternalOODerror("R3 silver external OOD feature policy is invalid")
        models = protocol.get("models")
        if models != [
            {"model_id": "CONSTANT_TRAINING_MEAN", "hyperparameters": {}},
            {"model_id": "SEQUENCE_RIDGE_FULL", "hyperparameters": {"alpha_grid": [0.01, 0.1, 1.0, 10.0, 100.0]}},
            {"model_id": "SEQUENCE_RIDGE_COMPOSITION_ONLY", "hyperparameters": {"alpha_grid": [0.01, 0.1, 1.0, 10.0, 100.0]}},
        ]:
            raise R3SilverExternalOODerror("R3 silver external OOD models are invalid")
        metrics = _mapping(protocol.get("metrics"), "R3 silver external OOD metrics")
        if set(metrics) != self.REQUIRED_METRICS or metrics != {
            "primary": "equal-weight mean external measurement-batch Spearman correlation",
            "secondary": [
                "equal-weight mean external measurement-batch mean absolute error",
                "equal-weight mean external measurement-batch root mean square error",
            ],
            "constant_rank_metric_policy": "undefined; report MAE and RMSE only",
        }:
            raise R3SilverExternalOODerror("R3 silver external OOD metrics are invalid")
        uncertainty = _mapping(protocol.get("uncertainty"), "R3 silver external OOD uncertainty")
        if set(uncertainty) != self.REQUIRED_UNCERTAINTY or uncertainty != {
            "method": "external measurement-batch cluster bootstrap percentile interval",
            "resamples": 2000,
            "random_seed": 20260816,
        }:
            raise R3SilverExternalOODerror("R3 silver external OOD uncertainty is invalid")
        negative = _mapping(protocol.get("negative_control"), "R3 silver external OOD negative control")
        if set(negative) != self.REQUIRED_NEGATIVE or negative != {
            "method": "permute R3 development targets independently within each development measurement batch while holding observed nested-selected alpha fixed",
            "resamples": 256,
            "random_seed": 20260817,
            "tail": "one-sided upper tail",
        }:
            raise R3SilverExternalOODerror("R3 silver external OOD negative control is invalid")
        return protocol, paths

    @staticmethod
    def _read_csv(path: Path, label: str) -> list[dict[str, str]]:
        try:
            with path.open("r", encoding="utf-8", newline="") as stream:
                rows = list(csv.DictReader(stream))
        except OSError as exc:
            raise R3SilverExternalOODerror(f"cannot read {label}") from exc
        if not rows or not rows[0]:
            raise R3SilverExternalOODerror(f"{label} is empty")
        return rows

    @staticmethod
    def _rank_percentiles(rows: Sequence[Mapping[str, str]]) -> dict[str, tuple[float, int]]:
        by_batch: dict[str, list[Mapping[str, str]]] = defaultdict(list)
        for row in rows:
            if row.get("rank_target_eligible") == "true":
                by_batch[_string(row.get("measurement_batch_id"), "silver measurement batch ID")].append(row)
        ranks: dict[str, tuple[float, int]] = {}
        for batch_id, batch_rows in by_batch.items():
            ordered = sorted(
                batch_rows,
                key=lambda row: (-float(row["author_numeric_value"]), row["source_coordinate"]),
            )
            count = len(ordered)
            start = 0
            while start < count:
                end = start + 1
                while end < count and float(ordered[end]["author_numeric_value"]) == float(
                    ordered[start]["author_numeric_value"]
                ):
                    end += 1
                midrank = (start + 1 + end) / 2.0
                percentile = 0.5 if count == 1 else (count - midrank) / (count - 1)
                for row in ordered[start:end]:
                    identifier = f"{batch_id}:{row['source_coordinate']}"
                    if identifier in ranks:
                        raise R3SilverExternalOODerror("silver source rank identity is duplicated")
                    ranks[identifier] = (percentile, count)
                start = end
        return ranks

    def _external_observations(
        self,
        source_map_path: Path,
        feature_values: Mapping[str, tuple[float, ...]],
        protocol: Mapping[str, Any],
    ) -> tuple[list[_Observation], list[dict[str, Any]], set[str]]:
        source_rows = self._read_csv(source_map_path, "silver source cell map")
        required = {
            "source_id", "laboratory_anchor", "source_worksheet", "source_row", "source_coordinate",
            "source_identifier", "measurement_batch_id", "author_quantity_type", "author_numeric_value",
            "rank_target_eligible",
        }
        if not required.issubset(source_rows[0]):
            raise R3SilverExternalOODerror("silver source cell map schema is invalid")
        source_id = protocol["external_evaluation"]["source_id"]
        laboratory_anchor = protocol["external_evaluation"]["laboratory_anchor"]
        if any(
            row.get("source_id") != source_id or row.get("laboratory_anchor") != laboratory_anchor
            for row in source_rows
        ):
            raise R3SilverExternalOODerror("silver source map identity differs from the frozen protocol")
        ranks = self._rank_percentiles(source_rows)
        candidates: list[tuple[dict[str, str], tuple[float, int]]] = []
        for row in source_rows:
            identifier = f"{row['measurement_batch_id']}:{row['source_coordinate']}"
            rank = ranks.get(identifier)
            if rank is not None and row["source_identifier"] in feature_values:
                candidates.append((row, rank))
        by_batch: dict[str, int] = defaultdict(int)
        accessions: set[str] = set()
        observations: list[_Observation] = []
        target_rows: list[dict[str, Any]] = []
        for row, (percentile, positive_count) in candidates:
            accession = row["source_identifier"]
            batch_id = row["measurement_batch_id"]
            by_batch[batch_id] += 1
            accessions.add(accession)
            target_id = f"R3SILVER:{row['source_worksheet']}:{row['source_row']}:{batch_id}"
            observations.append(
                _Observation(
                    target_observation_id=target_id,
                    source_id=source_id,
                    canonical_accession=accession,
                    laboratory_anchor=laboratory_anchor,
                    measurement_batch_id=batch_id,
                    target=percentile,
                    feature_values=feature_values[accession],
                )
            )
            target_rows.append(
                {
                    "external_target_observation_id": target_id,
                    "source_id": source_id,
                    "laboratory_anchor": laboratory_anchor,
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
        external = protocol["external_evaluation"]
        if (
            len(by_batch) != external["expected_measurement_batch_count"]
            or len(accessions) < external["expected_shared_canonical_protein_count_at_least"]
            or any(count < external["minimum_proteins_per_measurement_batch"] for count in by_batch.values())
        ):
            raise R3SilverExternalOODerror("silver source does not meet frozen external OOD coverage")
        return sorted(observations, key=lambda item: (item.measurement_batch_id, item.target_observation_id)), target_rows, accessions

    @staticmethod
    def _format(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, float):
            return format(value, ".17g")
        return str(value)

    @classmethod
    def _write_csv(cls, path: Path, fields: Sequence[str], rows: Sequence[Mapping[str, Any]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
            writer.writeheader()
            for row in rows:
                writer.writerow({field: cls._format(row.get(field)) for field in fields})

    def run(self, *, strict: bool = False) -> R3SilverExternalOODSummary:
        if not strict:
            raise R3SilverExternalOODerror("R3 silver external OOD requires --strict")
        if self.output_root.exists():
            raise R3SilverExternalOODerror("R3 silver external OOD already executed")
        protocol, paths = self._protocol()
        try:
            R3AnalysisProtocolWorkflow(self.root, self.output_data_root).verify()
            R3SilverPlasmaSourceAuditWorkflow(self.root, self.silver_assets_root).verify()
        except Exception as exc:
            raise R3SilverExternalOODerror("a frozen R3 input receipt does not verify") from exc
        r3_protocol_receipt = self._json(paths["r3_analysis_protocol_receipt"], "R3 protocol receipt")
        silver_receipt = self._json(paths["silver_source_audit_receipt"], "silver source receipt")
        if (
            r3_protocol_receipt.get("status") != "FROZEN_R3_COMMON_RANK_ANALYSIS_PROTOCOL"
            or r3_protocol_receipt.get("target_status") != "FROZEN_R3_RANK_BENCHMARK"
            or silver_receipt.get("status")
            != "ADMITTED_REAL_HUMAN_PLASMA_EXTERNAL_OOD_SOURCE_PENDING_PROTOCOL_FREEZE"
            or silver_receipt.get("model_fitted") is not False
        ):
            raise R3SilverExternalOODerror("frozen R3 input receipt state is invalid")
        helper = R3ModelEvaluationWorkflow(self.root, self.output_data_root, self.feature_root)
        try:
            development, development_accessions = helper._observations(
                paths["r3_common_target_ledger"], paths["r3_sequence_feature_table"]
            )
        except R3ModelEvaluationError as exc:
            raise R3SilverExternalOODerror("frozen R3 development data is invalid") from exc
        if len(development) != 2724 or len(development_accessions) != 99:
            raise R3SilverExternalOODerror("frozen R3 development cohort differs")
        features = {row.canonical_accession: row.feature_values for row in development}
        external, target_rows, external_accessions = self._external_observations(
            paths["silver_source_cell_map"], features, protocol
        )
        full_indices = tuple(range(len(helper.FEATURE_NAMES)))
        composition_indices = tuple(
            helper.FEATURE_NAMES.index(name) for name in helper.COMPOSITION_FEATURE_NAMES
        )
        full_alpha, full_selection = helper._select_alpha(
            development, full_indices, minimum_proteins=10
        )
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
            batch_metrics = helper._batch_metrics(external, predictions[model_id], minimum_proteins=10)
            aggregate = helper._aggregate(batch_metrics)
            primary_status = "UNDEFINED_CONSTANT_PREDICTION" if model_id == "CONSTANT_TRAINING_MEAN" else "DEFINED"
            intervals: dict[str, dict[str, float | int] | None] = {}
            for source_metric, report_metric in (
                ("spearman", "mean_spearman"),
                ("mae", "mean_mae"),
                ("rmse", "mean_rmse"),
            ):
                values = [metric[source_metric] for metric in batch_metrics]
                intervals[report_metric] = (
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
            model_rows.append(
                {
                    "model_id": model_id,
                    "external_observation_count": len(external),
                    "external_measurement_batch_count": len(batch_metrics),
                    "primary_metric_status": primary_status,
                    **aggregate,
                    "mean_spearman_lower_95": None if intervals["mean_spearman"] is None else intervals["mean_spearman"]["lower_95"],
                    "mean_spearman_upper_95": None if intervals["mean_spearman"] is None else intervals["mean_spearman"]["upper_95"],
                    "mean_mae_lower_95": intervals["mean_mae"]["lower_95"],
                    "mean_mae_upper_95": intervals["mean_mae"]["upper_95"],
                    "mean_rmse_lower_95": intervals["mean_rmse"]["lower_95"],
                    "mean_rmse_upper_95": intervals["mean_rmse"]["upper_95"],
                }
            )
            for metric in batch_metrics:
                metric_by_model_batch[(model_id, metric["measurement_batch_id"])] = metric
                batch_rows.append(
                    {"model_id": model_id, **metric, "spearman_status": primary_status if metric["spearman"] is None else "DEFINED"}
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
            raise R3SilverExternalOODerror("full sequence OOD primary metric is undefined")
        paired_batches = sorted(
            batch_id for model_id, batch_id in metric_by_model_batch if model_id == "SEQUENCE_RIDGE_FULL"
        )
        paired_difference = [
            float(metric_by_model_batch[("SEQUENCE_RIDGE_FULL", batch_id)]["spearman"])
            - float(metric_by_model_batch[("SEQUENCE_RIDGE_COMPOSITION_ONLY", batch_id)]["spearman"])
            for batch_id in paired_batches
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
            null_metrics = helper._batch_metrics(
                external, helper._predict_ridge(null_model, external), minimum_proteins=10
            )
            score = helper._aggregate(null_metrics)["mean_spearman"]
            if score is None:
                raise R3SilverExternalOODerror("silver permutation control has undefined primary metric")
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
            {"model_id": "SEQUENCE_RIDGE_FULL", **row, "selected_alpha": full_alpha}
            for row in full_selection
        ] + [
            {"model_id": "SEQUENCE_RIDGE_COMPOSITION_ONLY", **row, "selected_alpha": composition_alpha}
            for row in composition_selection
        ]
        self.output_root.mkdir(parents=True, exist_ok=False)
        paths = {
            "external_target_ledger": self.output_root / "silver_external_rank_target_ledger.csv",
            "predictions": self.output_root / "silver_external_ood_predictions.csv",
            "batch_metrics": self.output_root / "silver_external_measurement_batch_metrics.csv",
            "model_metrics": self.output_root / "silver_external_ood_model_metrics.csv",
            "selection": self.output_root / "silver_external_development_nested_selection.csv",
            "negative_control": self.output_root / "silver_external_within_batch_permutation.csv",
            "parameters": self.output_root / "silver_external_model_parameters.json",
        }
        self._write_csv(paths["external_target_ledger"], self.TARGET_FIELDS, target_rows)
        self._write_csv(
            paths["predictions"],
            ["model_id", "external_target_observation_id", "canonical_accession", "measurement_batch_id", "observed_rank_percentile_descending", "predicted_rank_percentile_descending"],
            prediction_rows,
        )
        self._write_csv(
            paths["batch_metrics"],
            ["model_id", "measurement_batch_id", "protein_count", "spearman", "spearman_status", "mae", "rmse"],
            batch_rows,
        )
        self._write_csv(
            paths["model_metrics"],
            ["model_id", "external_observation_count", "external_measurement_batch_count", "primary_metric_status", "mean_spearman", "mean_spearman_lower_95", "mean_spearman_upper_95", "mean_mae", "mean_mae_lower_95", "mean_mae_upper_95", "mean_rmse", "mean_rmse_lower_95", "mean_rmse_upper_95"],
            model_rows,
        )
        self._write_csv(
            paths["selection"],
            ["model_id", "alpha", "held_out_inner_batch_id", "spearman", "selected_alpha"],
            selection_rows,
        )
        self._write_csv(paths["negative_control"], ["resample", "null_mean_spearman"], null_rows)
        parameters = {
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
        }
        self._write_json(paths["parameters"], parameters)
        artifacts = {
            name: {"relative_path": path.relative_to(self.root).as_posix(), "sha256": _sha256(path)}
            for name, path in paths.items()
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
                name: {"relative_path": path.relative_to(self.root).as_posix(), "sha256": _sha256(path)}
                for name, path in paths.items()
            },
            "development_observation_count": len(development),
            "development_canonical_protein_count": len(development_accessions),
            "external_observation_count": len(external),
            "external_shared_canonical_protein_count": len(external_accessions),
            "external_measurement_batch_count": len({row.measurement_batch_id for row in external}),
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
        report_path = self.output_root / "silver_external_ood_report.json"
        self._write_json(report_path, report)
        receipt = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "status": self.STATUS,
            "report_sha256": _sha256(report_path),
            "development_observation_count": len(development),
            "external_observation_count": len(external),
            "external_shared_canonical_protein_count": len(external_accessions),
            "external_measurement_batch_count": len({row.measurement_batch_id for row in external}),
            "model_count": len(helper.MODEL_IDS),
            "model_fitted": True,
            "independent_validation": False,
            "external_scientific_reproduction": False,
            "scientific_submission_ready": False,
        }
        receipt_path = self.output_root / "silver_external_ood_receipt.json"
        self._write_json(receipt_path, receipt)
        return R3SilverExternalOODSummary(
            development_observation_count=len(development),
            external_observation_count=len(external),
            shared_canonical_protein_count=len(external_accessions),
            external_measurement_batch_count=len({row.measurement_batch_id for row in external}),
            model_count=len(helper.MODEL_IDS),
            receipt_path=receipt_path,
        )

    def verify(self) -> R3SilverExternalOODSummary:
        report_path = self.output_root / "silver_external_ood_report.json"
        receipt_path = self.output_root / "silver_external_ood_receipt.json"
        report = self._json(report_path, "silver external OOD report")
        receipt = self._json(receipt_path, "silver external OOD receipt")
        artifacts = _mapping(report.get("artifacts"), "silver external OOD artifacts")
        valid_artifacts = bool(artifacts)
        for item_value in artifacts.values():
            item = _mapping(item_value, "silver external OOD artifact")
            if set(item) != self.REQUIRED_REFERENCE:
                valid_artifacts = False
                break
            try:
                path = self._root_file(_string(item.get("relative_path"), "artifact path"), "artifact")
                valid_artifacts = valid_artifacts and _sha256(path) == _checksum(item.get("sha256"), "artifact")
            except Exception:
                valid_artifacts = False
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
            or not valid_artifacts
        ):
            raise R3SilverExternalOODerror("silver external OOD receipt is invalid")
        return R3SilverExternalOODSummary(
            development_observation_count=int(receipt["development_observation_count"]),
            external_observation_count=int(receipt["external_observation_count"]),
            shared_canonical_protein_count=int(receipt["external_shared_canonical_protein_count"]),
            external_measurement_batch_count=int(receipt["external_measurement_batch_count"]),
            model_count=int(receipt["model_count"]),
            receipt_path=receipt_path,
        )
