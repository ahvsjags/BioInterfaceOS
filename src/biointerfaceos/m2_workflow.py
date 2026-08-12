"""Fixture-backed direct black-box M2 baseline."""

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
    _group_metrics,
    _hash_bucket,
    _mapping,
    _mean,
    _number,
    _predict_linear,
    _regression_metrics,
    _ridge_fit,
    _sha256,
    _string,
)


class M2Error(RuntimeError):
    """Raised when the M2 model contract is invalid."""


@dataclass(frozen=True)
class M2Summary:
    """Summary of one M2 fit."""

    instances: int
    train: int
    validation: int
    model_kind: str
    validation_rmse: float
    resumed: int
    receipt_path: Path


def _encode_text(value: Any, label: str) -> float:
    text = _string(value, label).lower()
    return _hash_bucket(text)


class M2Workflow:
    """Fit a low-capacity direct model with explicit feature and OOD audits."""

    def __init__(
        self,
        root: Path,
        *,
        config_path: Path | None = None,
        fixture_path: Path | None = None,
        output_root: Path | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.config_path = config_path or self.root / "configs/models/m2.yaml"
        self.fixture_path = fixture_path or self.root / "tests/fixtures/models/m2_fixture.json"
        self.baseline_fixture_path = self.root / "tests/fixtures/benchmark/baseline_fixture.json"
        self.output_root = output_root or self.root / "reports/models/m2"

    def _config(self) -> dict[str, Any]:
        try:
            config = _mapping(
                yaml.safe_load(self.config_path.read_text(encoding="utf-8")),
                "M2 config",
            )
        except (OSError, UnicodeError, yaml.YAMLError) as exc:
            raise M2Error(f"cannot load M2 config: {exc}") from exc
        if config.get("schema_version") != 1 or config.get("model") != "M2":
            raise M2Error("M2 config schema or model is invalid")
        if config.get("seed") != 31 or config.get("bootstrap_samples") != 128:
            raise M2Error("M2 seed/bootstrap configuration is not frozen")
        if config.get("model_kind") != "regularized_polynomial_fallback":
            raise M2Error("M2 model kind is not the declared fallback")
        return config

    def _fixture(self) -> dict[str, Any]:
        try:
            data = _mapping(json.loads(self.fixture_path.read_text(encoding="utf-8")), "M2 fixture")
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise M2Error(f"cannot load M2 fixture: {exc}") from exc
        if data.get("schema_version") != 1 or data.get("mode") != "m2_direct_fixture":
            raise M2Error("M2 fixture schema or mode is invalid")
        if not isinstance(data.get("inputs"), list) or not isinstance(data.get("rows"), list):
            raise M2Error("M2 inputs/rows are invalid")
        return data

    def _inputs(self, fixture: Mapping[str, Any]) -> dict[str, Any]:
        required = {
            "T067 public instances": self.root
            / "reports/benchmark/instances/public_instances.json",
            "T069 baseline fixture": self.baseline_fixture_path,
        }
        loaded: dict[str, Any] = {}
        seen: set[str] = set()
        for value in fixture["inputs"]:
            row = _mapping(value, "M2 input")
            label = _string(row.get("label"), "M2 input label")
            if label not in required:
                raise M2Error(f"unexpected M2 input: {label}")
            path = (self.root / _string(row.get("path"), "M2 input path")).resolve(strict=True)
            if path != required[label].resolve(strict=True):
                raise M2Error(f"M2 input path mismatch: {label}")
            if _sha256(path.read_bytes()) != _string(row.get("sha256"), "M2 input checksum"):
                raise M2Error(f"M2 input checksum differs: {label}")
            loaded[label] = json.loads(path.read_text(encoding="utf-8"))
            seen.add(label)
        if seen != set(required):
            raise M2Error("M2 inputs do not match T067/T069 contract")
        public = _mapping(loaded["T067 public instances"], "public instances")
        baseline = _mapping(loaded["T069 baseline fixture"], "baseline fixture")
        if public.get("status") != "VALID" or public.get("target_values_exposed") is not False:
            raise M2Error("M2 public instances are not target-isolated")
        return {"public": public, "baseline": baseline}

    @staticmethod
    def _targets(baseline: Mapping[str, Any]) -> dict[str, float]:
        targets: dict[str, float] = {}
        for value in baseline["targets"]:
            row = _mapping(value, "M2 target")
            instance_id = _string(row.get("instance_id"), "M2 target instance ID")
            if instance_id in targets:
                raise M2Error(f"duplicate M2 target: {instance_id}")
            targets[instance_id] = _number(row.get("target"), "M2 target")
        return targets

    @staticmethod
    def _rows(
        fixture: Mapping[str, Any], public: Mapping[str, Any], targets: Mapping[str, float]
    ) -> list[dict[str, Any]]:
        public_rows = {
            _string(_mapping(row, "public row").get("instance_id"), "public ID"): _mapping(
                row, "public row"
            )
            for row in public["instances"]
        }
        required = {
            "instance_id",
            "split",
            "material_feature",
            "environment_feature",
            "protocol_feature",
            "missingness",
        }
        rows: list[dict[str, Any]] = []
        seen: set[str] = set()
        for value in fixture["rows"]:
            row = _mapping(value, "M2 row")
            if set(row) != required:
                raise M2Error("M2 row fields do not match schema")
            instance_id = _string(row.get("instance_id"), "M2 instance ID")
            if instance_id not in public_rows or instance_id in seen:
                raise M2Error(f"M2 row identity is invalid: {instance_id}")
            split = _string(row.get("split"), "M2 split")
            if split not in {"train", "validation"}:
                raise M2Error(f"M2 split is invalid: {split}")
            public_split = _string(public_rows[instance_id].get("split"), "public split")
            if split != public_split:
                raise M2Error(f"M2 split differs from T067: {instance_id}")
            rows.append(
                {
                    "instance_id": instance_id,
                    "family": _string(public_rows[instance_id].get("family"), "public family"),
                    "group_key": _string(
                        public_rows[instance_id].get("group_key"), "public group key"
                    ),
                    "split": split,
                    "material_feature": _encode_text(
                        row.get("material_feature"), "material feature"
                    ),
                    "environment_feature": _encode_text(
                        row.get("environment_feature"), "environment feature"
                    ),
                    "protocol_feature": _encode_text(
                        row.get("protocol_feature"), "protocol feature"
                    ),
                    "missingness": _number(row.get("missingness"), "M2 missingness"),
                    "target": targets[instance_id],
                }
            )
            seen.add(instance_id)
        if seen != set(public_rows):
            raise M2Error("M2 rows do not cover public instances")
        return rows

    @staticmethod
    def _features(row: Mapping[str, Any]) -> list[float]:
        base = [
            float(row["material_feature"]),
            float(row["environment_feature"]),
            float(row["protocol_feature"]),
            float(row["missingness"]),
        ]
        return [
            1.0,
            *base,
            *(value * value for value in base),
            base[0] * base[1],
            base[1] * base[2],
            base[0] * base[2],
        ]

    @staticmethod
    def _permutation_importance(
        train: list[dict[str, Any]], coefficients: list[float], feature_names: list[str]
    ) -> list[dict[str, Any]]:
        baseline_predictions = {
            row["instance_id"]: _predict_linear(coefficients, M2Workflow._features(row))
            for row in train
        }
        baseline_rmse = _regression_metrics(train, baseline_predictions)["rmse"]
        importances: list[dict[str, Any]] = []
        for index, name in enumerate(feature_names, start=1):
            permuted = list(train)
            values = [row[name] for row in train]
            rotated = values[1:] + values[:1]
            changed = [
                dict(row, **{name: value}) for row, value in zip(permuted, rotated, strict=True)
            ]
            predictions = {
                row["instance_id"]: _predict_linear(coefficients, M2Workflow._features(row))
                for row in changed
            }
            score = _regression_metrics(changed, predictions)["rmse"]
            importances.append(
                {
                    "feature": name,
                    "coefficient_l1": round(abs(coefficients[index]), 6),
                    "permutation_delta_rmse": round(score - baseline_rmse, 6),
                }
            )
        importances.sort(key=lambda item: (-item["coefficient_l1"], item["feature"]))
        return importances

    def run(self, *, fixture: bool = True) -> M2Summary:
        """Fit and audit M2 from fixed train/validation rows."""
        if not fixture:
            raise M2Error("--fixture is required for M2")
        config = self._config()
        fixture_data = self._fixture()
        inputs = self._inputs(fixture_data)
        targets = self._targets(inputs["baseline"])
        rows = self._rows(fixture_data, inputs["public"], targets)
        train = [row for row in rows if row["split"] == "train"]
        validation = [row for row in rows if row["split"] == "validation"]
        if not train or not validation:
            raise M2Error("M2 requires train and validation rows")
        coefficients = _ridge_fit(
            [self._features(row) for row in train],
            [row["target"] for row in train],
            ridge=float(config["ridge"]),
        )
        predictions = {
            row["instance_id"]: _predict_linear(coefficients, self._features(row)) for row in rows
        }
        train_metrics = _regression_metrics(train, predictions)
        validation_metrics = _regression_metrics(validation, predictions)
        residual_sd = math.sqrt(
            _mean([(row["target"] - predictions[row["instance_id"]]) ** 2 for row in train])
        )
        calibration = {
            "validation_mean_absolute_error": round(
                _mean([abs(row["target"] - predictions[row["instance_id"]]) for row in validation]),
                6,
            ),
            "train_residual_sd": round(residual_sd, 6),
            "calibration_error": round(
                _mean(
                    [
                        abs(abs(row["target"] - predictions[row["instance_id"]]) - residual_sd)
                        for row in validation
                    ]
                ),
                6,
            ),
            "uncertainty_source": "train_residual_sd",
        }
        feature_names = [
            "material_feature",
            "environment_feature",
            "protocol_feature",
            "missingness",
        ]
        importance = self._permutation_importance(train, coefficients, feature_names)
        excluded_fields = ["instance_id", "family", "group_key", "split"]
        feature_audit = {
            "schema_version": 1,
            "identifier_features_used": False,
            "excluded_fields": excluded_fields,
            "feature_names": feature_names,
            "missingness_indicator_used": True,
            "train_only_fit": True,
            "validation_used_for_tuning": False,
        }
        diagnostics = {
            "schema_version": 1,
            "converged": True,
            "model_kind": config["model_kind"],
            "ridge": config["ridge"],
            "coefficients_finite": all(math.isfinite(value) for value in coefficients),
            "identity_features_used": False,
            "validation_tuning": False,
            "fallback_reason": "Small fixture favors a low-capacity regularized polynomial model.",
        }
        raw_payloads: dict[str, Any] = {
            "results": {
                "schema_version": 1,
                "model": "M2",
                "status": "VALID",
                "target_values_exposed": False,
                "model_kind": config["model_kind"],
                "train_metrics": train_metrics,
                "validation_metrics": validation_metrics,
                "validation_confidence_interval": _bootstrap_ci(
                    validation,
                    predictions,
                    int(config["seed"]),
                    int(config["bootstrap_samples"]),
                ),
                "group_metrics": _group_metrics(validation, predictions, "group_key"),
                "family_metrics": _group_metrics(validation, predictions, "family"),
                "split_metrics": _group_metrics(validation, predictions, "split"),
            },
            "calibration": calibration,
            "feature_audit": feature_audit,
            "importance": {
                "schema_version": 1,
                "method": "train_permutation_and_coefficient_l1",
                "features": importance,
            },
            "diagnostics": diagnostics,
            "failures": {"schema_version": 1, "status": "VALID", "failures": []},
        }
        resume_key = _sha256(_canonical(raw_payloads))
        self.output_root.mkdir(parents=True, exist_ok=True)
        paths = {
            "results": self.output_root / "m2_results.json",
            "calibration": self.output_root / "calibration.json",
            "feature_audit": self.output_root / "feature_audit.json",
            "importance": self.output_root / "feature_importance.json",
            "diagnostics": self.output_root / "diagnostics.json",
            "failures": self.output_root / "failure_ledger.json",
            "receipt": self.output_root / "m2_receipt.json",
            "log": self.output_root / "m2_log.json",
            "manifest": self.output_root / "m2_manifest.json",
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
            "model": "M2",
            "status": "VALID",
            "fixture": True,
            "instances": len(rows),
            "train": len(train),
            "validation": len(validation),
            "model_kind": config["model_kind"],
            "validation_rmse": validation_metrics["rmse"],
            "target_values_exposed": False,
            "identity_features_used": False,
            "resume_key": resume_key,
            "artifacts": artifact_records,
        }
        payload_bytes["receipt"] = _canonical(receipt)
        payload_bytes["log"] = _canonical(
            {
                "schema_version": 1,
                "resume_key": resume_key,
                "events": [
                    {"event": "T067_T069_inputs_verified", "instances": len(rows)},
                    {"event": "m2_train_only_fit_completed", "model_kind": config["model_kind"]},
                    {
                        "event": "identifier_feature_audit_passed",
                        "excluded": len(excluded_fields),
                    },
                    {
                        "event": "ood_calibration_and_importance_completed",
                        "validation": len(validation),
                    },
                ],
            }
        )
        payload_bytes["manifest"] = _canonical(
            {
                "schema_version": 1,
                "model": "M2",
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
                raise M2Error("existing M2 receipt differs from rerun")
            for name, payload in payload_bytes.items():
                if paths[name].read_bytes() != payload:
                    raise M2Error(f"existing M2 artifact differs: {name}")
            resumed = 1
        else:
            for name, payload in payload_bytes.items():
                paths[name].write_bytes(payload)
            resumed = 0
        return M2Summary(
            instances=len(rows),
            train=len(train),
            validation=len(validation),
            model_kind=str(config["model_kind"]),
            validation_rmse=float(validation_metrics["rmse"]),
            resumed=resumed,
            receipt_path=paths["receipt"],
        )
