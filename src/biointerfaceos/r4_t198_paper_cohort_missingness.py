"""Execute pre-registered missingness and coverage sensitivity on the paper cohort.

The primary T181 analysis keeps the published ``>=10`` positive-protein gate.
T198 does not replace that analysis; it reports a threshold grid and a fully
nested within-development permutation for the primary threshold.  No source NA
or explicit zero is imputed, and biological-unit clusters remain the uncertainty
unit.
"""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence

import numpy as np

from biointerfaceos.r3_analysis_protocol import R3AnalysisProtocolWorkflow
from biointerfaceos.r3_model_evaluation import R3ModelEvaluationError, R3ModelEvaluationWorkflow, _Observation
from biointerfaceos.r3_uniprot_mapping import _canonical, _checksum, _mapping, _sha256, _string
from biointerfaceos.r4_pxd017052_nsclc_biological_ood import (
    R4PXD017052NSCLCBOODWorkflow,
)
from biointerfaceos.r4_pxd017052_nsclc_source_audit import (
    R4PXD017052NSCLCSourceAuditError,
    R4PXD017052NSCLCSourceAuditWorkflow,
)


class R4T198MissingnessError(RuntimeError):
    """Raised when the T198 sensitivity cannot close its frozen inputs."""


@dataclass(frozen=True)
class R4T198MissingnessSummary:
    threshold_count: int
    primary_threshold: int
    primary_batch_count: int
    primary_biological_unit_count: int
    primary_observation_count: int
    receipt_path: Path


