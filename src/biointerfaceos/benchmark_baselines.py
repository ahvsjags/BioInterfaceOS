"""Deterministic data/statistical baselines for the development benchmark."""

from __future__ import annotations

import hashlib
import json
import math
import random
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class BenchmarkBaselineError(RuntimeError):
    """Raised when a simple baseline contract is invalid."""


@dataclass(frozen=True)
class BenchmarkBaselineSummary:
    """Summary of one simple-baseline run."""

    baselines: int
    successful: int
    validation_instances: int
    best_rmse: float
    resumed: int
    receipt_path: Path


def _canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise BenchmarkBaselineError(f"{label} must be an object")
    return dict(value)


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise BenchmarkBaselineError(f"{label} must be a non-empty string")
    return value.strip()


def _number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise BenchmarkBaselineError(f"{label} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise BenchmarkBaselineError(f"{label} must be finite")
    return result


def _mean(values: list[float]) -> float:
    if not values:
        raise BenchmarkBaselineError("cannot average an empty list")
    return sum(values) / len(values)


def _hash_bucket(value: str) -> float:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) / 0xFFFFFFFF


def _solve(matrix: list[list[float]], vector: list[float]) -> list[float]:
    size = len(vector)
    augmented = [row[:] + [vector[index]] for index, row in enumerate(matrix)]
    for column in range(size):
        pivot = max(range(column, size), key=lambda index: abs(augmented[index][column]))
        if abs(augmented[pivot][column]) < 1e-12:
            raise BenchmarkBaselineError("linear baseline normal equations are singular")
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        pivot_value = augmented[column][column]
        augmented[column] = [value / pivot_value for value in augmented[column]]
        for row in range(size):
            if row == column:
                continue
            factor = augmented[row][column]
            augmented[row] = [
                current - factor * basis for current, basis in zip(augmented[row], augmented[column], strict=True)
            ]
    return [augmented[index][-1] for index in range(size)]


def _ridge_fit(features: list[list[float]], targets: list[float], ridge: float) -> list[float]:
    width = len(features[0])
    matrix = [[0.0 for _ in range(width)] for _ in range(width)]
    vector = [0.0 for _ in range(width)]
    for row, target in zip(features, targets, strict=True):
        for left in range(width):
            vector[left] += row[left] * target
            for right in range(width):
                matrix[left][right] += row[left] * row[right]
    for index in range(1, width):
        matrix[index][index] += ridge
    return _solve(matrix, vector)


def _predict_linear(coefficients: list[float], features: list[float]) -> float:
    return sum(coefficient * value for coefficient, value in zip(coefficients, features, strict=True))


def _rmse(rows: list[dict[str, Any]], predictions: Mapping[str, float]) -> float:
    return math.sqrt(
        _mean([(float(predictions[_string(row["instance_id"], "instance ID")]) - row["target"]) ** 2 for row in rows])
    )


def _regression_metrics(rows: list[dict[str, Any]], predictions: Mapping[str, float]) -> dict[str, Any]:
    errors = [float(predictions[_string(row["instance_id"], "instance ID")]) - row["target"] for row in rows]
    targets = [row["target"] for row in rows]
    mse = _mean([error**2 for error in errors])
    target_mean = _mean(targets)
    total_sum = sum((target - target_mean) ** 2 for target in targets)
    r2 = 1.0 - sum(error**2 for error in errors) / total_sum if total_sum else 0.0
    return {
        "instances": len(rows),
        "mae": round(_mean([abs(error) for error in errors]), 6),
        "mse": round(mse, 6),
        "rmse": round(math.sqrt(mse), 6),
        "r2": round(r2, 6),
    }


def _group_metrics(rows: list[dict[str, Any]], predictions: Mapping[str, float], field: str) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        key = _string(row[field], f"group field {field}")
        groups.setdefault(key, []).append(row)
    return [{field: key, **_regression_metrics(groups[key], predictions)} for key in sorted(groups)]


def _bootstrap_ci(rows: list[dict[str, Any]], predictions: Mapping[str, float], seed: int, samples: int) -> list[float]:
    rng = random.Random(seed)
    values: list[float] = []
    for _ in range(samples):
        sample = [rows[rng.randrange(len(rows))] for _ in rows]
        values.append(_rmse(sample, predictions))
    values.sort()
    lower_index = int(0.025 * (len(values) - 1))
    upper_index = int(0.975 * (len(values) - 1))
    return [round(values[lower_index], 6), round(values[upper_index], 6)]


