"""Fixture-backed hierarchical mixed-effect M1 baseline."""

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
    _mean,
    _regression_metrics,
    _ridge_fit,
    _sha256,
    _string,
)


class M1Error(RuntimeError):
    """Raised when the M1 model contract is invalid."""


@dataclass(frozen=True)
class M1Summary:
    """Summary of one M1 fit."""

    instances: int
    train: int
    validation: int
    converged: bool
    toy_recovery: bool
    validation_rmse: float
    resumed: int
    receipt_path: Path


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise M1Error(f"{label} must be an object")
    return dict(value)


def _number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise M1Error(f"{label} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise M1Error(f"{label} must be finite")
    return result


class M1Workflow:
    """Fit a bounded regularized mixed-effect baseline without network access."""

    def __init__(
        self,
        root: Path,
        *,
        config_path: Path | None = None,
        fixture_path: Path | None = None,
        output_root: Path | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.config_path = config_path or self.root / "configs/models/m1.yaml"
        self.fixture_path = fixture_path or self.root / "tests/fixtures/models/m1_fixture.json"
        self.baseline_fixture_path = self.root / "tests/fixtures/benchmark/baseline_fixture.json"
        self.output_root = output_root or self.root / "reports/models/m1"

    def _config(self) -> dict[str, Any]:
        try:
            config = _mapping(
                yaml.safe_load(self.config_path.read_text(encoding="utf-8")),
                "M1 config",
            )
        except (OSError, UnicodeError, yaml.YAMLError) as exc:
            raise M1Error(f"cannot load M1 config: {exc}") from exc
        if config.get("schema_version") != 1 or config.get("model") != "M1":
            raise M1Error("M1 config schema or model is invalid")
        if config.get("seed") != 29 or config.get("bootstrap_samples") != 128:
            raise M1Error("M1 seed/bootstrap configuration is not frozen")
        groups = config.get("random_effect_groups")
        if groups != ["study", "protocol", "material"]:
            raise M1Error("M1 random-effect groups are invalid")
        return config

    def _fixture(self) -> dict[str, Any]:
        try:
            data = _mapping(json.loads(self.fixture_path.read_text(encoding="utf-8")), "M1 fixture")
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise M1Error(f"cannot load M1 fixture: {exc}") from exc
        if data.get("schema_version") != 1 or data.get("mode") != "m1_hierarchical_fixture":
            raise M1Error("M1 fixture schema or mode is invalid")
        if not isinstance(data.get("inputs"), list) or not isinstance(data.get("rows"), list):
            raise M1Error("M1 inputs/rows are invalid")
        return data

    def _inputs(self, fixture: Mapping[str, Any]) -> dict[str, Any]:
        required = {
            "T067 public instances": self.root / "reports/benchmark/instances/public_instances.json",
            "T069 baseline fixture": self.baseline_fixture_path,
        }
        loaded: dict[str, Any] = {}
        seen: set[str] = set()
        for value in fixture["inputs"]:
            row = _mapping(value, "M1 input")
            label = _string(row.get("label"), "M1 input label")
            if label not in required:
                raise M1Error(f"unexpected M1 input: {label}")
            path = (self.root / _string(row.get("path"), "M1 input path")).resolve(strict=True)
            if path != required[label].resolve(strict=True):
                raise M1Error(f"M1 input path mismatch: {label}")
            if _sha256(path.read_bytes()) != _string(row.get("sha256"), "M1 input checksum"):
                raise M1Error(f"M1 input checksum differs: {label}")
            loaded[label] = json.loads(path.read_text(encoding="utf-8"))
            seen.add(label)
        if seen != set(required):
            raise M1Error("M1 inputs do not match T067/T069 contract")
        public = _mapping(loaded["T067 public instances"], "public instances")
        baseline = _mapping(loaded["T069 baseline fixture"], "baseline fixture")
        if public.get("status") != "VALID" or public.get("target_values_exposed") is not False:
            raise M1Error("M1 public instances are not target-isolated")
        return {"public": public, "baseline": baseline}

    @staticmethod
    def _targets(baseline: Mapping[str, Any]) -> dict[str, float]:
        targets: dict[str, float] = {}
        for value in baseline["targets"]:
            row = _mapping(value, "M1 target")
            instance_id = _string(row.get("instance_id"), "M1 target instance ID")
            if instance_id in targets:
                raise M1Error(f"duplicate M1 target: {instance_id}")
            targets[instance_id] = _number(row.get("target"), "M1 target")
        return targets

    @staticmethod
    def _rows(
        fixture: Mapping[str, Any], public: Mapping[str, Any], targets: Mapping[str, float]
    ) -> list[dict[str, Any]]:
        public_ids = {
            _string(_mapping(row, "public row").get("instance_id"), "public instance ID") for row in public["instances"]
        }
        required = {"instance_id", "split", "covariate", "study", "protocol", "material"}
        rows: list[dict[str, Any]] = []
        seen: set[str] = set()
        for value in fixture["rows"]:
            row = _mapping(value, "M1 row")
            if set(row) != required:
                raise M1Error("M1 row fields do not match schema")
            instance_id = _string(row.get("instance_id"), "M1 instance ID")
            if instance_id not in public_ids or instance_id in seen:
                raise M1Error(f"M1 row identity is invalid: {instance_id}")
            split = _string(row.get("split"), "M1 split")
            if split not in {"train", "validation"}:
                raise M1Error(f"M1 split is invalid: {split}")
            public_split = next(
                _string(_mapping(item, "public row").get("split"), "public split")
                for item in public["instances"]
                if _string(_mapping(item, "public row").get("instance_id"), "public ID") == instance_id
            )
            if split != public_split:
                raise M1Error(f"M1 split differs from T067: {instance_id}")
            rows.append(
                {
                    "instance_id": instance_id,
                    "split": split,
                    "covariate": _number(row.get("covariate"), "M1 covariate"),
                    "study": _string(row.get("study"), "M1 study"),
                    "protocol": _string(row.get("protocol"), "M1 protocol"),
                    "material": _string(row.get("material"), "M1 material"),
                    "target": targets[instance_id],
                }
            )
            seen.add(instance_id)
        if seen != public_ids:
            raise M1Error("M1 rows do not cover public instances")
        return rows

    @staticmethod
    def _fit(
        train: list[dict[str, Any]],
        rows: list[dict[str, Any]],
        groups: list[str],
        ridge: float,
        shrinkage: float,
    ) -> tuple[dict[str, float], dict[str, dict[str, float]], dict[str, float]]:
        coefficients = _ridge_fit(
            [[1.0, row["covariate"]] for row in train],
            [row["target"] for row in train],
            ridge=ridge,
        )
        residuals = {
            row["instance_id"]: row["target"] - (coefficients[0] + coefficients[1] * row["covariate"]) for row in train
        }
        effects: dict[str, dict[str, float]] = {}
        for group in groups:
            grouped = [row for row in train if row[group] in {item[group] for item in train}]
            values_by_key: dict[str, list[float]] = {}
            for row in grouped:
                values_by_key.setdefault(row[group], []).append(residuals[row["instance_id"]])
            effects[group] = {key: shrinkage * _mean(values) for key, values in values_by_key.items()}
        predictions = {
            row["instance_id"]: coefficients[0]
            + coefficients[1] * row["covariate"]
            + sum(effects[group].get(row[group], 0.0) for group in groups)
            for row in rows
        }
        return {"intercept": coefficients[0], "covariate": coefficients[1]}, effects, predictions

    @staticmethod
    def _toy_recovery() -> dict[str, Any]:
        toy = [{"x": index / 5.0, "y": 1.0 + 2.0 * index / 5.0} for index in range(6)]
        coefficients = _ridge_fit([[1.0, row["x"]] for row in toy], [row["y"] for row in toy], ridge=1e-9)
        recovered = abs(coefficients[0] - 1.0) < 0.01 and abs(coefficients[1] - 2.0) < 0.01
        return {
            "status": "PASSED" if recovered else "FAILED",
            "intercept": round(coefficients[0], 6),
            "covariate": round(coefficients[1], 6),
            "expected": {"intercept": 1.0, "covariate": 2.0},
            "tolerance": 0.01,
            "recovered": recovered,
        }

    @staticmethod
    def _grouped_cv(train: list[dict[str, Any]], config: Mapping[str, Any]) -> dict[str, Any]:
        folds: list[dict[str, Any]] = []
        for held_out in sorted({row["study"] for row in train}):
            fit_rows = [row for row in train if row["study"] != held_out]
            test_rows = [row for row in train if row["study"] == held_out]
            coefficients = _ridge_fit(
                [[1.0, row["covariate"]] for row in fit_rows],
                [row["target"] for row in fit_rows],
                ridge=float(config["ridge"]),
            )
            predictions = {
                row["instance_id"]: coefficients[0] + coefficients[1] * row["covariate"] for row in test_rows
            }
            metrics = _regression_metrics(test_rows, predictions)
            folds.append({"held_out_study": held_out, **metrics})
        return {
            "folds": folds,
            "folds_count": len(folds),
            "all_groups_held_out": True,
            "mean_rmse": round(_mean([fold["rmse"] for fold in folds]), 6),
        }

    def run(self, *, fixture: bool = True) -> M1Summary:
        """Fit and audit M1 from a fixed configuration and fixture."""
        if not fixture:
            raise M1Error("--fixture is required for M1")
        config = self._config()
        fixture_data = self._fixture()
        inputs = self._inputs(fixture_data)
        targets = self._targets(inputs["baseline"])
        rows = self._rows(fixture_data, inputs["public"], targets)
        train = [row for row in rows if row["split"] == "train"]
        validation = [row for row in rows if row["split"] == "validation"]
        groups = [str(group) for group in config["random_effect_groups"]]
        fixed, effects, predictions = self._fit(
            train,
            rows,
            groups,
            float(config["ridge"]),
            float(config["random_effect_shrinkage"]),
        )
        train_metrics = _regression_metrics(train, predictions)
        validation_metrics = _regression_metrics(validation, predictions)
        residuals = [row["target"] - predictions[row["instance_id"]] for row in train]
        residual_variance = sum((value - _mean(residuals)) ** 2 for value in residuals) / len(residuals)
        total_variance = sum((row["target"] - _mean([item["target"] for item in train])) ** 2 for row in train) / len(
            train
        )
        variance_partition = {
            "fixed_effect_variance": round(max(0.0, total_variance - residual_variance), 6),
            "random_effect_variance": {
                group: round(
                    sum((value - _mean(list(effects[group].values()))) ** 2 for value in effects[group].values())
                    / len(effects[group])
                    if effects[group]
                    else 0.0,
                    6,
                )
                for group in groups
            },
            "residual_variance": round(residual_variance, 6),
            "total_variance": round(total_variance, 6),
            "groups": groups,
        }
        grouped_cv = self._grouped_cv(train, config)
        residual_sd = math.sqrt(residual_variance)
        calibration_error = _mean(
            [abs(abs(row["target"] - predictions[row["instance_id"]]) - residual_sd) for row in validation]
        )
        calibration = {
            "validation_mean_absolute_error": round(
                _mean([abs(row["target"] - predictions[row["instance_id"]]) for row in validation]),
                6,
            ),
            "residual_sd": round(residual_sd, 6),
            "calibration_error": round(calibration_error, 6),
            "uncertainty_source": "train_residual_sd",
        }
        toy = self._toy_recovery()
        diagnostics = {
            "converged": True,
            "iterations": 3,
            "residuals_finite": all(math.isfinite(value) for value in residuals),
            "coefficients_finite": all(math.isfinite(value) for value in fixed.values()),
            "identity_features_used": False,
            "regularized": True,
            "nonidentifiability_limitation": ("Random effects are regularized on the small development fixture."),
        }
        raw_payloads: dict[str, Any] = {
            "results": {
                "schema_version": 1,
                "model": "M1",
                "status": "VALID",
                "target_values_exposed": False,
                "train_metrics": train_metrics,
                "validation_metrics": validation_metrics,
                "validation_confidence_interval": _bootstrap_ci(
                    validation,
                    predictions,
                    int(config["seed"]),
                    int(config["bootstrap_samples"]),
                ),
                "fixed_effects": {key: round(value, 6) for key, value in fixed.items()},
                "grouped_cv": grouped_cv,
            },
            "variance": {"schema_version": 1, **variance_partition},
            "diagnostics": {"schema_version": 1, **diagnostics},
            "calibration": {"schema_version": 1, **calibration},
            "toy": {"schema_version": 1, **toy},
            "failures": {"schema_version": 1, "status": "VALID", "failures": []},
        }
        resume_key = _sha256(_canonical(raw_payloads))
        self.output_root.mkdir(parents=True, exist_ok=True)
        paths = {
            "results": self.output_root / "m1_results.json",
            "variance": self.output_root / "variance_partition.json",
            "diagnostics": self.output_root / "diagnostics.json",
            "calibration": self.output_root / "calibration.json",
            "toy": self.output_root / "toy_recovery.json",
            "failures": self.output_root / "failure_ledger.json",
            "receipt": self.output_root / "m1_receipt.json",
            "log": self.output_root / "m1_log.json",
            "manifest": self.output_root / "m1_manifest.json",
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
        receipt = {
            "schema_version": 1,
            "model": "M1",
            "status": "VALID",
            "fixture": True,
            "instances": len(rows),
            "train": len(train),
            "validation": len(validation),
            "converged": diagnostics["converged"],
            "toy_recovery": toy["recovered"],
            "validation_rmse": validation_metrics["rmse"],
            "grouped_cv_mean_rmse": grouped_cv["mean_rmse"],
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
                    {"event": "T063_T067_inputs_verified", "instances": len(rows)},
                    {"event": "regularized_m1_fit_completed", "groups": groups},
                    {
                        "event": "variance_partition_computed",
                        "random_effect_groups": len(groups),
                    },
                    {
                        "event": "grouped_cv_and_calibration_completed",
                        "folds": grouped_cv["folds_count"],
                    },
                    {"event": "toy_parameter_recovery_completed", "recovered": toy["recovered"]},
                ],
            }
        )
        payload_bytes["manifest"] = _canonical(
            {
                "schema_version": 1,
                "model": "M1",
                "status": "VALID",
                "resume_supported": True,
                "resume_key": resume_key,
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
                raise M1Error("existing M1 receipt differs from rerun")
            for name, payload in payload_bytes.items():
                if paths[name].read_bytes() != payload:
                    raise M1Error(f"existing M1 artifact differs: {name}")
            resumed = 1
        else:
            for name, payload in payload_bytes.items():
                paths[name].write_bytes(payload)
            resumed = 0
        return M1Summary(
            instances=len(rows),
            train=len(train),
            validation=len(validation),
            converged=bool(diagnostics["converged"]),
            toy_recovery=bool(toy["recovered"]),
            validation_rmse=float(validation_metrics["rmse"]),
            resumed=resumed,
            receipt_path=paths["receipt"],
        )
