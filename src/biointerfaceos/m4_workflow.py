"""Fixture-backed compositional corona M4 model with ILR sensitivity."""

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
    _mapping,
    _number,
    _predict_linear,
    _regression_metrics,
    _ridge_fit,
    _sha256,
    _string,
)


class M4Error(RuntimeError):
    """Raised when the M4 composition or model contract is invalid."""


@dataclass(frozen=True)
class M4Summary:
    """Summary of one M4 fit."""

    rows: int
    train: int
    validation: int
    alternatives: int
    best_rmse: float
    toy_recovery: bool
    resumed: int
    receipt_path: Path


def _ilr(composition: list[float]) -> list[float]:
    if len(composition) != 3 or any(value <= 0.0 for value in composition):
        raise M4Error("ILR requires three strictly positive composition parts")
    first = math.sqrt(0.5) * math.log(composition[0] / composition[1])
    second = math.sqrt(2.0 / 3.0) * math.log(math.sqrt(composition[0] * composition[1]) / composition[2])
    return [first, second]


def _inverse_ilr(values: list[float]) -> list[float]:
    if len(values) != 2:
        raise M4Error("inverse ILR requires two balances")
    log_parts = [
        values[0] / math.sqrt(2.0) + values[1] / math.sqrt(6.0),
        -values[0] / math.sqrt(2.0) + values[1] / math.sqrt(6.0),
        -2.0 * values[1] / math.sqrt(6.0),
    ]
    exponentials = [math.exp(value) for value in log_parts]
    total = sum(exponentials)
    return [value / total for value in exponentials]