class BenchmarkBaselineWorkflow:
    """Run simple baselines with fixed feature, seed, and split contracts."""

    def __init__(
        self,
        root: Path,
        *,
        fixture_path: Path | None = None,
        output_root: Path | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.fixture_path = fixture_path or (self.root / "tests/fixtures/benchmark/baseline_fixture.json")
        self.instances_path = self.root / "reports/benchmark/instances/public_instances.json"
        self.grading_metrics_path = self.root / "reports/benchmark/grading/metrics.json"
        self.output_root = output_root or self.root / "reports/benchmark/baselines"

    def _load_fixture(self) -> dict[str, Any]:
        try:
            data = _mapping(
                json.loads(self.fixture_path.read_text(encoding="utf-8")),
                "baseline fixture",
            )
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise BenchmarkBaselineError(f"cannot load baseline fixture: {exc}") from exc
        if data.get("schema_version") != 1 or data.get("mode") != "benchmark_baselines_simple":
            raise BenchmarkBaselineError("baseline fixture schema or mode is invalid")
        if data.get("target_values_are_fixture_only") is not True:
            raise BenchmarkBaselineError("baseline targets must be marked fixture-only")
        if not isinstance(data.get("inputs"), list) or not isinstance(data.get("targets"), list):
            raise BenchmarkBaselineError("baseline inputs/targets are invalid")
        config = _mapping(data.get("config"), "baseline config")
        if config.get("seed") != 17 or config.get("bootstrap_samples") != 128:
            raise BenchmarkBaselineError("baseline seed/bootstrap configuration is not frozen")
        if config.get("group") != "simple":
            raise BenchmarkBaselineError("baseline fixture is not the simple group")
        return data

    def _verify_inputs(self, fixture: Mapping[str, Any]) -> dict[str, Any]:
        required = {
            "T067 public instances": self.instances_path,
            "T068 grader metrics": self.grading_metrics_path,
        }
        seen: set[str] = set()
        loaded: dict[str, Any] = {}
        for value in fixture["inputs"]:
            row = _mapping(value, "baseline input")
            label = _string(row.get("label"), "baseline input label")
            if label not in required:
                raise BenchmarkBaselineError(f"unexpected baseline input: {label}")
            relative = _string(row.get("path"), "baseline input path")
            path = (self.root / relative).resolve(strict=True)
            if path != required[label].resolve(strict=True):
                raise BenchmarkBaselineError(f"baseline input path mismatch: {label}")
            expected = _string(row.get("sha256"), "baseline input checksum")
            if _sha256(path.read_bytes()) != expected:
                raise BenchmarkBaselineError(f"baseline input checksum differs: {label}")
            loaded[label] = json.loads(path.read_text(encoding="utf-8"))
            seen.add(label)
        if seen != set(required):
            raise BenchmarkBaselineError("baseline inputs do not match T067/T068 contract")
        public = _mapping(loaded["T067 public instances"], "public instances")
        metrics = _mapping(loaded["T068 grader metrics"], "grader metrics")
        if public.get("status") != "VALID" or public.get("target_values_exposed") is not False:
            raise BenchmarkBaselineError("public instances are not target-isolated")
        if metrics.get("status") != "VALID" or metrics.get("target_values_exposed") is not False:
            raise BenchmarkBaselineError("grader metrics are not target-isolated")
        return public

    @staticmethod
    def _targets(fixture: Mapping[str, Any], public: Mapping[str, Any]) -> dict[str, float]:
        public_ids = {
            _string(_mapping(row, "public instance").get("instance_id"), "public instance ID")
            for row in public["instances"]
        }
        targets: dict[str, float] = {}
        for value in fixture["targets"]:
            row = _mapping(value, "baseline target")
            if set(row) != {"instance_id", "target"}:
                raise BenchmarkBaselineError("baseline target fields do not match schema")
            instance_id = _string(row.get("instance_id"), "baseline target instance ID")
            if instance_id not in public_ids or instance_id in targets:
                raise BenchmarkBaselineError(f"baseline target identity is invalid: {instance_id}")
            targets[instance_id] = _number(row.get("target"), "baseline target")
        if set(targets) != public_ids:
            raise BenchmarkBaselineError("baseline targets do not cover public instances")
        return targets

    @staticmethod
    def _features(
        public_rows: list[dict[str, Any]],
    ) -> tuple[dict[str, list[float]], dict[str, Any]]:
        excluded_tokens = ("id", "locator", "cluster", "group", "study", "paper", "project")
        excluded: set[str] = set()
        vectors: dict[str, list[float]] = {}
        for row in public_rows:
            instance_id = _string(row.get("instance_id"), "public instance ID")
            public_input = _mapping(row.get("public_input"), "public input")
            numeric: list[float] = []
            categorical: list[float] = []
            missing = 0
            leaves = 0
            stack: list[tuple[str, Any]] = list(public_input.items())
            while stack:
                key, value = stack.pop()
                key_text = str(key)
                if any(token in key_text.lower() for token in excluded_tokens):
                    excluded.add(key_text)
                    continue
                if isinstance(value, Mapping):
                    stack.extend((f"{key_text}.{child_key}", child_value) for child_key, child_value in value.items())
                    continue
                leaves += 1
                if value is None:
                    missing += 1
                elif isinstance(value, bool | int | float):
                    numeric.append(float(value))
                elif isinstance(value, str):
                    categorical.append(_hash_bucket(f"{key_text}={value}"))
                else:
                    raise BenchmarkBaselineError(f"unsupported public feature value: {key_text}")
            vectors[instance_id] = [
                _mean(categorical) if categorical else 0.0,
                _mean(numeric) if numeric else 0.0,
                missing / leaves if leaves else 1.0,
                _number(row.get("missingness"), "instance missingness"),
            ]
        return vectors, {
            "schema_version": 1,
            "identifier_features_excluded": True,
            "excluded_fields": sorted(excluded),
            "feature_names": [
                "categorical_hash_mean",
                "numeric_mean",
                "public_input_missing_ratio",
                "instance_missingness",
            ],
        }

    def run(self, *, group: str = "simple") -> BenchmarkBaselineSummary:
        """Run all simple baselines from the frozen fixture."""
        if group != "simple":
            raise BenchmarkBaselineError("--group simple is required for baseline run")
        data = self._load_fixture()
        public = self._verify_inputs(data)
        targets = self._targets(data, public)
        public_rows = [_mapping(row, "public instance") for row in public["instances"]]
        vectors, feature_audit = self._features(public_rows)
        rows = [
            {
                **row,
                "target": targets[_string(row.get("instance_id"), "instance ID")],
            }
            for row in public_rows
        ]
        train = [row for row in rows if row.get("split") == "train"]
        validation = [row for row in rows if row.get("split") == "validation"]
        if not train or not validation:
            raise BenchmarkBaselineError("baseline split requires train and validation rows")
        seed = int(_mapping(data["config"], "baseline config")["seed"])
        bootstrap_samples = int(_mapping(data["config"], "baseline config")["bootstrap_samples"])
        global_mean = _mean([row["target"] for row in train])
        family_values: dict[str, list[float]] = {}
        for row in train:
            family_values.setdefault(_string(row["family"], "family"), []).append(row["target"])
        family_means = {key: _mean(value) for key, value in family_values.items()}
        train_vectors = [vectors[_string(row["instance_id"], "instance ID")] for row in train]
        train_targets = [row["target"] for row in train]
        linear_coefficients = _ridge_fit([[1.0, *vector] for vector in train_vectors], train_targets, ridge=0.1)
        baseline_predictions: dict[str, dict[str, float]] = {}
        for name in ("mean", "family_mean", "knn", "linear", "mixed_effect"):
            predictions: dict[str, float] = {}
            for row in rows:
                instance_id = _string(row["instance_id"], "instance ID")
                family = _string(row["family"], "family")
                if name == "mean":
                    prediction = global_mean
                elif name == "family_mean":
                    prediction = family_means.get(family, global_mean)
                elif name == "knn":
                    distances = sorted(
                        (
                            math.sqrt(
                                sum(
                                    (left - right) ** 2
                                    for left, right in zip(vectors[instance_id], candidate, strict=True)
                                )
                            ),
                            train_row["target"],
                        )
                        for candidate, train_row in zip(train_vectors, train, strict=True)
                    )
                    prediction = _mean([target for _, target in distances[:3]])
                elif name == "linear":
                    prediction = _predict_linear(linear_coefficients, [1.0, *vectors[instance_id]])
                else:
                    family_mean = family_means.get(family, global_mean)
                    prediction = global_mean + 0.75 * (family_mean - global_mean)
                predictions[instance_id] = prediction
            baseline_predictions[name] = predictions
        results: list[dict[str, Any]] = []
        for offset, (name, predictions) in enumerate(baseline_predictions.items()):
            train_metrics = _regression_metrics(train, predictions)
            validation_metrics = _regression_metrics(validation, predictions)
            result = {
                "baseline": name,
                "status": "SUCCESS",
                "seed": seed,
                "config": {
                    "group": group,
                    "bootstrap_samples": bootstrap_samples,
                    "knn_k": 3,
                    "linear_ridge": 0.1,
                    "mixed_effect_shrinkage": 0.75,
                    "feature_names": feature_audit["feature_names"],
                },
                "train_metrics": train_metrics,
                "validation_metrics": validation_metrics,
                "primary_ood_metric": "rmse",
                "primary_ood_value": validation_metrics["rmse"],
                "primary_ood_confidence_interval": _bootstrap_ci(
                    validation, predictions, seed + offset, bootstrap_samples
                ),
                "family_metrics": _group_metrics(validation, predictions, "family"),
                "split_metrics": _group_metrics(validation, predictions, "split"),
                "group_metrics": _group_metrics(validation, predictions, "group_key"),
                "missingness": {
                    "validation_mean": round(_mean([row["missingness"] for row in validation]), 6),
                    "validation_instances": len(validation),
                    "missingness_indicator_used": True,
                },
            }
            results.append(result)
        raw_payloads: dict[str, Any] = {
            "results": {
                "schema_version": 1,
                "benchmark_version": public["benchmark_version"],
                "group": group,
                "status": "VALID",
                "target_values_exposed": False,
                "baselines": results,
            },
            "feature_audit": feature_audit,
            "failures": {"schema_version": 1, "status": "VALID", "failures": []},
        }
        resume_key = _sha256(_canonical(raw_payloads))
        self.output_root.mkdir(parents=True, exist_ok=True)
        paths = {
            "results": self.output_root / "baseline_results.json",
            "feature_audit": self.output_root / "feature_audit.json",
            "failures": self.output_root / "failure_ledger.json",
            "receipt": self.output_root / "baseline_receipt.json",
            "log": self.output_root / "baseline_log.json",
            "manifest": self.output_root / "baseline_manifest.json",
        }
        payload_bytes = {name: _canonical(value) for name, value in raw_payloads.items()}
        artifact_records = {
            name: {
                "path": str(path.relative_to(self.root)) if path.is_relative_to(self.root) else str(path),
                "sha256": _sha256(payload_bytes[name]),
                "bytes": len(payload_bytes[name]),
            }
            for name, path in paths.items()
            if name in payload_bytes
        }
        best_rmse = min(float(result["primary_ood_value"]) for result in results)
        receipt = {
            "schema_version": 1,
            "status": "VALID",
            "fixture": True,
            "group": group,
            "baselines": len(results),
            "successful": len([result for result in results if result["status"] == "SUCCESS"]),
            "validation_instances": len(validation),
            "best_rmse": best_rmse,
            "seed": seed,
            "bootstrap_samples": bootstrap_samples,
            "target_values_exposed": False,
            "resume_key": resume_key,
            "artifacts": artifact_records,
        }
        payload_bytes["receipt"] = _canonical(receipt)
        payload_bytes["log"] = _canonical(
            {
                "schema_version": 1,
                "resume_key": resume_key,
                "events": [
                    {"event": "T067_T068_inputs_verified", "instances": len(rows)},
                    {
                        "event": "identifier_feature_audit_passed",
                        "excluded": len(feature_audit["excluded_fields"]),
                    },
                    {"event": "simple_baselines_completed", "baselines": len(results)},
                    {
                        "event": "bootstrap_confidence_intervals_computed",
                        "samples": bootstrap_samples,
                    },
                ],
            }
        )
        payload_bytes["manifest"] = _canonical(
            {
                "schema_version": 1,
                "status": "VALID",
                "resume_supported": True,
                "resume_key": resume_key,
                "group": group,
                "baselines": len(results),
                "successful": len(results),
                "target_values_exposed": False,
                "artifacts": {
                    name: {
                        "path": str(path.relative_to(self.root)) if path.is_relative_to(self.root) else str(path),
                        "sha256": _sha256(payload_bytes[name]),
                        "bytes": len(payload_bytes[name]),
                    }
                    for name, path in paths.items()
                    if name in payload_bytes
                },
            }
        )
        existing_receipt = paths["receipt"].read_bytes() if paths["receipt"].exists() else None
        if existing_receipt is not None:
            if existing_receipt != payload_bytes["receipt"]:
                raise BenchmarkBaselineError("existing baseline receipt differs from rerun")
            for name, payload in payload_bytes.items():
                if paths[name].read_bytes() != payload:
                    raise BenchmarkBaselineError(f"existing baseline artifact differs: {name}")
            resumed = 1
        else:
            for name, payload in payload_bytes.items():
                paths[name].write_bytes(payload)
            resumed = 0
        return BenchmarkBaselineSummary(
            baselines=len(results),
            successful=len(results),
            validation_instances=len(validation),
            best_rmse=best_rmse,
            resumed=resumed,
            receipt_path=paths["receipt"],
        )