class R4T198PaperCohortMissingnessWorkflow:
    """Run threshold, retention and selection-aware negative-control sensitivity."""

    AUDIT_ID = "bioif-r4-t198-paper-cohort-missingness-v1.0.0"
    STATUS = "T198_PAPER_COHORT_MISSINGNESS_EXECUTED_EXPLORATORY"
    PROTOCOL_RELATIVE = "docs/data/R4_T198_PAPER_COHORT_MISSINGNESS_PROTOCOL.json"
    REGISTRY_RELATIVE = "docs/data/R4_T198_PAPER_COHORT_MISSINGNESS_REGISTRY.json"
    SOURCE_MAP_RELATIVE = "data/raw/r4_candidate_pxd017052_nsclc/derived/R4_PXD017052_NSCLC_source_cell_map.csv"
    SOURCE_AUDIT_RECEIPT_RELATIVE = "reports/review_round_4/pxd017052_nsclc_source_audit/v1.0.0/pxd017052_nsclc_source_audit_receipt.json"
    R3_LEDGER_RELATIVE = "data/raw/r3_common_rank_target/R3_common_rank_target_ledger.csv"
    FEATURE_RELATIVE = "data/raw/r3_uniprot_sequence_features/uniprot_sequence_features/R3_uniprot_sequence_features.csv"
    OUTPUT_RELATIVE = "reports/review_round_4/t198_paper_cohort_missingness/v1.0.0"
    REQUIRED_REFERENCE = {"relative_path", "sha256"}
    MODEL_IDS = R3ModelEvaluationWorkflow.MODEL_IDS

    def __init__(self, root: Path, *, output_root: Path | None = None) -> None:
        self.root = root.resolve(strict=True)
        candidate = (output_root or self.root / self.OUTPUT_RELATIVE).resolve(strict=False)
        if not candidate.is_relative_to(self.root):
            raise R4T198MissingnessError("T198 output must remain under repository root")
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
            raise R4T198MissingnessError(f"cannot parse {label}") from exc

    def _root_file(self, relative_path: str, label: str) -> Path:
        if "\\" in relative_path:
            raise R4T198MissingnessError(f"{label} must use POSIX separators")
        pure = PurePosixPath(relative_path)
        if pure.is_absolute() or not pure.parts or ".." in pure.parts:
            raise R4T198MissingnessError(f"{label} escapes repository root")
        path = (self.root / Path(*pure.parts)).resolve(strict=False)
        if not path.is_relative_to(self.root) or not path.is_file():
            raise R4T198MissingnessError(f"{label} is missing or outside repository root")
        return path

    def _reference(self, value: Any, label: str) -> Path:
        reference = _mapping(value, label)
        if set(reference) != self.REQUIRED_REFERENCE:
            raise R4T198MissingnessError(f"{label} reference fields are invalid")
        path = self._root_file(_string(reference["relative_path"], label), label)
        if _sha256(path) != _checksum(reference["sha256"], label):
            raise R4T198MissingnessError(f"{label} checksum differs")
        return path

    @staticmethod
    def _read_csv(path: Path, label: str) -> list[dict[str, str]]:
        try:
            with path.open("r", encoding="utf-8", newline="") as stream:
                rows = list(csv.DictReader(stream))
        except OSError as exc:
            raise R4T198MissingnessError(f"cannot read {label}") from exc
        if not rows or not rows[0]:
            raise R4T198MissingnessError(f"{label} is empty")
        return rows

    def _registry(self) -> tuple[dict[str, Any], dict[str, Any], dict[str, Path]]:
        registry = self._json(self.root / self.REGISTRY_RELATIVE, "T198 registry")
        required = {
            "schema_version", "audit_id", "protocol_id", "status", "evidence_class",
            "allowed_claim_level", "protocol", "source_map", "source_audit_receipt",
            "r3_common_target_ledger", "r3_sequence_feature_table", "output_contract",
            "claim_boundary", "scientific_submission_ready",
        }
        if set(registry) != required or registry.get("schema_version") != 1:
            raise R4T198MissingnessError("T198 registry fields are invalid")
        if (
            registry.get("audit_id") != self.AUDIT_ID
            or registry.get("protocol_id") != self.AUDIT_ID
            or registry.get("status") != "T198_PAPER_COHORT_MISSINGNESS_REGISTERED"
            or registry.get("evidence_class") != "DEVELOPMENT_OBSERVATION"
            or registry.get("allowed_claim_level") != "EXPLORATORY"
            or registry.get("scientific_submission_ready") is not False
        ):
            raise R4T198MissingnessError("T198 registry identity or boundary is invalid")
        protocol_path = self._reference(registry["protocol"], "T198 protocol")
        protocol = self._json(protocol_path, "T198 protocol")
        if (
            protocol.get("protocol_id") != self.AUDIT_ID
            or protocol.get("status") != "FROZEN_BEFORE_T198_EXECUTION"
            or protocol.get("scientific_submission_ready") is not False
        ):
            raise R4T198MissingnessError("T198 protocol identity or boundary is invalid")
        refs = {
            "protocol": protocol_path,
            "source_map": self._reference(registry["source_map"], "T198 source map"),
            "source_audit_receipt": self._reference(registry["source_audit_receipt"], "T198 source audit receipt"),
            "r3_common_target_ledger": self._reference(registry["r3_common_target_ledger"], "R3 target ledger"),
            "r3_sequence_feature_table": self._reference(registry["r3_sequence_feature_table"], "R3 feature table"),
        }
        expected = {
            "source_map": self.root / self.SOURCE_MAP_RELATIVE,
            "source_audit_receipt": self.root / self.SOURCE_AUDIT_RECEIPT_RELATIVE,
            "r3_common_target_ledger": self.root / self.R3_LEDGER_RELATIVE,
            "r3_sequence_feature_table": self.root / self.FEATURE_RELATIVE,
        }
        if any(refs[key] != path for key, path in expected.items()):
            raise R4T198MissingnessError("T198 registry paths are not release-fixed")
        return registry, protocol, refs

    @staticmethod
    def _features(helper: R3ModelEvaluationWorkflow, rows: Sequence[_Observation]) -> dict[str, tuple[float, ...]]:
        return {row.canonical_accession: row.feature_values for row in rows}

    def _external_at_threshold(
        self,
        rows: Sequence[Mapping[str, str]],
        features: Mapping[str, tuple[float, ...]],
        threshold: int,
    ) -> tuple[list[_Observation], dict[str, str], dict[str, int]]:
        ranks = R4PXD017052NSCLCBOODWorkflow._rank_percentiles(rows)
        batch_to_unit = {row["measurement_batch_id"]: row["biological_unit_id"] for row in rows}
        mapped_positive: dict[str, int] = defaultdict(int)
        for row in rows:
            if row.get("rank_target_eligible") == "true" and row.get("canonical_accession") in features:
                mapped_positive[row["measurement_batch_id"]] += 1
        qualified = {batch for batch, count in mapped_positive.items() if count >= threshold}
        observations: list[_Observation] = []
        for row in rows:
            batch_id = row["measurement_batch_id"]
            accession = row.get("canonical_accession", "")
            rank = ranks.get(f"{batch_id}:{row['source_coordinate']}")
            if batch_id not in qualified or rank is None or accession not in features:
                continue
            observations.append(
                _Observation(
                    f"T198:{batch_id}:{row['source_coordinate']}",
                    row["source_id"],
                    accession,
                    row["laboratory_anchor"],
                    batch_id,
                    rank[0],
                    features[accession],
                )
            )
        if not observations:
            raise R4T198MissingnessError(f"T198 threshold {threshold} has no observations")
        return observations, batch_to_unit, dict(mapped_positive)

    @staticmethod
    def _unit_retention(
        observations: Sequence[_Observation], batch_to_unit: Mapping[str, str]
    ) -> dict[str, int]:
        return {
            unit: sum(1 for row in observations if batch_to_unit[row.measurement_batch_id] == unit)
            for unit in sorted(set(batch_to_unit[row.measurement_batch_id] for row in observations))
        }

    def run(self, *, strict: bool = False) -> R4T198MissingnessSummary:
        if not strict:
            raise R4T198MissingnessError("T198 execution requires --strict")
        if self.output_root.exists():
            raise R4T198MissingnessError("T198 execution already exists")
        _, protocol, refs = self._registry()
        try:
            R3AnalysisProtocolWorkflow(self.root, self.root / "data/raw").verify()
            R4PXD017052NSCLCSourceAuditWorkflow(
                self.root, self.root / "data/raw/r4_candidate_pxd017052_nsclc"
            ).verify()
        except (R4PXD017052NSCLCSourceAuditError, R3ModelEvaluationError, OSError) as exc:
            raise R4T198MissingnessError("T198 frozen source or R3 receipt does not verify") from exc
        helper = R3ModelEvaluationWorkflow(
            self.root, self.root / "data/raw", self.root / "data/raw/r3_uniprot_sequence_features"
        )
        try:
            development, accessions = helper._observations(
                refs["r3_common_target_ledger"], refs["r3_sequence_feature_table"]
            )
        except R3ModelEvaluationError as exc:
            raise R4T198MissingnessError("T198 R3 development observations are invalid") from exc
        features = self._features(helper, development)
        source_rows = self._read_csv(refs["source_map"], "T198 source map")
        thresholds = [int(item) for item in protocol["threshold_sensitivity"]["minimum_mapped_positive_proteins_per_batch"]]
        primary_threshold = int(protocol["primary_threshold"])
        if primary_threshold not in thresholds:
            raise R4T198MissingnessError("T198 primary threshold is not in the frozen grid")
        nested = _mapping(protocol["nested_selection"], "T198 nested selection")
        minimum_selection = int(nested["minimum_proteins_per_batch"])
        full_indices = tuple(range(len(helper.FEATURE_NAMES)))
        composition_indices = tuple(
            helper.FEATURE_NAMES.index(name) for name in helper.COMPOSITION_FEATURE_NAMES
        )
        full_alpha, full_selection = helper._select_alpha(
            development, full_indices, minimum_proteins=minimum_selection
        )
        composition_alpha, composition_selection = helper._select_alpha(
            development, composition_indices, minimum_proteins=minimum_selection
        )
        full_model = helper._fit_ridge(development, full_indices, full_alpha)
        composition_model = helper._fit_ridge(development, composition_indices, composition_alpha)
        threshold_rows: list[dict[str, Any]] = []
        metric_rows: list[dict[str, Any]] = []
        paired_rows: list[dict[str, Any]] = []
        unit_rows: list[dict[str, Any]] = []
        primary_external: list[_Observation] = []
        primary_batch_to_unit: dict[str, str] = {}
        uncertainty = _mapping(protocol["uncertainty"], "T198 uncertainty")
        for threshold in thresholds:
            external, batch_to_unit, mapped_positive = self._external_at_threshold(
                source_rows, features, threshold
            )
            if threshold == primary_threshold:
                primary_external = external
                primary_batch_to_unit = batch_to_unit
            retained_units = self._unit_retention(external, batch_to_unit)
            threshold_rows.append(
                {
                    "minimum_mapped_positive_proteins_per_batch": threshold,
                    "external_observation_count": len(external),
                    "measurement_batch_count": len({row.measurement_batch_id for row in external}),
                    "biological_unit_count": len(retained_units),
                    "all_source_map_measurement_batch_count": len(batch_to_unit),
                    "batch_retention_fraction": len({row.measurement_batch_id for row in external}) / len(batch_to_unit),
                    "biological_unit_retention_fraction": len(retained_units) / len(set(batch_to_unit.values())),
                    "source_value_state_counts": dict(Counter(row.get("author_value_state", "") for row in source_rows)),
                    "source_na_row_count": sum(row.get("author_value_state") == "AUTHOR_NA" for row in source_rows),
                    "source_explicit_zero_row_count": sum(row.get("author_value_state") == "AUTHOR_EXPLICIT_ZERO" for row in source_rows),
                }
            )
            predictions = {
                "SEQUENCE_RIDGE_FULL": helper._predict_ridge(full_model, external),
                "SEQUENCE_RIDGE_COMPOSITION_ONLY": helper._predict_ridge(composition_model, external),
            }
            metrics_by_model: dict[str, list[dict[str, Any]]] = {}
            for model_id, prediction in predictions.items():
                metrics = helper._batch_metrics(external, prediction, minimum_proteins=threshold)
                aggregate, by_unit = R4PXD017052NSCLCBOODWorkflow._subject_metrics(metrics, batch_to_unit)
                spearman_ci = R4PXD017052NSCLCBOODWorkflow._cluster_bootstrap(
                    by_unit, "spearman", resamples=int(uncertainty["resamples"]), seed=int(uncertainty["random_seed"]) + threshold
                )
                mae_ci = R4PXD017052NSCLCBOODWorkflow._cluster_bootstrap(
                    by_unit, "mae", resamples=int(uncertainty["resamples"]), seed=int(uncertainty["random_seed"]) + threshold + 100
                )
                rmse_ci = R4PXD017052NSCLCBOODWorkflow._cluster_bootstrap(
                    by_unit, "rmse", resamples=int(uncertainty["resamples"]), seed=int(uncertainty["random_seed"]) + threshold + 200
                )
                metric_rows.append(
                    {
                        "threshold": threshold,
                        "model_id": model_id,
                        "external_observation_count": len(external),
                        "measurement_batch_count": len(metrics),
                        "biological_unit_count": len(by_unit),
                        **aggregate,
                        "subject_equal_mean_spearman_lower_95": None if spearman_ci is None else spearman_ci["lower_95"],
                        "subject_equal_mean_spearman_upper_95": None if spearman_ci is None else spearman_ci["upper_95"],
                        "subject_equal_mean_mae_lower_95": None if mae_ci is None else mae_ci["lower_95"],
                        "subject_equal_mean_mae_upper_95": None if mae_ci is None else mae_ci["upper_95"],
                        "subject_equal_mean_rmse_lower_95": None if rmse_ci is None else rmse_ci["lower_95"],
                        "subject_equal_mean_rmse_upper_95": None if rmse_ci is None else rmse_ci["upper_95"],
                    }
                )
                for unit_id, values in by_unit.items():
                    unit_rows.append(
                        {
                            "threshold": threshold,
                            "model_id": model_id,
                            "biological_unit_id": unit_id,
                            "measurement_batch_count": retained_units[unit_id],
                            "subject_mean_spearman": values["spearman"],
                            "subject_mean_mae": values["mae"],
                            "subject_mean_rmse": values["rmse"],
                        }
                    )
                metrics_by_model[model_id] = metrics
            full_metrics = metrics_by_model["SEQUENCE_RIDGE_FULL"]
            composition_metrics = metrics_by_model["SEQUENCE_RIDGE_COMPOSITION_ONLY"]
            deltas = [
                float(full["spearman"]) - float(composition["spearman"])
                for full, composition in zip(full_metrics, composition_metrics, strict=True)
            ]
            paired_rows.append(
                {
                    "threshold": threshold,
                    "paired_measurement_batch_count": len(deltas),
                    "full_minus_composition_batch_mean_spearman": float(np.mean(deltas)),
                    **helper._bootstrap(
                        deltas,
                        resamples=int(uncertainty["resamples"]),
                        seed=int(uncertainty["random_seed"]) + threshold + 500,
                    ),
                }
            )
        negative = _mapping(protocol["negative_control"], "T198 negative control")
        primary_full = helper._predict_ridge(full_model, primary_external)
        primary_metrics = helper._batch_metrics(primary_external, primary_full, minimum_proteins=primary_threshold)
        primary_observed = R4PXD017052NSCLCBOODWorkflow._subject_metrics(primary_metrics, primary_batch_to_unit)[0]["subject_equal_mean_spearman"]
        if primary_observed is None:
            raise R4T198MissingnessError("T198 primary negative-control statistic is undefined")
        development_targets = np.asarray([row.target for row in development], dtype=float)
        by_batch: dict[str, list[int]] = defaultdict(list)
        for index, row in enumerate(development):
            by_batch[row.measurement_batch_id].append(index)
        rng = np.random.default_rng(int(negative["random_seed"]))
        null_rows: list[dict[str, Any]] = []
        null_scores: list[float] = []
        for resample in range(1, int(negative["resamples"]) + 1):
            permuted = development_targets.copy()
            for positions in by_batch.values():
                permuted[positions] = rng.permutation(permuted[positions])
            permuted_development = [
                _Observation(row.target_observation_id, row.source_id, row.canonical_accession,
                             row.laboratory_anchor, row.measurement_batch_id, float(target), row.feature_values)
                for row, target in zip(development, permuted, strict=True)
            ]
            alpha, _ = helper._select_alpha(
                permuted_development, full_indices, minimum_proteins=minimum_selection
            )
            model = helper._fit_ridge(permuted_development, full_indices, alpha, targets=permuted)
            metrics = helper._batch_metrics(
                primary_external, helper._predict_ridge(model, primary_external), minimum_proteins=primary_threshold
            )
            score = R4PXD017052NSCLCBOODWorkflow._subject_metrics(metrics, primary_batch_to_unit)[0]["subject_equal_mean_spearman"]
            if score is None:
                raise R4T198MissingnessError("T198 null primary statistic is undefined")
            null_scores.append(float(score))
            null_rows.append({"resample": resample, "selected_alpha": alpha, "null_subject_equal_mean_spearman": float(score)})
        paths = {
            "threshold_summary": self.output_root / "threshold_summary.csv",
            "threshold_model_metrics": self.output_root / "threshold_model_metrics.csv",
            "threshold_paired_ablation": self.output_root / "threshold_paired_ablation.csv",
            "unit_metrics": self.output_root / "threshold_unit_metrics.csv",
            "selection_aware_negative_control": self.output_root / "primary_selection_aware_negative_control.csv",
            "parameters": self.output_root / "parameters.json",
        }
        self.output_root.mkdir(parents=True, exist_ok=False)
        self._write_csv(paths["threshold_summary"], list(threshold_rows[0]), threshold_rows)
        self._write_csv(paths["threshold_model_metrics"], list(metric_rows[0]), metric_rows)
        self._write_csv(paths["threshold_paired_ablation"], list(paired_rows[0]), paired_rows)
        self._write_csv(paths["unit_metrics"], list(unit_rows[0]), unit_rows)
        self._write_csv(paths["selection_aware_negative_control"], list(null_rows[0]), null_rows)
        self._write_json(paths["parameters"], {
            "development_observation_count": len(development),
            "development_target_count": len(accessions),
            "full_selected_alpha": full_alpha,
            "composition_selected_alpha": composition_alpha,
            "primary_threshold": primary_threshold,
            "primary_observation_count": len(primary_external),
            "primary_measurement_batch_count": len({row.measurement_batch_id for row in primary_external}),
            "primary_biological_unit_count": len(set(primary_batch_to_unit.values())),
            "nested_selection_rows_full": full_selection,
            "nested_selection_rows_composition": composition_selection,
            "source_map_value_state_counts": dict(Counter(row.get("author_value_state", "") for row in source_rows)),
            "negative_control": {
                "resamples": int(negative["resamples"]),
                "selection_reexecuted_per_resample": True,
                "observed_subject_equal_mean_spearman": primary_observed,
                "null_mean": float(np.mean(null_scores)),
                "null_lower_95": float(np.quantile(null_scores, 0.025)),
                "null_upper_95": float(np.quantile(null_scores, 0.975)),
                "one_sided_upper_tail_p": float((1 + sum(value >= primary_observed for value in null_scores)) / (1 + len(null_scores))),
            },
        })
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
            "threshold_summary": threshold_rows,
            "model_results": metric_rows,
            "paired_ablation": paired_rows,
            "negative_control_summary": json.loads(paths["parameters"].read_text(encoding="utf-8"))["negative_control"],
            "artifacts": artifacts,
            "claim_boundary": protocol["claim_boundary"],
            "independent_validation": False,
            "external_scientific_reproduction": False,
            "scientific_submission_ready": False,
        }
        report_path = self.output_root / "t198_paper_cohort_missingness_report.json"
        self._write_json(report_path, report)
        receipt = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "status": self.STATUS,
            "report_sha256": _sha256(report_path),
            "threshold_count": len(thresholds),
            "primary_threshold": primary_threshold,
            "primary_batch_count": len({row.measurement_batch_id for row in primary_external}),
            "primary_biological_unit_count": len(set(primary_batch_to_unit.values())),
            "primary_observation_count": len(primary_external),
            "selection_reexecuted_in_negative_control": True,
            "independent_validation": False,
            "external_scientific_reproduction": False,
            "scientific_submission_ready": False,
        }
        receipt_path = self.output_root / "t198_paper_cohort_missingness_receipt.json"
        self._write_json(receipt_path, receipt)
        return R4T198MissingnessSummary(
            len(thresholds), primary_threshold, int(receipt["primary_batch_count"]),
            int(receipt["primary_biological_unit_count"]), int(receipt["primary_observation_count"]), receipt_path
        )

    def verify(self, *, strict: bool = True) -> R4T198MissingnessSummary:
        if not strict:
            raise R4T198MissingnessError("T198 verification requires --strict")
        _, protocol, _ = self._registry()
        report_path = self.output_root / "t198_paper_cohort_missingness_report.json"
        receipt_path = self.output_root / "t198_paper_cohort_missingness_receipt.json"
        report = self._json(report_path, "T198 report")
        receipt = self._json(receipt_path, "T198 receipt")
        artifacts = _mapping(report.get("artifacts"), "T198 artifacts")
        for value in artifacts.values():
            item = _mapping(value, "T198 artifact")
            if set(item) != self.REQUIRED_REFERENCE:
                raise R4T198MissingnessError("T198 artifact reference fields are invalid")
            path = self._root_file(_string(item["relative_path"], "T198 artifact path"), "T198 artifact")
            if _sha256(path) != _checksum(item["sha256"], "T198 artifact checksum"):
                raise R4T198MissingnessError("T198 artifact checksum differs")
        if (
            report.get("audit_id") != self.AUDIT_ID
            or report.get("status") != self.STATUS
            or report.get("scientific_submission_ready") is not False
            or receipt.get("audit_id") != self.AUDIT_ID
            or receipt.get("status") != self.STATUS
            or receipt.get("report_sha256") != _sha256(report_path)
            or receipt.get("selection_reexecuted_in_negative_control") is not True
            or receipt.get("scientific_submission_ready") is not False
        ):
            raise R4T198MissingnessError("T198 receipt is invalid")
        return R4T198MissingnessSummary(
            int(receipt["threshold_count"]), int(receipt["primary_threshold"]),
            int(receipt["primary_batch_count"]), int(receipt["primary_biological_unit_count"]),
            int(receipt["primary_observation_count"]), receipt_path
        )
