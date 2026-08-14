"""Fixture-backed calibrated uncertainty and abstention workflow."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

from biointerfaceos.benchmark_baselines import (
    _canonical,
    _mapping,
    _regression_metrics,
    _sha256,
    _string,
)


class UncertaintyError(RuntimeError):
    """Raised when the calibrated uncertainty contract is invalid."""


@dataclass(frozen=True)
class UncertaintySummary:
    """Summary of one deterministic uncertainty fit."""

    rows: int
    calibration: int
    validation: int
    selected_model: str
    calibration_passed: bool
    coverage: float
    selective_risk_decreases: bool
    ood_abstentions: int
    resumed: int
    receipt_path: Path


def _number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise UncertaintyError(f"{label} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise UncertaintyError(f"{label} must be finite")
    return result


def _quantile(values: list[float], probability: float) -> float:
    if not values:
        raise UncertaintyError("cannot compute a quantile of empty values")
    ordered = sorted(values)
    index = int(probability * (len(ordered) - 1))
    return ordered[index]


def _metrics(rows: list[dict[str, Any]], predictions: Mapping[str, float]) -> dict[str, Any]:
    adapted = [{"instance_id": row["row_id"], "target": row["target"]} for row in rows]
    return _regression_metrics(
        adapted,
        {row["row_id"]: predictions[row["row_id"]] for row in rows},
    )


def _binary_metrics(rows: list[dict[str, Any]], scores: Mapping[str, float], threshold: float) -> dict[str, Any]:
    counts = {"true_positive": 0, "false_positive": 0, "true_negative": 0, "false_negative": 0}
    for row in rows:
        predicted = scores[row["row_id"]] >= threshold
        actual = row["ood"]
        if predicted and actual:
            counts["true_positive"] += 1
        elif predicted and not actual:
            counts["false_positive"] += 1
        elif not predicted and not actual:
            counts["true_negative"] += 1
        else:
            counts["false_negative"] += 1
    tp = counts["true_positive"]
    fp = counts["false_positive"]
    fn = counts["false_negative"]
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return {
        "threshold": threshold,
        **counts,
        "precision": round(precision, 6),
        "recall": round(recall, 6),
        "f1": round(2.0 * precision * recall / (precision + recall), 6) if precision + recall else 0.0,
    }


class UncertaintyWorkflow:
    """Calibrate ensemble/conformal uncertainty and abstain on OOD rows."""

    def __init__(
        self,
        root: Path,
        *,
        config_path: Path | None = None,
        fixture_path: Path | None = None,
        output_root: Path | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.config_path = config_path or self.root / "configs/models/uncertainty.yaml"
        self.fixture_path = fixture_path or (self.root / "tests/fixtures/models/uncertainty_fixture.json")
        self.output_root = output_root or self.root / "reports/models/uncertainty"

    def _config(self) -> dict[str, Any]:
        try:
            config = _mapping(
                yaml.safe_load(self.config_path.read_text(encoding="utf-8")),
                "uncertainty config",
            )
        except (OSError, UnicodeError, yaml.YAMLError) as exc:
            raise UncertaintyError(f"cannot load uncertainty config: {exc}") from exc
        if config.get("schema_version") != 1 or config.get("model") != "UNCERTAINTY":
            raise UncertaintyError("uncertainty config schema or model is invalid")
        if config.get("seed") != 61 or config.get("bootstrap_samples") != 128:
            raise UncertaintyError("uncertainty seed/bootstrap configuration is not frozen")
        if config.get("fallback_model") != "conservative_conformal":
            raise UncertaintyError("uncertainty fallback model is invalid")
        return config

    def _fixture(self) -> dict[str, Any]:
        try:
            data = _mapping(
                json.loads(self.fixture_path.read_text(encoding="utf-8")),
                "uncertainty fixture",
            )
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise UncertaintyError(f"cannot load uncertainty fixture: {exc}") from exc
        if data.get("schema_version") != 1 or data.get("mode") != "uncertainty_fixture":
            raise UncertaintyError("uncertainty fixture schema or mode is invalid")
        if not isinstance(data.get("inputs"), list) or not isinstance(data.get("rows"), list):
            raise UncertaintyError("uncertainty inputs/rows are invalid")
        return data

    def _inputs(self, fixture: Mapping[str, Any]) -> None:
        expected = {
            "T071 M1 receipt": (
                self.root / "reports/models/m1/m1_receipt.json",
                "6f11129540792ffe84e185b84f4b11d8d2d39466f906d226e28d0648789aca5f",
            ),
            "T072 M2 receipt": (
                self.root / "reports/models/m2/m2_receipt.json",
                "69c8ca21da919bdfdcf5139c806f1e5807abef4ccb0d2c72b5303b6dce4be517",
            ),
            "T074 M4 receipt": (
                self.root / "reports/models/m4/m4_receipt.json",
                "a86fb1c74acdc0c5804bb7b4f4cf16e2e1be14689ae75b0864790ae750d54455",
            ),
            "T076 M6 receipt": (
                self.root / "reports/models/m6/m6_receipt.json",
                "8ab469c76f87aa530743773d8582199a04f1eb4e91be62c6f0910f68622c759a",
            ),
            "T077 M7 receipt": (
                self.root / "reports/models/m7/m7_receipt.json",
                "819df04448f30434233f7fcd5909e71716b35a7fe78adbcd974d9a011ad28cd6",
            ),
        }
        seen: set[str] = set()
        for value in fixture["inputs"]:
            row = _mapping(value, "uncertainty input")
            label = _string(row.get("label"), "uncertainty input label")
            if label not in expected:
                raise UncertaintyError(f"unexpected uncertainty input: {label}")
            path, checksum = expected[label]
            declared_path = (self.root / _string(row.get("path"), "uncertainty input path")).resolve(strict=True)
            if declared_path != path.resolve(strict=True):
                raise UncertaintyError(f"uncertainty input path mismatch: {label}")
            if _sha256(path.read_bytes()) != checksum or row.get("sha256") != checksum:
                raise UncertaintyError(f"uncertainty input checksum differs: {label}")
            receipt = _mapping(json.loads(path.read_text(encoding="utf-8")), f"{label} payload")
            if receipt.get("status") != "VALID":
                raise UncertaintyError(f"{label} is not valid")
            if label == "T076 M6 receipt" and receipt.get("causal_claim_permitted") is not False:
                raise UncertaintyError("M6 causal gate must remain closed")
            if label == "T077 M7 receipt" and receipt.get("selected_model") != "hierarchical_erm":
                raise UncertaintyError("M7 selected model is not the accepted fallback")
            seen.add(label)
        if seen != set(expected):
            raise UncertaintyError("uncertainty inputs do not match T071/T072/T074/T076/T077")

    @staticmethod
    def _rows(fixture: Mapping[str, Any]) -> list[dict[str, Any]]:
        required = {
            "row_id",
            "split",
            "domain",
            "distance",
            "ood",
            "target",
            "pred_m1",
            "pred_m2",
            "pred_m7",
        }
        rows: list[dict[str, Any]] = []
        seen: set[str] = set()
        for value in fixture["rows"]:
            source = _mapping(value, "uncertainty row")
            if set(source) != required:
                raise UncertaintyError("uncertainty row fields do not match schema")
            row_id = _string(source.get("row_id"), "uncertainty row ID")
            if row_id in seen:
                raise UncertaintyError(f"duplicate uncertainty row: {row_id}")
            split = _string(source.get("split"), "uncertainty split")
            if split not in {"calibration", "validation"}:
                raise UncertaintyError(f"uncertainty split is invalid: {split}")
            ood = source.get("ood")
            if not isinstance(ood, bool):
                raise UncertaintyError("uncertainty OOD flag must be boolean")
            rows.append(
                {
                    "row_id": row_id,
                    "split": split,
                    "domain": _string(source.get("domain"), "uncertainty domain"),
                    "distance": _number(source.get("distance"), "uncertainty distance"),
                    "ood": ood,
                    "target": _number(source.get("target"), "uncertainty target"),
                    "pred_m1": _number(source.get("pred_m1"), "uncertainty M1 prediction"),
                    "pred_m2": _number(source.get("pred_m2"), "uncertainty M2 prediction"),
                    "pred_m7": _number(source.get("pred_m7"), "uncertainty M7 prediction"),
                }
            )
            seen.add(row_id)
        if not rows:
            raise UncertaintyError("uncertainty fixture has no rows")
        return rows

    @staticmethod
    def _prediction(row: Mapping[str, Any]) -> tuple[float, float]:
        values = [float(row["pred_m1"]), float(row["pred_m2"]), float(row["pred_m7"])]
        return sum(values) / len(values), max(values) - min(values)

    def run(self, *, fixture: bool = True) -> UncertaintySummary:
        """Run calibration, selective risk, OOD detection, and abstention policy."""
        if not fixture:
            raise UncertaintyError("--fixture is required for uncertainty")
        config = self._config()
        fixture_data = self._fixture()
        self._inputs(fixture_data)
        rows = self._rows(fixture_data)
        calibration = [row for row in rows if row["split"] == "calibration"]
        validation = [row for row in rows if row["split"] == "validation"]
        if not calibration or not validation:
            raise UncertaintyError("uncertainty requires calibration and validation rows")
        predictions: dict[str, float] = {}
        uncertainties: dict[str, float] = {}
        residuals: list[float] = []
        for row in rows:
            prediction, spread = self._prediction(row)
            predictions[row["row_id"]] = prediction
            uncertainties[row["row_id"]] = spread + 0.1 * row["distance"]
            if row["split"] == "calibration":
                residuals.append(abs(prediction - row["target"]))
        coverage_target = float(config["coverage_target"])
        quantile = float(config["conformal_quantile"])
        radius = _quantile(residuals, quantile)
        covered = {row["row_id"]: abs(predictions[row["row_id"]] - row["target"]) <= radius for row in validation}
        coverage = sum(covered.values()) / len(covered)
        domain_calibration: list[dict[str, Any]] = []
        for domain in sorted({row["domain"] for row in validation}):
            members = [row for row in validation if row["domain"] == domain]
            domain_calibration.append(
                {
                    "domain": domain,
                    "rows": len(members),
                    "coverage": round(sum(covered[row["row_id"]] for row in members) / len(members), 6),
                    "mean_interval_width": round(2.0 * radius, 6),
                    "mean_abs_error": round(
                        sum(abs(predictions[row["row_id"]] - row["target"]) for row in members) / len(members),
                        6,
                    ),
                }
            )
        calibration_passed = coverage >= coverage_target and all(
            record["coverage"] >= coverage_target for record in domain_calibration
        )
        thresholds = [float(value) for value in config["selective_thresholds"]]
        selective_curve: list[dict[str, Any]] = []
        for threshold in thresholds:
            retained = [row for row in validation if uncertainties[row["row_id"]] <= threshold]
            if not retained:
                continue
            selective_curve.append(
                {
                    "uncertainty_threshold": threshold,
                    "coverage": round(len(retained) / len(validation), 6),
                    "abstention_rate": round(1.0 - len(retained) / len(validation), 6),
                    "selective_rmse": _metrics(retained, predictions)["rmse"],
                    "retained_rows": len(retained),
                }
            )
        selective_risks = [record["selective_rmse"] for record in selective_curve]
        selective_risk_decreases = all(
            left >= right for left, right in zip(selective_risks, selective_risks[1:], strict=False)
        )
        distance_scores = {row["row_id"]: row["distance"] for row in validation}
        uncertainty_scores = {row["row_id"]: uncertainties[row["row_id"]] for row in validation}
        distance_detector = _binary_metrics(validation, distance_scores, float(config["ood_distance_threshold"]))
        uncertainty_detector = _binary_metrics(
            validation, uncertainty_scores, float(config["ood_uncertainty_threshold"])
        )
        abstain_ids = sorted(
            row["row_id"]
            for row in validation
            if distance_scores[row["row_id"]] >= float(config["ood_distance_threshold"])
            or uncertainty_scores[row["row_id"]] >= float(config["ood_uncertainty_threshold"])
        )
        overconfident_ood = [row["row_id"] for row in validation if row["ood"] and row["row_id"] not in abstain_ids]
        ood_policy_passed = not overconfident_ood
        selected_model = (
            "ensemble_conformal" if calibration_passed and ood_policy_passed else str(config["fallback_model"])
        )
        calibration_audit = {
            "schema_version": 1,
            "calibration_rows": len(calibration),
            "validation_rows": len(validation),
            "coverage_target": coverage_target,
            "conformal_quantile": quantile,
            "conformal_radius": round(radius, 6),
            "coverage": round(coverage, 6),
            "domain_calibration": domain_calibration,
            "passed": calibration_passed,
            "target_values_exposed": False,
        }
        selective = {
            "schema_version": 1,
            "curve": selective_curve,
            "risk_decreases_with_abstention": selective_risk_decreases,
            "target_values_exposed": False,
        }
        ood = {
            "schema_version": 1,
            "distance_detector": distance_detector,
            "uncertainty_detector": uncertainty_detector,
            "abstention_ids": abstain_ids,
            "ood_rows": sum(row["ood"] for row in validation),
            "overconfident_ood_ids": overconfident_ood,
            "ood_policy_passed": ood_policy_passed,
            "target_values_exposed": False,
        }
        policy = {
            "schema_version": 1,
            "selected_model": selected_model,
            "fallback_used": selected_model == str(config["fallback_model"]),
            "abstain_on_distance_at_least": config["ood_distance_threshold"],
            "abstain_on_uncertainty_at_least": config["ood_uncertainty_threshold"],
            "overconfident_ood_rejected": ood_policy_passed,
            "target_values_exposed": False,
        }
        results = {
            "schema_version": 1,
            "model": "UNCERTAINTY",
            "status": "VALID",
            "selected_model": selected_model,
            "validation_metrics": _metrics(validation, predictions),
            "validation_prediction_count": len(validation),
            "target_values_exposed": False,
        }
        raw_payloads: dict[str, Any] = {
            "calibration": calibration_audit,
            "selective_risk": selective,
            "ood_detection": ood,
            "abstention_policy": policy,
            "uncertainty_results": results,
            "failures": {"schema_version": 1, "status": "VALID", "failures": []},
        }
        resume_key = _sha256(_canonical(raw_payloads))
        self.output_root.mkdir(parents=True, exist_ok=True)
        paths = {
            "calibration": self.output_root / "calibration_audit.json",
            "selective_risk": self.output_root / "selective_risk.json",
            "ood_detection": self.output_root / "ood_detection.json",
            "abstention_policy": self.output_root / "abstention_policy.json",
            "uncertainty_results": self.output_root / "uncertainty_results.json",
            "failures": self.output_root / "failure_ledger.json",
            "receipt": self.output_root / "uncertainty_receipt.json",
            "log": self.output_root / "uncertainty_log.json",
            "manifest": self.output_root / "uncertainty_manifest.json",
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
            "model": "UNCERTAINTY",
            "status": "VALID",
            "fixture": True,
            "rows": len(rows),
            "calibration": len(calibration),
            "validation": len(validation),
            "selected_model": selected_model,
            "calibration_passed": calibration_passed,
            "coverage": round(coverage, 6),
            "selective_risk_decreases": selective_risk_decreases,
            "ood_abstentions": len(abstain_ids),
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
                    {"event": "T071_T072_T074_T076_T077_inputs_verified", "rows": len(rows)},
                    {"event": "domain_calibration_completed", "domains": len(domain_calibration)},
                    {"event": "selective_risk_evaluated", "monotonic": selective_risk_decreases},
                    {"event": "ood_abstention_policy_applied", "abstentions": len(abstain_ids)},
                ],
            }
        )
        payload_bytes["manifest"] = _canonical(
            {
                "schema_version": 1,
                "model": "UNCERTAINTY",
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
                raise UncertaintyError("existing uncertainty receipt differs from rerun")
            for name, payload in payload_bytes.items():
                if paths[name].read_bytes() != payload:
                    raise UncertaintyError(f"existing uncertainty artifact differs: {name}")
            resumed = 1
        else:
            for name, payload in payload_bytes.items():
                paths[name].write_bytes(payload)
            resumed = 0
        return UncertaintySummary(
            rows=len(rows),
            calibration=len(calibration),
            validation=len(validation),
            selected_model=selected_model,
            calibration_passed=calibration_passed,
            coverage=round(coverage, 6),
            selective_risk_decreases=selective_risk_decreases,
            ood_abstentions=len(abstain_ids),
            resumed=resumed,
            receipt_path=paths["receipt"],
        )
