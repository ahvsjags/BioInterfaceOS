"""Route-specific estimand and paired-delta uncertainty correction for T284."""

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


class R4T290PaperOodUncertaintyError(RuntimeError):
    """Raised when the route-specific T290 correction cannot close."""


@dataclass(frozen=True)
class R4T290PaperOodUncertaintySummary:
    route_count: int
    supported_positive_count: int
    supported_negative_count: int
    indeterminate_count: int
    receipt_path: Path


class R4T290PaperOodUncertaintyWorkflow:
    AUDIT_ID = "bioif-r4-t290-paper-ood-uncertainty-v1.0.0"
    STATUS = "T290_ROUTE_SPECIFIC_ESTIMAND_AND_PAIRED_UNCERTAINTY_COMPLETED"
    PROTOCOL_RELATIVE = "docs/data/R4_T290_PAPER_OOD_UNCERTAINTY_PROTOCOL_20260815.json"
    OUTPUT_RELATIVE = "reports/review_round_4/t290_paper_ood_uncertainty/v1.0.0"
    ROUTES = (
        (
            "T203_PMC10257194",
            "reports/review_round_4/pmc10257194_paper_ood/v1.0.0/r4_external_ood_predictions.csv",
            "measurement_batch_id",
            "mean_batch_spearman",
            290203,
        ),
        (
            "T159_SMALL_MOLECULE",
            "reports/review_round_4/small_molecule_corona_ood/v1.0.0/r4_external_ood_predictions.csv",
            "measurement_batch_id",
            "mean_batch_spearman",
            290159,
        ),
        (
            "T209_MANCHESTER",
            "reports/review_round_4/manchester_nanoomic_ood/v1.1.0/r4_manchester_ood_predictions.csv",
            "biological_unit_id",
            "subject_equal_mean_spearman",
            290209,
        ),
        (
            "T181_PXD017052",
            "reports/review_round_4/pxd017052_nsclc_biological_ood/v1.0.0/r4_pxd017052_nsclc_ood_predictions.csv",
            "biological_unit_id",
            "subject_equal_mean_spearman",
            290181,
        ),
        (
            "T176_PXD068107",
            "reports/review_round_4/pxd068107_technical_ood/v1.0.0/r4_pxd068107_ood_predictions.csv",
            "measurement_batch_id",
            "mean_batch_spearman",
            290176,
        ),
        (
            "T177_PMC13106918",
            "reports/review_round_4/pmc13106918_technical_ood/v1.0.0/r4_pmc13106918_ood_predictions.csv",
            "measurement_batch_id",
            "mean_batch_spearman",
            290177,
        ),
    )

    def __init__(self, root: Path, *, output_root: Path | None = None) -> None:
        self.root = root.resolve(strict=True)
        candidate = (output_root or self.root / self.OUTPUT_RELATIVE).resolve(strict=False)
        if not candidate.is_relative_to(self.root):
            raise R4T290PaperOodUncertaintyError("T290 output must remain under repository root")
        self.output_root = candidate

    @staticmethod
    def _json(path: Path, label: str) -> dict[str, Any]:
        try:
            return _mapping(json.loads(path.read_text(encoding="utf-8")), label)
        except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
            raise R4T290PaperOodUncertaintyError(f"cannot parse {label}") from exc

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

    def _file(self, relative: str, label: str) -> Path:
        pure = PurePosixPath(relative)
        if pure.is_absolute() or not pure.parts or ".." in pure.parts:
            raise R4T290PaperOodUncertaintyError(f"{label} escapes repository root")
        path = (self.root / Path(*pure.parts)).resolve(strict=False)
        if not path.is_relative_to(self.root) or not path.is_file():
            raise R4T290PaperOodUncertaintyError(f"{label} is missing")
        return path

    def _reference(self, value: Any, label: str) -> Path:
        reference = _mapping(value, label)
        if set(reference) != {"relative_path", "sha256"}:
            raise R4T290PaperOodUncertaintyError(f"{label} reference fields are invalid")
        path = self._file(_string(reference["relative_path"], label), label)
        if _sha256(path) != _checksum(reference["sha256"], label):
            raise R4T290PaperOodUncertaintyError(f"{label} checksum differs")
        return path

    @staticmethod
    def _csv(path: Path, label: str) -> list[dict[str, str]]:
        try:
            with path.open("r", encoding="utf-8", newline="") as stream:
                rows = list(csv.DictReader(stream))
        except OSError as exc:
            raise R4T290PaperOodUncertaintyError(f"cannot read {label}") from exc
        if not rows or not rows[0]:
            raise R4T290PaperOodUncertaintyError(f"{label} is empty")
        return rows

    @staticmethod
    def _spearman(rows: Sequence[Mapping[str, str]], prediction_key: str) -> float:
        observed = np.asarray([float(row["observed_rank_percentile_descending"]) for row in rows], dtype=float)
        predicted = np.asarray([float(row[prediction_key]) for row in rows], dtype=float)
        if len(rows) < 2 or np.ptp(observed) == 0 or np.ptp(predicted) == 0:
            return float("nan")
        observed_rank = R4T290PaperOodUncertaintyWorkflow._average_rank(observed)
        predicted_rank = R4T290PaperOodUncertaintyWorkflow._average_rank(predicted)
        return float(np.corrcoef(observed_rank, predicted_rank)[0, 1])

    @staticmethod
    def _average_rank(values: np.ndarray) -> np.ndarray:
        """Return one-based average ranks, preserving ties for Spearman's rho."""
        order = np.argsort(values, kind="mergesort")
        sorted_values = values[order]
        ranks = np.empty(len(values), dtype=float)
        start = 0
        while start < len(values):
            end = start + 1
            while end < len(values) and sorted_values[end] == sorted_values[start]:
                end += 1
            ranks[order[start:end]] = (start + 1 + end) / 2.0
            start = end
        return ranks

    @staticmethod
    def _bootstrap(values: np.ndarray, seed: int) -> tuple[float, float]:
        if len(values) < 2:
            return float("nan"), float("nan")
        rng = np.random.default_rng(seed)
        sampled = rng.integers(0, len(values), size=(2000, len(values)))
        means = values[sampled].mean(axis=1)
        return float(np.quantile(means, 0.025)), float(np.quantile(means, 0.975))

    def _route(
        self, route_id: str, path: Path, cluster_field: str, metric_name: str, seed: int
    ) -> dict[str, Any]:
        rows = self._csv(path, route_id)
        required = {
            "model_id",
            "observed_rank_percentile_descending",
            "predicted_rank_percentile_descending",
            cluster_field,
        }
        if not required.issubset(rows[0]):
            raise R4T290PaperOodUncertaintyError(f"{route_id} prediction columns do not support {metric_name}")
        model_rows: dict[str, list[dict[str, str]]] = defaultdict(list)
        for row in rows:
            model_rows[row["model_id"]].append(row)
        full = model_rows.get("SEQUENCE_RIDGE_FULL", [])
        composition = model_rows.get("SEQUENCE_RIDGE_COMPOSITION_ONLY", [])
        if not full or not composition:
            raise R4T290PaperOodUncertaintyError(f"{route_id} is missing full/composition predictions")
        full_by_cluster: dict[str, list[dict[str, str]]] = defaultdict(list)
        composition_by_cluster: dict[str, list[dict[str, str]]] = defaultdict(list)
        for row in full:
            full_by_cluster[row[cluster_field]].append(row)
        for row in composition:
            composition_by_cluster[row[cluster_field]].append(row)
        clusters = sorted(set(full_by_cluster) & set(composition_by_cluster))
        deltas: list[float] = []
        full_metrics: list[float] = []
        composition_metrics: list[float] = []
        paired_observation_count = 0
        for cluster in clusters:
            full_value = self._spearman(full_by_cluster[cluster], "predicted_rank_percentile_descending")
            composition_value = self._spearman(composition_by_cluster[cluster], "predicted_rank_percentile_descending")
            if not np.isfinite(full_value) or not np.isfinite(composition_value):
                continue
            full_metrics.append(full_value)
            composition_metrics.append(composition_value)
            deltas.append(full_value - composition_value)
            paired_observation_count += min(len(full_by_cluster[cluster]), len(composition_by_cluster[cluster]))
        if not deltas:
            raise R4T290PaperOodUncertaintyError(f"{route_id} has no finite paired cluster metrics")
        delta_values = np.asarray(deltas, dtype=float)
        lower, upper = self._bootstrap(delta_values, seed)
        delta_mean = float(delta_values.mean())
        if lower > 0:
            status = "SUPPORTED_POSITIVE"
        elif upper < 0:
            status = "SUPPORTED_NEGATIVE"
        else:
            status = "INDETERMINATE"
        return {
            "route_id": route_id,
            "metric_name": metric_name,
            "cluster_unit": cluster_field,
            "cluster_count": len(deltas),
            "paired_observation_count": paired_observation_count,
            "full_metric_mean": float(np.mean(full_metrics)),
            "composition_metric_mean": float(np.mean(composition_metrics)),
            "paired_delta_mean": delta_mean,
            "paired_delta_lower_95": lower,
            "paired_delta_upper_95": upper,
            "paired_delta_status": status,
            "bootstrap_resamples": 2000,
            "bootstrap_seed": seed,
            "source_predictions_sha256": _sha256(path),
            "claim_status": "AUTHOR_RUN_ROUTE_SPECIFIC_UNCERTAINTY_ONLY",
        }

    def run(self, *, strict: bool = False) -> R4T290PaperOodUncertaintySummary:
        if not strict:
            raise R4T290PaperOodUncertaintyError("T290 execution requires --strict")
        if self.output_root.exists():
            raise R4T290PaperOodUncertaintyError("T290 execution already exists")
        protocol_path = self._file(self.PROTOCOL_RELATIVE, "T290 protocol")
        protocol = self._json(protocol_path, "T290 protocol")
        if protocol.get("protocol_id") != self.AUDIT_ID or protocol.get("scientific_submission_ready") is not False:
            raise R4T290PaperOodUncertaintyError("T290 protocol identity or claim boundary is invalid")
        references = _mapping(protocol["input_artifacts"], "T290 input artifacts")
        rows = []
        for route_id, _relative, cluster_field, metric_name, seed in self.ROUTES:
            path = self._reference(references[route_id], route_id)
            rows.append(self._route(route_id, path, cluster_field, metric_name, seed))
        fields = list(rows[0])
        self.output_root.mkdir(parents=True, exist_ok=False)
        effects_path = self.output_root / "route_specific_paired_uncertainty.csv"
        self._write_csv(effects_path, fields, rows)
        report = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "status": self.STATUS,
            "protocol_sha256": _sha256(protocol_path),
            "execution_module_sha256": _sha256(Path(__file__).resolve(strict=True)),
            "route_count": len(rows),
            "supported_positive_count": sum(row["paired_delta_status"] == "SUPPORTED_POSITIVE" for row in rows),
            "supported_negative_count": sum(row["paired_delta_status"] == "SUPPORTED_NEGATIVE" for row in rows),
            "indeterminate_count": sum(row["paired_delta_status"] == "INDETERMINATE" for row in rows),
            "pooling_prohibited": True,
            "independent_validation": False,
            "external_scientific_reproduction": False,
            "scientific_submission_ready": False,
            "routes": rows,
            "artifacts": {
                "route_specific_paired_uncertainty": {
                    "relative_path": effects_path.relative_to(self.root).as_posix(),
                    "sha256": _sha256(effects_path),
                }
            },
            "claim_boundary": protocol["claim_boundary"],
        }
        report_path = self.output_root / "t290_paper_ood_uncertainty_report.json"
        self._write_json(report_path, report)
        receipt = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "status": self.STATUS,
            "report_sha256": _sha256(report_path),
            "route_count": len(rows),
            "supported_positive_count": report["supported_positive_count"],
            "supported_negative_count": report["supported_negative_count"],
            "indeterminate_count": report["indeterminate_count"],
            "pooling_prohibited": True,
            "independent_validation": False,
            "external_scientific_reproduction": False,
            "scientific_submission_ready": False,
        }
        receipt_path = self.output_root / "t290_paper_ood_uncertainty_receipt.json"
        self._write_json(receipt_path, receipt)
        return R4T290PaperOodUncertaintySummary(
            len(rows),
            report["supported_positive_count"],
            report["supported_negative_count"],
            report["indeterminate_count"],
            receipt_path,
        )

    def verify(self, *, strict: bool = True) -> R4T290PaperOodUncertaintySummary:
        if not strict:
            raise R4T290PaperOodUncertaintyError("T290 verification requires --strict")
        report_path = self._file(f"{self.OUTPUT_RELATIVE}/t290_paper_ood_uncertainty_report.json", "T290 report")
        receipt_path = self._file(f"{self.OUTPUT_RELATIVE}/t290_paper_ood_uncertainty_receipt.json", "T290 receipt")
        report = self._json(report_path, "T290 report")
        receipt = self._json(receipt_path, "T290 receipt")
        artifact = _mapping(
            _mapping(report["artifacts"], "T290 artifacts")["route_specific_paired_uncertainty"],
            "T290 artifact",
        )
        effects_path = self._reference(artifact, "T290 artifact")
        rows = self._csv(effects_path, "T290 artifact")
        if (
            report.get("audit_id") != self.AUDIT_ID
            or report.get("status") != self.STATUS
            or report.get("route_count") != 6
            or report.get("pooling_prohibited") is not True
            or report.get("scientific_submission_ready") is not False
            or receipt.get("audit_id") != self.AUDIT_ID
            or receipt.get("status") != self.STATUS
            or receipt.get("report_sha256") != _sha256(report_path)
            or receipt.get("route_count") != 6
            or len(rows) != 6
            or any(not row.get("metric_name") or not row.get("cluster_unit") for row in rows)
        ):
            raise R4T290PaperOodUncertaintyError("T290 receipt is invalid")
        return R4T290PaperOodUncertaintySummary(
            int(receipt["route_count"]),
            int(receipt["supported_positive_count"]),
            int(receipt["supported_negative_count"]),
            int(receipt["indeterminate_count"]),
            receipt_path,
        )
