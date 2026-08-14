"""Add frozen measurement-batch uncertainty intervals to the T238 route."""

from __future__ import annotations

import csv
import hashlib
import json
import math
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np


class R4T255ClusterUncertaintyError(RuntimeError):
    """Raised when the T255 contract cannot be verified or executed."""


@dataclass(frozen=True)
class R4T255ClusterUncertaintySummary:
    outer_fold_count: int
    model_count: int
    metric_row_count: int
    defined_metric_count: int
    receipt_path: Path


class R4T255ClusterUncertaintyWorkflow:
    """Run and verify the pre-registered batch-cluster uncertainty extension."""

    AUDIT_ID = "bioif-r4-t255-cluster-uncertainty-v1.0.0"
    PROTOCOL_RELATIVE = "docs/data/R4_T255_CLUSTER_UNCERTAINTY_PROTOCOL_20260814.json"
    REGISTRY_RELATIVE = "docs/data/R4_T255_CLUSTER_UNCERTAINTY_REGISTRY_20260814.json"
    T238_REPORT_RELATIVE = (
        "reports/review_round_4/t238_four_source_availability_execution/v1.0.0/"
        "t238_four_source_availability_execution_report.json"
    )
    T238_BATCH_RELATIVE = (
        "reports/review_round_4/t238_four_source_availability_execution/v1.0.0/outer_fold_batch_metrics.csv"
    )
    T238_PAIRED_RELATIVE = (
        "reports/review_round_4/t238_four_source_availability_execution/v1.0.0/paired_composition_ablation.csv"
    )
    OUTPUT_RELATIVE = "reports/review_round_4/t255_cluster_uncertainty/v1.0.0"
    REPORT_NAME = "t255_cluster_uncertainty_report.json"
    RECEIPT_NAME = "t255_cluster_uncertainty_receipt.json"
    METRICS_NAME = "cluster_bootstrap_metrics.csv"
    MODEL_IDS = ("CONSTANT_TRAINING_MEAN", "SEQUENCE_RIDGE_FULL", "SEQUENCE_RIDGE_COMPOSITION_ONLY")
    METRICS = ("spearman", "mae", "rmse")
    PROTOCOL_SHA256 = "REPLACED_BY_GENERATED_HASH"

    def __init__(self, root: Path, *, output_root: Path | None = None) -> None:
        self.root = root.resolve(strict=True)
        candidate = (output_root or self.root / self.OUTPUT_RELATIVE).resolve(strict=False)
        if not candidate.is_relative_to(self.root):
            raise R4T255ClusterUncertaintyError("T255 output must remain under repository root")
        self.output_root = candidate

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _normalized_text_sha256(path: Path) -> str:
        """Hash source text independently of the checkout newline convention."""
        payload = path.read_text(encoding="utf-8").replace("\r\n", "\n").encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    @staticmethod
    def _write_json(path: Path, value: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        path.write_bytes(payload.encode("utf-8"))

    @staticmethod
    def _write_csv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)

    def _file(self, relative: str, label: str) -> Path:
        path = (self.root / relative).resolve(strict=False)
        if not path.is_relative_to(self.root) or not path.is_file():
            raise R4T255ClusterUncertaintyError(f"{label} is missing or outside repository root")
        return path

    def _protocol(self) -> tuple[dict[str, Any], Path, Path, Path]:
        protocol_path = self._file(self.PROTOCOL_RELATIVE, "T255 protocol")
        protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
        if protocol.get("protocol_id") != self.AUDIT_ID or protocol.get("status") != "FROZEN_BEFORE_T255_EXECUTION":
            raise R4T255ClusterUncertaintyError("T255 protocol identity or freeze status is invalid")
        if protocol.get("scientific_submission_ready") is not False:
            raise R4T255ClusterUncertaintyError("T255 protocol cannot claim submission readiness")
        inputs = protocol.get("inputs", {})
        paths: list[Path] = []
        for key in ("t238_report", "t238_batch_metrics", "t238_protocol"):
            ref = inputs.get(key, {})
            path = self._file(str(ref.get("relative_path", "")), key)
            if self._sha256(path) != str(ref.get("sha256", "")):
                raise R4T255ClusterUncertaintyError(f"{key} checksum differs from frozen protocol")
            paths.append(path)
        if protocol.get("bootstrap", {}).get("resamples") != 2000:
            raise R4T255ClusterUncertaintyError("T255 bootstrap resample count is not 2000")
        return protocol, paths[0], paths[1], paths[2]

    def _registry(self) -> tuple[dict[str, Any], Path]:
        registry_path = self._file(self.REGISTRY_RELATIVE, "T255 registry")
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        if (
            registry.get("audit_id") != self.AUDIT_ID
            or registry.get("protocol_id") != self.AUDIT_ID
            or registry.get("status") != "T255_CLUSTER_UNCERTAINTY_REGISTERED"
            or registry.get("scientific_submission_ready") is not False
        ):
            raise R4T255ClusterUncertaintyError("T255 registry identity or boundary is invalid")
        expected = registry.get("output_contract", {}).get("relative_path")
        if expected != self.OUTPUT_RELATIVE:
            raise R4T255ClusterUncertaintyError("T255 output contract does not match implementation")
        return registry, registry_path

    @staticmethod
    def _read_rows(path: Path) -> list[dict[str, str]]:
        with path.open("r", encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        if not rows:
            raise R4T255ClusterUncertaintyError("T238 batch metrics are empty")
        expected = {
            "outer_fold_id",
            "held_out_source_id",
            "model_id",
            "measurement_batch_id",
            "protein_count",
            "spearman",
            "mae",
            "rmse",
            "spearman_status",
        }
        if set(rows[0]) != expected:
            raise R4T255ClusterUncertaintyError("T238 batch metric schema differs")
        return rows

    @staticmethod
    def _finite(value: str) -> float | None:
        if value == "":
            return None
        parsed = float(value)
        if not math.isfinite(parsed):
            raise R4T255ClusterUncertaintyError("T238 metric is not finite")
        return parsed

    def _compute(self, protocol: dict[str, Any], batch_path: Path) -> list[dict[str, Any]]:
        rows = self._read_rows(batch_path)
        groups: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
        for row in rows:
            key = (row["outer_fold_id"], row["held_out_source_id"], row["model_id"])
            if row["model_id"] not in self.MODEL_IDS:
                raise R4T255ClusterUncertaintyError("unexpected T238 model id")
            groups[key].append(row)
        if len(groups) != 12:
            raise R4T255ClusterUncertaintyError("T238 must contain 4 folds x 3 models")
        resamples = int(protocol["bootstrap"]["resamples"])
        output: list[dict[str, Any]] = []
        model_index = {model: index for index, model in enumerate(self.MODEL_IDS, start=1)}
        fold_ids = sorted({key[0] for key in groups})
        fold_index = {fold: index for index, fold in enumerate(fold_ids, start=1)}
        for (fold, source, model), group in sorted(groups.items()):
            cluster_count = len(group)
            if cluster_count < 6 or len({row["measurement_batch_id"] for row in group}) != cluster_count:
                raise R4T255ClusterUncertaintyError("T255 requires unique measurement-batch clusters")
            seed = 25500 + 100 * fold_index[fold] + model_index[model]
            rng = np.random.default_rng(seed)
            for metric in self.METRICS:
                values = np.asarray(
                    [self._finite(row[metric]) for row in group if self._finite(row[metric]) is not None]
                )
                defined = values.size > 0
                if metric == "spearman" and model == "CONSTANT_TRAINING_MEAN":
                    if defined:
                        raise R4T255ClusterUncertaintyError("constant-model Spearman must remain undefined")
                    estimate = lower = upper = None
                elif not defined:
                    raise R4T255ClusterUncertaintyError("non-constant metric is unexpectedly undefined")
                else:
                    estimates = np.empty(resamples, dtype=float)
                    for index in range(resamples):
                        estimates[index] = float(np.mean(values[rng.integers(0, values.size, size=values.size)]))
                    estimate = float(np.mean(values))
                    lower = float(np.quantile(estimates, 0.025))
                    upper = float(np.quantile(estimates, 0.975))
                output.append(
                    {
                        "outer_fold_id": fold,
                        "held_out_source_id": source,
                        "model_id": model,
                        "metric": metric,
                        "estimate": estimate,
                        "lower_95": lower,
                        "upper_95": upper,
                        "measurement_batch_cluster_count": cluster_count,
                        "observation_count": sum(int(row["protein_count"]) for row in group),
                        "resamples": resamples,
                        "seed": seed,
                        "defined_status": "UNDEFINED_CONSTANT_PREDICTION"
                        if metric == "spearman" and model == "CONSTANT_TRAINING_MEAN"
                        else "DEFINED",
                    }
                )
        return output

    def run(self, *, strict: bool = False) -> R4T255ClusterUncertaintySummary:
        if not strict:
            raise R4T255ClusterUncertaintyError("T255 execution requires --strict")
        if self.output_root.exists():
            raise R4T255ClusterUncertaintyError("T255 output already exists")
        protocol, report_path, batch_path, _ = self._protocol()
        _, registry_path = self._registry()
        report = json.loads(report_path.read_text(encoding="utf-8"))
        if report.get("scientific_submission_ready") is not False:
            raise R4T255ClusterUncertaintyError("T238 report boundary is invalid")
        rows = self._compute(protocol, batch_path)
        paired_path = self._file(self.T238_PAIRED_RELATIVE, "T238 paired ablation")
        with paired_path.open("r", encoding="utf-8", newline="") as stream:
            paired = list(csv.DictReader(stream))
        if len(paired) != 4 or any(int(row["resamples"]) != 2000 for row in paired):
            raise R4T255ClusterUncertaintyError("T238 paired-ablation interval is not frozen at 2000 resamples")
        output = self.output_root
        metrics_path = output / self.METRICS_NAME
        self._write_csv(metrics_path, list(rows[0]), rows)
        artifact = {
            "cluster_bootstrap_metrics": {
                "relative_path": metrics_path.relative_to(self.root).as_posix(),
                "sha256": self._sha256(metrics_path),
            }
        }
        report_value = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "protocol_id": protocol["protocol_id"],
            "protocol_sha256": self._sha256(self._file(self.PROTOCOL_RELATIVE, "T255 protocol")),
            "registry_sha256": self._sha256(registry_path),
            "execution_module_sha256": self._normalized_text_sha256(Path(__file__)),
            "t238_report_sha256": self._sha256(report_path),
            "t238_batch_metrics_sha256": self._sha256(batch_path),
            "status": "T255_CLUSTER_UNCERTAINTY_COMPLETED_EXPLORATORY",
            "evidence_class": protocol["evidence_class"],
            "allowed_claim_level": protocol["allowed_claim_level"],
            "metric_rows": rows,
            "paired_ablation_reused": True,
            "paired_ablation_sha256": self._sha256(paired_path),
            "artifacts": artifact,
            "claim_boundary": protocol["claim_boundary"],
            "scientific_submission_ready": False,
        }
        report_out = output / self.REPORT_NAME
        self._write_json(report_out, report_value)
        receipt = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "status": report_value["status"],
            "report_sha256": self._sha256(report_out),
            "cluster_bootstrap_metrics_sha256": self._sha256(metrics_path),
            "execution_module_sha256": report_value["execution_module_sha256"],
            "outer_fold_count": len({row["outer_fold_id"] for row in rows}),
            "model_count": len(self.MODEL_IDS),
            "metric_count": len(self.METRICS),
            "metric_row_count": len(rows),
            "defined_metric_count": sum(row["defined_status"] == "DEFINED" for row in rows),
            "bootstrap_resamples": 2000,
            "cluster_key": ["outer_fold_id", "held_out_source_id", "measurement_batch_id"],
            "donor_level_effective_n_claimed": False,
            "scientific_submission_ready": False,
        }
        receipt_path = output / self.RECEIPT_NAME
        self._write_json(receipt_path, receipt)
        return R4T255ClusterUncertaintySummary(4, 3, len(rows), int(receipt["defined_metric_count"]), receipt_path)

    def verify(self, *, strict: bool = True) -> R4T255ClusterUncertaintySummary:
        if not strict:
            raise R4T255ClusterUncertaintyError("T255 verification requires --strict")
        protocol, report_path, batch_path, _ = self._protocol()
        _, registry_path = self._registry()
        protocol_path = self._file(self.PROTOCOL_RELATIVE, "T255 protocol")
        paired_path = self._file(self.T238_PAIRED_RELATIVE, "T238 paired ablation")
        module_path = Path(__file__).resolve(strict=True)
        output = self.output_root
        metrics_path = output / self.METRICS_NAME
        report_out = output / self.REPORT_NAME
        receipt_path = output / self.RECEIPT_NAME
        if not (metrics_path.is_file() and report_out.is_file() and receipt_path.is_file()):
            raise R4T255ClusterUncertaintyError("T255 output files are missing")
        report = json.loads(report_out.read_text(encoding="utf-8"))
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        protocol_matches = report.get("protocol_sha256") == self._sha256(protocol_path)
        report_matches = report.get("t238_report_sha256") == self._sha256(report_path)
        registry_matches = report.get("registry_sha256") == self._sha256(registry_path)
        module_matches = report.get("execution_module_sha256") == self._normalized_text_sha256(module_path)
        if not (protocol_matches and report_matches and registry_matches and module_matches):
            raise R4T255ClusterUncertaintyError("T255 report input binding differs")
        if report.get("t238_batch_metrics_sha256") != self._sha256(batch_path):
            raise R4T255ClusterUncertaintyError("T255 batch input binding differs")
        artifact = report.get("artifacts", {}).get("cluster_bootstrap_metrics", {})
        expected_metrics_relative = metrics_path.relative_to(self.root).as_posix()
        if artifact.get("relative_path") != expected_metrics_relative:
            raise R4T255ClusterUncertaintyError("T255 metric artifact path binding differs")
        if artifact.get("sha256") != self._sha256(metrics_path):
            raise R4T255ClusterUncertaintyError("T255 metric artifact checksum differs")
        if report.get("paired_ablation_sha256") != self._sha256(paired_path):
            raise R4T255ClusterUncertaintyError("T255 paired-ablation binding differs")
        if (
            report.get("scientific_submission_ready") is not False
            or receipt.get("scientific_submission_ready") is not False
        ):
            raise R4T255ClusterUncertaintyError("T255 cannot claim submission readiness")
        rows = report.get("metric_rows")
        if not isinstance(rows, list) or len(rows) != 36:
            raise R4T255ClusterUncertaintyError("T255 metric row count differs")
        if (
            receipt.get("report_sha256") != self._sha256(report_out)
            or receipt.get("cluster_bootstrap_metrics_sha256") != self._sha256(metrics_path)
            or receipt.get("execution_module_sha256") != self._normalized_text_sha256(module_path)
            or receipt.get("metric_row_count") != 36
        ):
            raise R4T255ClusterUncertaintyError("T255 receipt binding differs")
        return R4T255ClusterUncertaintySummary(4, 3, 36, int(receipt["defined_metric_count"]), receipt_path)
