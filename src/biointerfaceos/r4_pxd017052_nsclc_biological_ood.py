"""Execute the frozen exploratory OOD analysis on the 141-subject cohort."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

import numpy as np

from biointerfaceos.r3_analysis_protocol import R3AnalysisProtocolError, R3AnalysisProtocolWorkflow
from biointerfaceos.r3_model_evaluation import R3ModelEvaluationError, R3ModelEvaluationWorkflow, _Observation
from biointerfaceos.r3_uniprot_mapping import _canonical, _checksum, _mapping, _sha256, _string
from biointerfaceos.r4_pxd017052_nsclc_source_audit import (
    R4PXD017052NSCLCSourceAuditError,
    R4PXD017052NSCLCSourceAuditWorkflow,
)


class R4PXD017052NSCLCBOODError(RuntimeError):
    """Raised when the frozen biological-cohort OOD cannot run safely."""


@dataclass(frozen=True)
class R4PXD017052NSCLCBOODSummary:
    development_observation_count: int
    external_observation_count: int
    external_shared_canonical_protein_count: int
    external_measurement_batch_count: int
    biological_unit_count: int
    model_count: int
    receipt_path: Path


class R4PXD017052NSCLCBOODWorkflow:
    """Fit only on frozen R3 and score source-local ranks for 141 subjects."""

    AUDIT_ID = "bioif-r4-pxd017052-nsclc-biological-ood-v1.0.0"
    PROTOCOL_RELATIVE = "docs/data/R4_T181_PXD017052_NSCLC_BIOLOGICAL_OOD_PROTOCOL.json"
    OUTPUT_RELATIVE = "reports/review_round_4/pxd017052_nsclc_biological_ood/v1.0.0"
    STATUS = "R4_BIOLOGICAL_COHORT_OOD_EXECUTED_EXPLORATORY"
    REQUIRED_REFERENCE = {"relative_path", "sha256"}

    def __init__(self, root: Path, output_data_root: Path, feature_root: Path, source_assets_root: Path, *, protocol_path: Path | None = None, output_root: Path | None = None) -> None:
        self.root = root.resolve(strict=True)
        self.output_data_root = output_data_root.resolve(strict=False)
        self.feature_root = feature_root.resolve(strict=False)
        self.source_assets_root = source_assets_root.resolve(strict=False)
        self.protocol_path = protocol_path or self.root / self.PROTOCOL_RELATIVE
        self.output_root = output_root or self.root / self.OUTPUT_RELATIVE

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
            return _mapping(json.loads(path.read_text(encoding="utf-8")), label)
        except (OSError, UnicodeError, json.JSONDecodeError, TypeError) as exc:
            raise R4PXD017052NSCLCBOODError(f"cannot parse {label}") from exc

    def _root_file(self, relative_path: str, label: str) -> Path:
        if "\\" in relative_path:
            raise R4PXD017052NSCLCBOODError(f"{label} must use POSIX separators")
        pure = PurePosixPath(relative_path)
        path = (self.root / Path(*pure.parts)).resolve(strict=False)
        if pure.is_absolute() or not pure.parts or ".." in pure.parts or not path.is_relative_to(self.root) or not path.is_file():
            raise R4PXD017052NSCLCBOODError(f"{label} is missing or escapes repository root")
        return path

    def _reference(self, value: Any, label: str) -> Path:
        item = _mapping(value, label)
        if set(item) != self.REQUIRED_REFERENCE:
            raise R4PXD017052NSCLCBOODError(f"{label} fields are invalid")
        path = self._root_file(_string(item.get("relative_path"), label), label)
        if _sha256(path) != _checksum(item.get("sha256"), label):
            raise R4PXD017052NSCLCBOODError(f"{label} checksum differs")
        return path

    def _protocol(self) -> tuple[dict[str, Any], dict[str, Path]]:
        protocol = self._json(self.protocol_path, "PXD017052 NSCLC biological OOD protocol")
        expected = {"schema_version", "protocol_id", "frozen_at", "evidence_class", "allowed_claim_level", "references", "target", "development_selection", "external_evaluation", "feature_policy", "models", "metrics", "uncertainty", "negative_control", "claim_boundary"}
        if set(protocol) != expected or protocol.get("schema_version") != 1 or protocol.get("protocol_id") != "bioif-r4-pxd017052-nsclc-biological-ood-protocol-v1.0.0" or protocol.get("evidence_class") != "DEVELOPMENT_OBSERVATION" or protocol.get("allowed_claim_level") != "EXPLORATORY":
            raise R4PXD017052NSCLCBOODError("biological OOD protocol identity is invalid")
        refs = _mapping(protocol.get("references"), "biological OOD references")
        if set(refs) != {"r3_analysis_protocol_receipt", "r3_common_target_ledger", "r3_sequence_feature_table", "r4_source_audit_receipt", "r4_source_cell_map"}:
            raise R4PXD017052NSCLCBOODError("biological OOD references are invalid")
        paths = {key: self._reference(value, key) for key, value in refs.items()}
        if self.output_data_root != (self.root / "data/raw").resolve(strict=False) or self.feature_root != (self.root / "data/raw/r3_uniprot_sequence_features").resolve(strict=False) or self.source_assets_root != (self.root / "data/raw/r4_candidate_pxd017052_nsclc").resolve(strict=False):
            raise R4PXD017052NSCLCBOODError("biological OOD requires fixed repository roots")
        external = _mapping(protocol.get("external_evaluation"), "biological external evaluation")
        required_external = {"source_id": "PXD017052_SEER_BROAD_NSCLC_COHORT", "laboratory_anchor": "Seer, Inc. / Broad Institute of MIT and Harvard", "biological_unit": "individual subject plasma sample identified by the first header token", "measurement_role": "NP_CORONA only; depleted plasma columns excluded", "expected_biological_unit_count": 141, "expected_measurement_batch_count": 705, "expected_rank_qualified_measurement_batch_count": 666, "expected_external_observation_count": 17026, "expected_shared_canonical_protein_count": 34, "minimum_proteins_per_measurement_batch": 10, "access_condition": "paper-attached CC-BY-4.0 Supplementary Data 5; author-run exploratory cohort OOD; not a protected lockbox and not an independent evaluator"}
        if external != required_external:
            raise R4PXD017052NSCLCBOODError("biological external evaluation contract is invalid")
        return protocol, paths

    @staticmethod
    def _read_csv(path: Path, label: str) -> list[dict[str, str]]:
        try:
            with path.open("r", encoding="utf-8", newline="") as stream:
                rows = list(csv.DictReader(stream))
        except OSError as exc:
            raise R4PXD017052NSCLCBOODError(f"cannot read {label}") from exc
        if not rows or not rows[0]:
            raise R4PXD017052NSCLCBOODError(f"{label} is empty")
        return rows

    @staticmethod
    def _rank_percentiles(rows: Sequence[Mapping[str, str]]) -> dict[str, tuple[float, int]]:
        grouped: dict[str, list[Mapping[str, str]]] = defaultdict(list)
        for row in rows:
            if row.get("rank_target_eligible") == "true":
                grouped[_string(row.get("measurement_batch_id"), "measurement batch")].append(row)
        ranks: dict[str, tuple[float, int]] = {}
        for batch_id, batch_rows in grouped.items():
            ordered = sorted(batch_rows, key=lambda row: (-float(row["author_numeric_value"]), row["source_coordinate"]))
            count = len(ordered)
            start = 0
            while start < count:
                end = start + 1
                while end < count and float(ordered[end]["author_numeric_value"]) == float(ordered[start]["author_numeric_value"]):
                    end += 1
                midrank = (start + 1 + end) / 2.0
                percentile = 0.5 if count == 1 else (count - midrank) / (count - 1)
                for row in ordered[start:end]:
                    identity = f"{batch_id}:{row['source_coordinate']}"
                    if identity in ranks:
                        raise R4PXD017052NSCLCBOODError("external rank identity is duplicated")
                    ranks[identity] = (percentile, count)
                start = end
        return ranks

    def _external_observations(self, source_map_path: Path, feature_values: Mapping[str, tuple[float, ...]], protocol: Mapping[str, Any]) -> tuple[list[_Observation], list[dict[str, Any]], set[str], dict[str, str]]:
        rows = self._read_csv(source_map_path, "PXD017052 NSCLC source cell map")
        required = {"source_id", "laboratory_anchor", "source_worksheet", "source_row", "source_coordinate", "canonical_accession", "biological_unit_id", "measurement_batch_id", "author_quantity_type", "author_numeric_value", "rank_target_eligible"}
        if not required.issubset(rows[0]):
            raise R4PXD017052NSCLCBOODError("biological source cell map schema is invalid")
        external = protocol["external_evaluation"]
        if any(row.get("source_id") != external["source_id"] or row.get("laboratory_anchor") != external["laboratory_anchor"] for row in rows):
            raise R4PXD017052NSCLCBOODError("biological source map identity differs")
        ranks = self._rank_percentiles(rows)
        batch_to_unit = {row["measurement_batch_id"]: row["biological_unit_id"] for row in rows}
        if len(batch_to_unit) != 705 or len(set(batch_to_unit.values())) != 141:
            raise R4PXD017052NSCLCBOODError("biological unit accounting differs")
        positive_by_batch = defaultdict(int)
        for row in rows:
            if row["rank_target_eligible"] == "true":
                positive_by_batch[row["measurement_batch_id"]] += 1
        qualified = {batch for batch, count in positive_by_batch.items() if count >= external["minimum_proteins_per_measurement_batch"]}
        if len(qualified) != 666:
            raise R4PXD017052NSCLCBOODError("qualified batch accounting differs")
        observations: list[_Observation] = []
        target_rows: list[dict[str, Any]] = []
        accessions: set[str] = set()
        for row in rows:
            batch_id = row["measurement_batch_id"]
            rank = ranks.get(f"{batch_id}:{row['source_coordinate']}")
            accession = row["canonical_accession"]
            if batch_id not in qualified or rank is None or accession not in feature_values:
                continue
            percentile, positive_count = rank
            target_id = f"R4PXD017052NSCLC:{row['source_row']}:{row['source_coordinate']}:{batch_id}"
            observations.append(_Observation(target_id, external["source_id"], accession, external["laboratory_anchor"], batch_id, percentile, feature_values[accession]))
            target_rows.append({"external_target_observation_id": target_id, "source_id": external["source_id"], "laboratory_anchor": external["laboratory_anchor"], "canonical_accession": accession, "biological_unit_id": row["biological_unit_id"], "clinical_group": row["clinical_group"], "particle": row["particle"], "measurement_batch_id": batch_id, "source_worksheet": row["source_worksheet"], "source_row": row["source_row"], "source_coordinate": row["source_coordinate"], "author_quantity_type": row["author_quantity_type"], "author_numeric_value": float(row["author_numeric_value"]), "rank_percentile_descending": percentile, "measurement_batch_positive_protein_count": positive_count})
            accessions.add(accession)
        if len(observations) != 17026 or len(accessions) != 34:
            raise R4PXD017052NSCLCBOODError("external observation accounting differs")
        return observations, target_rows, accessions, batch_to_unit

    @staticmethod
    def _subject_metrics(metrics: Sequence[Mapping[str, Any]], batch_to_unit: Mapping[str, str]) -> tuple[dict[str, float | None], dict[str, dict[str, float | None]]]:
        by_unit: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
        for metric in metrics:
            by_unit[batch_to_unit[str(metric["measurement_batch_id"])]].append(metric)
        rows: dict[str, dict[str, float | None]] = {}
        for unit, unit_metrics in sorted(by_unit.items()):
            rows[unit] = {name: (None if any(item[name] is None for item in unit_metrics) else float(np.mean([float(item[name]) for item in unit_metrics]))) for name in ("spearman", "mae", "rmse")}
        aggregate: dict[str, float | None] = {}
        for name in ("spearman", "mae", "rmse"):
            values = [row[name] for row in rows.values()]
            aggregate[f"subject_equal_mean_{name}"] = None if any(value is None for value in values) else float(np.mean([float(value) for value in values]))
        aggregate["biological_unit_count"] = float(len(rows))
        aggregate["measurement_batch_count"] = float(len(metrics))
        aggregate["batch_weighted_mean_spearman"] = None if any(item["spearman"] is None for item in metrics) else float(np.mean([float(item["spearman"]) for item in metrics]))
        return aggregate, rows

    @staticmethod
    def _cluster_bootstrap(unit_rows: Mapping[str, Mapping[str, float | None]], metric: str, *, resamples: int, seed: int) -> dict[str, float | int] | None:
        if any(row.get(metric) is None for row in unit_rows.values()):
            return None
        units = sorted(unit_rows)
        values = np.asarray([float(unit_rows[unit][metric]) for unit in units], dtype=float)
        rng = np.random.default_rng(seed)
        means = values[rng.integers(0, len(values), size=(resamples, len(values)))].mean(axis=1)
        interval = np.quantile(means, [0.025, 0.975], method="linear")
        return {"resamples": resamples, "seed": seed, "lower_95": float(interval[0]), "upper_95": float(interval[1])}

    def run(self, *, strict: bool = False) -> R4PXD017052NSCLCBOODSummary:
        if not strict:
            raise R4PXD017052NSCLCBOODError("biological cohort OOD requires --strict")
        if self.output_root.exists():
            raise R4PXD017052NSCLCBOODError("biological cohort OOD already executed")
        protocol, paths = self._protocol()
        try:
            R3AnalysisProtocolWorkflow(self.root, self.output_data_root).verify()
            R4PXD017052NSCLCSourceAuditWorkflow(self.root, self.source_assets_root).verify()
        except (R4PXD017052NSCLCSourceAuditError, R3AnalysisProtocolError, OSError) as exc:
            raise R4PXD017052NSCLCBOODError("frozen R3 or T180 input receipt does not verify") from exc
        helper = R3ModelEvaluationWorkflow(self.root, self.output_data_root, self.feature_root)
        try:
            development, development_accessions = helper._observations(paths["r3_common_target_ledger"], paths["r3_sequence_feature_table"])
        except R3ModelEvaluationError as exc:
            raise R4PXD017052NSCLCBOODError("frozen R3 development data is invalid") from exc
        if len(development) != 2724 or len(development_accessions) != 99:
            raise R4PXD017052NSCLCBOODError("frozen R3 development accounting differs")
        feature_values = {row.canonical_accession: row.feature_values for row in development}
        source_map = self.source_assets_root / "derived/R4_PXD017052_NSCLC_source_cell_map.csv"
        external, target_rows, accessions, batch_to_unit = self._external_observations(source_map, feature_values, protocol)
        full_indices = tuple(range(len(helper.FEATURE_NAMES)))
        composition_indices = tuple(helper.FEATURE_NAMES.index(name) for name in helper.COMPOSITION_FEATURE_NAMES)
        full_alpha, full_selection = helper._select_alpha(development, full_indices, minimum_proteins=10)
        composition_alpha, composition_selection = helper._select_alpha(development, composition_indices, minimum_proteins=10)
        constant_mean = float(np.mean([row.target for row in development]))
        full_model = helper._fit_ridge(development, full_indices, full_alpha)
        composition_model = helper._fit_ridge(development, composition_indices, composition_alpha)
        predictions = {"CONSTANT_TRAINING_MEAN": np.full(len(external), constant_mean, dtype=float), "SEQUENCE_RIDGE_FULL": helper._predict_ridge(full_model, external), "SEQUENCE_RIDGE_COMPOSITION_ONLY": helper._predict_ridge(composition_model, external)}
        uncertainty = protocol["uncertainty"]
        model_rows: list[dict[str, Any]] = []
        batch_rows: list[dict[str, Any]] = []
        subject_rows: list[dict[str, Any]] = []
        prediction_rows: list[dict[str, Any]] = []
        metric_by_model_batch: dict[tuple[str, str], dict[str, Any]] = {}
        for model_index, model_id in enumerate(helper.MODEL_IDS, start=1):
            metrics = helper._batch_metrics(external, predictions[model_id], minimum_proteins=10)
            aggregate, by_unit = self._subject_metrics(metrics, batch_to_unit)
            spearman_interval = self._cluster_bootstrap(by_unit, "spearman", resamples=uncertainty["resamples"], seed=uncertainty["random_seed"] + model_index * 100)
            mae_interval = self._cluster_bootstrap(by_unit, "mae", resamples=uncertainty["resamples"], seed=uncertainty["random_seed"] + model_index * 100 + 1)
            rmse_interval = self._cluster_bootstrap(by_unit, "rmse", resamples=uncertainty["resamples"], seed=uncertainty["random_seed"] + model_index * 100 + 2)
            status = "UNDEFINED_CONSTANT_PREDICTION" if model_id == "CONSTANT_TRAINING_MEAN" else "DEFINED"
            model_rows.append({"model_id": model_id, "external_observation_count": len(external), "external_measurement_batch_count": len(metrics), "biological_unit_count": int(aggregate["biological_unit_count"]), "primary_metric_status": status, **aggregate, "subject_equal_mean_spearman_lower_95": None if spearman_interval is None else spearman_interval["lower_95"], "subject_equal_mean_spearman_upper_95": None if spearman_interval is None else spearman_interval["upper_95"], "subject_equal_mean_mae_lower_95": None if mae_interval is None else mae_interval["lower_95"], "subject_equal_mean_mae_upper_95": None if mae_interval is None else mae_interval["upper_95"], "subject_equal_mean_rmse_lower_95": None if rmse_interval is None else rmse_interval["lower_95"], "subject_equal_mean_rmse_upper_95": None if rmse_interval is None else rmse_interval["upper_95"]})
            for metric in metrics:
                metric_by_model_batch[(model_id, metric["measurement_batch_id"])] = metric
                batch_rows.append({"model_id": model_id, **metric, "biological_unit_id": batch_to_unit[metric["measurement_batch_id"]], "spearman_status": status if metric["spearman"] is None else "DEFINED"})
            for unit, metric in by_unit.items():
                subject_rows.append({"model_id": model_id, "biological_unit_id": unit, **metric})
            for observation, value in zip(external, predictions[model_id], strict=True):
                prediction_rows.append({"model_id": model_id, "external_target_observation_id": observation.target_observation_id, "canonical_accession": observation.canonical_accession, "measurement_batch_id": observation.measurement_batch_id, "biological_unit_id": batch_to_unit[observation.measurement_batch_id], "observed_rank_percentile_descending": observation.target, "predicted_rank_percentile_descending": float(value)})
        paired_batches = sorted({batch for model_id, batch in metric_by_model_batch if model_id == "SEQUENCE_RIDGE_FULL"})
        paired_by_unit: dict[str, list[float]] = defaultdict(list)
        for batch in paired_batches:
            full = metric_by_model_batch[("SEQUENCE_RIDGE_FULL", batch)]["spearman"]
            composition = metric_by_model_batch[("SEQUENCE_RIDGE_COMPOSITION_ONLY", batch)]["spearman"]
            if full is None or composition is None:
                raise R4PXD017052NSCLCBOODError("paired ablation has undefined Spearman")
            paired_by_unit[batch_to_unit[batch]].append(float(full) - float(composition))
        paired_unit_values = {unit: {"delta": float(np.mean(values))} for unit, values in paired_by_unit.items()}
        paired_delta = float(np.mean([row["delta"] for row in paired_unit_values.values()]))
        paired_interval = self._cluster_bootstrap(paired_unit_values, "delta", resamples=uncertainty["resamples"], seed=uncertainty["random_seed"] + 701)
        observed_targets = np.asarray([row.target for row in development], dtype=float)
        by_development_batch: dict[str, list[int]] = defaultdict(list)
        for index, observation in enumerate(development):
            by_development_batch[observation.measurement_batch_id].append(index)
        negative = protocol["negative_control"]
        rng = np.random.default_rng(negative["random_seed"])
        null_rows: list[dict[str, Any]] = []
        null_primary: list[float] = []
        for resample in range(1, negative["resamples"] + 1):
            permuted = observed_targets.copy()
            for indices in by_development_batch.values():
                permuted[indices] = rng.permutation(permuted[indices])
            null_model = helper._fit_ridge(development, full_indices, full_alpha, targets=permuted)
            null_metrics = helper._batch_metrics(external, helper._predict_ridge(null_model, external), minimum_proteins=10)
            null_value = self._subject_metrics(null_metrics, batch_to_unit)[0]["subject_equal_mean_spearman"]
            if null_value is None:
                raise R4PXD017052NSCLCBOODError("negative control primary metric is undefined")
            null_primary.append(float(null_value))
            null_rows.append({"resample": resample, "null_subject_equal_mean_spearman": float(null_value)})
        observed_primary = next(row["subject_equal_mean_spearman"] for row in model_rows if row["model_id"] == "SEQUENCE_RIDGE_FULL")
        negative_summary = {"selected_alpha": full_alpha, "resamples": negative["resamples"], "random_seed": negative["random_seed"], "observed_subject_equal_mean_spearman": observed_primary, "null_subject_equal_mean_spearman_mean": float(np.mean(null_primary)), "null_subject_equal_mean_spearman_lower_95": float(np.quantile(null_primary, 0.025)), "null_subject_equal_mean_spearman_upper_95": float(np.quantile(null_primary, 0.975)), "one_sided_upper_tail_p": float((1 + sum(value >= observed_primary for value in null_primary)) / (1 + len(null_primary)))}
        selection_rows = [{"model_id": "SEQUENCE_RIDGE_FULL", **row, "selected_alpha": full_alpha} for row in full_selection] + [{"model_id": "SEQUENCE_RIDGE_COMPOSITION_ONLY", **row, "selected_alpha": composition_alpha} for row in composition_selection]
        self.output_root.mkdir(parents=True, exist_ok=False)
        output_paths = {
            "external_target_ledger": self.output_root / "r4_pxd017052_nsclc_rank_target_ledger.csv",
            "predictions": self.output_root / "r4_pxd017052_nsclc_ood_predictions.csv",
            "batch_metrics": self.output_root / "r4_pxd017052_nsclc_measurement_batch_metrics.csv",
            "subject_metrics": self.output_root / "r4_pxd017052_nsclc_biological_unit_metrics.csv",
            "model_metrics": self.output_root / "r4_pxd017052_nsclc_ood_model_metrics.csv",
            "selection": self.output_root / "r4_pxd017052_nsclc_nested_selection.csv",
            "negative_control": self.output_root / "r4_pxd017052_nsclc_within_batch_permutation.csv",
            "parameters": self.output_root / "r4_pxd017052_nsclc_model_parameters.json",
        }
        self._write_csv(output_paths["external_target_ledger"], list(target_rows[0]), target_rows)
        self._write_csv(output_paths["predictions"], list(prediction_rows[0]), prediction_rows)
        self._write_csv(output_paths["batch_metrics"], list(batch_rows[0]), batch_rows)
        self._write_csv(output_paths["subject_metrics"], list(subject_rows[0]), subject_rows)
        self._write_csv(output_paths["model_metrics"], list(model_rows[0]), model_rows)
        self._write_csv(output_paths["selection"], list(selection_rows[0]), selection_rows)
        self._write_csv(output_paths["negative_control"], list(null_rows[0]), null_rows)
        self._write_json(output_paths["parameters"], {"development_observation_count": len(development), "external_observation_count": len(external), "biological_unit_count": len(set(batch_to_unit.values())), "CONSTANT_TRAINING_MEAN": {"development_target_mean": constant_mean}, "SEQUENCE_RIDGE_FULL": {**helper._ridge_parameters(full_model, helper.FEATURE_NAMES), "negative_control": negative_summary}, "SEQUENCE_RIDGE_COMPOSITION_ONLY": helper._ridge_parameters(composition_model, helper.COMPOSITION_FEATURE_NAMES)})
        artifacts = {name: {"relative_path": path.relative_to(self.root).as_posix(), "sha256": _sha256(path)} for name, path in output_paths.items()}
        report = {"schema_version": 1, "audit_id": self.AUDIT_ID, "protocol_id": protocol["protocol_id"], "protocol_sha256": _sha256(self.protocol_path), "execution_module_sha256": _sha256(Path(__file__).resolve(strict=True)), "numpy_version": np.__version__, "status": self.STATUS, "evidence_class": protocol["evidence_class"], "allowed_claim_level": protocol["allowed_claim_level"], "input_references": {name: {"relative_path": path.relative_to(self.root).as_posix(), "sha256": _sha256(path)} for name, path in paths.items()}, "development_observation_count": len(development), "development_canonical_protein_count": len(development_accessions), "external_observation_count": len(external), "external_shared_canonical_protein_count": len(accessions), "external_measurement_batch_count": len({row.measurement_batch_id for row in external}), "biological_unit_count": len(set(batch_to_unit.values())), "laboratory_anchor_count": 1, "model_results": model_rows, "paired_composition_ablation": {"paired_measurement_batch_count": len(paired_batches), "paired_biological_unit_count": len(paired_unit_values), "full_minus_composition_subject_equal_mean_spearman": paired_delta, "cluster_bootstrap": paired_interval}, "negative_control_summary": negative_summary, "external_access_condition": protocol["external_evaluation"]["access_condition"], "artifacts": artifacts, "claim_boundary": protocol["claim_boundary"], "independent_validation": False, "external_scientific_reproduction": False, "scientific_submission_ready": False}
        report_path = self.output_root / "r4_pxd017052_nsclc_biological_ood_report.json"
        self._write_json(report_path, report)
        receipt = {"schema_version": 1, "audit_id": self.AUDIT_ID, "status": self.STATUS, "report_sha256": _sha256(report_path), "development_observation_count": len(development), "external_observation_count": len(external), "external_shared_canonical_protein_count": len(accessions), "external_measurement_batch_count": len({row.measurement_batch_id for row in external}), "biological_unit_count": len(set(batch_to_unit.values())), "model_count": len(helper.MODEL_IDS), "model_fitted": True, "independent_validation": False, "external_scientific_reproduction": False, "scientific_submission_ready": False}
        receipt_path = self.output_root / "r4_pxd017052_nsclc_biological_ood_receipt.json"
        self._write_json(receipt_path, receipt)
        return R4PXD017052NSCLCBOODSummary(len(development), len(external), len(accessions), len({row.measurement_batch_id for row in external}), len(set(batch_to_unit.values())), len(helper.MODEL_IDS), receipt_path)

    def verify(self) -> R4PXD017052NSCLCBOODSummary:
        report_path = self.output_root / "r4_pxd017052_nsclc_biological_ood_report.json"
        receipt_path = self.output_root / "r4_pxd017052_nsclc_biological_ood_receipt.json"
        report = self._json(report_path, "biological OOD report")
        receipt = self._json(receipt_path, "biological OOD receipt")
        artifacts = _mapping(report.get("artifacts"), "biological OOD artifacts")
        for value in artifacts.values():
            item = _mapping(value, "biological OOD artifact")
            if set(item) != self.REQUIRED_REFERENCE or _sha256(self._root_file(_string(item.get("relative_path"), "artifact path"), "artifact")) != _checksum(item.get("sha256"), "artifact"):
                raise R4PXD017052NSCLCBOODError("biological OOD artifact checksum differs")
        if report.get("audit_id") != self.AUDIT_ID or receipt.get("audit_id") != self.AUDIT_ID or report.get("status") != self.STATUS or receipt.get("status") != self.STATUS or receipt.get("report_sha256") != _sha256(report_path) or receipt.get("model_fitted") is not True or receipt.get("independent_validation") is not False or receipt.get("external_scientific_reproduction") is not False or receipt.get("scientific_submission_ready") is not False:
            raise R4PXD017052NSCLCBOODError("biological OOD receipt is invalid")
        return R4PXD017052NSCLCBOODSummary(int(receipt["development_observation_count"]), int(receipt["external_observation_count"]), int(receipt["external_shared_canonical_protein_count"]), int(receipt["external_measurement_batch_count"]), int(receipt["biological_unit_count"]), int(receipt["model_count"]), receipt_path)
