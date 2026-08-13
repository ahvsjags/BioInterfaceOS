"""Execute the frozen full-text core-facility portability analysis (T194).

The source is the openly licensed supplementary quantitative table from
PMC9633814.  It is deliberately treated as technical-domain evidence: the
same pooled human-plasma aliquot was distributed to multiple core facilities,
so this workflow cannot be used to claim independent biological cohorts.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import re
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

import numpy as np

from biointerfaceos.r3_model_evaluation import (
    R3ModelEvaluationError,
    R3ModelEvaluationWorkflow,
    _Observation,
)
from biointerfaceos.r3_uniprot_mapping import _canonical, _checksum, _mapping, _sha256, _string


class R4T194FulltextExecutionError(RuntimeError):
    """Raised when frozen T194 inputs or outputs fail validation."""


@dataclass(frozen=True)
class R4T194FulltextExecutionSummary:
    observation_count: int
    target_universe_count: int
    core_facility_count: int
    measurement_batch_count: int
    model_count: int
    receipt_path: Path


class R4T194FulltextCoreFacilityExecutionWorkflow:
    """Run a study-held-out, core-facility-held-out technical analysis."""

    AUDIT_ID = "bioif-r4-t194-fulltext-core-facility-execution-v1.0.0"
    STATUS = "T194_FULLTEXT_CORE_FACILITY_EXECUTION_COMPLETED_EXPLORATORY"
    PROTOCOL_RELATIVE = "docs/data/R4_T194_FULLTEXT_CORE_FACILITY_EXECUTION_PROTOCOL.json"
    REGISTRY_RELATIVE = "docs/data/R4_T194_FULLTEXT_CORE_FACILITY_EXECUTION_REGISTRY.json"
    MAP_RELATIVE = (
        "data/raw/r3_fulltext_pmc9633814/derived/"
        "R3_PMC9633814_semiquantitative_source_cell_map.csv"
    )
    TARGET_RELATIVE = "data/raw/r3_common_rank_target/R3_common_rank_target_ledger.csv"
    FEATURE_RELATIVE = (
        "data/raw/r3_uniprot_sequence_features/uniprot_sequence_features/"
        "R3_uniprot_sequence_features.csv"
    )
    OUTPUT_RELATIVE = "reports/review_round_4/t194_fulltext_core_facility_execution/v1.0.0"
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
            raise R4T194FulltextExecutionError("T194 output must remain under repository root")
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
            raise R4T194FulltextExecutionError(f"cannot parse {label}") from exc

    def _root_file(self, relative_path: str, label: str) -> Path:
        if "\\" in relative_path:
            raise R4T194FulltextExecutionError(f"{label} must use POSIX separators")
        pure = PurePosixPath(relative_path)
        if pure.is_absolute() or not pure.parts or ".." in pure.parts:
            raise R4T194FulltextExecutionError(f"{label} escapes repository root")
        path = (self.root / Path(*pure.parts)).resolve(strict=False)
        if not path.is_relative_to(self.root) or not path.is_file():
            raise R4T194FulltextExecutionError(f"{label} is missing or outside repository root")
        return path

    def _reference(self, value: Any, label: str) -> Path:
        reference = _mapping(value, label)
        if set(reference) != self.REQUIRED_REFERENCE:
            raise R4T194FulltextExecutionError(f"{label} reference fields are invalid")
        path = self._root_file(_string(reference["relative_path"], label), label)
        if _sha256(path) != _checksum(reference["sha256"], label):
            raise R4T194FulltextExecutionError(f"{label} checksum differs")
        return path

    @staticmethod
    def _read_csv(path: Path, label: str) -> list[dict[str, str]]:
        try:
            with path.open("r", encoding="utf-8", newline="") as stream:
                rows = list(csv.DictReader(stream))
        except OSError as exc:
            raise R4T194FulltextExecutionError(f"cannot read {label}") from exc
        if not rows or not rows[0]:
            raise R4T194FulltextExecutionError(f"{label} is empty")
        return rows

    def _documents(self) -> tuple[dict[str, Any], dict[str, Any], dict[str, Path]]:
        registry = self._json(self.root / self.REGISTRY_RELATIVE, "T194 registry")
        expected_registry = {
            "schema_version", "audit_id", "protocol_id", "status", "evidence_class",
            "allowed_claim_level", "protocol", "source_cell_map", "r3_common_target_ledger",
            "r3_sequence_feature_table", "expected_accounting", "output_contract",
            "claim_boundary", "scientific_submission_ready",
        }
        if set(registry) != expected_registry or registry.get("schema_version") != 1:
            raise R4T194FulltextExecutionError("T194 registry fields are invalid")
        if (
            registry["audit_id"] != self.AUDIT_ID
            or registry["protocol_id"] != self.AUDIT_ID
            or registry["status"] != "T194_FULLTEXT_CORE_FACILITY_EXECUTION_REGISTERED"
            or registry["evidence_class"] != "DEVELOPMENT_OBSERVATION"
            or registry["allowed_claim_level"] != "EXPLORATORY"
            or registry["scientific_submission_ready"] is not False
        ):
            raise R4T194FulltextExecutionError("T194 registry identity or boundary is invalid")
        protocol_path = self._reference(registry["protocol"], "T194 protocol")
        protocol = self._json(protocol_path, "T194 protocol")
        if (
            protocol.get("protocol_id") != self.AUDIT_ID
            or protocol.get("status") != "FROZEN_BEFORE_T194_EXECUTION"
            or protocol.get("scientific_submission_ready") is not False
        ):
            raise R4T194FulltextExecutionError("T194 protocol identity or boundary is invalid")
        refs = {
            "source_cell_map": self._reference(registry["source_cell_map"], "T194 source map"),
            "r3_common_target_ledger": self._reference(
                registry["r3_common_target_ledger"], "R3 target ledger"
            ),
            "r3_sequence_feature_table": self._reference(
                registry["r3_sequence_feature_table"], "R3 feature table"
            ),
        }
        if refs["source_cell_map"] != self.root / self.MAP_RELATIVE:
            raise R4T194FulltextExecutionError("T194 source map path is not release-fixed")
        if refs["r3_common_target_ledger"] != self.root / self.TARGET_RELATIVE:
            raise R4T194FulltextExecutionError("T194 target ledger path is not release-fixed")
        if refs["r3_sequence_feature_table"] != self.root / self.FEATURE_RELATIVE:
            raise R4T194FulltextExecutionError("T194 feature table path is not release-fixed")
        return registry, protocol, refs

    def _features_and_targets(
        self, refs: Mapping[str, Path], protocol: Mapping[str, Any]
    ) -> tuple[dict[str, tuple[float, ...]], set[str]]:
        feature_rows = self._read_csv(refs["r3_sequence_feature_table"], "R3 feature table")
        expected_columns = {"canonical_accession", *R3ModelEvaluationWorkflow.FEATURE_NAMES}
        if set(feature_rows[0]) != expected_columns:
            raise R4T194FulltextExecutionError("R3 feature table schema differs")
        features: dict[str, tuple[float, ...]] = {}
        for row in feature_rows:
            accession = _string(row.get("canonical_accession"), "feature accession")
            if accession in features:
                raise R4T194FulltextExecutionError("R3 feature table repeats an accession")
            try:
                values = tuple(float(row[name]) for name in R3ModelEvaluationWorkflow.FEATURE_NAMES)
            except (TypeError, ValueError) as exc:
                raise R4T194FulltextExecutionError("R3 feature value is invalid") from exc
            if not all(math.isfinite(value) for value in values):
                raise R4T194FulltextExecutionError("R3 feature value is not finite")
            features[accession] = values
        target_rows = self._read_csv(refs["r3_common_target_ledger"], "R3 common target ledger")
        targets = {
            _string(row["canonical_accession"], "R3 target accession")
            for row in target_rows
            if row.get("common_rank_target_member") == "true"
        }
        expected_count = int(_mapping(protocol["frozen_target_universe"], "T194 target universe")["expected_target_count"])
        if len(targets) != expected_count or set(features) != targets:
            raise R4T194FulltextExecutionError("pre-frozen target universe does not close feature table")
        return features, targets

    @staticmethod
    def _numeric_replicates(row: Mapping[str, str]) -> list[float]:
        values: list[float] = []
        for field in ("replicate_1", "replicate_2", "replicate_3"):
            value = row.get(field, "")
            try:
                parsed = float(value)
            except (TypeError, ValueError):
                continue
            if math.isfinite(parsed) and parsed > 0.0:
                values.append(parsed)
        return values

    @staticmethod
    def _split_accessions(value: str) -> list[str]:
        return [token for token in re.split(r"[;|,\s]+", value or "") if token]

    @staticmethod
    def _rank_values(values: Sequence[float]) -> list[float]:
        order = sorted(range(len(values)), key=lambda index: (-values[index], index))
        ranks = [0.0] * len(values)
        cursor = 0
        while cursor < len(order):
            end = cursor + 1
            while end < len(order) and values[order[end]] == values[order[cursor]]:
                end += 1
            midrank = (cursor + 1 + end) / 2.0
            percentile = 0.5 if len(order) == 1 else (len(order) - midrank) / (len(order) - 1)
            for position in range(cursor, end):
                ranks[order[position]] = percentile
            cursor = end
        return ranks

    def _source_observations(
        self,
        refs: Mapping[str, Path],
        features: Mapping[str, tuple[float, ...]],
        targets: set[str],
        registry: Mapping[str, Any],
        protocol: Mapping[str, Any],
    ) -> tuple[list[_Observation], list[dict[str, Any]], dict[str, Any]]:
        rows = self._read_csv(refs["source_cell_map"], "PMC9633814 source map")
        expected_rows = int(_mapping(registry["expected_accounting"], "T194 accounting")["raw_map_rows"])
        if len(rows) != expected_rows:
            raise R4T194FulltextExecutionError("PMC9633814 raw map row count differs")
        by_core: dict[str, list[tuple[dict[str, str], float, list[str]]]] = defaultdict(list)
        for row in rows:
            core = _string(row.get("core_facility_code"), "core facility code")
            numeric = self._numeric_replicates(row)
            if not numeric:
                continue
            accessions = self._split_accessions(row.get("protein_ids", ""))
            by_core[core].append((row, float(np.mean(numeric)), accessions))
        core_count = len(by_core)
        expected_cores = int(_mapping(protocol["outer_split"], "T194 outer split")["expected_core_count"])
        if core_count != expected_cores:
            raise R4T194FulltextExecutionError("T194 core-facility count differs")
        observations: list[_Observation] = []
        ledger: list[dict[str, Any]] = []
        accounting: dict[str, Any] = {}
        selected_count = 0
        for core in sorted(by_core):
            core_rows = by_core[core]
            ranks = self._rank_values([item[1] for item in core_rows])
            source_id = f"PMC9633814_CORE_FACILITY_{core}"
            batch_id = source_id
            anchor = source_id
            target_seen: set[str] = set()
            core_selected = 0
            for index, (row, value, accessions) in enumerate(core_rows):
                hits = sorted(set(accessions).intersection(targets))
                if len(hits) > 1:
                    raise R4T194FulltextExecutionError("a source row maps to multiple frozen targets")
                if not hits:
                    continue
                accession = hits[0]
                if accession in target_seen:
                    raise R4T194FulltextExecutionError("a core repeats a frozen target row")
                target_seen.add(accession)
                identity = "|".join((source_id, row.get("source_coordinate", ""), accession))
                observation_id = "T194_" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:20]
                observations.append(
                    _Observation(
                        target_observation_id=observation_id,
                        source_id=source_id,
                        canonical_accession=accession,
                        laboratory_anchor=anchor,
                        measurement_batch_id=batch_id,
                        target=ranks[index],
                        feature_values=features[accession],
                    )
                )
                ledger.append(
                    {
                        "target_observation_id": observation_id,
                        "source_id": source_id,
                        "laboratory_anchor": anchor,
                        "source_license": "CC-BY-4.0",
                        "canonical_accession": accession,
                        "measurement_batch_id": batch_id,
                        "biological_unit_id": "PMC9633814:COMMON_POOLED_HUMAN_PLASMA_ALIQUOT",
                        "source_asset_id": row.get("source_asset_id", ""),
                        "source_worksheet": row.get("source_worksheet", ""),
                        "source_row": row.get("source_row", ""),
                        "source_coordinate": row.get("source_cell_range", ""),
                        "source_identifier": row.get("protein_ids", ""),
                        "author_quantity_type": "MEAN_AVAILABLE_REPLICATES",
                        "author_numeric_value": format(value, ".17g"),
                        "author_value_state": "POSITIVE_QUANTIFIED",
                        "rank_target_eligible": "true",
                        "prefrozen_target_universe_member": "true",
                        "multi_accession_group_flag": "true" if len(accessions) > 1 else "false",
                        "source_local_rank_percentile": format(ranks[index], ".17g"),
                        "source_batch_positive_count": len(core_rows),
                        "cross_source_scale_use": "PROHIBITED",
                    }
                )
                core_selected += 1
            selected_count += core_selected
            accounting[source_id] = {
                "core_facility_code": core,
                "raw_numeric_rows": len(core_rows),
                "observation_count": core_selected,
                "target_count": len(target_seen),
                "measurement_batch_count": 1,
                "biological_unit_semantics": "common pooled aliquot; technical core-facility domain",
            }
        expected_obs = int(_mapping(registry["expected_accounting"], "T194 accounting")["eligible_observation_count"])
        if selected_count != expected_obs or len({row.canonical_accession for row in observations}) != len(targets):
            raise R4T194FulltextExecutionError("T194 observation or target accounting differs")
        return sorted(observations, key=lambda row: row.target_observation_id), sorted(ledger, key=lambda row: row["target_observation_id"]), accounting

    def _execute_models(
        self, observations: Sequence[_Observation], protocol: Mapping[str, Any]
    ) -> dict[str, Any]:
        helper = R3ModelEvaluationWorkflow(
            self.root,
            self.root / "data/raw",
            self.root / "data/raw/r3_uniprot_sequence_features",
            output_root=self.root / "reports/review_round_4/t194_helper_unused",
        )
        outer = sorted({row.laboratory_anchor for row in observations})
        if len(outer) != 12:
            raise R4T194FulltextExecutionError("T194 requires 12 core-facility outer folds")
        nested = _mapping(protocol["nested_selection"], "T194 nested selection")
        minimum_proteins = int(nested["minimum_proteins_per_selection_batch"])
        uncertainty = _mapping(protocol["uncertainty"], "T194 uncertainty")
        negative = _mapping(protocol["negative_control"], "T194 negative control")
        full_indices = tuple(range(len(helper.FEATURE_NAMES)))
        composition_indices = tuple(helper.FEATURE_NAMES.index(name) for name in helper.COMPOSITION_FEATURE_NAMES)
        predictions: list[dict[str, Any]] = []
        batch_metrics: list[dict[str, Any]] = []
        fold_metrics: list[dict[str, Any]] = []
        selections: list[dict[str, Any]] = []
        ablations: list[dict[str, Any]] = []
        negative_rows: list[dict[str, Any]] = []
        parameters: dict[str, Any] = {}
        for fold_index, held_out in enumerate(outer, start=1):
            fold_id = f"T194_OUTER_{fold_index:02d}"
            development = [row for row in observations if row.laboratory_anchor != held_out]
            testing = sorted(
                [row for row in observations if row.laboratory_anchor == held_out],
                key=lambda row: row.target_observation_id,
            )
            try:
                full_alpha, full_selection = helper._select_alpha(development, full_indices, minimum_proteins=minimum_proteins)
                composition_alpha, composition_selection = helper._select_alpha(development, composition_indices, minimum_proteins=minimum_proteins)
            except R3ModelEvaluationError as exc:
                raise R4T194FulltextExecutionError("T194 nested alpha selection failed") from exc
            for row in full_selection:
                selections.append({"outer_fold_id": fold_id, "held_out_core": held_out, "model_id": "SEQUENCE_RIDGE_FULL", **row, "selected_alpha": full_alpha})
            for row in composition_selection:
                selections.append({"outer_fold_id": fold_id, "held_out_core": held_out, "model_id": "SEQUENCE_RIDGE_COMPOSITION_ONLY", **row, "selected_alpha": composition_alpha})
            constant_mean = float(np.mean([row.target for row in development]))
            full_model = helper._fit_ridge(development, full_indices, full_alpha)
            composition_model = helper._fit_ridge(development, composition_indices, composition_alpha)
            predictions_by_model = {
                "CONSTANT_TRAINING_MEAN": np.full(len(testing), constant_mean),
                "SEQUENCE_RIDGE_FULL": helper._predict_ridge(full_model, testing),
                "SEQUENCE_RIDGE_COMPOSITION_ONLY": helper._predict_ridge(composition_model, testing),
            }
            parameters[fold_id] = {
                "held_out_core": held_out,
                "development_observation_count": len(development),
                "held_out_observation_count": len(testing),
                "SEQUENCE_RIDGE_FULL": helper._ridge_parameters(full_model, helper.FEATURE_NAMES),
                "SEQUENCE_RIDGE_COMPOSITION_ONLY": helper._ridge_parameters(composition_model, helper.COMPOSITION_FEATURE_NAMES),
                "constant_training_mean": constant_mean,
            }
            metrics_by_model: dict[str, list[dict[str, Any]]] = {}
            for model_id in self.MODEL_IDS:
                predicted = predictions_by_model[model_id]
                metrics = helper._batch_metrics(testing, predicted, minimum_proteins=minimum_proteins)
                metrics_by_model[model_id] = metrics
                aggregate = helper._aggregate(metrics)
                fold_metrics.append({
                    "outer_fold_id": fold_id,
                    "held_out_core": held_out,
                    "model_id": model_id,
                    "held_out_observation_count": len(testing),
                    "held_out_measurement_batch_count": len(metrics),
                    "primary_metric_status": "UNDEFINED_CONSTANT_PREDICTION" if model_id == "CONSTANT_TRAINING_MEAN" else "DEFINED",
                    **aggregate,
                })
                for metric in metrics:
                    batch_metrics.append({"outer_fold_id": fold_id, "held_out_core": held_out, "model_id": model_id, **metric})
                for observation, value in zip(testing, predicted, strict=True):
                    predictions.append({
                        "outer_fold_id": fold_id,
                        "held_out_core": held_out,
                        "model_id": model_id,
                        "target_observation_id": observation.target_observation_id,
                        "source_id": observation.source_id,
                        "canonical_accession": observation.canonical_accession,
                        "measurement_batch_id": observation.measurement_batch_id,
                        "observed_rank_percentile_descending": observation.target,
                        "predicted_rank_percentile_descending": float(value),
                    })
            full_metric = metrics_by_model["SEQUENCE_RIDGE_FULL"][0]
            composition_metric = metrics_by_model["SEQUENCE_RIDGE_COMPOSITION_ONLY"][0]
            differences = [] if full_metric["spearman"] is None or composition_metric["spearman"] is None else [float(full_metric["spearman"]) - float(composition_metric["spearman"])]
            ablation = {"outer_fold_id": fold_id, "held_out_core": held_out, "paired_measurement_batch_count": len(differences), "full_minus_composition_spearman": differences[0] if differences else None}
            ablations.append(ablation)
            dev_targets = np.asarray([row.target for row in development], dtype=float)
            by_core: dict[str, list[int]] = defaultdict(list)
            for position, row in enumerate(development):
                by_core[row.laboratory_anchor].append(position)
            rng = np.random.default_rng(int(negative["random_seed"]) + fold_index)
            null_values: list[float] = []
            for resample in range(1, int(negative["resamples"]) + 1):
                permuted = dev_targets.copy()
                for positions in by_core.values():
                    permuted[positions] = rng.permutation(permuted[positions])
                null_model = helper._fit_ridge(development, full_indices, full_alpha, targets=permuted)
                null_metric = helper._batch_metrics(testing, helper._predict_ridge(null_model, testing), minimum_proteins=minimum_proteins)[0]
                if null_metric["spearman"] is None:
                    raise R4T194FulltextExecutionError("T194 negative-control Spearman is undefined")
                null_value = float(null_metric["spearman"])
                null_values.append(null_value)
                negative_rows.append({"outer_fold_id": fold_id, "held_out_core": held_out, "selected_alpha": full_alpha, "resample": resample, "null_spearman": null_value})
            observed = float(full_metric["spearman"]) if full_metric["spearman"] is not None else None
            if observed is None:
                raise R4T194FulltextExecutionError("T194 full-model primary metric is undefined")
            parameters[fold_id]["negative_control"] = {
                "resamples": int(negative["resamples"]),
                "random_seed": int(negative["random_seed"]) + fold_index,
                "observed_spearman": observed,
                "null_spearman_mean": float(np.mean(null_values)),
                "null_spearman_lower_95": float(np.quantile(null_values, 0.025)),
                "null_spearman_upper_95": float(np.quantile(null_values, 0.975)),
                "one_sided_upper_tail_p": float((1 + sum(value >= observed for value in null_values)) / (1 + len(null_values))),
            }
        cluster_bootstrap: dict[str, Any] = {}
        for model_id in self.MODEL_IDS:
            values = [float(row["mean_spearman"]) for row in fold_metrics if row["model_id"] == model_id and row["mean_spearman"] is not None]
            if values:
                cluster_bootstrap[model_id] = {"cluster_count": len(values), **helper._bootstrap(values, resamples=int(uncertainty["resamples"]), seed=int(uncertainty["random_seed"]))}
            else:
                cluster_bootstrap[model_id] = {
                    "cluster_count": 0,
                    "resamples": int(uncertainty["resamples"]),
                    "seed": int(uncertainty["random_seed"]),
                    "lower_95": None,
                    "upper_95": None,
                    "status": "UNDEFINED_CONSTANT_PREDICTION",
                }
        return {
            "predictions": predictions,
            "batch_metrics": batch_metrics,
            "fold_metrics": fold_metrics,
            "selections": selections,
            "ablations": ablations,
            "negative_rows": negative_rows,
            "parameters": parameters,
            "cluster_bootstrap": cluster_bootstrap,
        }

    def run(self, *, strict: bool = False) -> R4T194FulltextExecutionSummary:
        if not strict:
            raise R4T194FulltextExecutionError("T194 execution requires --strict")
        if self.output_root.exists():
            raise R4T194FulltextExecutionError("T194 execution already exists")
        registry, protocol, refs = self._documents()
        features, targets = self._features_and_targets(refs, protocol)
        observations, ledger, accounting = self._source_observations(refs, features, targets, registry, protocol)
        artifacts = self._execute_models(observations, protocol)
        self.output_root.mkdir(parents=True, exist_ok=False)
        paths = {
            "ledger": self.output_root / "fulltext_core_prefrozen_target_ledger.csv",
            "predictions": self.output_root / "outer_fold_predictions.csv",
            "batch_metrics": self.output_root / "core_batch_metrics.csv",
            "fold_metrics": self.output_root / "outer_fold_metrics.csv",
            "inner_selection": self.output_root / "nested_inner_selection.csv",
            "paired_ablation": self.output_root / "paired_composition_ablation.csv",
            "negative_control": self.output_root / "within_core_rank_permutation.csv",
            "parameters": self.output_root / "outer_fold_model_parameters.json",
        }
        self._write_csv(paths["ledger"], self.LEDGER_FIELDS, ledger)
        self._write_csv(paths["predictions"], ["outer_fold_id", "held_out_core", "model_id", "target_observation_id", "source_id", "canonical_accession", "measurement_batch_id", "observed_rank_percentile_descending", "predicted_rank_percentile_descending"], artifacts["predictions"])
        self._write_csv(paths["batch_metrics"], ["outer_fold_id", "held_out_core", "model_id", "measurement_batch_id", "protein_count", "spearman", "mae", "rmse"], artifacts["batch_metrics"])
        self._write_csv(paths["fold_metrics"], ["outer_fold_id", "held_out_core", "model_id", "held_out_observation_count", "held_out_measurement_batch_count", "primary_metric_status", "mean_spearman", "mean_mae", "mean_rmse"], artifacts["fold_metrics"])
        self._write_csv(paths["inner_selection"], ["outer_fold_id", "held_out_core", "model_id", "alpha", "held_out_inner_batch_id", "spearman", "selected_alpha"], artifacts["selections"])
        self._write_csv(paths["paired_ablation"], ["outer_fold_id", "held_out_core", "paired_measurement_batch_count", "full_minus_composition_spearman"], artifacts["ablations"])
        self._write_csv(paths["negative_control"], ["outer_fold_id", "held_out_core", "selected_alpha", "resample", "null_spearman"], artifacts["negative_rows"])
        self._write_json(paths["parameters"], artifacts["parameters"])
        artifact_manifest = {name: {"relative_path": path.relative_to(self.root).as_posix(), "sha256": _sha256(path)} for name, path in paths.items()}
        report = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "status": self.STATUS,
            "evidence_class": registry["evidence_class"],
            "allowed_claim_level": registry["allowed_claim_level"],
            "input_references": {name: {"relative_path": path.relative_to(self.root).as_posix(), "sha256": _sha256(path)} for name, path in refs.items()},
            "source_semantics": {
                "source_article": "10.1038/s41467-022-34438-8",
                "source_pmcid": "PMC9633814",
                "source_license": "CC-BY-4.0",
                "core_facility_count": len(accounting),
                "biological_unit_count": 1,
                "biological_unit_semantics": "one common pooled human-plasma aliquot; technical core-facility replication",
            },
            "target_universe": {"source": "R3_common_rank_target_ledger", "count": len(targets), "selection_after_outer_split": False},
            "source_accounting": accounting,
            "frozen_cohort": {"observation_count": len(observations), "target_universe_count": len(targets), "core_facility_count": len({row.laboratory_anchor for row in observations}), "measurement_batch_count": len({row.measurement_batch_id for row in observations}), "outer_fold_count": 12, "model_count": len(self.MODEL_IDS)},
            "model_results": artifacts["fold_metrics"],
            "paired_composition_ablation": artifacts["ablations"],
            "core_cluster_bootstrap": artifacts["cluster_bootstrap"],
            "artifacts": artifact_manifest,
            "claim_boundary": protocol["claim_boundary"],
            "independent_validation": False,
            "external_scientific_reproduction": False,
            "external_user_adoption": False,
            "scientific_submission_ready": False,
        }
        report_path = self.output_root / "t194_fulltext_core_facility_execution_report.json"
        self._write_json(report_path, report)
        receipt = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "status": self.STATUS,
            "report_sha256": _sha256(report_path),
            "observation_count": len(observations),
            "target_universe_count": len(targets),
            "core_facility_count": len({row.laboratory_anchor for row in observations}),
            "measurement_batch_count": len({row.measurement_batch_id for row in observations}),
            "outer_fold_count": 12,
            "model_count": len(self.MODEL_IDS),
            "outcome_analysis_run": True,
            "model_fitted": True,
            "independent_validation": False,
            "external_scientific_reproduction": False,
            "scientific_submission_ready": False,
        }
        receipt_path = self.output_root / "t194_fulltext_core_facility_execution_receipt.json"
        self._write_json(receipt_path, receipt)
        return R4T194FulltextExecutionSummary(len(observations), len(targets), len({row.laboratory_anchor for row in observations}), len({row.measurement_batch_id for row in observations}), len(self.MODEL_IDS), receipt_path)

    def verify(self, *, strict: bool = True) -> R4T194FulltextExecutionSummary:
        if not strict:
            raise R4T194FulltextExecutionError("T194 verification requires --strict")
        report_path = self.output_root / "t194_fulltext_core_facility_execution_report.json"
        receipt_path = self.output_root / "t194_fulltext_core_facility_execution_receipt.json"
        report = self._json(report_path, "T194 report")
        receipt = self._json(receipt_path, "T194 receipt")
        artifacts = _mapping(report.get("artifacts"), "T194 artifacts")
        for item in artifacts.values():
            reference = _mapping(item, "T194 artifact")
            if set(reference) != self.REQUIRED_REFERENCE:
                raise R4T194FulltextExecutionError("T194 artifact reference fields are invalid")
            path = self._root_file(_string(reference["relative_path"], "T194 artifact path"), "T194 artifact")
            if _sha256(path) != _checksum(reference["sha256"], "T194 artifact checksum"):
                raise R4T194FulltextExecutionError("T194 artifact checksum differs")
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
            raise R4T194FulltextExecutionError("T194 report or receipt is invalid")
        return R4T194FulltextExecutionSummary(int(receipt["observation_count"]), int(receipt["target_universe_count"]), int(receipt["core_facility_count"]), int(receipt["measurement_batch_count"]), int(receipt["model_count"]), receipt_path)
