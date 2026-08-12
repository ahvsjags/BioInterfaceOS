"""Deterministic fixture-backed grading for BioInterfaceBench."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class BenchmarkGradeError(RuntimeError):
    """Raised when a benchmark submission or metric contract is invalid."""


@dataclass(frozen=True)
class BenchmarkGradeSummary:
    """Summary of one deterministic grading run."""

    cases: int
    instances: int
    perfect_accuracy: float
    wrong_accuracy: float
    abstain_coverage: float
    resumed: int
    receipt_path: Path


def _canonical(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    ).encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise BenchmarkGradeError(f"{label} must be an object")
    return dict(value)


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise BenchmarkGradeError(f"{label} must be a non-empty string")
    return value.strip()


def _bounded_number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise BenchmarkGradeError(f"{label} must be numeric")
    result = float(value)
    if not math.isfinite(result) or not 0.0 <= result <= 1.0:
        raise BenchmarkGradeError(f"{label} must be within [0, 1]")
    return result


def _forbidden_fields(value: Any, forbidden: set[str], path: str) -> list[str]:
    found: list[str] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            key_text = str(key)
            child_path = f"{path}.{key_text}"
            if key_text in forbidden:
                found.append(child_path)
            found.extend(_forbidden_fields(child, forbidden, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_forbidden_fields(child, forbidden, f"{path}[{index}]"))
    return found


def _wrong_value(target: Any) -> Any:
    if isinstance(target, bool):
        return not target
    if isinstance(target, int | float):
        return float(target) + 1.0
    if isinstance(target, str):
        return f"WRONG::{target}"
    return {"wrong": True}


def _calibration_error(correct: list[bool], confidence: list[float]) -> float:
    if not correct:
        return 0.0
    bins: list[list[tuple[bool, float]]] = [[] for _ in range(5)]
    for observed, value in zip(correct, confidence, strict=True):
        index = min(4, int(value * 5.0))
        bins[index].append((observed, value))
    total = len(correct)
    error = 0.0
    for entries in bins:
        if entries:
            accuracy = sum(item[0] for item in entries) / len(entries)
            mean_confidence = sum(item[1] for item in entries) / len(entries)
            error += len(entries) / total * abs(accuracy - mean_confidence)
    return round(error, 6)


def _metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(rows)
    answered = [row for row in rows if not row["abstained"]]
    correct = sum(row["correct"] for row in answered)
    accuracy = correct / len(answered) if answered else None
    coverage = len(answered) / total if total else 0.0
    confidence = [1.0 - row["uncertainty"] for row in answered]
    return {
        "instances": total,
        "answered": len(answered),
        "abstained": total - len(answered),
        "correct": correct,
        "accuracy": round(accuracy, 6) if accuracy is not None else None,
        "coverage": round(coverage, 6),
        "selective_risk": round(1.0 - accuracy, 6) if accuracy is not None else None,
        "mean_uncertainty": round(sum(row["uncertainty"] for row in rows) / total, 6)
        if total
        else 0.0,
        "calibration_error": _calibration_error(
            [bool(row["correct"]) for row in answered], confidence
        ),
    }


def _group_metrics(rows: list[dict[str, Any]], field: str) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        key = _string(row[field], f"group field {field}")
        groups.setdefault(key, []).append(row)
    return [{field: key, **_metrics(groups[key])} for key in sorted(groups)]


class BenchmarkGradingWorkflow:
    """Grade controlled submissions without exposing fixture target values."""

    def __init__(
        self,
        root: Path,
        *,
        fixture_path: Path | None = None,
        output_root: Path | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.fixture_path = fixture_path or (
            self.root / "tests/fixtures/benchmark/grading_fixture.json"
        )
        self.instances_path = self.root / "reports/benchmark/instances/public_instances.json"
        self.registry_path = self.root / "reports/benchmark/instances/hidden_target_registry.json"
        self.output_root = output_root or self.root / "reports/benchmark/grading"

    def _load_fixture(self) -> dict[str, Any]:
        try:
            data = _mapping(
                json.loads(self.fixture_path.read_text(encoding="utf-8")),
                "grading fixture",
            )
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise BenchmarkGradeError(f"cannot load grading fixture: {exc}") from exc
        if data.get("schema_version") != 1 or data.get("mode") != "benchmark_grade_fixture":
            raise BenchmarkGradeError("grading fixture schema or mode is invalid")
        if data.get("target_values_are_fixture_only") is not True:
            raise BenchmarkGradeError("grading targets must be marked fixture-only")
        if not isinstance(data.get("inputs"), list):
            raise BenchmarkGradeError("grading inputs must be a list")
        if not isinstance(data.get("targets"), list) or not isinstance(data.get("cases"), list):
            raise BenchmarkGradeError("grading targets/cases must be lists")
        return data

    def _verify_inputs(self, fixture: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
        required = {
            "T067 public instances": self.instances_path,
            "T067 hidden registry metadata": self.registry_path,
        }
        seen: set[str] = set()
        for value in fixture["inputs"]:
            row = _mapping(value, "grading input")
            label = _string(row.get("label"), "grading input label")
            if label not in required:
                raise BenchmarkGradeError(f"unexpected grading input: {label}")
            relative = _string(row.get("path"), "grading input path")
            expected_path = required[label].resolve(strict=True)
            observed_path = (self.root / relative).resolve(strict=True)
            if observed_path != expected_path:
                raise BenchmarkGradeError(f"grading input path mismatch: {label}")
            expected_hash = _string(row.get("sha256"), "grading input checksum")
            if _sha256(observed_path.read_bytes()) != expected_hash:
                raise BenchmarkGradeError(f"grading input checksum differs: {label}")
            seen.add(label)
        if seen != set(required):
            raise BenchmarkGradeError("grading inputs do not match T067 contract")
        try:
            public = _mapping(
                json.loads(self.instances_path.read_text(encoding="utf-8")), "public instances"
            )
            registry = _mapping(
                json.loads(self.registry_path.read_text(encoding="utf-8")), "hidden registry"
            )
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise BenchmarkGradeError(f"cannot load T067 grading inputs: {exc}") from exc
        if public.get("status") != "VALID" or public.get("target_values_exposed") is not False:
            raise BenchmarkGradeError("public benchmark is not target-isolated")
        if registry.get("status") != "LOCKED_REGISTRY_METADATA_ONLY":
            raise BenchmarkGradeError("hidden registry is not metadata-only")
        if registry.get("target_values_exposed") is not False:
            raise BenchmarkGradeError("hidden registry exposes target values")
        return public, registry

    @staticmethod
    def _validate_targets(
        fixture: Mapping[str, Any], public: Mapping[str, Any], registry: Mapping[str, Any]
    ) -> dict[str, Any]:
        public_rows = [_mapping(row, "public instance") for row in public["instances"]]
        registry_rows = [_mapping(row, "hidden registry row") for row in registry["targets"]]
        public_ids = {_string(row.get("instance_id"), "public instance ID") for row in public_rows}
        registry_ids = {
            _string(row.get("instance_id"), "registry instance ID") for row in registry_rows
        }
        if public_ids != registry_ids:
            raise BenchmarkGradeError("public and hidden registry instance IDs differ")
        targets: dict[str, Any] = {}
        for value in fixture["targets"]:
            row = _mapping(value, "fixture target")
            expected = {"instance_id", "target"}
            if set(row) != expected:
                raise BenchmarkGradeError("fixture target fields do not match schema")
            instance_id = _string(row.get("instance_id"), "fixture target instance ID")
            if instance_id not in public_ids or instance_id in targets:
                raise BenchmarkGradeError(f"fixture target identity is invalid: {instance_id}")
            targets[instance_id] = row["target"]
        if set(targets) != public_ids:
            raise BenchmarkGradeError("fixture targets do not cover T067 instances")
        forbidden = {"accepted_value", "hidden_target", "label", "outcome", "target"}
        exposed = _forbidden_fields(public, forbidden, "public")
        if exposed:
            raise BenchmarkGradeError("public benchmark contains forbidden target fields")
        return targets

    @staticmethod
    def _validate_cases(fixture: Mapping[str, Any]) -> list[dict[str, Any]]:
        cases: list[dict[str, Any]] = []
        seen: set[str] = set()
        for value in fixture["cases"]:
            row = _mapping(value, "grading case")
            if set(row) != {"case_id", "mode", "uncertainty"}:
                raise BenchmarkGradeError("grading case fields do not match schema")
            case_id = _string(row.get("case_id"), "grading case ID")
            mode = _string(row.get("mode"), "grading case mode")
            if mode not in {"perfect", "wrong", "abstain"}:
                raise BenchmarkGradeError(f"unknown grading case mode: {mode}")
            if case_id in seen:
                raise BenchmarkGradeError(f"duplicate grading case: {case_id}")
            seen.add(case_id)
            cases.append(
                {
                    "case_id": case_id,
                    "mode": mode,
                    "uncertainty": _bounded_number(row["uncertainty"], "case uncertainty"),
                }
            )
        if not cases:
            raise BenchmarkGradeError("grading fixture has no cases")
        return cases

    @staticmethod
    def _evaluate_case(
        case: Mapping[str, Any], public_rows: list[dict[str, Any]], targets: Mapping[str, Any]
    ) -> dict[str, Any]:
        mode = _string(case["mode"], "grading mode")
        uncertainty = float(case["uncertainty"])
        rows: list[dict[str, Any]] = []
        for instance in public_rows:
            instance_id = _string(instance.get("instance_id"), "public instance ID")
            target = targets[instance_id]
            abstained = mode == "abstain"
            prediction = (
                None if abstained else target if mode == "perfect" else _wrong_value(target)
            )
            correct = not abstained and prediction == target
            rows.append(
                {
                    "instance_id": instance_id,
                    "family": _string(instance.get("family"), "public family"),
                    "split": _string(instance.get("split"), "public split"),
                    "group_key": _string(instance.get("group_key"), "public group key"),
                    "correct": correct,
                    "abstained": abstained,
                    "uncertainty": uncertainty,
                }
            )
        return {
            "case_id": _string(case["case_id"], "grading case ID"),
            "mode": mode,
            "scores": rows,
            "overall": _metrics(rows),
            "family_metrics": _group_metrics(rows, "family"),
            "split_metrics": _group_metrics(rows, "split"),
            "group_metrics": _group_metrics(rows, "group_key"),
        }

    def run(self, *, fixture: bool = True) -> BenchmarkGradeSummary:
        """Grade perfect, wrong, and abstain controls from an offline fixture."""
        if not fixture:
            raise BenchmarkGradeError("--fixture is required for benchmark grade")
        data = self._load_fixture()
        public, registry = self._verify_inputs(data)
        targets = self._validate_targets(data, public, registry)
        cases = self._validate_cases(data)
        public_rows = [_mapping(row, "public instance") for row in public["instances"]]
        evaluated = [self._evaluate_case(case, public_rows, targets) for case in cases]
        by_mode = {row["mode"]: row for row in evaluated}
        for required in ("perfect", "wrong", "abstain"):
            if required not in by_mode:
                raise BenchmarkGradeError(f"required grading control is missing: {required}")
        if by_mode["perfect"]["overall"]["accuracy"] != 1.0:
            raise BenchmarkGradeError("perfect control did not score 1.0 accuracy")
        if by_mode["wrong"]["overall"]["accuracy"] != 0.0:
            raise BenchmarkGradeError("wrong control did not score 0.0 accuracy")
        if by_mode["abstain"]["overall"]["coverage"] != 0.0:
            raise BenchmarkGradeError("abstain control did not score 0.0 coverage")
        raw_payloads: dict[str, Any] = {
            "scores": {
                "schema_version": 1,
                "benchmark_version": public["benchmark_version"],
                "status": "VALID",
                "target_values_exposed": False,
                "cases": evaluated,
            },
            "metrics": {
                "schema_version": 1,
                "benchmark_version": public["benchmark_version"],
                "status": "VALID",
                "target_values_exposed": False,
                "cases": {
                    case["case_id"]: {
                        "overall": case["overall"],
                        "family_metrics": case["family_metrics"],
                        "split_metrics": case["split_metrics"],
                        "group_metrics": case["group_metrics"],
                    }
                    for case in evaluated
                },
            },
            "failures": {
                "schema_version": 1,
                "status": "VALID",
                "failures": [],
                "target_values_exposed": False,
            },
        }
        resume_key = _sha256(_canonical(raw_payloads))
        self.output_root.mkdir(parents=True, exist_ok=True)
        paths = {
            "scores": self.output_root / "instance_scores.json",
            "metrics": self.output_root / "metrics.json",
            "failures": self.output_root / "failure_ledger.json",
            "receipt": self.output_root / "grading_receipt.json",
            "log": self.output_root / "grading_log.json",
            "manifest": self.output_root / "grading_manifest.json",
        }
        payload_bytes = {name: _canonical(value) for name, value in raw_payloads.items()}
        artifact_records = {
            name: {
                "path": str(path.relative_to(self.root))
                if path.is_relative_to(self.root)
                else str(path),
                "sha256": _sha256(payload_bytes[name]),
                "bytes": len(payload_bytes[name]),
            }
            for name, path in paths.items()
            if name in payload_bytes
        }
        receipt = {
            "schema_version": 1,
            "status": "VALID",
            "fixture": True,
            "instances": len(public_rows),
            "cases": len(evaluated),
            "perfect_accuracy": by_mode["perfect"]["overall"]["accuracy"],
            "wrong_accuracy": by_mode["wrong"]["overall"]["accuracy"],
            "abstain_coverage": by_mode["abstain"]["overall"]["coverage"],
            "target_values_exposed": False,
            "network_accessed": False,
            "resume_key": resume_key,
            "artifacts": artifact_records,
        }
        payload_bytes["receipt"] = _canonical(receipt)
        payload_bytes["log"] = _canonical(
            {
                "schema_version": 1,
                "resume_key": resume_key,
                "events": [
                    {"event": "T067_inputs_verified", "instances": len(public_rows)},
                    {"event": "controls_graded", "cases": len(evaluated)},
                    {
                        "event": "grouped_metrics_computed",
                        "groups": len(evaluated[0]["group_metrics"]),
                    },
                    {"event": "target_isolation_verified", "exposed": False},
                ],
            }
        )
        payload_bytes["manifest"] = _canonical(
            {
                "schema_version": 1,
                "status": "VALID",
                "resume_supported": True,
                "resume_key": resume_key,
                "instances": len(public_rows),
                "cases": len(evaluated),
                "target_values_exposed": False,
                "artifacts": {
                    name: {
                        "path": str(path.relative_to(self.root))
                        if path.is_relative_to(self.root)
                        else str(path),
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
                raise BenchmarkGradeError("existing grading receipt differs from rerun")
            for name, payload in payload_bytes.items():
                if paths[name].read_bytes() != payload:
                    raise BenchmarkGradeError(f"existing grading artifact differs: {name}")
            resumed = 1
        else:
            for name, payload in payload_bytes.items():
                paths[name].write_bytes(payload)
            resumed = 0
        return BenchmarkGradeSummary(
            cases=len(evaluated),
            instances=len(public_rows),
            perfect_accuracy=float(by_mode["perfect"]["overall"]["accuracy"]),
            wrong_accuracy=float(by_mode["wrong"]["overall"]["accuracy"]),
            abstain_coverage=float(by_mode["abstain"]["overall"]["coverage"]),
            resumed=resumed,
            receipt_path=paths["receipt"],
        )
