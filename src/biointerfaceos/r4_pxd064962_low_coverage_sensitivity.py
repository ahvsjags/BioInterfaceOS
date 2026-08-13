"""Execute the frozen PXD064962 low-coverage sensitivity analysis.

This workflow is deliberately separate from the primary R4 OOD endpoint.  It
uses the public CC0 MaxQuant table only after the R3 feature table, target
ledger and model-selection policy have been verified.  Technical replicates
are ranked separately and then averaged within a labelled patient/timepoint
batch; any protein group mapping to multiple frozen targets is retained in the
source audit but excluded from quantitative target observations. Extra
non-target identifiers are retained when exactly one frozen target is mapped.
"""

from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

import numpy as np

from biointerfaceos.r3_analysis_protocol import R3AnalysisProtocolError, R3AnalysisProtocolWorkflow
from biointerfaceos.r3_model_evaluation import (
    R3ModelEvaluationError,
    R3ModelEvaluationWorkflow,
    _Observation,
)
from biointerfaceos.r3_uniprot_mapping import _canonical, _checksum, _mapping, _sha256, _string
from biointerfaceos.r4_pxd064962_source_audit import (
    R4PXD064962SourceAuditError,
    R4PXD064962SourceAuditWorkflow,
)


class R4PXD064962SensitivityError(RuntimeError):
    """Raised when the frozen PXD064962 sensitivity execution is invalid."""


@dataclass(frozen=True)
class R4PXD064962SensitivitySummary:
    """Compact accounting for the secondary exploratory execution."""

    development_observation_count: int
    external_observation_count: int
    all_eligible_batch_count: int
    low_coverage_batch_count: int
    high_coverage_batch_count: int
    biological_unit_count: int
    shared_positive_target_count: int
    model_count: int
    receipt_path: Path


