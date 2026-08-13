"""Execute the frozen small-n PXD060795 sensitivity analysis."""

from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path, PurePosixPath
from typing import Any

import numpy as np

from biointerfaceos.r3_analysis_protocol import R3AnalysisProtocolWorkflow
from biointerfaceos.r3_model_evaluation import R3ModelEvaluationError, R3ModelEvaluationWorkflow, _Observation
from biointerfaceos.r3_uniprot_mapping import _canonical, _checksum, _mapping, _sha256, _string


class R4DalianPlasmaCoronaSensitivityError(RuntimeError):
    """Raised when the frozen small-n sensitivity contract cannot execute."""


class R4DalianPlasmaCoronaSensitivityWorkflow:
    """Fit only on frozen R3 and score the six eligible Dalian corona batches."""

    AUDIT_ID = "bioif-r4-dalian-plasma-corona-sensitivity-v1.0.0"
    PROTOCOL_RELATIVE = "docs/data/R4_T163_PXD060795_SENSITIVITY_PROTOCOL.json"
    OUTPUT_RELATIVE = "reports/review_round_4/dalian_plasma_corona_sensitivity/v1.0.0"
    MODEL_IDS = ("CONSTANT_TRAINING_MEAN", "SEQUENCE_RIDGE_FULL", "SEQUENCE_RIDGE_COMPOSITION_ONLY")

    def __init__(self, root: Path, *, protocol_path: Path | None = None, output_root: Path | None = None) -> None:
        self.root = root.resolve(strict=True)
        self.protocol_path = protocol_path or self.root / self.PROTOCOL_RELATIVE
        self.output_root = output_root or self.root / self.OUTPUT_RELATIVE

    @staticmethod
    def _json(path: Path, label: str) -> dict[str, Any]:
        try:
            return _mapping(json.loads(path.read_text(encoding="utf-8")), label)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise R4DalianPlasmaCoronaSensitivityError(f"cannot parse {label}") from exc

    @staticmethod
    def _write(path: Path, value: Any) -> None:
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

    def _root_file(self, relative: str, label: str) -> Path:
        if "\\" in relative:
            raise R4DalianPlasmaCoronaSensitivityError(f"{label} must use POSIX separators")
        pure = PurePosixPath(relative)
        if pure.is_absolute() or not pure.parts or ".." in pure.parts:
            raise R4DalianPlasmaCoronaSensitivityError(f"{label} escapes repository root")
        path = (self.root / Path(*pure.parts)).resolve(strict=False)
        if not path.is_relative_to(self.root) or not path.is_file():
            raise R4DalianPlasmaCoronaSensitivityError(f"{label} is missing or outside repository root")
        return path

    def _reference(self, value: Any, label: str) -> Path:
        ref = _mapping(value, label)
        if set(ref) != {"relative_path", "sha256"}:
            raise R4DalianPlasmaCoronaSensitivityError(f"{label} fields are invalid")
        path = self._root_file(_string(ref["relative_path"], label), label)
        if _sha256(path) != _checksum(ref["sha256"], label):
            raise R4DalianPlasmaCoronaSensitivityError(f"{label} checksum differs")
        return path

    def _protocol(self) -> tuple[dict[str, Any], dict[str, Path]]:
        protocol = self._json(self.protocol_path, "R4 Dalian sensitivity protocol")
        required = {"schema_version", "protocol_id", "frozen_at", "evidence_class", "allowed_claim_level", "references", "target", "external_evaluation", "models", "uncertainty", "negative_control", "claim_boundary"}
        if set(protocol) != required or protocol.get("schema_version") != 1 or protocol.get("protocol_id") != self.AUDIT_ID:
            raise R4DalianPlasmaCoronaSensitivityError("sensitivity protocol identity is invalid")
        if protocol.get("evidence_class") != "DEVELOPMENT_OBSERVATION" or protocol.get("allowed_claim_level") != "EXPLORATORY":
            raise R4DalianPlasmaCoronaSensitivityError("sensitivity evidence boundary is invalid")
        refs = _mapping(protocol["references"], "sensitivity references")
        if set(refs) != {"r3_analysis_protocol_receipt", "r3_common_target_ledger", "r3_sequence_feature_table", "r4_source_audit_receipt", "r4_source_cell_map"}:
            raise R4DalianPlasmaCoronaSensitivityError("sensitivity references are invalid")
        paths = {key: self._reference(value, key) for key, value in refs.items()}
        if _mapping(protocol["target"], "sensitivity target")["target_id"] != "R4_WITHIN_MEASUREMENT_BATCH_POSITIVE_QUANTIFICATION_RANK_PERCENTILE":
            raise R4DalianPlasmaCoronaSensitivityError("sensitivity target is invalid")
        external = _mapping(protocol["external_evaluation"], "sensitivity external contract")
        if external.get("source_id") != "PXD060795_DALIAN_PLA_MICRO_NANOPLASTIC_HUMAN_PLASMA_CORONA" or external.get("expected_measurement_batch_count") != 6 or external.get("expected_shared_canonical_protein_count") != 22 or external.get("small_n_sensitivity_only") is not True:
            raise R4DalianPlasmaCoronaSensitivityError("sensitivity external contract is invalid")
        if protocol["models"] != [
            {"model_id": "CONSTANT_TRAINING_MEAN", "hyperparameters": {}},
            {"model_id": "SEQUENCE_RIDGE_FULL", "hyperparameters": {"alpha_grid": [0.01, 0.1, 1.0, 10.0, 100.0]}},
            {"model_id": "SEQUENCE_RIDGE_COMPOSITION_ONLY", "hyperparameters": {"alpha_grid": [0.01, 0.1, 1.0, 10.0, 100.0]}},
        ]:
            raise R4DalianPlasmaCoronaSensitivityError("sensitivity model contract is invalid")
        return protocol, paths

    @staticmethod
    def _read_csv(path: Path, label: str) -> list[dict[str, str]]:
        try:
            with path.open(encoding="utf-8", newline="") as stream:
                rows = list(csv.DictReader(stream))
        except OSError as exc:
            raise R4DalianPlasmaCoronaSensitivityError(f"cannot read {label}") from exc
        if not rows or not rows[0]:
            raise R4DalianPlasmaCoronaSensitivityError(f"{label} is empty")
        return rows

    @staticmethod
    def _ranks(rows: Sequence[Mapping[str, str]]) -> list[_Observation]:
        by_batch: dict[str, list[Mapping[str, str]]] = defaultdict(list)
        for row in rows:
            if row.get("analysis_candidate_eligible") == "true" and row.get("rank_target_eligible") == "true":
                by_batch[_string(row.get("measurement_batch_id"), "measurement batch")].append(row)
        observations: list[_Observation] = []
        for batch, batch_rows in sorted(by_batch.items()):
            ordered = sorted(batch_rows, key=lambda row: (-float(row["author_numeric_value"]), row["source_coordinate"]))
            count = len(ordered)
            start = 0
            while start < count:
                end = start + 1
                while end < count and float(ordered[end]["author_numeric_value"]) == float(ordered[start]["author_numeric_value"]):
                    end += 1
                midrank = (start + 1 + end) / 2.0
                target = 0.5 if count == 1 else (count - midrank) / (count - 1)
                for row in ordered[start:end]:
                    observations.append(
                        _Observation(
                            target_observation_id=f"{batch}:{row['source_coordinate']}",
                            source_id=row["source_id"],
                            canonical_accession=row["canonical_accession"],
                            laboratory_anchor=row["laboratory_anchor"],
                            measurement_batch_id=batch,
                            target=target,
                            feature_values=(),
                        )
                    )
                start = end
        if len({row.target_observation_id for row in observations}) != len(observations):
            raise R4DalianPlasmaCoronaSensitivityError("sensitivity target identity is duplicated")
        return observations

    def run(self, *, strict: bool = False) -> dict[str, Any]:
        if not strict:
            raise R4DalianPlasmaCoronaSensitivityError("Dalian sensitivity analysis requires --strict")
        if self.output_root.exists():
            raise R4DalianPlasmaCoronaSensitivityError("Dalian sensitivity analysis already executed")
        protocol, paths = self._protocol()
        try:
            R3AnalysisProtocolWorkflow(self.root, self.root / "data/raw").verify()
            helper = R3ModelEvaluationWorkflow(self.root, self.root / "data/raw", self.root / "data/raw/r3_uniprot_sequence_features")
            development, development_accessions = helper._observations(paths["r3_common_target_ledger"], paths["r3_sequence_feature_table"])
        except (R3ModelEvaluationError, OSError) as exc:
            raise R4DalianPlasmaCoronaSensitivityError("frozen R3 development inputs are invalid") from exc
        source_rows = self._read_csv(paths["r4_source_cell_map"], "Dalian source cell map")
        if any(row.get("source_id") != protocol["external_evaluation"]["source_id"] for row in source_rows):
            raise R4DalianPlasmaCoronaSensitivityError("Dalian source identity differs from protocol")
        external_raw = self._ranks(source_rows)
        feature_values = {row.canonical_accession: row.feature_values for row in development}
        external: list[_Observation] = []
        for row in external_raw:
            if row.canonical_accession not in feature_values:
                raise R4DalianPlasmaCoronaSensitivityError("Dalian target lacks frozen sequence features")
            external.append(_Observation(row.target_observation_id, row.source_id, row.canonical_accession, row.laboratory_anchor, row.measurement_batch_id, row.target, feature_values[row.canonical_accession]))
        if len(external) != 109 or len({row.measurement_batch_id for row in external}) != 6:
            raise R4DalianPlasmaCoronaSensitivityError("Dalian sensitivity target accounting differs")
        full_indices = tuple(range(len(helper.FEATURE_NAMES)))
        composition_indices = tuple(helper.FEATURE_NAMES.index(name) for name in helper.COMPOSITION_FEATURE_NAMES)
        full_alpha, full_selection = helper._select_alpha(development, full_indices, minimum_proteins=10)
        composition_alpha, composition_selection = helper._select_alpha(development, composition_indices, minimum_proteins=10)
        full_model = helper._fit_ridge(development, full_indices, full_alpha)
        composition_model = helper._fit_ridge(development, composition_indices, composition_alpha)
        predictions = {
            "CONSTANT_TRAINING_MEAN": np.full(len(external), float(np.mean([row.target for row in development]))),
            "SEQUENCE_RIDGE_FULL": helper._predict_ridge(full_model, external),
            "SEQUENCE_RIDGE_COMPOSITION_ONLY": helper._predict_ridge(composition_model, external),
        }
        metrics: dict[str, dict[str, Any]] = {}
        batch_metrics: list[dict[str, Any]] = []
        for model_id in self.MODEL_IDS:
            rows = helper._batch_metrics(external, predictions[model_id], minimum_proteins=10)
            aggregate = helper._aggregate(rows)
            metrics[model_id] = {"external_observation_count": len(external), "external_measurement_batch_count": len(rows), **aggregate}
            batch_metrics.extend({"model_id": model_id, **row} for row in rows)
        full_by_batch = {row["measurement_batch_id"]: float(row["spearman"]) for row in batch_metrics if row["model_id"] == "SEQUENCE_RIDGE_FULL"}
        comp_by_batch = {row["measurement_batch_id"]: float(row["spearman"]) for row in batch_metrics if row["model_id"] == "SEQUENCE_RIDGE_COMPOSITION_ONLY"}
        differences = [full_by_batch[key] - comp_by_batch[key] for key in sorted(full_by_batch)]
        uncertainty = protocol["uncertainty"]
        ablation = {"paired_measurement_batch_count": len(differences), "full_minus_composition_mean_spearman": float(np.mean(differences)), **helper._bootstrap(differences, resamples=int(uncertainty["resamples"]), seed=int(uncertainty["random_seed"]) + 701)}
        observed_targets = np.asarray([row.target for row in development], dtype=float)
        by_development_batch: dict[str, list[int]] = defaultdict(list)
        for index, row in enumerate(development):
            by_development_batch[row.measurement_batch_id].append(index)
        rng = np.random.default_rng(int(protocol["negative_control"]["random_seed"]))
        null_scores: list[float] = []
        for _ in range(int(protocol["negative_control"]["resamples"])):
            permuted = observed_targets.copy()
            for indices in by_development_batch.values():
                permuted[indices] = rng.permutation(permuted[indices])
            null_model = helper._fit_ridge(development, full_indices, full_alpha, targets=permuted)
            score = helper._aggregate(helper._batch_metrics(external, helper._predict_ridge(null_model, external), minimum_proteins=10))["mean_spearman"]
            if score is None:
                raise R4DalianPlasmaCoronaSensitivityError("Dalian negative-control metric is undefined")
            null_scores.append(float(score))
        observed = float(metrics["SEQUENCE_RIDGE_FULL"]["mean_spearman"])
        negative = {"observed_mean_spearman": observed, "null_mean_spearman_mean": float(np.mean(null_scores)), "null_mean_spearman_lower_95": float(np.quantile(null_scores, 0.025)), "null_mean_spearman_upper_95": float(np.quantile(null_scores, 0.975)), "one_sided_upper_tail_p": float((1 + sum(value >= observed for value in null_scores)) / (1 + len(null_scores)))}
        self.output_root.mkdir(parents=True, exist_ok=False)
        metrics_path = self.output_root / "dalian_sensitivity_model_metrics.json"
        batch_path = self.output_root / "dalian_sensitivity_batch_metrics.csv"
        self._write(metrics_path, metrics)
        self._write_csv(batch_path, ["model_id", "measurement_batch_id", "protein_count", "spearman", "mae", "rmse"], batch_metrics)
        report = {"schema_version": 1, "audit_id": self.AUDIT_ID, "protocol_sha256": _sha256(self.protocol_path), "status": "R4_DALIAN_SMALL_N_SENSITIVITY_EXECUTED_EXPLORATORY", "development_observation_count": len(development), "development_canonical_protein_count": len(development_accessions), "external_observation_count": len(external), "external_measurement_batch_count": len({row.measurement_batch_id for row in external}), "model_metrics": metrics, "paired_composition_ablation": ablation, "negative_control": negative, "artifacts": {"model_metrics": {"relative_path": metrics_path.relative_to(self.root).as_posix(), "sha256": _sha256(metrics_path)}, "batch_metrics": {"relative_path": batch_path.relative_to(self.root).as_posix(), "sha256": _sha256(batch_path)}}, "model_fitted": True, "independent_validation": False, "external_scientific_reproduction": False, "scientific_submission_ready": False, "claim_boundary": protocol["claim_boundary"]}
        report_path = self.output_root / "dalian_sensitivity_report.json"
        self._write(report_path, report)
        receipt = {"schema_version": 1, "audit_id": self.AUDIT_ID, "status": report["status"], "report_sha256": _sha256(report_path), "model_fitted": True, "independent_validation": False, "external_scientific_reproduction": False, "scientific_submission_ready": False, "external_measurement_batch_count": 6}
        receipt_path = self.output_root / "dalian_sensitivity_receipt.json"
        self._write(receipt_path, receipt)
        return {"external_observation_count": len(external), "external_measurement_batch_count": 6, "model_metrics": metrics, "paired_composition_ablation": ablation, "negative_control": negative, "receipt_path": receipt_path}
