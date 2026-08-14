"""Run cluster-aware paired sensitivity for the R4 author-run OOD result."""

from __future__ import annotations

import csv
import hashlib
import json
import random
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class R4OODClusterSensitivityError(RuntimeError):
    """Raised when the frozen R4 cluster sensitivity audit is invalid."""


@dataclass(frozen=True)
class R4OODClusterSensitivitySummary:
    status: str
    batch_count: int
    biological_unit_count: int
    laboratory_count: int
    report_path: Path


class R4OODClusterSensitivityWorkflow:
    """Audit unit-weighted model and paired-ablation sensitivity without promotion."""

    PROTOCOL_RELATIVE = "docs/data/R4_T175_OOD_CLUSTER_SENSITIVITY_PROTOCOL.json"
    SOURCE_MAP_RELATIVE = (
        "data/raw/r4_candidate_pmc11544298/derived/R4_PMC11544298_small_molecule_corona_source_cell_map.csv"
    )
    BATCH_METRICS_RELATIVE = (
        "reports/review_round_4/small_molecule_corona_ood/v1.0.0/r4_external_measurement_batch_metrics.csv"
    )
    OOD_REPORT_RELATIVE = "reports/review_round_4/small_molecule_corona_ood/v1.0.0/r4_external_ood_report.json"
    OUTPUT_RELATIVE = "reports/review_round_4/small_molecule_corona_cluster_sensitivity/v1.0.0"
    AUDIT_ID = "bioif-r4-ood-cluster-sensitivity-v1.0.0"
    STATUS = "R4_OOD_CLUSTER_SENSITIVITY_AUDITED_EXPLORATORY"
    FULL_MODEL = "SEQUENCE_RIDGE_FULL"
    COMPOSITION_MODEL = "SEQUENCE_RIDGE_COMPOSITION_ONLY"

    def __init__(
        self,
        root: Path,
        *,
        protocol_path: Path | None = None,
        output_root: Path | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.protocol_path = protocol_path or self.root / self.PROTOCOL_RELATIVE
        self.output_root = output_root or self.root / self.OUTPUT_RELATIVE

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()

    @staticmethod
    def _json(path: Path, label: str) -> dict[str, Any]:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise R4OODClusterSensitivityError(f"cannot parse {label}") from exc
        if not isinstance(value, dict):
            raise R4OODClusterSensitivityError(f"{label} must be an object")
        return value

    @staticmethod
    def _mean(values: list[float]) -> float:
        if not values:
            raise R4OODClusterSensitivityError("cannot average an empty cluster")
        return sum(values) / len(values)

    @staticmethod
    def _checksum(value: Any, label: str) -> str:
        if not isinstance(value, str) or len(value) != 64:
            raise R4OODClusterSensitivityError(f"{label} must be a SHA-256 digest")
        if any(character not in "0123456789abcdef" for character in value):
            raise R4OODClusterSensitivityError(f"{label} must be lowercase hexadecimal")
        return value

    def _root_file(self, relative_path: str, label: str) -> Path:
        path = (self.root / Path(*Path(relative_path).parts)).resolve(strict=False)
        if Path(relative_path).is_absolute() or ".." in Path(relative_path).parts:
            raise R4OODClusterSensitivityError(f"{label} must be a safe relative path")
        if not path.is_relative_to(self.root) or not path.is_file():
            raise R4OODClusterSensitivityError(f"{label} is missing or outside the repository")
        return path

    def _protocol(self) -> tuple[dict[str, Any], dict[str, Path]]:
        protocol = self._json(self.protocol_path, "R4 cluster sensitivity protocol")
        expected = {
            "schema_version",
            "protocol_id",
            "frozen_at",
            "evidence_class",
            "allowed_claim_level",
            "source_map",
            "batch_metrics",
            "upstream_ood_report",
            "cluster_unit",
            "pooled_unit_rule",
            "models",
            "paired_ablation",
            "uncertainty",
            "claim_boundary",
        }
        if set(protocol) != expected or protocol["schema_version"] != 1:
            raise R4OODClusterSensitivityError("R4 cluster sensitivity protocol fields are invalid")
        if (
            protocol["protocol_id"] != self.AUDIT_ID
            or protocol["evidence_class"] != "DEVELOPMENT_OBSERVATION"
            or protocol["allowed_claim_level"] != "EXPLORATORY"
            or protocol["cluster_unit"] != "biological_unit_id"
            or protocol["models"] != [self.FULL_MODEL, self.COMPOSITION_MODEL]
        ):
            raise R4OODClusterSensitivityError("R4 cluster sensitivity protocol identity is invalid")
        paths: dict[str, Path] = {}
        for key in ("source_map", "batch_metrics", "upstream_ood_report"):
            reference = protocol[key]
            if not isinstance(reference, dict) or set(reference) != {"relative_path", "sha256"}:
                raise R4OODClusterSensitivityError(f"{key} reference is invalid")
            path = self._root_file(reference["relative_path"], key)
            if self._sha256(path) != self._checksum(reference["sha256"], key):
                raise R4OODClusterSensitivityError(f"{key} checksum differs")
            paths[key] = path
        uncertainty = protocol["uncertainty"]
        if uncertainty != {
            "method": "equal-weight biological-unit bootstrap over unit-level means",
            "resamples": 2000,
            "random_seed": 20260827,
        }:
            raise R4OODClusterSensitivityError("R4 cluster sensitivity uncertainty changed")
        return protocol, paths

    @staticmethod
    def _read_csv(path: Path, label: str) -> list[dict[str, str]]:
        try:
            with path.open("r", encoding="utf-8", newline="") as stream:
                rows = list(csv.DictReader(stream))
        except OSError as exc:
            raise R4OODClusterSensitivityError(f"cannot read {label}") from exc
        if not rows or not rows[0]:
            raise R4OODClusterSensitivityError(f"{label} is empty")
        return rows

    @staticmethod
    def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
        with path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fieldnames, extrasaction="raise")
            writer.writeheader()
            writer.writerows(rows)

    @staticmethod
    def _write_json(path: Path, value: Any) -> None:
        path.write_text(
            json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )

    @staticmethod
    def _bootstrap(values: dict[str, float], resamples: int, seed: int) -> dict[str, float | int]:
        keys = sorted(values)
        if not keys:
            raise R4OODClusterSensitivityError("cluster bootstrap has no units")
        rng = random.Random(seed)
        sampled = [sum(values[rng.choice(keys)] for _ in keys) / len(keys) for _ in range(resamples)]
        sampled.sort()
        return {
            "resamples": resamples,
            "lower_95": sampled[int(0.025 * (resamples - 1))],
            "upper_95": sampled[int(0.975 * (resamples - 1))],
        }

    def run(self, *, strict: bool = False) -> R4OODClusterSensitivitySummary:
        if not strict:
            raise R4OODClusterSensitivityError("R4 cluster sensitivity audit requires --strict")
        if self.output_root.exists():
            raise R4OODClusterSensitivityError("R4 cluster sensitivity audit already executed")
        protocol, paths = self._protocol()
        source_rows = self._read_csv(paths["source_map"], "R4 source map")
        batch_to_unit: dict[str, str] = {}
        labs: dict[str, set[str]] = defaultdict(set)
        for row in source_rows:
            if row.get("rank_target_eligible") != "true":
                continue
            batch_id = row.get("measurement_batch_id", "")
            unit_id = row.get("biological_unit_id", "")
            if not batch_id or not unit_id:
                raise R4OODClusterSensitivityError("source map cluster key is missing")
            previous = batch_to_unit.setdefault(batch_id, unit_id)
            if previous != unit_id:
                raise R4OODClusterSensitivityError("a measurement batch spans multiple biological units")
            labs[unit_id].add(row.get("laboratory_anchor", ""))
        metric_rows = self._read_csv(paths["batch_metrics"], "R4 batch metrics")
        required = {"model_id", "measurement_batch_id", "spearman", "spearman_status"}
        if not required.issubset(metric_rows[0]):
            raise R4OODClusterSensitivityError("R4 batch metrics schema is incomplete")
        by_model_unit: dict[str, dict[str, list[float]]] = {
            self.FULL_MODEL: defaultdict(list),
            self.COMPOSITION_MODEL: defaultdict(list),
        }
        by_model_batch: dict[str, dict[str, float]] = {
            self.FULL_MODEL: {},
            self.COMPOSITION_MODEL: {},
        }
        for row in metric_rows:
            model_id = row["model_id"]
            if model_id not in by_model_unit or row["spearman_status"] != "DEFINED":
                continue
            batch_id = row["measurement_batch_id"]
            if batch_id not in batch_to_unit:
                raise R4OODClusterSensitivityError("metrics contain an unknown measurement batch")
            value = float(row["spearman"])
            unit_id = batch_to_unit[batch_id]
            by_model_unit[model_id][unit_id].append(value)
            if batch_id in by_model_batch[model_id]:
                raise R4OODClusterSensitivityError("duplicate model-batch metric")
            by_model_batch[model_id][batch_id] = value
        if set(by_model_unit[self.FULL_MODEL]) != set(by_model_unit[self.COMPOSITION_MODEL]):
            raise R4OODClusterSensitivityError("model unit clusters do not match")
        unit_rows: list[dict[str, Any]] = []
        model_results: list[dict[str, Any]] = []
        for model_id in (self.FULL_MODEL, self.COMPOSITION_MODEL):
            unit_means = {unit: self._mean(values) for unit, values in by_model_unit[model_id].items()}
            batch_values = list(by_model_batch[model_id].values())
            bootstrap = self._bootstrap(
                unit_means,
                protocol["uncertainty"]["resamples"],
                protocol["uncertainty"]["random_seed"] + (1 if model_id == self.FULL_MODEL else 2),
            )
            model_results.append(
                {
                    "model_id": model_id,
                    "measurement_batch_count": len(batch_values),
                    "biological_unit_count": len(unit_means),
                    "batch_weighted_mean_spearman": self._mean(batch_values),
                    "unit_weighted_mean_spearman": self._mean(list(unit_means.values())),
                    "unit_weighted_cluster_bootstrap": bootstrap,
                }
            )
            for unit_id in sorted(unit_means):
                unit_rows.append(
                    {
                        "model_id": model_id,
                        "biological_unit_id": unit_id,
                        "unit_class": "POOLED" if "POOLED" in unit_id.upper() else "DONOR_LABELLED",
                        "laboratory_count": len(labs[unit_id]),
                        "measurement_batch_count": len(by_model_unit[model_id][unit_id]),
                        "mean_spearman": unit_means[unit_id],
                    }
                )
        paired_batch_deltas = {
            batch_id: by_model_batch[self.FULL_MODEL][batch_id] - by_model_batch[self.COMPOSITION_MODEL][batch_id]
            for batch_id in by_model_batch[self.FULL_MODEL]
            if batch_id in by_model_batch[self.COMPOSITION_MODEL]
        }
        delta_by_unit: dict[str, list[float]] = defaultdict(list)
        for batch_id, value in paired_batch_deltas.items():
            delta_by_unit[batch_to_unit[batch_id]].append(value)
        delta_unit_means = {unit: self._mean(values) for unit, values in delta_by_unit.items()}
        paired = {
            "paired_measurement_batch_count": len(paired_batch_deltas),
            "batch_weighted_mean_full_minus_composition": self._mean(list(paired_batch_deltas.values())),
            "unit_weighted_mean_full_minus_composition": self._mean(list(delta_unit_means.values())),
            "unit_weighted_cluster_bootstrap": self._bootstrap(
                delta_unit_means,
                protocol["uncertainty"]["resamples"],
                protocol["uncertainty"]["random_seed"] + 3,
            ),
            "by_biological_unit": [
                {
                    "biological_unit_id": unit,
                    "measurement_batch_count": len(delta_by_unit[unit]),
                    "full_minus_composition_mean_spearman": delta_unit_means[unit],
                }
                for unit in sorted(delta_unit_means)
            ],
        }
        self.output_root.mkdir(parents=True)
        unit_path = self.output_root / "r4_external_cluster_unit_model_metrics.csv"
        self._write_csv(unit_path, list(unit_rows[0]), unit_rows)
        report = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "protocol_id": protocol["protocol_id"],
            "protocol_sha256": self._sha256(self.protocol_path),
            "status": self.STATUS,
            "evidence_class": protocol["evidence_class"],
            "allowed_claim_level": protocol["allowed_claim_level"],
            "cluster_structure": {
                "measurement_batch_count": len(batch_to_unit),
                "biological_unit_count": len(set(batch_to_unit.values())),
                "laboratory_count": len({lab for values in labs.values() for lab in values}),
                "pooled_unit_count": len({unit for unit in batch_to_unit.values() if "POOLED" in unit.upper()}),
                "donor_labelled_unit_count": len(
                    {unit for unit in batch_to_unit.values() if "POOLED" not in unit.upper()}
                ),
            },
            "model_results": model_results,
            "paired_ablation": paired,
            "artifacts": {
                "cluster_unit_model_metrics": {
                    "relative_path": unit_path.relative_to(self.root).as_posix(),
                    "sha256": self._sha256(unit_path),
                }
            },
            "independent_validation": False,
            "external_scientific_reproduction": False,
            "scientific_submission_ready": False,
            "claim_boundary": protocol["claim_boundary"],
        }
        report_path = self.output_root / "r4_external_cluster_sensitivity_report.json"
        self._write_json(report_path, report)
        receipt = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "status": self.STATUS,
            "report_sha256": self._sha256(report_path),
            "batch_count": len(batch_to_unit),
            "biological_unit_count": len(set(batch_to_unit.values())),
            "laboratory_count": len({lab for values in labs.values() for lab in values}),
            "independent_validation": False,
            "external_scientific_reproduction": False,
            "scientific_submission_ready": False,
        }
        self._write_json(self.output_root / "r4_external_cluster_sensitivity_receipt.json", receipt)
        return R4OODClusterSensitivitySummary(
            self.STATUS,
            len(batch_to_unit),
            len(set(batch_to_unit.values())),
            len({lab for values in labs.values() for lab in values}),
            report_path,
        )

    def verify(self) -> R4OODClusterSensitivitySummary:
        """Verify the cluster sensitivity receipt and its aggregate CSV."""
        protocol, _ = self._protocol()
        report_path = self.output_root / "r4_external_cluster_sensitivity_report.json"
        receipt_path = self.output_root / "r4_external_cluster_sensitivity_receipt.json"
        report = self._json(report_path, "R4 cluster sensitivity report")
        receipt = self._json(receipt_path, "R4 cluster sensitivity receipt")
        artifacts = report.get("artifacts")
        if not isinstance(artifacts, dict) or set(artifacts) != {"cluster_unit_model_metrics"}:
            raise R4OODClusterSensitivityError("R4 cluster sensitivity artifact is invalid")
        reference = artifacts["cluster_unit_model_metrics"]
        if not isinstance(reference, dict) or set(reference) != {"relative_path", "sha256"}:
            raise R4OODClusterSensitivityError("R4 cluster sensitivity artifact reference is invalid")
        artifact_path = self._root_file(reference["relative_path"], "R4 cluster sensitivity artifact")
        if self._sha256(artifact_path) != self._checksum(reference["sha256"], "R4 cluster sensitivity artifact"):
            raise R4OODClusterSensitivityError("R4 cluster sensitivity artifact checksum differs")
        if (
            report.get("audit_id") != self.AUDIT_ID
            or report.get("protocol_id") != protocol["protocol_id"]
            or report.get("status") != self.STATUS
            or report.get("scientific_submission_ready") is not False
            or receipt.get("audit_id") != self.AUDIT_ID
            or receipt.get("status") != self.STATUS
            or receipt.get("report_sha256") != self._sha256(report_path)
            or receipt.get("scientific_submission_ready") is not False
        ):
            raise R4OODClusterSensitivityError("R4 cluster sensitivity receipt is invalid")
        return R4OODClusterSensitivitySummary(
            self.STATUS,
            int(receipt["batch_count"]),
            int(receipt["biological_unit_count"]),
            int(receipt["laboratory_count"]),
            report_path,
        )
