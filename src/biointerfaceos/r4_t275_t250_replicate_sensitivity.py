"""Quantify T250 technical-replicate weighting sensitivity at the held-out endpoint."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

from biointerfaceos.r3_model_evaluation import R3ModelEvaluationWorkflow
from biointerfaceos.r3_uniprot_mapping import _canonical, _sha256


class R4T275ReplicateSensitivityError(RuntimeError):
    """Raised when T275 cannot close its input/output contract."""


class R4T275T250ReplicateSensitivityWorkflow:
    """Compare the original replicate-weighted endpoint with target-collapsed sensitivity."""

    T250_OUTPUT = "reports/review_round_4/t250_four_lab_common_target_execution/v1.0.0"
    OUTPUT = "reports/review_round_4/t275_t250_replicate_sensitivity/v1.0.0"

    def __init__(self, root: Path, *, output_root: Path | None = None) -> None:
        self.root = root.resolve(strict=True)
        self.input_root = self.root / self.T250_OUTPUT
        self.output_root = (output_root or self.root / self.OUTPUT).resolve(strict=False)
        if not self.output_root.is_relative_to(self.root):
            raise R4T275ReplicateSensitivityError("T275 output escapes repository root")

    @staticmethod
    def _read_csv(path: Path) -> list[dict[str, str]]:
        with path.open(encoding="utf-8", newline="") as stream:
            return list(csv.DictReader(stream))

    @staticmethod
    def _metric(rows: list[tuple[float, float]]) -> dict[str, float | None]:
        observed = np.asarray([row[0] for row in rows], dtype=float)
        predicted = np.asarray([row[1] for row in rows], dtype=float)
        return {
            "spearman": R3ModelEvaluationWorkflow._spearman(observed, predicted),
            "mae": float(np.mean(np.abs(observed - predicted))),
            "rmse": float(np.sqrt(np.mean(np.square(observed - predicted)))),
        }

    def run(self, *, strict: bool = False) -> dict[str, Any]:
        if not strict:
            raise R4T275ReplicateSensitivityError("T275 replicate sensitivity requires --strict")
        if self.output_root.exists():
            raise R4T275ReplicateSensitivityError("T275 output already exists")
        ledger = self._read_csv(self.input_root / "source_local_prefrozen_target_ledger.csv")
        predictions = self._read_csv(self.input_root / "outer_fold_predictions.csv")
        duplicate_groups: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
        for row in ledger:
            duplicate_groups[(row["source_id"], row["measurement_batch_id"], row["canonical_accession"])].append(row)
        duplicates = {key: rows for key, rows in duplicate_groups.items() if len(rows) > 1}
        if not duplicates:
            raise R4T275ReplicateSensitivityError("T250 duplicate technical-replicate groups were not found")
        duplicate_rows = []
        for key, rows in sorted(duplicates.items()):
            duplicate_rows.append(
                {
                    "source_id": key[0],
                    "measurement_batch_id": key[1],
                    "canonical_accession": key[2],
                    "row_count": len(rows),
                    "target_observation_ids": ";".join(sorted(row["target_observation_id"] for row in rows)),
                    "technical_replicate_ids": ";".join(sorted(row.get("technical_replicate_id", "") for row in rows)),
                    "collapse_rule": (
                        "mean of source-local rank percentile and predicted values "
                        "within canonical target/batch group"
                    ),
                }
            )
        metric_rows: list[dict[str, Any]] = []
        by_fold_model: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
        for row in predictions:
            by_fold_model[(row["outer_fold_id"], row["model_id"])].append(row)
        for (fold_id, model_id), rows in sorted(by_fold_model.items()):
            original_batches: dict[tuple[str, str], list[tuple[float, float]]] = defaultdict(list)
            collapsed_targets: dict[tuple[str, str, str], list[tuple[float, float]]] = defaultdict(list)
            for row in rows:
                source = row["source_id"]
                batch = row["measurement_batch_id"]
                pair = (
                    float(row["observed_rank_percentile_descending"]),
                    float(row["predicted_rank_percentile_descending"]),
                )
                original_batches[(source, batch)].append(pair)
                collapsed_targets[(source, batch, row["canonical_accession"])].append(pair)
            collapsed_batches: dict[tuple[str, str], list[tuple[float, float]]] = defaultdict(list)
            for (source, batch, _accession), pairs in collapsed_targets.items():
                collapsed_batches[(source, batch)].append(
                    (float(np.mean([pair[0] for pair in pairs])), float(np.mean([pair[1] for pair in pairs])))
                )
            original_metrics = [self._metric(pairs) for pairs in original_batches.values() if len(pairs) >= 3]
            collapsed_metrics = [self._metric(pairs) for pairs in collapsed_batches.values() if len(pairs) >= 3]
            original_spearman = [item["spearman"] for item in original_metrics if item["spearman"] is not None]
            collapsed_spearman = [item["spearman"] for item in collapsed_metrics if item["spearman"] is not None]
            original_mean_spearman = (
                float(np.mean(original_spearman)) if original_spearman else None
            )
            collapsed_mean_spearman = (
                float(np.mean(collapsed_spearman)) if collapsed_spearman else None
            )
            spearman_difference = (
                float(collapsed_mean_spearman - original_mean_spearman)
                if collapsed_mean_spearman is not None and original_mean_spearman is not None
                else None
            )
            metric_rows.append(
                {
                    "outer_fold_id": fold_id,
                    "model_id": model_id,
                    "original_batch_count": len(original_metrics),
                    "collapsed_batch_count": len(collapsed_metrics),
                    "original_defined_spearman_batch_count": len(original_spearman),
                    "collapsed_defined_spearman_batch_count": len(collapsed_spearman),
                    "original_replicate_weighted_mean_spearman": original_mean_spearman,
                    "collapsed_target_equalized_mean_spearman": collapsed_mean_spearman,
                    "collapsed_minus_original_mean_spearman": spearman_difference,
                    "original_mean_mae": float(np.mean([item["mae"] for item in original_metrics])),
                    "collapsed_mean_mae": float(np.mean([item["mae"] for item in collapsed_metrics])),
                    "original_mean_rmse": float(np.mean([item["rmse"] for item in original_metrics])),
                    "collapsed_mean_rmse": float(np.mean([item["rmse"] for item in collapsed_metrics])),
                    "scope": "post_fit_endpoint_sensitivity; model_training_was_not_refit",
                }
            )
        self.output_root.mkdir(parents=True, exist_ok=False)
        metric_path = self.output_root / "replicate_sensitivity.csv"
        with metric_path.open("w", encoding="utf-8", newline="") as stream:
            fields = list(metric_rows[0])
            writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
            writer.writeheader()
            writer.writerows(metric_rows)
        duplicate_path = self.output_root / "duplicate_technical_replicate_groups.csv"
        with duplicate_path.open("w", encoding="utf-8", newline="") as stream:
            fields = list(duplicate_rows[0])
            writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
            writer.writeheader()
            writer.writerows(duplicate_rows)
        report = {
            "schema_version": 1,
            "audit_id": "bioif-r4-t275-t250-replicate-sensitivity-v1.0.0",
            "status": "T275_REPLICATE_SENSITIVITY_COMPLETED_POST_FIT",
            "input_output_root": self.T250_OUTPUT,
            "duplicate_group_count": len(duplicate_rows),
            "duplicate_extra_row_count": sum(int(row["row_count"]) - 1 for row in duplicate_rows),
            "duplicate_source_scope": ["PXD064962_UCD_EVENT"],
            "metric_policy": (
                "collapse duplicate source/batch/canonical-target rows by mean rank "
                "and mean prediction for endpoint sensitivity"
            ),
            "refit_status": "NOT_REFIT",
            "metric_artifact": {
                "relative_path": metric_path.relative_to(self.root).as_posix(),
                "sha256": _sha256(metric_path),
            },
            "duplicate_artifact": {
                "relative_path": duplicate_path.relative_to(self.root).as_posix(),
                "sha256": _sha256(duplicate_path),
            },
            "claim_boundary": (
                "This is a post-fit technical-replicate endpoint sensitivity. It does not "
                "replace a pre-registered replicate-aware model refit or independent validation."
            ),
            "scientific_submission_ready": False,
        }
        report_path = self.output_root / "t275_replicate_sensitivity_report.json"
        report_path.write_bytes(_canonical(report))
        return report

    def verify(self, *, strict: bool = True) -> dict[str, Any]:
        if not strict:
            raise R4T275ReplicateSensitivityError("T275 verification requires --strict")
        report_path = self.output_root / "t275_replicate_sensitivity_report.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        for key in ("metric_artifact", "duplicate_artifact"):
            path = self.root / report[key]["relative_path"]
            if _sha256(path) != report[key]["sha256"]:
                raise R4T275ReplicateSensitivityError(f"T275 {key} hash differs")
        if report.get("refit_status") != "NOT_REFIT" or report.get("scientific_submission_ready") is not False:
            raise R4T275ReplicateSensitivityError("T275 claim boundary is invalid")
        return report
