"""Execute the frozen author-run public OOD analysis for the R4 corona candidate."""

from __future__ import annotations

import csv
import json
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
from biointerfaceos.r3_uniprot_mapping import _canonical, _checksum, _mapping, _sha256, _string
from biointerfaceos.r4_small_molecule_corona_source_audit import (
    R4SmallMoleculeCoronaSourceAuditError,
    R4SmallMoleculeCoronaSourceAuditWorkflow,
)


class R4SmallMoleculeCoronaOODError(RuntimeError):
    """Raised when the frozen R4 public OOD analysis cannot run safely."""


@dataclass(frozen=True)
class R4SmallMoleculeCoronaOODSummary:
    development_observation_count: int
    external_observation_count: int
    shared_canonical_protein_count: int
    external_measurement_batch_count: int
    model_count: int
    receipt_path: Path


class R4SmallMoleculeCoronaOODWorkflow:
    """Fit only on frozen R3 and score the byte-verified R4 source-local ranks."""

    AUDIT_ID = "bioif-r4-pmc11544298-external-ood-v1.0.0"
    PROTOCOL_RELATIVE = "docs/data/R4_T159_SMALL_MOLECULE_CORONA_OOD_PROTOCOL.json"
    OUTPUT_RELATIVE = "reports/review_round_4/small_molecule_corona_ood/v1.0.0"
    STATUS = "R4_PUBLIC_SAME_LINEAGE_OOD_EXECUTED_EXPLORATORY"
    REQUIRED_REFERENCE = {"relative_path", "sha256"}
    TARGET_FIELDS = [
        "external_target_observation_id", "source_id", "laboratory_anchor",
        "canonical_accession", "measurement_batch_id", "source_worksheet", "source_row",
        "source_coordinate", "author_quantity_type", "author_numeric_value",
        "rank_percentile_descending", "measurement_batch_positive_protein_count",
    ]
    SOURCE_AUDIT_WORKFLOW = R4SmallMoleculeCoronaSourceAuditWorkflow
    SOURCE_AUDIT_ERROR = R4SmallMoleculeCoronaSourceAuditError

    def __init__(
        self,
        root: Path,
        output_data_root: Path,
        feature_root: Path,
        source_assets_root: Path,
        *,
        protocol_path: Path | None = None,
        output_root: Path | None = None,
    ) -> None:
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
    def _json(path: Path, label: str) -> dict[str, Any]:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            return _mapping(value, label)
        except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
            raise R4SmallMoleculeCoronaOODError(f"cannot parse {label}") from exc

    def _root_file(self, relative_path: str, label: str) -> Path:
        if "\\" in relative_path:
            raise R4SmallMoleculeCoronaOODError(f"{label} must use a POSIX relative path")
        pure = PurePosixPath(relative_path)
        if pure.is_absolute() or not pure.parts or ".." in pure.parts:
            raise R4SmallMoleculeCoronaOODError(f"{label} escapes repository root")
        path = (self.root / Path(*pure.parts)).resolve(strict=False)
        if not path.is_relative_to(self.root) or not path.is_file():
            raise R4SmallMoleculeCoronaOODError(f"{label} is missing or outside repository root")
        return path

    def _reference(self, value: Any, label: str) -> Path:
        item = _mapping(value, label)
        if set(item) != self.REQUIRED_REFERENCE:
            raise R4SmallMoleculeCoronaOODError(f"{label} fields are invalid")
        path = self._root_file(_string(item.get("relative_path"), label), label)
        try:
            expected = _checksum(item.get("sha256"), label)
        except Exception as exc:
            raise R4SmallMoleculeCoronaOODError(f"{label} checksum is invalid") from exc
        if _sha256(path) != expected:
            raise R4SmallMoleculeCoronaOODError(f"{label} checksum differs")
        return path

    def _protocol(self) -> tuple[dict[str, Any], dict[str, Path]]:
        protocol = self._json(self.protocol_path, "R4 small-molecule OOD protocol")
        expected_top = {
            "schema_version", "protocol_id", "frozen_at", "evidence_class", "allowed_claim_level",
            "references", "target", "development_selection", "external_evaluation", "feature_policy",
            "models", "metrics", "uncertainty", "negative_control", "claim_boundary",
        }
        if set(protocol) != expected_top or protocol.get("schema_version") != 1:
            raise R4SmallMoleculeCoronaOODError("R4 OOD protocol fields are invalid")
        if (
            protocol.get("protocol_id") != "bioif-r4-pmc11544298-external-ood-protocol-v1.0.0"
            or protocol.get("evidence_class") != "DEVELOPMENT_OBSERVATION"
            or protocol.get("allowed_claim_level") != "EXPLORATORY"
        ):
            raise R4SmallMoleculeCoronaOODError("R4 OOD protocol identity is invalid")
        refs = _mapping(protocol.get("references"), "R4 OOD references")
        expected_refs = {
            "r3_analysis_protocol_receipt", "r3_common_target_ledger", "r3_sequence_feature_table",
            "r4_source_audit_receipt", "r4_source_cell_map",
        }
        if set(refs) != expected_refs:
            raise R4SmallMoleculeCoronaOODError("R4 OOD references are invalid")
        paths = {key: self._reference(value, key) for key, value in refs.items()}
        if self.output_data_root != (self.root / "data/raw").resolve(strict=False):
            raise R4SmallMoleculeCoronaOODError("R4 OOD requires the fixed data/raw root")
        if self.feature_root != (self.root / "data/raw/r3_uniprot_sequence_features").resolve(strict=False):
            raise R4SmallMoleculeCoronaOODError("R4 OOD requires the fixed feature root")
        if self.source_assets_root != (self.root / "data/raw/r4_candidate_pmc11544298").resolve(strict=False):
            raise R4SmallMoleculeCoronaOODError("R4 OOD requires the fixed R4 source root")
        if _mapping(protocol["target"], "R4 OOD target") != {
            "target_id": "R4_WITHIN_MEASUREMENT_BATCH_POSITIVE_QUANTIFICATION_RANK_PERCENTILE",
            "development_target": "the frozen R3 source-local descending midrank percentile",
            "external_target": "descending midrank percentile among strictly positive finite source-reported values within each eligible R4 corona measurement batch",
            "cross_study_raw_scale": "PROHIBITED",
        }:
            raise R4SmallMoleculeCoronaOODError("R4 OOD target is invalid")
        external = _mapping(protocol["external_evaluation"], "R4 external evaluation")
        if external != {
            "source_id": "PMC11544298_SMALL_MOLECULE_HUMAN_PLASMA_CORONA",
            "laboratory_anchor": "Michigan State University-led small-molecule protein-corona study",
            "analysis_population": "source-cell rows with analysis_candidate_eligible=true, rank_target_eligible=true and canonical accession present in the frozen R3 feature table",
            "minimum_proteins_per_measurement_batch": 10,
            "expected_measurement_batch_count": 134,
            "expected_shared_canonical_protein_count_at_least": 94,
            "access_condition": "public CC-BY supplementary source; author-run public OOD candidate; not a protected lockbox and not an independent evaluator",
        }:
            raise R4SmallMoleculeCoronaOODError("R4 external evaluation contract is invalid")
        if protocol["models"] != [
            {"model_id": "CONSTANT_TRAINING_MEAN", "hyperparameters": {}},
            {"model_id": "SEQUENCE_RIDGE_FULL", "hyperparameters": {"alpha_grid": [0.01, 0.1, 1.0, 10.0, 100.0]}},
            {"model_id": "SEQUENCE_RIDGE_COMPOSITION_ONLY", "hyperparameters": {"alpha_grid": [0.01, 0.1, 1.0, 10.0, 100.0]}},
        ]:
            raise R4SmallMoleculeCoronaOODError("R4 model contract is invalid")
        return protocol, paths

    @staticmethod
    def _read_csv(path: Path, label: str) -> list[dict[str, str]]:
        try:
            with path.open("r", encoding="utf-8", newline="") as stream:
                rows = list(csv.DictReader(stream))
        except OSError as exc:
            raise R4SmallMoleculeCoronaOODError(f"cannot read {label}") from exc
        if not rows or not rows[0]:
            raise R4SmallMoleculeCoronaOODError(f"{label} is empty")
        return rows

    @staticmethod
    def _rank_percentiles(rows: Sequence[Mapping[str, str]]) -> dict[str, tuple[float, int]]:
        by_batch: dict[str, list[Mapping[str, str]]] = defaultdict(list)
        for row in rows:
            if row.get("analysis_candidate_eligible") == "true" and row.get("rank_target_eligible") == "true":
                by_batch[_string(row.get("measurement_batch_id"), "R4 measurement batch ID")].append(row)
        ranks: dict[str, tuple[float, int]] = {}
        for batch_id, batch_rows in by_batch.items():
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
                        raise R4SmallMoleculeCoronaOODError("R4 source rank identity is duplicated")
                    ranks[identity] = (percentile, count)
                start = end
        return ranks

    def _external_observations(
        self, source_map_path: Path, feature_values: Mapping[str, tuple[float, ...]], protocol: Mapping[str, Any]
    ) -> tuple[list[_Observation], list[dict[str, Any]], set[str]]:
        rows = self._read_csv(source_map_path, "R4 source cell map")
        required = {
            "source_id", "laboratory_anchor", "source_worksheet", "source_row", "source_coordinate",
            "source_identifier", "measurement_batch_id", "author_quantity_type", "author_numeric_value",
            "analysis_candidate_eligible", "rank_target_eligible",
        }
        if not required.issubset(rows[0]):
            raise R4SmallMoleculeCoronaOODError("R4 source cell map schema is invalid")
        external_contract = protocol["external_evaluation"]
        if any(
            row.get("source_id") != external_contract["source_id"]
            or row.get("laboratory_anchor") != external_contract["laboratory_anchor"]
            for row in rows
        ):
            raise R4SmallMoleculeCoronaOODError("R4 source map identity differs from frozen protocol")
        ranks = self._rank_percentiles(rows)
        observations: list[_Observation] = []
        target_rows: list[dict[str, Any]] = []
        accessions: set[str] = set()
        by_batch: dict[str, int] = defaultdict(int)
        for row in rows:
            identity = f"{row['measurement_batch_id']}:{row['source_coordinate']}"
            rank = ranks.get(identity)
            accession = row.get("source_identifier", "")
            if rank is None or accession not in feature_values:
                continue
            percentile, positive_count = rank
            batch_id = row["measurement_batch_id"]
            target_id = f"R4PMC11544298:{row['source_asset_id']}:{row['source_worksheet']}:{row['source_row']}:{batch_id}"
            observations.append(_Observation(target_id, external_contract["source_id"], accession, external_contract["laboratory_anchor"], batch_id, percentile, feature_values[accession]))
            target_rows.append({
                "external_target_observation_id": target_id,
                "source_id": external_contract["source_id"],
                "laboratory_anchor": external_contract["laboratory_anchor"],
                "canonical_accession": accession,
                "measurement_batch_id": batch_id,
                "source_worksheet": row["source_worksheet"],
                "source_row": row["source_row"],
                "source_coordinate": row["source_coordinate"],
                "author_quantity_type": row["author_quantity_type"],
                "author_numeric_value": float(row["author_numeric_value"]),
                "rank_percentile_descending": percentile,
                "measurement_batch_positive_protein_count": positive_count,
            })
            by_batch[batch_id] += 1
            accessions.add(accession)
        if (
            len(by_batch) != external_contract["expected_measurement_batch_count"]
            or len(accessions) < external_contract["expected_shared_canonical_protein_count_at_least"]
            or any(count < external_contract["minimum_proteins_per_measurement_batch"] for count in by_batch.values())
        ):
            raise R4SmallMoleculeCoronaOODError("R4 source does not meet frozen external OOD coverage")
        return sorted(observations, key=lambda row: (row.measurement_batch_id, row.target_observation_id)), target_rows, accessions

    @staticmethod
    def _format(value: Any) -> str:
        return "" if value is None else format(value, ".17g") if isinstance(value, float) else str(value)

    @classmethod
    def _write_csv(cls, path: Path, fields: Sequence[str], rows: Sequence[Mapping[str, Any]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
            writer.writeheader()
            for row in rows:
                writer.writerow({field: cls._format(row.get(field)) for field in fields})

    def run(self, *, strict: bool = False) -> R4SmallMoleculeCoronaOODSummary:
        if not strict:
            raise R4SmallMoleculeCoronaOODError("R4 small-molecule OOD requires --strict")
        if self.output_root.exists():
            raise R4SmallMoleculeCoronaOODError("R4 small-molecule OOD already executed")
        protocol, paths = self._protocol()
        try:
            R3AnalysisProtocolWorkflow(self.root, self.output_data_root).verify()
            self.SOURCE_AUDIT_WORKFLOW(self.root, self.source_assets_root).verify()
        except (Exception, self.SOURCE_AUDIT_ERROR) as exc:
            raise R4SmallMoleculeCoronaOODError("a frozen R3/R4 input receipt does not verify") from exc
        helper = R3ModelEvaluationWorkflow(self.root, self.output_data_root, self.feature_root)
        try:
            development, development_accessions = helper._observations(paths["r3_common_target_ledger"], paths["r3_sequence_feature_table"])
        except R3ModelEvaluationError as exc:
            raise R4SmallMoleculeCoronaOODError("frozen R3 development data is invalid") from exc
        if len(development) != 2724 or len(development_accessions) != 99:
            raise R4SmallMoleculeCoronaOODError("frozen R3 development cohort differs")
        feature_values = {row.canonical_accession: row.feature_values for row in development}
        external, target_rows, accessions = self._external_observations(paths["r4_source_cell_map"], feature_values, protocol)
        full_indices = tuple(range(len(helper.FEATURE_NAMES)))
        composition_indices = tuple(helper.FEATURE_NAMES.index(name) for name in helper.COMPOSITION_FEATURE_NAMES)
        full_alpha, full_selection = helper._select_alpha(development, full_indices, minimum_proteins=10)
        composition_alpha, composition_selection = helper._select_alpha(development, composition_indices, minimum_proteins=10)
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
            for metric_name, key in (("spearman", "mean_spearman"), ("mae", "mean_mae"), ("rmse", "mean_rmse")):
                values = [metric[metric_name] for metric in metrics]
                intervals[key] = None if any(value is None for value in values) else helper._bootstrap([float(value) for value in values], resamples=uncertainty["resamples"], seed=uncertainty["random_seed"] + model_index * 100)
            if model_id == "SEQUENCE_RIDGE_FULL":
                full_primary = aggregate["mean_spearman"]
            model_rows.append({
                "model_id": model_id, "external_observation_count": len(external),
                "external_measurement_batch_count": len(metrics), "primary_metric_status": status,
                **aggregate,
                "mean_spearman_lower_95": None if intervals["mean_spearman"] is None else intervals["mean_spearman"]["lower_95"],
                "mean_spearman_upper_95": None if intervals["mean_spearman"] is None else intervals["mean_spearman"]["upper_95"],
                "mean_mae_lower_95": intervals["mean_mae"]["lower_95"], "mean_mae_upper_95": intervals["mean_mae"]["upper_95"],
                "mean_rmse_lower_95": intervals["mean_rmse"]["lower_95"], "mean_rmse_upper_95": intervals["mean_rmse"]["upper_95"],
            })
            for metric in metrics:
                metric_by_model_batch[(model_id, metric["measurement_batch_id"])] = metric
                batch_rows.append({"model_id": model_id, **metric, "spearman_status": status if metric["spearman"] is None else "DEFINED"})
            for observation, value in zip(external, predictions[model_id], strict=True):
                prediction_rows.append({"model_id": model_id, "external_target_observation_id": observation.target_observation_id, "canonical_accession": observation.canonical_accession, "measurement_batch_id": observation.measurement_batch_id, "observed_rank_percentile_descending": observation.target, "predicted_rank_percentile_descending": float(value)})
        if full_primary is None:
            raise R4SmallMoleculeCoronaOODError("R4 full sequence OOD primary metric is undefined")
        paired_batches = sorted({batch for model_id, batch in metric_by_model_batch if model_id == "SEQUENCE_RIDGE_FULL"})
        paired_difference = [float(metric_by_model_batch[("SEQUENCE_RIDGE_FULL", batch)]["spearman"]) - float(metric_by_model_batch[("SEQUENCE_RIDGE_COMPOSITION_ONLY", batch)]["spearman"]) for batch in paired_batches]
        ablation = {"paired_measurement_batch_count": len(paired_difference), "full_minus_composition_mean_spearman": float(np.mean(paired_difference)), **helper._bootstrap(paired_difference, resamples=uncertainty["resamples"], seed=uncertainty["random_seed"] + 701)}
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
            score = helper._aggregate(helper._batch_metrics(external, helper._predict_ridge(null_model, external), minimum_proteins=10))["mean_spearman"]
            if score is None:
                raise R4SmallMoleculeCoronaOODError("R4 permutation control has undefined primary metric")
            null_primary.append(float(score))
            null_rows.append({"resample": resample, "null_mean_spearman": float(score)})
        negative_summary = {
            "selected_alpha": full_alpha, "resamples": negative["resamples"], "random_seed": negative["random_seed"],
            "observed_mean_spearman": full_primary, "null_mean_spearman_mean": float(np.mean(null_primary)),
            "null_mean_spearman_lower_95": float(np.quantile(null_primary, 0.025)), "null_mean_spearman_upper_95": float(np.quantile(null_primary, 0.975)),
            "one_sided_upper_tail_p": float((1 + sum(value >= full_primary for value in null_primary)) / (1 + len(null_primary))),
        }
        selection_rows = [{"model_id": "SEQUENCE_RIDGE_FULL", **row, "selected_alpha": full_alpha} for row in full_selection] + [{"model_id": "SEQUENCE_RIDGE_COMPOSITION_ONLY", **row, "selected_alpha": composition_alpha} for row in composition_selection]
        self.output_root.mkdir(parents=True, exist_ok=False)
        output_paths = {
            "external_target_ledger": self.output_root / "r4_external_rank_target_ledger.csv",
            "predictions": self.output_root / "r4_external_ood_predictions.csv",
            "batch_metrics": self.output_root / "r4_external_measurement_batch_metrics.csv",
            "model_metrics": self.output_root / "r4_external_ood_model_metrics.csv",
            "selection": self.output_root / "r4_external_nested_selection.csv",
            "negative_control": self.output_root / "r4_external_within_batch_permutation.csv",
            "parameters": self.output_root / "r4_external_model_parameters.json",
        }
        self._write_csv(output_paths["external_target_ledger"], self.TARGET_FIELDS, target_rows)
        self._write_csv(output_paths["predictions"], ["model_id", "external_target_observation_id", "canonical_accession", "measurement_batch_id", "observed_rank_percentile_descending", "predicted_rank_percentile_descending"], prediction_rows)
        self._write_csv(output_paths["batch_metrics"], ["model_id", "measurement_batch_id", "protein_count", "spearman", "spearman_status", "mae", "rmse"], batch_rows)
        self._write_csv(output_paths["model_metrics"], ["model_id", "external_observation_count", "external_measurement_batch_count", "primary_metric_status", "mean_spearman", "mean_spearman_lower_95", "mean_spearman_upper_95", "mean_mae", "mean_mae_lower_95", "mean_mae_upper_95", "mean_rmse", "mean_rmse_lower_95", "mean_rmse_upper_95"], model_rows)
        self._write_csv(output_paths["selection"], ["model_id", "alpha", "held_out_inner_batch_id", "spearman", "selected_alpha"], selection_rows)
        self._write_csv(output_paths["negative_control"], ["resample", "null_mean_spearman"], null_rows)
        self._write_json(output_paths["parameters"], {"development_observation_count": len(development), "external_observation_count": len(external), "CONSTANT_TRAINING_MEAN": {"development_target_mean": constant_mean}, "SEQUENCE_RIDGE_FULL": {**helper._ridge_parameters(full_model, helper.FEATURE_NAMES), "negative_control": negative_summary}, "SEQUENCE_RIDGE_COMPOSITION_ONLY": helper._ridge_parameters(composition_model, helper.COMPOSITION_FEATURE_NAMES)})
        artifacts = {name: {"relative_path": path.relative_to(self.root).as_posix(), "sha256": _sha256(path)} for name, path in output_paths.items()}
        report = {
            "schema_version": 1, "audit_id": self.AUDIT_ID, "protocol_id": protocol["protocol_id"], "protocol_sha256": _sha256(self.protocol_path), "execution_module_sha256": _sha256(Path(__file__).resolve(strict=True)), "numpy_version": np.__version__, "status": self.STATUS, "evidence_class": protocol["evidence_class"], "allowed_claim_level": protocol["allowed_claim_level"],
            "input_references": {name: {"relative_path": path.relative_to(self.root).as_posix(), "sha256": _sha256(path)} for name, path in paths.items()},
            "development_observation_count": len(development), "development_canonical_protein_count": len(development_accessions), "external_observation_count": len(external), "external_shared_canonical_protein_count": len(accessions), "external_measurement_batch_count": len({row.measurement_batch_id for row in external}), "model_results": model_rows, "paired_composition_ablation": ablation, "negative_control_summary": negative_summary, "external_access_condition": protocol["external_evaluation"]["access_condition"], "artifacts": artifacts, "claim_boundary": protocol["claim_boundary"], "independent_validation": False, "external_scientific_reproduction": False, "scientific_submission_ready": False,
        }
        report_path = self.output_root / "r4_external_ood_report.json"
        self._write_json(report_path, report)
        receipt = {"schema_version": 1, "audit_id": self.AUDIT_ID, "status": self.STATUS, "report_sha256": _sha256(report_path), "development_observation_count": len(development), "external_observation_count": len(external), "external_shared_canonical_protein_count": len(accessions), "external_measurement_batch_count": len({row.measurement_batch_id for row in external}), "model_count": len(helper.MODEL_IDS), "model_fitted": True, "independent_validation": False, "external_scientific_reproduction": False, "scientific_submission_ready": False}
        receipt_path = self.output_root / "r4_external_ood_receipt.json"
        self._write_json(receipt_path, receipt)
        return R4SmallMoleculeCoronaOODSummary(len(development), len(external), len(accessions), len({row.measurement_batch_id for row in external}), len(helper.MODEL_IDS), receipt_path)

    def verify(self) -> R4SmallMoleculeCoronaOODSummary:
        report_path = self.output_root / "r4_external_ood_report.json"
        receipt_path = self.output_root / "r4_external_ood_receipt.json"
        report = self._json(report_path, "R4 OOD report")
        receipt = self._json(receipt_path, "R4 OOD receipt")
        artifacts = _mapping(report.get("artifacts"), "R4 OOD artifacts")
        valid = bool(artifacts)
        for value in artifacts.values():
            item = _mapping(value, "R4 OOD artifact")
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
            report.get("audit_id") != self.AUDIT_ID or receipt.get("audit_id") != self.AUDIT_ID
            or report.get("status") != self.STATUS or receipt.get("status") != self.STATUS
            or receipt.get("report_sha256") != _sha256(report_path) or receipt.get("model_fitted") is not True
            or receipt.get("independent_validation") is not False or receipt.get("external_scientific_reproduction") is not False
            or receipt.get("scientific_submission_ready") is not False or not valid
        ):
            raise R4SmallMoleculeCoronaOODError("R4 OOD receipt is invalid")
        return R4SmallMoleculeCoronaOODSummary(int(receipt["development_observation_count"]), int(receipt["external_observation_count"]), int(receipt["external_shared_canonical_protein_count"]), int(receipt["external_measurement_batch_count"]), int(receipt["model_count"]), receipt_path)