class R4PXD064962LowCoverageSensitivityWorkflow:
    """Fit on frozen R3 and score source-local ranks in PXD064962."""

    AUDIT_ID = "bioif-r4-pxd064962-low-coverage-sensitivity-v1.0.0"
    STATUS = "R4_PXD064962_LOW_COVERAGE_SENSITIVITY_EXECUTED_EXPLORATORY"
    PROTOCOL_RELATIVE = "docs/data/R4_T188_PXD064962_LOW_COVERAGE_SENSITIVITY_PROTOCOL.json"
    SOURCE_ASSET_RELATIVE = "data/raw/r4_candidate_pxd064962_ucd/proteinGroups.txt"
    OUTPUT_RELATIVE = "reports/review_round_4/pxd064962_low_coverage_sensitivity/v1.0.0"
    REQUIRED_REFERENCE = {"relative_path", "sha256"}
    MODEL_IDS = R3ModelEvaluationWorkflow.MODEL_IDS

    def __init__(self, root: Path, *, output_root: Path | None = None) -> None:
        self.root = root.resolve(strict=True)
        self.protocol_path = self.root / self.PROTOCOL_RELATIVE
        self.output_root = output_root or self.root / self.OUTPUT_RELATIVE

    @staticmethod
    def _json(path: Path, label: str) -> dict[str, Any]:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise R4PXD064962SensitivityError(f"cannot parse {label}") from exc
        try:
            return _mapping(value, label)
        except Exception as exc:
            raise R4PXD064962SensitivityError(f"cannot parse {label}") from exc

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
                writer.writerow(
                    {field: "" if row.get(field) is None else row.get(field) for field in fields}
                )

    def _root_file(self, relative_path: str, label: str) -> Path:
        if "\\" in relative_path:
            raise R4PXD064962SensitivityError(f"{label} must use POSIX separators")
        pure = PurePosixPath(relative_path)
        path = (self.root / Path(*pure.parts)).resolve(strict=False)
        if pure.is_absolute() or not pure.parts or ".." in pure.parts:
            raise R4PXD064962SensitivityError(f"{label} escapes repository root")
        if not path.is_relative_to(self.root) or not path.is_file():
            raise R4PXD064962SensitivityError(f"{label} is missing or outside repository root")
        return path

    def _reference(self, value: Any, label: str) -> Path:
        reference = _mapping(value, label)
        if set(reference) != self.REQUIRED_REFERENCE:
            raise R4PXD064962SensitivityError(f"{label} fields are invalid")
        path = self._root_file(_string(reference.get("relative_path"), label), label)
        if _sha256(path) != _checksum(reference.get("sha256"), label):
            raise R4PXD064962SensitivityError(f"{label} checksum differs")
        return path

    def _protocol(self) -> tuple[dict[str, Any], dict[str, Path]]:
        protocol = self._json(self.protocol_path, "T188 sensitivity protocol")
        expected = {
            "schema_version",
            "protocol_id",
            "status",
            "source_registry",
            "source_accession",
            "license_provenance",
            "estimand",
            "primary_endpoint",
            "references",
            "secondary_endpoint",
            "execution_contract",
            "prohibited_claims",
            "required_receipts",
            "claim_boundary",
        }
        if set(protocol) != expected or protocol.get("schema_version") != 1:
            raise R4PXD064962SensitivityError("T188 protocol fields are invalid")
        if (
            protocol.get("protocol_id") != "bioif-r4-pxd064962-low-coverage-sensitivity-v1.0.0"
            or protocol.get("status") != "FROZEN_SECONDARY_SENSITIVITY_ONLY"
        ):
            raise R4PXD064962SensitivityError("T188 protocol identity is invalid")
        if protocol.get("source_accession") != "PXD064962":
            raise R4PXD064962SensitivityError("T188 source accession is invalid")
        refs = _mapping(protocol["references"], "T188 references")
        expected_refs = {
            "r3_analysis_protocol_receipt",
            "r3_common_target_ledger",
            "r3_sequence_feature_table",
            "source_registry",
            "source_audit_receipt",
            "source_cell_map",
            "source_protein_groups",
            "pride_project_metadata",
        }
        if set(refs) != expected_refs:
            raise R4PXD064962SensitivityError("T188 reference set is invalid")
        paths = {name: self._reference(value, name) for name, value in refs.items()}
        contract = _mapping(protocol["execution_contract"], "T188 execution contract")
        if contract.get("coverage_strata") != {
            "exploratory_minimum": 5,
            "primary_frozen_minimum": 10,
            "expected_all_eligible_batches": 30,
            "expected_batches_5_to_9": 25,
            "expected_batches_at_least_10": 5,
        }:
            raise R4PXD064962SensitivityError("T188 coverage contract is invalid")
        uncertainty = _mapping(contract.get("uncertainty"), "T188 uncertainty")
        if uncertainty != {
            "cluster": "labelled patient/timepoint biological unit",
            "resamples": 2000,
            "random_seed": 1880,
            "interval": "percentile 95% cluster bootstrap",
        }:
            raise R4PXD064962SensitivityError("T188 uncertainty contract is invalid")
        negative = _mapping(contract.get("negative_control"), "T188 negative control")
        if negative != {
            "type": "within-development-batch target permutation",
            "resamples": 256,
            "random_seed": 1881,
            "reselect_alpha_per_resample": True,
            "tail": "one-sided upper tail",
        }:
            raise R4PXD064962SensitivityError("T188 negative-control contract is invalid")
        return protocol, paths

    @staticmethod
    def _number(value: str, label: str) -> float | None:
        if value is None or not value.strip():
            return None
        try:
            number = float(value)
        except ValueError as exc:
            raise R4PXD064962SensitivityError(f"{label} is not numeric") from exc
        if not math.isfinite(number) or number < 0:
            raise R4PXD064962SensitivityError(f"{label} is not finite and non-negative")
        return number

    @staticmethod
    def _rank(values: Sequence[tuple[str, float]]) -> dict[str, float]:
        ordered = sorted(values, key=lambda item: (-item[1], item[0]))
        ranks: dict[str, float] = {}
        start = 0
        while start < len(ordered):
            end = start + 1
            while end < len(ordered) and ordered[end][1] == ordered[start][1]:
                end += 1
            midrank = (start + 1 + end) / 2.0
            percentile = 0.5 if len(ordered) == 1 else (len(ordered) - midrank) / (len(ordered) - 1)
            for coordinate, _ in ordered[start:end]:
                ranks[coordinate] = percentile
            start = end
        return ranks

    def _external_observations(
        self, feature_values: Mapping[str, tuple[float, ...]], protocol: Mapping[str, Any]
    ) -> tuple[
        list[_Observation],
        list[dict[str, Any]],
        dict[str, str],
        dict[str, set[str]],
        dict[str, str],
        list[dict[str, Any]],
    ]:
        source_path = self._root_file(self.SOURCE_ASSET_RELATIVE, "PXD064962 proteinGroups")
        csv.field_size_limit(10**9)
        with source_path.open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream, delimiter="\t")
            if reader.fieldnames is None:
                raise R4PXD064962SensitivityError("PXD064962 proteinGroups header is missing")
            columns = [field for field in reader.fieldnames if field.startswith("LFQ intensity ")]
            rows = list(reader)
        if len(rows) != 405 or len(columns) != 60:
            raise R4PXD064962SensitivityError("PXD064962 table dimensions differ")
        source_audit = R4PXD064962SourceAuditWorkflow(self.root, source_path.parent)
        target_accessions = source_audit._features(
            self._root_file(
                "data/raw/r3_uniprot_sequence_features/uniprot_sequence_features/R3_uniprot_sequence_features.csv",
                "R3 feature table",
            )
        )
        batch_to_unit: dict[str, str] = {}
        batch_target_sets: dict[str, set[str]] = defaultdict(set)
        batch_rank_values: dict[tuple[str, str], list[float]] = defaultdict(list)
        batch_target_coordinates: dict[tuple[str, str], list[str]] = defaultdict(list)
        batch_target_values: dict[tuple[str, str], list[float]] = defaultdict(list)
        batch_target_states: dict[tuple[str, str], dict[str, str]] = defaultdict(dict)
        batch_replicate_ids: dict[str, set[str]] = defaultdict(set)
        for column in columns:
            sample = column.removeprefix("LFQ intensity ")
            sample_info = source_audit._sample_contract(sample)
            batch = sample_info["measurement_batch_id"]
            batch_to_unit[batch] = sample_info["biological_unit_id"]
            replicate_id = sample_info["technical_replicate_id"]
            batch_replicate_ids[batch].add(replicate_id)
            positive_rows: list[tuple[str, float]] = []
            parsed: list[tuple[int, str, float | None, set[str]]] = []
            for row_number, row in enumerate(rows, start=2):
                value = self._number(row.get(column, ""), f"{column}:{row_number}")
                identifiers = {
                    value.strip()
                    for value in row.get("Protein IDs", "").split(";")
                    if value.strip()
                }
                hits = identifiers & target_accessions
                coordinate = f"{column}:{row_number}"
                parsed.append((row_number, coordinate, value, hits))
                if len(hits) == 1:
                    accession = next(iter(hits))
                    state = (
                        "BLANK"
                        if value is None
                        else ("ZERO" if value == 0 else ("POSITIVE" if value > 0 else "NONFINITE"))
                    )
                    batch_target_states[(batch, accession)][replicate_id] = state
                if value is not None and value > 0:
                    positive_rows.append((coordinate, value))
            ranks = self._rank(positive_rows)
            for _row_number, coordinate, value, hits in parsed:
                if value is None or value <= 0 or len(hits) != 1:
                    continue
                accession = next(iter(hits))
                rank = ranks[coordinate]
                key = (batch, accession)
                batch_rank_values[key].append(rank)
                batch_target_coordinates[key].append(coordinate)
                batch_target_values[key].append(value)
                batch_target_sets[batch].add(accession)
        counts = sorted(len(batch_target_sets[batch]) for batch in batch_to_unit)
        contract = _mapping(protocol["execution_contract"], "T188 execution contract")
        strata = _mapping(contract["coverage_strata"], "T188 coverage strata")
        if (
            len(batch_to_unit) != strata["expected_all_eligible_batches"]
            or counts.count(13) != 1
            or sum(count >= strata["primary_frozen_minimum"] for count in counts)
            != strata["expected_batches_at_least_10"]
            or sum(5 <= count < 10 for count in counts) != strata["expected_batches_5_to_9"]
        ):
            raise R4PXD064962SensitivityError("T188 source coverage accounting differs")
        eligible = {
            batch
            for batch in batch_to_unit
            if len(batch_target_sets[batch]) >= strata["exploratory_minimum"]
        }
        high = {
            batch
            for batch in eligible
            if len(batch_target_sets[batch]) >= strata["primary_frozen_minimum"]
        }
        observations: list[_Observation] = []
        target_rows: list[dict[str, Any]] = []
        replicate_qc_rows: list[dict[str, Any]] = []
        for batch in sorted(batch_to_unit):
            target_keys = sorted(
                key for key in batch_target_states if key[0] == batch
                and any(state == "POSITIVE" for state in batch_target_states[key].values())
            )
            concordant_positive = 0
            positive_zero_discordant = 0
            positive_blank_discordant = 0
            positive_nonpositive_discordant = 0
            one_positive = 0
            for key in target_keys:
                states = list(batch_target_states[key].values())
                positive_count = states.count("POSITIVE")
                if positive_count == 2:
                    concordant_positive += 1
                elif positive_count == 1:
                    one_positive += 1
                    if "ZERO" in states:
                        positive_zero_discordant += 1
                    if "BLANK" in states:
                        positive_blank_discordant += 1
                    if any(state not in {"POSITIVE", "ZERO", "BLANK"} for state in states):
                        positive_nonpositive_discordant += 1
            replicate_qc_rows.append(
                {
                    "measurement_batch_id": batch,
                    "biological_unit_id": batch_to_unit[batch],
                    "technical_column_count": len(batch_replicate_ids[batch]),
                    "target_pairs_with_any_positive": len(target_keys),
                    "target_pairs_two_positive_replicates": concordant_positive,
                    "target_pairs_one_positive_replicate": one_positive,
                    "positive_zero_discordance_count": positive_zero_discordant,
                    "positive_blank_discordance_count": positive_blank_discordant,
                    "positive_nonpositive_discordance_count": positive_nonpositive_discordant,
                    "positive_replicate_concordance_fraction": (
                        None if not target_keys else concordant_positive / len(target_keys)
                    ),
                }
            )
        for batch in sorted(eligible):
            for accession in sorted(batch_target_sets[batch]):
                key = (batch, accession)
                ranks = batch_rank_values[key]
                if accession not in feature_values or not ranks:
                    continue
                target_id = f"R4PXD064962:{batch}:{accession}"
                rank = float(np.mean(ranks))
                observations.append(
                    _Observation(
                        target_id,
                        "PXD064962_UCD_EVENT",
                        accession,
                        "University College Dublin / Conway Institute",
                        batch,
                        rank,
                        feature_values[accession],
                    )
                )
                target_rows.append(
                    {
                        "external_target_observation_id": target_id,
                        "source_id": "PXD064962_UCD_EVENT",
                        "laboratory_anchor": "University College Dublin / Conway Institute",
                        "canonical_accession": accession,
                        "biological_unit_id": batch_to_unit[batch],
                        "measurement_batch_id": batch,
                        "technical_replicate_count": len(ranks),
                        "source_coordinates": ";".join(batch_target_coordinates[key]),
                        "author_positive_values": ";".join(
                            repr(value) for value in batch_target_values[key]
                        ),
                        "rank_percentile_mean_across_positive_technical_replicates": rank,
                        "measurement_batch_positive_unique_target_count": len(
                            batch_target_sets[batch]
                        ),
                        "coverage_stratum": "GE10" if batch in high else "GE5_LT10",
                    }
                )
        if len(observations) != 259 or len({row.canonical_accession for row in observations}) != 15:
            raise R4PXD064962SensitivityError("T188 external observation accounting differs")
        return (
            observations,
            target_rows,
            batch_to_unit,
            batch_target_sets,
            {batch: ("GE10" if batch in high else "GE5_LT10") for batch in eligible},
            replicate_qc_rows,
        )

    @staticmethod
    def _cluster_metrics(
        metrics: Sequence[Mapping[str, Any]], batch_to_unit: Mapping[str, str]
    ) -> tuple[dict[str, float | None], dict[str, dict[str, float | None]]]:
        by_unit: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
        for metric in metrics:
            by_unit[batch_to_unit[str(metric["measurement_batch_id"])]].append(metric)
        unit_rows: dict[str, dict[str, float | None]] = {}
        for unit, unit_metrics in sorted(by_unit.items()):
            unit_rows[unit] = {
                name: None
                if any(item[name] is None for item in unit_metrics)
                else float(np.mean([float(item[name]) for item in unit_metrics]))
                for name in ("spearman", "mae", "rmse")
            }
        aggregate: dict[str, float | None] = {}
        for name in ("spearman", "mae", "rmse"):
            values = [row[name] for row in unit_rows.values()]
            aggregate[f"subject_equal_mean_{name}"] = (
                None
                if any(value is None for value in values)
                else float(np.mean([float(value) for value in values]))
            )
        aggregate["biological_unit_count"] = float(len(unit_rows))
        aggregate["measurement_batch_count"] = float(len(metrics))
        aggregate["batch_weighted_mean_spearman"] = (
            None
            if any(item["spearman"] is None for item in metrics)
            else float(np.mean([float(item["spearman"]) for item in metrics]))
        )
        return aggregate, unit_rows

    @staticmethod
    def _cluster_bootstrap(
        unit_rows: Mapping[str, Mapping[str, float | None]],
        metric: str,
        *,
        resamples: int,
        seed: int,
    ) -> dict[str, float | int] | None:
        values = [row[metric] for row in unit_rows.values()]
        if not values or any(value is None for value in values):
            return None
        array = np.asarray([float(value) for value in values], dtype=float)
        rng = np.random.default_rng(seed)
        means = array[rng.integers(0, len(array), size=(resamples, len(array)))].mean(axis=1)
        interval = np.quantile(means, [0.025, 0.975], method="linear")
        return {
            "resamples": resamples,
            "seed": seed,
            "lower_95": float(interval[0]),
            "upper_95": float(interval[1]),
        }

    def run(self, *, strict: bool = False) -> R4PXD064962SensitivitySummary:
        if not strict:
            raise R4PXD064962SensitivityError("T188 sensitivity execution requires --strict")
        if self.output_root.exists():
            raise R4PXD064962SensitivityError("T188 sensitivity output already exists")
        protocol, paths = self._protocol()
        try:
            R3AnalysisProtocolWorkflow(self.root, self.root / "data/raw").verify()
            R4PXD064962SourceAuditWorkflow(
                self.root, self.root / "data/raw/r4_candidate_pxd064962_ucd"
            ).verify()
        except (R3AnalysisProtocolError, R4PXD064962SourceAuditError, OSError) as exc:
            raise R4PXD064962SensitivityError("frozen T188 or R3 inputs do not verify") from exc
        helper = R3ModelEvaluationWorkflow(
            self.root, self.root / "data/raw", self.root / "data/raw/r3_uniprot_sequence_features"
        )
        try:
            development, development_accessions = helper._observations(
                paths["r3_common_target_ledger"], paths["r3_sequence_feature_table"]
            )
        except R3ModelEvaluationError as exc:
            raise R4PXD064962SensitivityError("frozen R3 development data is invalid") from exc
        if len(development) != 2724 or len(development_accessions) != 99:
            raise R4PXD064962SensitivityError("frozen R3 development accounting differs")
        feature_values = {row.canonical_accession: row.feature_values for row in development}
        external, target_rows, batch_to_unit, batch_targets, strata_by_batch, replicate_qc_rows = (
            self._external_observations(feature_values, protocol)
        )
        all_batches = set(strata_by_batch)
        high_batches = {batch for batch, stratum in strata_by_batch.items() if stratum == "GE10"}
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
        uncertainty = _mapping(protocol["execution_contract"], "T188 execution contract")[
            "uncertainty"
        ]
        model_rows: list[dict[str, Any]] = []
        batch_rows: list[dict[str, Any]] = []
        unit_rows_output: list[dict[str, Any]] = []
        prediction_rows: list[dict[str, Any]] = []
        metrics_by_key: dict[tuple[str, str, str], dict[str, Any]] = {}
        for model_index, model_id in enumerate(helper.MODEL_IDS, start=1):
            for stratum_id, batches, minimum in (
                ("GE5_ALL", all_batches, 5),
                ("GE10_ONLY", high_batches, 10),
            ):
                indices = [
                    index
                    for index, row in enumerate(external)
                    if row.measurement_batch_id in batches
                ]
                subset = [external[index] for index in indices]
                subset_predictions = predictions[model_id][indices]
                metrics = helper._batch_metrics(
                    subset, subset_predictions, minimum_proteins=minimum
                )
                aggregate, units = self._cluster_metrics(metrics, batch_to_unit)
                spearman_ci = self._cluster_bootstrap(
                    units,
                    "spearman",
                    resamples=uncertainty["resamples"],
                    seed=uncertainty["random_seed"]
                    + model_index * 100
                    + (0 if stratum_id == "GE5_ALL" else 10),
                )
                mae_ci = self._cluster_bootstrap(
                    units,
                    "mae",
                    resamples=uncertainty["resamples"],
                    seed=uncertainty["random_seed"]
                    + model_index * 100
                    + 1
                    + (0 if stratum_id == "GE5_ALL" else 10),
                )
                rmse_ci = self._cluster_bootstrap(
                    units,
                    "rmse",
                    resamples=uncertainty["resamples"],
                    seed=uncertainty["random_seed"]
                    + model_index * 100
                    + 2
                    + (0 if stratum_id == "GE5_ALL" else 10),
                )
                model_rows.append(
                    {
                        "stratum_id": stratum_id,
                        "model_id": model_id,
                        "external_observation_count": len(subset),
                        "external_measurement_batch_count": len(metrics),
                        "biological_unit_count": int(aggregate["biological_unit_count"]),
                        "primary_metric_status": "UNDEFINED_CONSTANT_PREDICTION"
                        if model_id == "CONSTANT_TRAINING_MEAN"
                        else "DEFINED",
                        **aggregate,
                        "subject_equal_mean_spearman_lower_95": None
                        if spearman_ci is None
                        else spearman_ci["lower_95"],
                        "subject_equal_mean_spearman_upper_95": None
                        if spearman_ci is None
                        else spearman_ci["upper_95"],
                        "subject_equal_mean_mae_lower_95": None
                        if mae_ci is None
                        else mae_ci["lower_95"],
                        "subject_equal_mean_mae_upper_95": None
                        if mae_ci is None
                        else mae_ci["upper_95"],
                        "subject_equal_mean_rmse_lower_95": None
                        if rmse_ci is None
                        else rmse_ci["lower_95"],
                        "subject_equal_mean_rmse_upper_95": None
                        if rmse_ci is None
                        else rmse_ci["upper_95"],
                    }
                )
                for metric in metrics:
                    metrics_by_key[(stratum_id, model_id, metric["measurement_batch_id"])] = metric
                    batch_rows.append(
                        {
                            "stratum_id": stratum_id,
                            "model_id": model_id,
                            "biological_unit_id": batch_to_unit[metric["measurement_batch_id"]],
                            **metric,
                        }
                    )
                for unit, metric in units.items():
                    unit_rows_output.append(
                        {
                            "stratum_id": stratum_id,
                            "model_id": model_id,
                            "biological_unit_id": unit,
                            **metric,
                        }
                    )
            for observation, prediction in zip(external, predictions[model_id], strict=True):
                prediction_rows.append(
                    {
                        "model_id": model_id,
                        "external_target_observation_id": observation.target_observation_id,
                        "canonical_accession": observation.canonical_accession,
                        "measurement_batch_id": observation.measurement_batch_id,
                        "biological_unit_id": batch_to_unit[observation.measurement_batch_id],
                        "coverage_stratum": strata_by_batch[observation.measurement_batch_id],
                        "observed_rank_percentile_descending": observation.target,
                        "predicted_rank_percentile_descending": float(prediction),
                    }
                )
        paired_rows: list[dict[str, Any]] = []
        paired_by_stratum: dict[str, dict[str, float]] = {}
        for stratum_id, batches in (("GE5_ALL", all_batches), ("GE10_ONLY", high_batches)):
            deltas_by_unit: dict[str, list[float]] = defaultdict(list)
            for batch in sorted(batches):
                full = metrics_by_key[(stratum_id, "SEQUENCE_RIDGE_FULL", batch)]["spearman"]
                composition = metrics_by_key[
                    (stratum_id, "SEQUENCE_RIDGE_COMPOSITION_ONLY", batch)
                ]["spearman"]
                if full is None or composition is None:
                    raise R4PXD064962SensitivityError("T188 paired ablation has undefined Spearman")
                deltas_by_unit[batch_to_unit[batch]].append(float(full) - float(composition))
            unit_values = {unit: float(np.mean(values)) for unit, values in deltas_by_unit.items()}
            delta = float(np.mean(list(unit_values.values())))
            ci = helper._bootstrap(
                list(unit_values.values()),
                resamples=uncertainty["resamples"],
                seed=uncertainty["random_seed"] + (701 if stratum_id == "GE5_ALL" else 702),
            )
            paired_by_stratum[stratum_id] = {
                "full_minus_composition_subject_equal_mean_spearman": delta,
                **ci,
            }
            paired_rows.append(
                {
                    "stratum_id": stratum_id,
                    "paired_measurement_batch_count": len(batches),
                    "paired_biological_unit_count": len(unit_values),
                    **paired_by_stratum[stratum_id],
                }
            )
        negative_contract = _mapping(
            _mapping(protocol["execution_contract"], "T188 execution contract")["negative_control"],
            "T188 negative control",
        )
        observed_targets = np.asarray([row.target for row in development], dtype=float)
        by_development_batch: dict[str, list[int]] = defaultdict(list)
        for index, observation in enumerate(development):
            by_development_batch[observation.measurement_batch_id].append(index)
        rng = np.random.default_rng(negative_contract["random_seed"])
        null_scores: list[float] = []
        null_rows: list[dict[str, Any]] = []
        for resample in range(1, negative_contract["resamples"] + 1):
            permuted = observed_targets.copy()
            for indices in by_development_batch.values():
                permuted[indices] = rng.permutation(permuted[indices])
            permuted_development = [
                _Observation(
                    row.target_observation_id,
                    row.source_id,
                    row.canonical_accession,
                    row.laboratory_anchor,
                    row.measurement_batch_id,
                    float(target),
                    row.feature_values,
                )
                for row, target in zip(development, permuted, strict=True)
            ]
            permuted_alpha, _ = helper._select_alpha(
                permuted_development, full_indices, minimum_proteins=10
            )
            null_model = helper._fit_ridge(
                permuted_development, full_indices, permuted_alpha, targets=permuted
            )
            null_predictions = helper._predict_ridge(null_model, external)
            null_metrics = helper._batch_metrics(external, null_predictions, minimum_proteins=5)
            null_aggregate, _ = self._cluster_metrics(null_metrics, batch_to_unit)
            null_score = null_aggregate["subject_equal_mean_spearman"]
            if null_score is None:
                raise R4PXD064962SensitivityError("T188 negative-control metric is undefined")
            null_scores.append(float(null_score))
            null_rows.append(
                {
                    "resample": resample,
                    "selected_alpha": permuted_alpha,
                    "null_subject_equal_mean_spearman": float(null_score),
                }
            )
        observed_primary = next(
            row["subject_equal_mean_spearman"]
            for row in model_rows
            if row["stratum_id"] == "GE5_ALL" and row["model_id"] == "SEQUENCE_RIDGE_FULL"
        )
        negative_summary = {
            "observed_subject_equal_mean_spearman": observed_primary,
            "null_mean": float(np.mean(null_scores)),
            "null_lower_95": float(np.quantile(null_scores, 0.025)),
            "null_upper_95": float(np.quantile(null_scores, 0.975)),
            "one_sided_upper_tail_p": float(
                (1 + sum(value >= observed_primary for value in null_scores))
                / (1 + len(null_scores))
            ),
            "resamples": negative_contract["resamples"],
            "random_seed": negative_contract["random_seed"],
            "selection_reexecuted_per_resample": True,
            "statistic": "subject_equal_mean_spearman_over_30_labelled_patient_timepoint_units",
        }
        output = self.output_root
        output.mkdir(parents=True, exist_ok=False)
        artifact_paths = {
            "external_target_ledger": output / "r4_pxd064962_rank_target_ledger.csv",
            "predictions": output / "r4_pxd064962_sensitivity_predictions.csv",
            "batch_metrics": output / "r4_pxd064962_sensitivity_batch_metrics.csv",
            "biological_unit_metrics": output
            / "r4_pxd064962_sensitivity_biological_unit_metrics.csv",
            "model_metrics": output / "r4_pxd064962_sensitivity_model_metrics.csv",
            "selection": output / "r4_pxd064962_sensitivity_nested_selection.csv",
            "negative_control": output / "r4_pxd064962_sensitivity_within_batch_permutation.csv",
            "parameters": output / "r4_pxd064962_sensitivity_model_parameters.json",
            "technical_replicate_qc": output / "r4_pxd064962_technical_replicate_qc.csv",
        }
        self._write_csv(artifact_paths["external_target_ledger"], list(target_rows[0]), target_rows)
        self._write_csv(artifact_paths["predictions"], list(prediction_rows[0]), prediction_rows)
        self._write_csv(artifact_paths["batch_metrics"], list(batch_rows[0]), batch_rows)
        self._write_csv(
            artifact_paths["biological_unit_metrics"], list(unit_rows_output[0]), unit_rows_output
        )
        self._write_csv(artifact_paths["model_metrics"], list(model_rows[0]), model_rows)
        selection_rows = [
            {"model_id": "SEQUENCE_RIDGE_FULL", **row, "selected_alpha": full_alpha}
            for row in full_selection
        ] + [
            {
                "model_id": "SEQUENCE_RIDGE_COMPOSITION_ONLY",
                **row,
                "selected_alpha": composition_alpha,
            }
            for row in composition_selection
        ]
        self._write_csv(artifact_paths["selection"], list(selection_rows[0]), selection_rows)
        self._write_csv(artifact_paths["negative_control"], list(null_rows[0]), null_rows)
        self._write_csv(
            artifact_paths["technical_replicate_qc"],
            list(replicate_qc_rows[0]),
            replicate_qc_rows,
        )
        self._write_json(
            artifact_paths["parameters"],
            {
                "development_observation_count": len(development),
                "external_observation_count": len(external),
                "all_eligible_batch_count": len(all_batches),
                "high_coverage_batch_count": len(high_batches),
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
            for name, path in artifact_paths.items()
        }
        report = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "protocol_id": protocol["protocol_id"],
            "protocol_sha256": _sha256(self.protocol_path),
            "status": self.STATUS,
            "evidence_class": "EXPLORATORY_SENSITIVITY",
            "allowed_claim_level": "EXPLORATORY",
            "development_observation_count": len(development),
            "development_canonical_protein_count": len(development_accessions),
            "external_observation_count": len(external),
            "external_shared_positive_target_count": len(
                {row.canonical_accession for row in external}
            ),
            "all_eligible_batch_count": len(all_batches),
            "low_coverage_batch_count": len(all_batches - high_batches),
            "high_coverage_batch_count": len(high_batches),
            "biological_unit_count": len(set(batch_to_unit.values())),
            "technical_replicates_per_batch": 2,
            "model_results": model_rows,
            "paired_composition_ablation": paired_rows,
            "negative_control_summary": negative_summary,
            "technical_replicate_qc_summary": {
                "batch_count": len(replicate_qc_rows),
                "target_pairs_with_any_positive": sum(
                    row["target_pairs_with_any_positive"] for row in replicate_qc_rows
                ),
                "target_pairs_two_positive_replicates": sum(
                    row["target_pairs_two_positive_replicates"] for row in replicate_qc_rows
                ),
                "target_pairs_one_positive_replicate": sum(
                    row["target_pairs_one_positive_replicate"] for row in replicate_qc_rows
                ),
                "positive_zero_discordance_count": sum(
                    row["positive_zero_discordance_count"] for row in replicate_qc_rows
                ),
                "positive_blank_discordance_count": sum(
                    row["positive_blank_discordance_count"] for row in replicate_qc_rows
                ),
                "positive_nonpositive_discordance_count": sum(
                    row["positive_nonpositive_discordance_count"] for row in replicate_qc_rows
                ),
            },
            "artifacts": artifacts,
            "claim_boundary": protocol["claim_boundary"],
            "model_fitted": True,
            "independent_validation": False,
            "external_scientific_reproduction": False,
            "scientific_submission_ready": False,
            "primary_ood_minimum_met": False,
        }
        report_path = output / "r4_pxd064962_low_coverage_sensitivity_report.json"
        self._write_json(report_path, report)
        receipt = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "status": self.STATUS,
            "report_sha256": _sha256(report_path),
            "protocol_sha256": _sha256(self.protocol_path),
            "development_observation_count": len(development),
            "external_observation_count": len(external),
            "all_eligible_batch_count": len(all_batches),
            "low_coverage_batch_count": len(all_batches - high_batches),
            "high_coverage_batch_count": len(high_batches),
            "biological_unit_count": len(set(batch_to_unit.values())),
            "model_count": len(helper.MODEL_IDS),
            "model_fitted": True,
            "independent_validation": False,
            "external_scientific_reproduction": False,
            "scientific_submission_ready": False,
            "primary_ood_minimum_met": False,
        }
        receipt_path = output / "r4_pxd064962_low_coverage_sensitivity_receipt.json"
        self._write_json(receipt_path, receipt)
        return R4PXD064962SensitivitySummary(
            len(development),
            len(external),
            len(all_batches),
            len(all_batches - high_batches),
            len(high_batches),
            len(set(batch_to_unit.values())),
            len({row.canonical_accession for row in external}),
            len(helper.MODEL_IDS),
            receipt_path,
        )

    def verify(self) -> R4PXD064962SensitivitySummary:
        protocol, _ = self._protocol()
        output = self.output_root
        report_path = output / "r4_pxd064962_low_coverage_sensitivity_report.json"
        receipt_path = output / "r4_pxd064962_low_coverage_sensitivity_receipt.json"
        report = self._json(report_path, "T188 sensitivity report")
        receipt = self._json(receipt_path, "T188 sensitivity receipt")
        artifacts = _mapping(report.get("artifacts"), "T188 sensitivity artifacts")
        for value in artifacts.values():
            item = _mapping(value, "T188 sensitivity artifact")
            path = self._root_file(_string(item.get("relative_path"), "artifact path"), "artifact")
            if _sha256(path) != _checksum(item.get("sha256"), "artifact checksum"):
                raise R4PXD064962SensitivityError("T188 sensitivity artifact checksum differs")
        if (
            report.get("audit_id") != self.AUDIT_ID
            or report.get("protocol_id") != protocol["protocol_id"]
            or report.get("protocol_sha256") != _sha256(self.protocol_path)
            or report.get("status") != self.STATUS
            or receipt.get("audit_id") != self.AUDIT_ID
            or receipt.get("status") != self.STATUS
            or receipt.get("report_sha256") != _sha256(report_path)
            or receipt.get("protocol_sha256") != _sha256(self.protocol_path)
            or receipt.get("model_fitted") is not True
            or receipt.get("independent_validation") is not False
            or receipt.get("external_scientific_reproduction") is not False
            or receipt.get("scientific_submission_ready") is not False
            or receipt.get("primary_ood_minimum_met") is not False
        ):
            raise R4PXD064962SensitivityError("T188 sensitivity receipt is invalid")
        return R4PXD064962SensitivitySummary(
            int(receipt["development_observation_count"]),
            int(receipt["external_observation_count"]),
            int(receipt["all_eligible_batch_count"]),
            int(receipt["low_coverage_batch_count"]),
            int(receipt["high_coverage_batch_count"]),
            int(receipt["biological_unit_count"]),
            int(report["external_shared_positive_target_count"]),
            int(receipt["model_count"]),
            receipt_path,
        )