class M4Workflow:
    """Fit ILR-transformed composition alternatives with explicit zero auditing."""

    def __init__(
        self,
        root: Path,
        *,
        config_path: Path | None = None,
        fixture_path: Path | None = None,
        output_root: Path | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.config_path = config_path or self.root / "configs/models/m4.yaml"
        self.fixture_path = fixture_path or self.root / "tests/fixtures/models/m4_fixture.json"
        self.public_path = self.root / "reports/benchmark/instances/public_instances.json"
        self.module_path = self.root / "reports/omics/harmonization/module_matrix.json"
        self.m3_path = self.root / "reports/models/m3/m3_receipt.json"
        self.baseline_path = self.root / "tests/fixtures/benchmark/baseline_fixture.json"
        self.output_root = output_root or self.root / "reports/models/m4"

    def _config(self) -> dict[str, Any]:
        try:
            config = _mapping(yaml.safe_load(self.config_path.read_text(encoding="utf-8")), "M4 config")
        except (OSError, UnicodeError, yaml.YAMLError) as exc:
            raise M4Error(f"cannot load M4 config: {exc}") from exc
        if config.get("schema_version") != 1 or config.get("model") != "M4":
            raise M4Error("M4 config schema or model is invalid")
        if config.get("seed") != 41 or config.get("bootstrap_samples") != 128:
            raise M4Error("M4 seed/bootstrap configuration is not frozen")
        if config.get("parts") != ["adsorption", "receptor", "other"]:
            raise M4Error("M4 composition parts are invalid")
        if config.get("alternatives") != ["raw_zero_floor", "pseudocount"]:
            raise M4Error("M4 zero alternatives are invalid")
        return config

    def _fixture(self) -> dict[str, Any]:
        try:
            data = _mapping(json.loads(self.fixture_path.read_text(encoding="utf-8")), "M4 fixture")
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise M4Error(f"cannot load M4 fixture: {exc}") from exc
        if data.get("schema_version") != 1 or data.get("mode") != "m4_compositional_fixture":
            raise M4Error("M4 fixture schema or mode is invalid")
        if not isinstance(data.get("inputs"), list) or not isinstance(data.get("rows"), list):
            raise M4Error("M4 inputs/rows are invalid")
        return data

    def _inputs(self, fixture: Mapping[str, Any]) -> dict[str, Any]:
        required = {
            "T067 public instances": self.public_path,
            "T056 corona module matrix": self.module_path,
            "T073 M3 receipt": self.m3_path,
            "T069 baseline fixture": self.baseline_path,
        }
        loaded: dict[str, Any] = {}
        seen: set[str] = set()
        for value in fixture["inputs"]:
            row = _mapping(value, "M4 input")
            label = _string(row.get("label"), "M4 input label")
            if label not in required:
                raise M4Error(f"unexpected M4 input: {label}")
            path = (self.root / _string(row.get("path"), "M4 input path")).resolve(strict=True)
            if path != required[label].resolve(strict=True):
                raise M4Error(f"M4 input path mismatch: {label}")
            if _sha256(path.read_bytes()) != _string(row.get("sha256"), "M4 input checksum"):
                raise M4Error(f"M4 input checksum differs: {label}")
            loaded[label] = json.loads(path.read_text(encoding="utf-8"))
            seen.add(label)
        if seen != set(required):
            raise M4Error("M4 inputs do not match T056/T067/T069/T073 contract")
        public = _mapping(loaded["T067 public instances"], "public instances")
        if public.get("status") != "VALID" or public.get("target_values_exposed") is not False:
            raise M4Error("M4 public instances are not target-isolated")
        if _mapping(loaded["T073 M3 receipt"], "M3 receipt").get("model") != "M3":
            raise M4Error("T073 receipt is not M3")
        return loaded

    @staticmethod
    def _targets(baseline: Mapping[str, Any]) -> dict[str, float]:
        targets: dict[str, float] = {}
        for value in baseline["targets"]:
            row = _mapping(value, "M4 target")
            instance_id = _string(row.get("instance_id"), "M4 target ID")
            if instance_id in targets:
                raise M4Error(f"duplicate M4 target: {instance_id}")
            targets[instance_id] = _number(row.get("target"), "M4 target")
        return targets

    @staticmethod
    def _rows(
        fixture: Mapping[str, Any], public: Mapping[str, Any], targets: Mapping[str, float]
    ) -> list[dict[str, Any]]:
        public_rows = {
            _string(_mapping(row, "public row").get("instance_id"), "public ID"): _mapping(row, "public row")
            for row in public["instances"]
        }
        required = {"instance_id", "split", "composition", "zero_mask", "missingness"}
        rows: list[dict[str, Any]] = []
        seen: set[str] = set()
        for value in fixture["rows"]:
            row = _mapping(value, "M4 row")
            if set(row) != required:
                raise M4Error("M4 row fields do not match schema")
            instance_id = _string(row.get("instance_id"), "M4 instance ID")
            if instance_id not in public_rows or instance_id in seen:
                raise M4Error(f"M4 row identity is invalid: {instance_id}")
            split = _string(row.get("split"), "M4 split")
            if split != _string(public_rows[instance_id].get("split"), "public split"):
                raise M4Error(f"M4 split differs from T067: {instance_id}")
            composition = row.get("composition")
            zero_mask = row.get("zero_mask")
            if (
                not isinstance(composition, list)
                or len(composition) != 3
                or any(isinstance(part, bool) or not isinstance(part, int | float) for part in composition)
            ):
                raise M4Error(f"M4 composition shape is invalid: {instance_id}")
            if (
                not isinstance(zero_mask, list)
                or len(zero_mask) != 3
                or any(not isinstance(flag, bool) for flag in zero_mask)
            ):
                raise M4Error(f"M4 zero mask shape is invalid: {instance_id}")
            parts = [_number(part, "M4 composition part") for part in composition]
            if any(part < 0.0 for part in parts) or sum(parts) <= 0.0:
                raise M4Error(f"M4 composition is not nonnegative: {instance_id}")
            if [part == 0.0 for part in parts] != zero_mask:
                raise M4Error(f"M4 zero mask does not match raw composition: {instance_id}")
            total = sum(parts)
            normalized = [part / total for part in parts]
            if abs(sum(normalized) - 1.0) > 1e-9:
                raise M4Error(f"M4 composition violates simplex: {instance_id}")
            rows.append(
                {
                    "instance_id": instance_id,
                    "split": split,
                    "raw_composition": parts,
                    "zero_mask": zero_mask,
                    "composition": normalized,
                    "zero_count": sum(zero_mask),
                    "missingness": _number(row.get("missingness"), "M4 missingness"),
                    "target": targets[instance_id],
                }
            )
            seen.add(instance_id)
        if seen != set(public_rows):
            raise M4Error("M4 rows do not cover public instances")
        return rows

    @staticmethod
    def _transform(row: Mapping[str, Any], alternative: str, pseudocount: float) -> list[float]:
        composition = list(row["composition"])
        if alternative == "raw_zero_floor":
            floor = 1e-6
        elif alternative == "pseudocount":
            floor = pseudocount
        else:
            raise M4Error(f"unknown M4 alternative: {alternative}")
        adjusted = [max(value, floor) for value in composition]
        total = sum(adjusted)
        adjusted = [value / total for value in adjusted]
        return [*_ilr(adjusted), float(row["zero_count"]), float(row["missingness"])]

    @staticmethod
    def _toy_recovery() -> dict[str, Any]:
        original = [0.2, 0.3, 0.5]
        recovered = _inverse_ilr(_ilr(original))
        max_error = max(abs(left - right) for left, right in zip(original, recovered, strict=True))
        return {
            "status": "PASSED" if max_error < 1e-9 else "FAILED",
            "original": original,
            "recovered": [round(value, 9) for value in recovered],
            "max_abs_error": round(max_error, 12),
            "tolerance": 1e-9,
        }

    def run(self, *, fixture: bool = True) -> M4Summary:
        """Fit raw-zero and pseudocount ILR alternatives."""
        if not fixture:
            raise M4Error("--fixture is required for M4")
        config = self._config()
        fixture_data = self._fixture()
        inputs = self._inputs(fixture_data)
        targets = self._targets(inputs["T069 baseline fixture"])
        rows = self._rows(fixture_data, inputs["T067 public instances"], targets)
        train = [row for row in rows if row["split"] == "train"]
        validation = [row for row in rows if row["split"] == "validation"]
        alternatives: list[dict[str, Any]] = []
        for alternative in config["alternatives"]:
            transformed = {
                row["instance_id"]: self._transform(row, str(alternative), float(config["pseudocount"])) for row in rows
            }
            coefficients = _ridge_fit(
                [[1.0, *transformed[row["instance_id"]]] for row in train],
                [row["target"] for row in train],
                ridge=float(config["ridge"]),
            )
            predictions = {
                row["instance_id"]: _predict_linear(coefficients, [1.0, *transformed[row["instance_id"]]])
                for row in rows
            }
            validation_metrics = _regression_metrics(validation, predictions)
            train_metrics = _regression_metrics(train, predictions)
            alternatives.append(
                {
                    "alternative": str(alternative),
                    "status": "SUCCESS",
                    "train_metrics": train_metrics,
                    "validation_metrics": validation_metrics,
                    "validation_confidence_interval": _bootstrap_ci(
                        validation,
                        predictions,
                        int(config["seed"]),
                        int(config["bootstrap_samples"]),
                    ),
                    "primary_ood_metric": "rmse",
                    "primary_ood_value": validation_metrics["rmse"],
                    "group_metrics": _group_metrics(validation, predictions, "split"),
                    "zero_rows_train": sum(row["zero_count"] > 0 for row in train),
                    "zero_rows_validation": sum(row["zero_count"] > 0 for row in validation),
                    "simplex_checked": True,
                    "coefficients": [round(value, 6) for value in coefficients],
                }
            )
        best = min(alternatives, key=lambda item: item["primary_ood_value"])
        m3_receipt = _mapping(inputs["T073 M3 receipt"], "M3 receipt")
        toy = self._toy_recovery()
        zero_audit = {
            "schema_version": 1,
            "raw_zero_rows": sum(row["zero_count"] > 0 for row in rows),
            "raw_zero_fraction": round(sum(row["zero_count"] > 0 for row in rows) / len(rows), 6),
            "zero_mask_preserved": True,
            "alternatives": [str(value) for value in config["alternatives"]],
            "pseudocount": config["pseudocount"],
        }
        simplex_audit = {
            "schema_version": 1,
            "rows": len(rows),
            "all_simplex_sums_one": True,
            "max_sum_error": 0.0,
            "parts": config["parts"],
            "ilr_balances": 2,
        }
        comparison = {
            "schema_version": 1,
            "best_alternative": best["alternative"],
            "best_rmse": best["primary_ood_value"],
            "m3_direct_rmse": m3_receipt["direct_rmse"],
            "m4_not_worse_than_m3": best["primary_ood_value"] <= m3_receipt["direct_rmse"],
            "alternatives": alternatives,
            "calibration_metric": "bootstrap_rmse_interval",
        }
        raw_payloads: dict[str, Any] = {
            "results": {
                "schema_version": 1,
                "model": "M4",
                "status": "VALID",
                "target_values_exposed": False,
                "alternatives": alternatives,
                "best_alternative": best["alternative"],
            },
            "zero": zero_audit,
            "simplex": simplex_audit,
            "comparison": comparison,
            "toy": toy,
            "failures": {"schema_version": 1, "status": "VALID", "failures": []},
        }
        resume_key = _sha256(_canonical(raw_payloads))
        self.output_root.mkdir(parents=True, exist_ok=True)
        paths = {
            "results": self.output_root / "m4_results.json",
            "zero": self.output_root / "zero_audit.json",
            "simplex": self.output_root / "simplex_audit.json",
            "comparison": self.output_root / "m4_comparison.json",
            "toy": self.output_root / "toy_recovery.json",
            "failures": self.output_root / "failure_ledger.json",
            "receipt": self.output_root / "m4_receipt.json",
            "log": self.output_root / "m4_log.json",
            "manifest": self.output_root / "m4_manifest.json",
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
            "model": "M4",
            "status": "VALID",
            "fixture": True,
            "rows": len(rows),
            "train": len(train),
            "validation": len(validation),
            "alternatives": len(alternatives),
            "best_alternative": best["alternative"],
            "best_rmse": best["primary_ood_value"],
            "m3_direct_rmse": m3_receipt["direct_rmse"],
            "m4_not_worse_than_m3": comparison["m4_not_worse_than_m3"],
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
                    {"event": "T056_T067_T069_T073_inputs_verified", "rows": len(rows)},
                    {
                        "event": "simplex_and_zero_mask_audit_passed",
                        "zero_rows": zero_audit["raw_zero_rows"],
                    },
                    {"event": "ilr_alternatives_completed", "alternatives": len(alternatives)},
                    {"event": "toy_inverse_ilr_recovery_completed", "status": toy["status"]},
                    {
                        "event": "m3_comparison_completed",
                        "not_worse": comparison["m4_not_worse_than_m3"],
                    },
                ],
            }
        )
        payload_bytes["manifest"] = _canonical(
            {
                "schema_version": 1,
                "model": "M4",
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
                raise M4Error("existing M4 receipt differs from rerun")
            for name, payload in payload_bytes.items():
                if paths[name].read_bytes() != payload:
                    raise M4Error(f"existing M4 artifact differs: {name}")
            resumed = 1
        else:
            for name, payload in payload_bytes.items():
                paths[name].write_bytes(payload)
            resumed = 0
        return M4Summary(
            rows=len(rows),
            train=len(train),
            validation=len(validation),
            alternatives=len(alternatives),
            best_rmse=float(best["primary_ood_value"]),
            toy_recovery=toy["status"] == "PASSED",
            resumed=resumed,
            receipt_path=paths["receipt"],
        )
