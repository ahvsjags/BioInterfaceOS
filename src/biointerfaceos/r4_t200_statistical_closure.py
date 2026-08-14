"""Close the statistical-contract gaps identified in the R4 editorial review.

T200 does not refit a model or alter a frozen result.  It audits the published
T197/T198 artifacts and adds the missing, deterministic reporting layer:

* measurement-batch cluster intervals for every T197 held-out fold/model;
* a single primary estimand and an explicit descriptive multiplicity policy;
* stratified missingness and qualification tables for the paper cohort; and
* a receipt tying every closure artifact to the existing T197/T198 hashes.

The source data remain paper-attached and the evidence class remains
exploratory.  This task improves statistical completeness; it cannot create
independent external validation or external-participant evidence.
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

import numpy as np

from biointerfaceos.r3_uniprot_mapping import _canonical, _checksum, _mapping, _sha256, _string


class R4T200StatisticalClosureError(RuntimeError):
    """Raised when the statistical closure cannot verify its frozen inputs."""


@dataclass(frozen=True)
class R4T200StatisticalClosureSummary:
    t197_fold_interval_count: int
    t198_stratum_count: int
    t198_threshold_stratum_count: int
    receipt_path: Path


class R4T200StatisticalClosureWorkflow:
    """Audit T197/T198 outputs without changing their fitted models."""

    AUDIT_ID = "bioif-r4-t200-statistical-closure-v1.0.0"
    STATUS = "T200_STATISTICAL_CLOSURE_COMPLETED_EXPLORATORY"
    PROTOCOL_RELATIVE = "docs/data/R4_T200_STATISTICAL_CLOSURE_PROTOCOL.json"
    OUTPUT_RELATIVE = "reports/review_round_4/t200_statistical_closure/v1.0.0"
    T197_REPORT = "reports/review_round_4/t197_source_availability_execution/v1.0.0/t197_source_availability_execution_report.json"  # noqa: E501
    T197_BATCH = "reports/review_round_4/t197_source_availability_execution/v1.0.0/outer_fold_batch_metrics.csv"
    T198_SOURCE = "data/raw/r4_candidate_pxd017052_nsclc/derived/R4_PXD017052_NSCLC_source_cell_map.csv"
    T198_SUMMARY = "reports/review_round_4/t198_paper_cohort_missingness/v1.0.0/threshold_summary.csv"
    REQUIRED_REFERENCE = {"relative_path", "sha256"}
    METRICS = ("spearman", "mae", "rmse")
    MODELS = (
        "CONSTANT_TRAINING_MEAN",
        "SEQUENCE_RIDGE_FULL",
        "SEQUENCE_RIDGE_COMPOSITION_ONLY",
    )
    STRATA = ("biological_unit_id", "clinical_group", "particle")

    def __init__(self, root: Path, *, output_root: Path | None = None) -> None:
        self.root = root.resolve(strict=True)
        candidate = (output_root or self.root / self.OUTPUT_RELATIVE).resolve(strict=False)
        if not candidate.is_relative_to(self.root):
            raise R4T200StatisticalClosureError("T200 output must remain under repository root")
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
            raise R4T200StatisticalClosureError(f"cannot parse {label}") from exc

    @staticmethod
    def _csv(path: Path, label: str) -> list[dict[str, str]]:
        try:
            with path.open("r", encoding="utf-8", newline="") as stream:
                rows = list(csv.DictReader(stream))
        except OSError as exc:
            raise R4T200StatisticalClosureError(f"cannot read {label}") from exc
        if not rows or not rows[0]:
            raise R4T200StatisticalClosureError(f"{label} is empty")
        return rows

    def _file(self, relative: str, label: str) -> Path:
        pure = PurePosixPath(relative)
        if pure.is_absolute() or not pure.parts or ".." in pure.parts:
            raise R4T200StatisticalClosureError(f"{label} escapes repository root")
        path = (self.root / Path(*pure.parts)).resolve(strict=False)
        if not path.is_relative_to(self.root) or not path.is_file():
            raise R4T200StatisticalClosureError(f"{label} is missing")
        return path

    def _reference(self, value: Any, label: str) -> Path:
        reference = _mapping(value, label)
        if set(reference) != self.REQUIRED_REFERENCE:
            raise R4T200StatisticalClosureError(f"{label} reference fields are invalid")
        path = self._file(_string(reference["relative_path"], label), label)
        if _sha256(path) != _checksum(reference["sha256"], label):
            raise R4T200StatisticalClosureError(f"{label} checksum differs")
        return path

    @staticmethod
    def _cluster_interval(values: Sequence[float], *, resamples: int, seed: int) -> dict[str, Any]:
        array = np.asarray(values, dtype=float)
        if not len(array) or not np.all(np.isfinite(array)):
            raise R4T200StatisticalClosureError("cluster interval values are invalid")
        rng = np.random.default_rng(seed)
        draws = array[rng.integers(0, len(array), size=(resamples, len(array)))].mean(axis=1)
        lower, upper = np.quantile(draws, [0.025, 0.975], method="linear")
        return {
            "resamples": resamples,
            "seed": seed,
            "lower_95": float(lower),
            "upper_95": float(upper),
        }

    @staticmethod
    def _holm(p_values: Sequence[float]) -> list[float]:
        indexed = sorted(enumerate(p_values), key=lambda item: item[1])
        adjusted = [0.0] * len(p_values)
        running = 0.0
        for rank, (index, value) in enumerate(indexed, start=1):
            running = max(running, min(1.0, (len(p_values) - rank + 1) * value))
            adjusted[index] = running
        return adjusted

    def _t197_intervals(
        self, batch_rows: Sequence[Mapping[str, str]], protocol: Mapping[str, Any]
    ) -> list[dict[str, Any]]:
        uncertainty = _mapping(protocol["uncertainty"], "T200 T197 uncertainty")
        resamples = int(uncertainty["resamples"])
        seed_base = int(uncertainty["random_seed_base"])
        output: list[dict[str, Any]] = []
        for fold in sorted({row["outer_fold_id"] for row in batch_rows}):
            for model_index, model in enumerate(self.MODELS, start=1):
                selected = [row for row in batch_rows if row["outer_fold_id"] == fold and row["model_id"] == model]
                for metric_index, metric in enumerate(self.METRICS, start=1):
                    values = [float(row[metric]) for row in selected if row.get(metric, "") not in (None, "")]
                    if not values:
                        output.append(
                            {
                                "outer_fold_id": fold,
                                "model_id": model,
                                "metric": metric,
                                "cluster": "measurement_batch",
                                "cluster_count": 0,
                                "point_estimate": None,
                                "interval_status": "UNDEFINED_CONSTANT_PREDICTION",
                                "resamples": resamples,
                                "seed": None,
                                "lower_95": None,
                                "upper_95": None,
                            }
                        )
                        continue
                    seed = seed_base + int(fold.rsplit("_", 1)[-1]) * 1000 + model_index * 100 + metric_index
                    interval = self._cluster_interval(values, resamples=resamples, seed=seed)
                    output.append(
                        {
                            "outer_fold_id": fold,
                            "model_id": model,
                            "metric": metric,
                            "cluster": "measurement_batch",
                            "cluster_count": len(values),
                            "point_estimate": float(np.mean(values)),
                            "interval_status": "DEFINED",
                            **interval,
                        }
                    )
        return output

    @staticmethod
    def _t198_strata(
        source_rows: Sequence[Mapping[str, str]], thresholds: Sequence[int]
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        batch_meta: dict[str, dict[str, str]] = {}
        batch_positive: defaultdict[str, int] = defaultdict(int)
        batch_rows: defaultdict[str, list[Mapping[str, str]]] = defaultdict(list)
        for row in source_rows:
            batch = row["measurement_batch_id"]
            batch_meta.setdefault(batch, dict(row))
            batch_rows[batch].append(row)
            if row.get("rank_target_eligible", "").lower() == "true":
                batch_positive[batch] += 1
        strata_rows: list[dict[str, Any]] = []
        threshold_rows: list[dict[str, Any]] = []
        for dimension in R4T200StatisticalClosureWorkflow.STRATA:
            strata = sorted({row[dimension] for row in source_rows})
            for stratum in strata:
                rows = [row for row in source_rows if row[dimension] == stratum]
                batches = sorted({row["measurement_batch_id"] for row in rows})
                positive = sum(row.get("rank_target_eligible", "").lower() == "true" for row in rows)
                missing = sum(row.get("author_value_state") == "AUTHOR_NA" for row in rows)
                zero = sum(row.get("author_value_state") == "AUTHOR_EXPLICIT_ZERO" for row in rows)
                strata_rows.append(
                    {
                        "dimension": dimension,
                        "stratum": stratum,
                        "source_row_count": len(rows),
                        "positive_row_count": positive,
                        "author_na_row_count": missing,
                        "explicit_zero_row_count": zero,
                        "na_fraction": missing / len(rows) if rows else None,
                        "measurement_batch_count": len(batches),
                        "biological_unit_count": len({row["biological_unit_id"] for row in rows}),
                        "qualification_threshold_reference": "threshold_grid",
                    }
                )
                for threshold in thresholds:
                    qualified = [batch for batch in batches if batch_positive[batch] >= threshold]
                    threshold_rows.append(
                        {
                            "threshold": threshold,
                            "dimension": dimension,
                            "stratum": stratum,
                            "measurement_batch_count": len(batches),
                            "qualified_batch_count": len(qualified),
                            "qualification_rate": len(qualified) / len(batches) if batches else None,
                            "biological_unit_count": len(
                                {batch_meta[batch]["biological_unit_id"] for batch in qualified}
                            ),
                        }
                    )
        return strata_rows, threshold_rows

    def run(self, *, strict: bool = False) -> R4T200StatisticalClosureSummary:
        if not strict:
            raise R4T200StatisticalClosureError("T200 execution requires --strict")
        if self.output_root.exists():
            raise R4T200StatisticalClosureError("T200 execution already exists")
        protocol = self._json(self._file(self.PROTOCOL_RELATIVE, "T200 protocol"), "T200 protocol")
        if protocol.get("protocol_id") != self.AUDIT_ID or protocol.get("scientific_submission_ready") is not False:
            raise R4T200StatisticalClosureError("T200 protocol identity or claim boundary is invalid")
        t197_report_path = self._file(self.T197_REPORT, "T197 report")
        t197_batch_path = self._file(self.T197_BATCH, "T197 batch metrics")
        t198_source_path = self._file(self.T198_SOURCE, "T198 source map")
        t198_summary_path = self._file(self.T198_SUMMARY, "T198 threshold summary")
        t197_report = self._json(t197_report_path, "T197 report")
        t197_rows = self._csv(t197_batch_path, "T197 batch metrics")
        source_rows = self._csv(t198_source_path, "T198 source map")
        threshold_rows = self._csv(t198_summary_path, "T198 threshold summary")
        thresholds = [int(row["minimum_mapped_positive_proteins_per_batch"]) for row in threshold_rows]
        t197_intervals = self._t197_intervals(t197_rows, protocol)
        strata_rows, threshold_strata_rows = self._t198_strata(source_rows, thresholds)
        negative = [
            row
            for row in t197_report.get("negative_control_summary", [])
            if row.get("one_sided_upper_tail_p") is not None
        ]
        raw_p = [float(row["one_sided_upper_tail_p"]) for row in negative]
        holm = self._holm(raw_p) if raw_p else []
        multiplicity_rows = [
            {
                "family": "T197_outer_fold_negative_control",
                "hypothesis_id": f"{row['outer_fold_id']}_full_primary_spearman",
                "outer_fold_id": row["outer_fold_id"],
                "raw_p": float(row["one_sided_upper_tail_p"]),
                "holm_adjusted_p": float(holm[index]),
                "claim_status": "DESCRIPTIVE_EXPLORATORY_ONLY",
            }
            for index, row in enumerate(negative)
        ]
        output = self.output_root
        output.mkdir(parents=True, exist_ok=False)
        paths = {
            "t197_intervals": output / "t197_fold_metric_cluster_intervals.csv",
            "t198_strata": output / "t198_missingness_stratified.csv",
            "t198_threshold_strata": output / "t198_threshold_qualification_by_stratum.csv",
            "multiplicity": output / "multiplicity_policy_results.csv",
            "estimand": output / "estimand_contract.json",
        }
        self._write_csv(paths["t197_intervals"], list(t197_intervals[0]), t197_intervals)
        self._write_csv(paths["t198_strata"], list(strata_rows[0]), strata_rows)
        self._write_csv(paths["t198_threshold_strata"], list(threshold_strata_rows[0]), threshold_strata_rows)
        self._write_csv(
            paths["multiplicity"],
            list(multiplicity_rows[0])
            if multiplicity_rows
            else [
                "family",
                "hypothesis_id",
                "outer_fold_id",
                "raw_p",
                "holm_adjusted_p",
                "claim_status",
            ],
            multiplicity_rows,
        )
        estimand = protocol["estimands"]
        self._write_json(paths["estimand"], estimand)
        artifacts = {
            name: {"relative_path": path.relative_to(self.root).as_posix(), "sha256": _sha256(path)}
            for name, path in paths.items()
        }
        input_hashes = {
            "protocol": {
                "relative_path": self.PROTOCOL_RELATIVE,
                "sha256": _sha256(self._file(self.PROTOCOL_RELATIVE, "T200 protocol")),
            },
            "t197_report": {"relative_path": self.T197_REPORT, "sha256": _sha256(t197_report_path)},
            "t197_batch_metrics": {
                "relative_path": self.T197_BATCH,
                "sha256": _sha256(t197_batch_path),
            },
            "t198_source_map": {
                "relative_path": self.T198_SOURCE,
                "sha256": _sha256(t198_source_path),
            },
            "t198_threshold_summary": {
                "relative_path": self.T198_SUMMARY,
                "sha256": _sha256(t198_summary_path),
            },
        }
        report = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "protocol_id": protocol["protocol_id"],
            "protocol_sha256": input_hashes["protocol"]["sha256"],
            "execution_module_sha256": _sha256(Path(__file__).resolve(strict=True)),
            "status": self.STATUS,
            "evidence_class": "DEVELOPMENT_OBSERVATION",
            "allowed_claim_level": "EXPLORATORY",
            "input_references": input_hashes,
            "t197_fold_metric_cluster_interval_count": len(t197_intervals),
            "t198_missingness_stratum_count": len(strata_rows),
            "t198_threshold_stratum_count": len(threshold_strata_rows),
            "multiplicity_family_count": len({row["family"] for row in multiplicity_rows}),
            "artifacts": artifacts,
            "claim_boundary": protocol["claim_boundary"],
            "independent_validation": False,
            "external_scientific_reproduction": False,
            "scientific_submission_ready": False,
        }
        report_path = output / "t200_statistical_closure_report.json"
        self._write_json(report_path, report)
        receipt = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "status": self.STATUS,
            "report_sha256": _sha256(report_path),
            "t197_fold_metric_interval_count": len(t197_intervals),
            "t198_stratum_count": len(strata_rows),
            "t198_threshold_stratum_count": len(threshold_strata_rows),
            "estimand_frozen": True,
            "multiplicity_policy_frozen": True,
            "missingness_stratified": True,
            "independent_validation": False,
            "external_scientific_reproduction": False,
            "scientific_submission_ready": False,
        }
        receipt_path = output / "t200_statistical_closure_receipt.json"
        self._write_json(receipt_path, receipt)
        return R4T200StatisticalClosureSummary(
            len(t197_intervals), len(strata_rows), len(threshold_strata_rows), receipt_path
        )

    def verify(self, *, strict: bool = True) -> R4T200StatisticalClosureSummary:
        if not strict:
            raise R4T200StatisticalClosureError("T200 verification requires --strict")
        report_path = self._file(f"{self.OUTPUT_RELATIVE}/t200_statistical_closure_report.json", "T200 report")
        receipt_path = self._file(f"{self.OUTPUT_RELATIVE}/t200_statistical_closure_receipt.json", "T200 receipt")
        report = self._json(report_path, "T200 report")
        receipt = self._json(receipt_path, "T200 receipt")
        artifacts = _mapping(report.get("artifacts"), "T200 artifacts")
        for value in artifacts.values():
            item = _mapping(value, "T200 artifact")
            if set(item) != self.REQUIRED_REFERENCE:
                raise R4T200StatisticalClosureError("T200 artifact reference fields are invalid")
            path = self._file(_string(item["relative_path"], "T200 artifact"), "T200 artifact")
            if _sha256(path) != _checksum(item["sha256"], "T200 artifact"):
                raise R4T200StatisticalClosureError("T200 artifact checksum differs")
        if (
            report.get("audit_id") != self.AUDIT_ID
            or report.get("status") != self.STATUS
            or report.get("scientific_submission_ready") is not False
            or receipt.get("audit_id") != self.AUDIT_ID
            or receipt.get("status") != self.STATUS
            or receipt.get("report_sha256") != _sha256(report_path)
            or receipt.get("estimand_frozen") is not True
            or receipt.get("multiplicity_policy_frozen") is not True
            or receipt.get("missingness_stratified") is not True
            or receipt.get("scientific_submission_ready") is not False
        ):
            raise R4T200StatisticalClosureError("T200 receipt is invalid")
        return R4T200StatisticalClosureSummary(
            int(receipt["t197_fold_metric_interval_count"]),
            int(receipt["t198_stratum_count"]),
            int(receipt["t198_threshold_stratum_count"]),
            receipt_path,
        )
