"""Fixture-backed extraction benchmark, calibration, and G2 evaluation."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

BENCHMARK_ROOT = Path("reports/benchmark")
BENCHMARK_FIXTURE = Path("tests/fixtures/benchmark/extraction.json")


class BenchmarkError(RuntimeError):
    """Raised when benchmark fixtures or metric outputs are invalid."""


@dataclass(frozen=True)
class BenchmarkSummary:
    """Metrics and output paths from one benchmark run."""

    rows: int
    correct: int
    errors: int
    eligible_rows: int
    eligible_correct: int
    precision: float
    recall: float
    calibration_error: float
    g2_status: str
    metrics_path: Path
    calibration_path: Path
    taxonomy_path: Path
    model_card_path: Path
    receipt_path: Path


def _canonical(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BenchmarkError(f"invalid benchmark JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise BenchmarkError(f"benchmark JSON must be an object: {path}")
    return value


def _is_correct(row: Mapping[str, Any]) -> bool:
    if row["modality"] == "numeric":
        return math.isclose(
            float(row["predicted"]),
            float(row["expected"]),
            rel_tol=1e-9,
            abs_tol=1e-9,
        )
    return bool(row["predicted"] == row["expected"])


def _group_metrics(rows: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault(str(row[key]), []).append(row)
    output: dict[str, dict[str, Any]] = {}
    for group, members in sorted(groups.items()):
        correct = sum(bool(row["correct"]) for row in members)
        output[group] = {
            "rows": len(members),
            "correct": correct,
            "errors": len(members) - correct,
            "accuracy": correct / len(members),
            "mean_confidence": sum(float(row["confidence"]) for row in members) / len(members),
        }
    return output


class ExtractionBenchmark:
    """Compute deterministic extraction metrics and the automatic-field G2 gate."""

    def __init__(
        self,
        root: Path,
        *,
        fixture_path: Path | None = None,
        output_root: Path | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.fixture_path = fixture_path or self.root / BENCHMARK_FIXTURE
        self.output_root = output_root or self.root / BENCHMARK_ROOT

    def _load(self) -> tuple[list[dict[str, Any]], float, dict[str, float]]:
        value = _read_json(self.fixture_path)
        if set(value) != {"schema_version", "rows", "minimum_confidence", "g2_thresholds"}:
            raise BenchmarkError("benchmark fixture envelope is invalid")
        rows = value["rows"]
        threshold = value["minimum_confidence"]
        thresholds = value["g2_thresholds"]
        if (
            value["schema_version"] != 1
            or not isinstance(rows, list)
            or not isinstance(threshold, int | float)
            or isinstance(threshold, bool)
            or not isinstance(thresholds, Mapping)
        ):
            raise BenchmarkError("benchmark fixture schema is invalid")
        required = {
            "row_id",
            "modality",
            "material",
            "year",
            "expected",
            "predicted",
            "confidence",
            "source_locator",
        }
        allowed_modalities = {"numeric", "entity", "arm", "evidence"}
        normalized: list[dict[str, Any]] = []
        for raw in rows:
            if not isinstance(raw, Mapping) or set(raw) != required:
                raise BenchmarkError("benchmark row fields are invalid")
            row = dict(raw)
            if (
                not isinstance(row["row_id"], str)
                or not isinstance(row["modality"], str)
                or row["modality"] not in allowed_modalities
                or not isinstance(row["material"], str)
                or not isinstance(row["year"], int)
                or not isinstance(row["confidence"], int | float)
                or isinstance(row["confidence"], bool)
                or not 0.0 <= float(row["confidence"]) <= 1.0
                or not isinstance(row["source_locator"], str)
                or not row["source_locator"].startswith("asset:")
            ):
                raise BenchmarkError(f"benchmark row identity/confidence is invalid: {row}")
            normalized.append(row)
        if len({row["row_id"] for row in normalized}) != len(normalized):
            raise BenchmarkError("benchmark row IDs are not unique")
        threshold_map = {
            name: float(thresholds[name])
            for name in ("minimum_precision", "minimum_recall", "maximum_calibration_error")
        }
        if any(not 0.0 <= value <= 1.0 for value in threshold_map.values()):
            raise BenchmarkError("G2 thresholds are out of range")
        return normalized, float(threshold), threshold_map

    def run(self) -> BenchmarkSummary:
        """Run the benchmark and write metrics, calibration, taxonomy, and model card."""
        rows, threshold, g2_thresholds = self._load()
        for row in rows:
            row["correct"] = _is_correct(row)
        correct_rows = [row for row in rows if row["correct"]]
        error_rows = [row for row in rows if not row["correct"]]
        eligible = [row for row in rows if float(row["confidence"]) >= threshold]
        eligible_correct = [row for row in eligible if row["correct"]]
        precision = len(eligible_correct) / len(eligible) if eligible else 0.0
        recall = len(eligible_correct) / len(correct_rows) if correct_rows else 0.0
        calibration_error = (
            sum(abs(float(row["confidence"]) - (1.0 if row["correct"] else 0.0)) for row in eligible) / len(eligible)
            if eligible
            else 1.0
        )
        g2_status = (
            "PASS"
            if precision >= g2_thresholds["minimum_precision"]
            and recall >= g2_thresholds["minimum_recall"]
            and calibration_error <= g2_thresholds["maximum_calibration_error"]
            else "FAIL"
        )
        metrics = {
            "schema_version": 1,
            "rows": len(rows),
            "correct": len(correct_rows),
            "errors": len(error_rows),
            "overall_accuracy": len(correct_rows) / len(rows),
            "automatic_threshold": threshold,
            "eligible_rows": len(eligible),
            "eligible_correct": len(eligible_correct),
            "eligible_precision": precision,
            "eligible_recall": recall,
            "eligible_calibration_error": calibration_error,
            "g2_status": g2_status,
            "by_modality": _group_metrics(rows, "modality"),
            "by_material": _group_metrics(rows, "material"),
            "by_year": _group_metrics(rows, "year"),
        }
        bins = ((0.0, 0.5), (0.5, 0.75), (0.75, 0.9), (0.9, 1.01))
        calibration = {
            "schema_version": 1,
            "automatic_threshold": threshold,
            "bins": [
                {
                    "lower": lower,
                    "upper": upper,
                    "rows": len([row for row in rows if lower <= float(row["confidence"]) < upper]),
                    "mean_confidence": (
                        sum(float(row["confidence"]) for row in rows if lower <= float(row["confidence"]) < upper)
                        / len([row for row in rows if lower <= float(row["confidence"]) < upper])
                        if any(lower <= float(row["confidence"]) < upper for row in rows)
                        else None
                    ),
                    "accuracy": (
                        sum(bool(row["correct"]) for row in rows if lower <= float(row["confidence"]) < upper)
                        / len([row for row in rows if lower <= float(row["confidence"]) < upper])
                        if any(lower <= float(row["confidence"]) < upper for row in rows)
                        else None
                    ),
                }
                for lower, upper in bins
            ],
            "expected_calibration_error": calibration_error,
        }
        taxonomy_names = {
            "numeric": "NUMERIC_VALUE_MISMATCH",
            "entity": "ENTITY_RESOLUTION_ERROR",
            "arm": "ARM_LABEL_ERROR",
            "evidence": "EVIDENCE_LOCATOR_UNRESOLVED",
        }
        taxonomy = {
            "schema_version": 1,
            "errors": [
                {
                    "error_id": f"error:{row['row_id']}",
                    "row_id": row["row_id"],
                    "taxonomy": taxonomy_names[row["modality"]],
                    "modality": row["modality"],
                    "material": row["material"],
                    "year": row["year"],
                    "confidence": row["confidence"],
                    "expected": row["expected"],
                    "predicted": row["predicted"],
                    "source_locator": row["source_locator"],
                }
                for row in error_rows
            ],
            "counts": {
                name: sum(taxonomy_names[row["modality"]] == name for row in error_rows)
                for name in sorted(set(taxonomy_names.values()))
            },
        }
        model_card = {
            "schema_version": 1,
            "scope": "fixture-backed extraction benchmark",
            "modalities": ["numeric", "entity", "arm", "evidence"],
            "automatic_threshold": threshold,
            "g2_thresholds": g2_thresholds,
            "g2_status": g2_status,
            "g2_metrics": {
                "precision": precision,
                "recall": recall,
                "calibration_error": calibration_error,
            },
            "limitations": [
                "Rows are sanitized fixtures and do not represent expert review.",
                "High-confidence gating is not a substitute for unresolved evidence adjudication.",
                "The benchmark does not access locked-test payloads or live endpoints.",
            ],
        }
        self.output_root.mkdir(parents=True, exist_ok=True)
        outputs = {
            "extraction_metrics.json": metrics,
            "calibration.json": calibration,
            "error_taxonomy.json": taxonomy,
            "model_card.json": model_card,
        }
        serialized = {name: _canonical(value) for name, value in outputs.items()}
        receipt = {
            "schema_version": 1,
            "fixture": True,
            "g2_status": g2_status,
            "rows": len(rows),
            "outputs_sha256": {name: hashlib.sha256(content).hexdigest() for name, content in serialized.items()},
            "locked_test_accessed": False,
        }
        serialized["benchmark_receipt.json"] = _canonical(receipt)
        for name, content in serialized.items():
            (self.output_root / name).write_bytes(content)
        return BenchmarkSummary(
            rows=len(rows),
            correct=len(correct_rows),
            errors=len(error_rows),
            eligible_rows=len(eligible),
            eligible_correct=len(eligible_correct),
            precision=precision,
            recall=recall,
            calibration_error=calibration_error,
            g2_status=g2_status,
            metrics_path=self.output_root / "extraction_metrics.json",
            calibration_path=self.output_root / "calibration.json",
            taxonomy_path=self.output_root / "error_taxonomy.json",
            model_card_path=self.output_root / "model_card.json",
            receipt_path=self.output_root / "benchmark_receipt.json",
        )
