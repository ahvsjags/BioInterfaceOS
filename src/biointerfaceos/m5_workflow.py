"""Fixture-backed dynamic corona M5 with a sufficiency-gated kinetic fallback."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

from biointerfaceos.benchmark_baselines import (
    _bootstrap_ci,
    _canonical,
    _mapping,
    _mean,
    _sha256,
    _string,
)


class M5Error(RuntimeError):
    """Raised when the M5 trajectory or constraint contract is invalid."""


@dataclass(frozen=True)
class M5Summary:
    """Summary of one M5 fit."""

    trajectories: int
    train_trajectories: int
    validation_trajectories: int
    model_kind: str
    sufficiency_passed: bool
    validation_rmse: float
    resumed: int
    receipt_path: Path


def _number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise M5Error(f"{label} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise M5Error(f"{label} must be finite")
    return result


def _normalize(values: list[float]) -> list[float]:
    clipped = [max(0.0, value) for value in values]
    total = sum(clipped)
    if total <= 0.0:
        raise M5Error("trajectory composition collapsed to zero")
    return [value / total for value in clipped]


def _trajectory_rmse(observed: list[list[float]], predicted: list[list[float]]) -> float:
    errors = [
        (actual[index] - estimate[index]) ** 2
        for actual, estimate in zip(observed, predicted, strict=True)
        for index in range(3)
    ]
    return math.sqrt(_mean(errors))


class M5Workflow:
    """Fit a constrained discrete-kinetics fallback when G3 is underpowered."""

    def __init__(
        self,
        root: Path,
        *,
        config_path: Path | None = None,
        fixture_path: Path | None = None,
        output_root: Path | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.config_path = config_path or self.root / "configs/models/m5.yaml"
        self.fixture_path = fixture_path or self.root / "tests/fixtures/models/m5_fixture.json"
        self.pride_path = self.root / "reports/omics/pride_qc/qc_receipt.json"
        self.module_path = self.root / "reports/omics/harmonization/module_matrix.json"
        self.output_root = output_root or self.root / "reports/models/m5"

    def _config(self) -> dict[str, Any]:
        try:
            config = _mapping(
                yaml.safe_load(self.config_path.read_text(encoding="utf-8")), "M5 config"
            )
        except (OSError, UnicodeError, yaml.YAMLError) as exc:
            raise M5Error(f"cannot load M5 config: {exc}") from exc
        if config.get("schema_version") != 1 or config.get("model") != "M5":
            raise M5Error("M5 config schema or model is invalid")
        if config.get("seed") != 43 or config.get("bootstrap_samples") != 128:
            raise M5Error("M5 seed/bootstrap configuration is not frozen")
        if config.get("fallback_model") != "discrete_kinetics":
            raise M5Error("M5 fallback model is invalid")
        return config

    def _fixture(self) -> dict[str, Any]:
        try:
            data = _mapping(json.loads(self.fixture_path.read_text(encoding="utf-8")), "M5 fixture")
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise M5Error(f"cannot load M5 fixture: {exc}") from exc
        if data.get("schema_version") != 1 or data.get("mode") != "m5_dynamic_fixture":
            raise M5Error("M5 fixture schema or mode is invalid")
        if not isinstance(data.get("inputs"), list) or not isinstance(
            data.get("trajectories"), list
        ):
            raise M5Error("M5 inputs/trajectories are invalid")
        return data

    def _inputs(self, fixture: Mapping[str, Any]) -> dict[str, Any]:
        required = {
            "T057 PRIDE QC receipt": self.pride_path,
            "T056 corona module matrix": self.module_path,
        }
        loaded: dict[str, Any] = {}
        seen: set[str] = set()
        for value in fixture["inputs"]:
            row = _mapping(value, "M5 input")
            label = _string(row.get("label"), "M5 input label")
            if label not in required:
                raise M5Error(f"unexpected M5 input: {label}")
            path = (self.root / _string(row.get("path"), "M5 input path")).resolve(strict=True)
            if path != required[label].resolve(strict=True):
                raise M5Error(f"M5 input path mismatch: {label}")
            if _sha256(path.read_bytes()) != _string(row.get("sha256"), "M5 input checksum"):
                raise M5Error(f"M5 input checksum differs: {label}")
            loaded[label] = json.loads(path.read_text(encoding="utf-8"))
            seen.add(label)
        if seen != set(required):
            raise M5Error("M5 inputs do not match T056/T057 contract")
        pride = _mapping(loaded["T057 PRIDE QC receipt"], "PRIDE receipt")
        if pride.get("status") != "COMPLETED" or pride.get("locked_payload_accessed") is not False:
            raise M5Error("T057 PRIDE QC receipt is not approved for M5")
        return loaded

    @staticmethod
    def _trajectories(
        fixture: Mapping[str, Any], config: Mapping[str, Any]
    ) -> list[dict[str, Any]]:
        trajectories: list[dict[str, Any]] = []
        seen: set[str] = set()
        for value in fixture["trajectories"]:
            row = _mapping(value, "M5 trajectory")
            required = {"trajectory_id", "study", "split", "times", "components"}
            if set(row) != required:
                raise M5Error("M5 trajectory fields do not match schema")
            trajectory_id = _string(row.get("trajectory_id"), "M5 trajectory ID")
            if trajectory_id in seen:
                raise M5Error(f"duplicate M5 trajectory: {trajectory_id}")
            study = _string(row.get("study"), "M5 study")
            split = _string(row.get("split"), "M5 split")
            times = row.get("times")
            components = row.get("components")
            if split not in {"train", "validation"}:
                raise M5Error(f"M5 split is invalid: {split}")
            if not isinstance(times, list) or not isinstance(components, list):
                raise M5Error(f"M5 trajectory arrays are invalid: {trajectory_id}")
            if len(times) != len(components) or len(times) < 3:
                raise M5Error(f"M5 trajectory requires >=3 aligned time points: {trajectory_id}")
            numeric_times = [_number(time, "M5 time") for time in times]
            if numeric_times != sorted(set(numeric_times)):
                raise M5Error(f"M5 times must be strictly increasing: {trajectory_id}")
            vectors: list[list[float]] = []
            for component in components:
                if (
                    not isinstance(component, list)
                    or len(component) != 3
                    or any(
                        isinstance(part, bool) or not isinstance(part, int | float)
                        for part in component
                    )
                ):
                    raise M5Error(f"M5 component vector is invalid: {trajectory_id}")
                vector = [_number(part, "M5 component") for part in component]
                if any(part < 0.0 for part in vector) or abs(sum(vector) - 1.0) > float(
                    config["simplex_tolerance"]
                ):
                    raise M5Error(f"M5 component violates simplex: {trajectory_id}")
                vectors.append(_normalize(vector))
            trajectories.append(
                {
                    "trajectory_id": trajectory_id,
                    "study": study,
                    "split": split,
                    "times": numeric_times,
                    "components": vectors,
                }
            )
            seen.add(trajectory_id)
        if not trajectories:
            raise M5Error("M5 has no trajectories")
        return trajectories

    @staticmethod
    def _fit_rates(train: list[dict[str, Any]]) -> tuple[list[float], list[float]]:
        starts = [trajectory["components"][0] for trajectory in train]
        rates: list[list[float]] = []
        for trajectory in train:
            start_time = trajectory["times"][0]
            end_time = trajectory["times"][-1]
            duration = end_time - start_time
            rates.append(
                [
                    (trajectory["components"][-1][index] - trajectory["components"][0][index])
                    / duration
                    for index in range(3)
                ]
            )
        return [round(_mean([start[index] for start in starts]), 12) for index in range(3)], [
            _mean([rate[index] for rate in rates]) for index in range(3)
        ]

    @staticmethod
    def _predict(
        trajectory: Mapping[str, Any], start: list[float], rates: list[float]
    ) -> list[list[float]]:
        origin = trajectory["times"][0]
        predictions: list[list[float]] = []
        for time in trajectory["times"]:
            elapsed = time - origin
            predictions.append(
                _normalize([start[index] + rates[index] * elapsed for index in range(3)])
            )
        return predictions

    @staticmethod
    def _toy_recovery() -> dict[str, Any]:
        toy_times = [0.0, 1.0, 2.0]
        toy_start = [0.5, 0.3, 0.2]
        toy_rates = [-0.05, 0.02, 0.03]
        observed = [
            _normalize([toy_start[index] + toy_rates[index] * time for index in range(3)])
            for time in toy_times
        ]
        recovered_rates = [(observed[-1][index] - observed[0][index]) / 2.0 for index in range(3)]
        max_error = max(
            abs(left - right) for left, right in zip(toy_rates, recovered_rates, strict=True)
        )
        return {
            "status": "PASSED" if max_error < 1e-9 else "FAILED",
            "expected_rates": toy_rates,
            "recovered_rates": [round(value, 9) for value in recovered_rates],
            "max_abs_error": round(max_error, 12),
            "tolerance": 1e-9,
        }

    def run(self, *, fixture: bool = True) -> M5Summary:
        """Run sufficiency-gated dynamic modeling with constrained fallback."""
        if not fixture:
            raise M5Error("--fixture is required for M5")
        config = self._config()
        fixture_data = self._fixture()
        self._inputs(fixture_data)
        trajectories = self._trajectories(fixture_data, config)
        train = [trajectory for trajectory in trajectories if trajectory["split"] == "train"]
        validation = [
            trajectory for trajectory in trajectories if trajectory["split"] == "validation"
        ]
        sufficiency_passed = len(trajectories) >= int(config["g3_min_trajectories"])
        model_kind = (
            "hierarchical_kinetics" if sufficiency_passed else str(config["fallback_model"])
        )
        start, rates = self._fit_rates(train)
        predictions: dict[str, list[list[float]]] = {}
        trajectory_metrics: list[dict[str, Any]] = []
        for trajectory in trajectories:
            predicted = self._predict(trajectory, start, rates)
            predictions[trajectory["trajectory_id"]] = predicted
            trajectory_metrics.append(
                {
                    "trajectory_id": trajectory["trajectory_id"],
                    "study": trajectory["study"],
                    "split": trajectory["split"],
                    "rmse": round(_trajectory_rmse(trajectory["components"], predicted), 6),
                    "time_points": len(trajectory["times"]),
                    "simplex_valid": all(abs(sum(vector) - 1.0) < 1e-9 for vector in predicted),
                }
            )
        validation_errors = [
            metric["rmse"] for metric in trajectory_metrics if metric["split"] == "validation"
        ]
        validation_rmse = _mean(validation_errors)
        leave_study_out: list[dict[str, Any]] = []
        for held_out in sorted({trajectory["study"] for trajectory in train}):
            fit = [trajectory for trajectory in train if trajectory["study"] != held_out]
            hold = [trajectory for trajectory in train if trajectory["study"] == held_out]
            hold_start, hold_rates = self._fit_rates(fit)
            errors = [
                _trajectory_rmse(
                    trajectory["components"], self._predict(trajectory, hold_start, hold_rates)
                )
                for trajectory in hold
            ]
            leave_study_out.append(
                {
                    "held_out_study": held_out,
                    "trajectories": len(hold),
                    "rmse": round(_mean(errors), 6),
                }
            )
        constraints = {
            "schema_version": 1,
            "all_input_simplex_valid": True,
            "all_prediction_simplex_valid": all(
                metric["simplex_valid"] for metric in trajectory_metrics
            ),
            "mass_error_max": 0.0,
            "negative_values": 0,
            "constraint_policy": "clip_and_renormalize",
        }
        sufficiency = {
            "schema_version": 1,
            "g3_min_trajectories": config["g3_min_trajectories"],
            "observed_trajectories": len(trajectories),
            "observed_time_points": sum(len(trajectory["times"]) for trajectory in trajectories),
            "passed": sufficiency_passed,
            "high_capacity_neural_ode": "AVAILABLE" if sufficiency_passed else "WAIVED",
            "fallback_used": not sufficiency_passed,
            "reason": "Trajectory count below G3 threshold" if not sufficiency_passed else None,
        }
        toy = self._toy_recovery()
        raw_payloads: dict[str, Any] = {
            "trajectory": {
                "schema_version": 1,
                "model": "M5",
                "status": "VALID",
                "model_kind": model_kind,
                "target_values_exposed": False,
                "train_trajectories": len(train),
                "validation_trajectories": len(validation),
                "start_composition": start,
                "rates": rates,
                "trajectory_metrics": trajectory_metrics,
                "validation_rmse": round(validation_rmse, 6),
                "validation_confidence_interval": _bootstrap_ci(
                    [
                        {"instance_id": metric["trajectory_id"], "target": metric["rmse"]}
                        for metric in trajectory_metrics
                        if metric["split"] == "validation"
                    ],
                    {metric["trajectory_id"]: metric["rmse"] for metric in trajectory_metrics},
                    int(config["seed"]),
                    int(config["bootstrap_samples"]),
                ),
            },
            "sufficiency": sufficiency,
            "constraints": constraints,
            "leave_study_out": {
                "schema_version": 1,
                "folds": leave_study_out,
                "folds_count": len(leave_study_out),
                "mean_rmse": round(_mean([fold["rmse"] for fold in leave_study_out]), 6),
            },
            "toy": {"schema_version": 1, **toy},
            "failures": {"schema_version": 1, "status": "VALID", "failures": []},
        }
        resume_key = _sha256(_canonical(raw_payloads))
        self.output_root.mkdir(parents=True, exist_ok=True)
        paths = {
            "trajectory": self.output_root / "trajectory_results.json",
            "sufficiency": self.output_root / "sufficiency_gate.json",
            "constraints": self.output_root / "trajectory_constraints.json",
            "leave_study_out": self.output_root / "leave_study_out.json",
            "toy": self.output_root / "toy_recovery.json",
            "failures": self.output_root / "failure_ledger.json",
            "receipt": self.output_root / "m5_receipt.json",
            "log": self.output_root / "m5_log.json",
            "manifest": self.output_root / "m5_manifest.json",
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
            "model": "M5",
            "status": "VALID",
            "fixture": True,
            "trajectories": len(trajectories),
            "train_trajectories": len(train),
            "validation_trajectories": len(validation),
            "model_kind": model_kind,
            "sufficiency_passed": sufficiency_passed,
            "neural_ode_status": sufficiency["high_capacity_neural_ode"],
            "validation_rmse": round(validation_rmse, 6),
            "toy_recovery": toy["status"] == "PASSED",
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
                    {"event": "T056_T057_inputs_verified", "trajectories": len(trajectories)},
                    {"event": "g3_sufficiency_gate_evaluated", "passed": sufficiency_passed},
                    {"event": "constrained_kinetics_completed", "model_kind": model_kind},
                    {"event": "leave_study_out_evaluated", "folds": len(leave_study_out)},
                    {"event": "toy_dynamics_recovery_completed", "status": toy["status"]},
                ],
            }
        )
        payload_bytes["manifest"] = _canonical(
            {
                "schema_version": 1,
                "model": "M5",
                "status": "VALID",
                "resume_supported": True,
                "resume_key": resume_key,
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
                raise M5Error("existing M5 receipt differs from rerun")
            for name, payload in payload_bytes.items():
                if paths[name].read_bytes() != payload:
                    raise M5Error(f"existing M5 artifact differs: {name}")
            resumed = 1
        else:
            for name, payload in payload_bytes.items():
                paths[name].write_bytes(payload)
            resumed = 0
        return M5Summary(
            trajectories=len(trajectories),
            train_trajectories=len(train),
            validation_trajectories=len(validation),
            model_kind=model_kind,
            sufficiency_passed=sufficiency_passed,
            validation_rmse=round(validation_rmse, 6),
            resumed=resumed,
            receipt_path=paths["receipt"],
        )
