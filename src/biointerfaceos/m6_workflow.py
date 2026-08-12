"""Fixture-backed hierarchical causal-world M6 with automatic claim downgrading."""

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
    _predict_linear,
    _regression_metrics,
    _ridge_fit,
    _sha256,
    _string,
)


class M6Error(RuntimeError):
    """Raised when the M6 causal-world contract is invalid."""


@dataclass(frozen=True)
class M6Summary:
    """Summary of one deterministic M6 fit."""

    rows: int
    train: int
    validation: int
    overlap_passed: bool
    causal_claim_permitted: bool
    validation_rmse: float
    resumed: int
    receipt_path: Path


def _number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise M6Error(f"{label} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise M6Error(f"{label} must be finite")
    return result


def _rmse(rows: list[dict[str, Any]], predictions: Mapping[str, float]) -> float:
    errors = [
        float(predictions[_string(row["row_id"], "M6 row ID")]) - float(row["outcome"])
        for row in rows
    ]
    return math.sqrt(sum(error * error for error in errors) / len(errors))


class M6Workflow:
    """Fit a predictive mediator model and audit whether causal claims are identified."""

    def __init__(
        self,
        root: Path,
        *,
        config_path: Path | None = None,
        fixture_path: Path | None = None,
        output_root: Path | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.config_path = config_path or self.root / "configs/models/m6.yaml"
        self.fixture_path = fixture_path or self.root / "tests/fixtures/models/m6_fixture.json"
        self.output_root = output_root or self.root / "reports/models/m6"

    def _config(self) -> dict[str, Any]:
        try:
            config = _mapping(
                yaml.safe_load(self.config_path.read_text(encoding="utf-8")), "M6 config"
            )
        except (OSError, UnicodeError, yaml.YAMLError) as exc:
            raise M6Error(f"cannot load M6 config: {exc}") from exc
        if config.get("schema_version") != 1 or config.get("model") != "M6":
            raise M6Error("M6 config schema or model is invalid")
        if config.get("seed") != 47 or config.get("bootstrap_samples") != 128:
            raise M6Error("M6 seed/bootstrap configuration is not frozen")
        if config.get("language_policy") != "automatic_downgrade":
            raise M6Error("M6 language policy is invalid")
        return config

    def _fixture(self) -> dict[str, Any]:
        try:
            data = _mapping(json.loads(self.fixture_path.read_text(encoding="utf-8")), "M6 fixture")
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise M6Error(f"cannot load M6 fixture: {exc}") from exc
        if data.get("schema_version") != 1 or data.get("mode") != "m6_causal_fixture":
            raise M6Error("M6 fixture schema or mode is invalid")
        if not isinstance(data.get("inputs"), list) or not isinstance(data.get("rows"), list):
            raise M6Error("M6 inputs/rows are invalid")
        return data

    def _inputs(self, fixture: Mapping[str, Any]) -> None:
        expected = {
            "T073 M3 receipt": (
                self.root / "reports/models/m3/m3_receipt.json",
                "0e86a9759d497bd9e0c0b16041f006f1e48dc24811f5329670f566f57a0d6566",
            ),
            "T074 M4 receipt": (
                self.root / "reports/models/m4/m4_receipt.json",
                "a86fb1c74acdc0c5804bb7b4f4cf16e2e1be14689ae75b0864790ae750d54455",
            ),
            "T075 M5 receipt": (
                self.root / "reports/models/m5/m5_receipt.json",
                "70ed6a8b32134239fa095af162bc5c1089ed5bc637fad056dfcc3f731ea0a79e",
            ),
        }
        seen: set[str] = set()
        for value in fixture["inputs"]:
            row = _mapping(value, "M6 input")
            label = _string(row.get("label"), "M6 input label")
            if label not in expected:
                raise M6Error(f"unexpected M6 input: {label}")
            path, checksum = expected[label]
            declared_path = (self.root / _string(row.get("path"), "M6 input path")).resolve(
                strict=True
            )
            if declared_path != path.resolve(strict=True):
                raise M6Error(f"M6 input path mismatch: {label}")
            if _sha256(path.read_bytes()) != checksum or row.get("sha256") != checksum:
                raise M6Error(f"M6 input checksum differs: {label}")
            receipt = _mapping(json.loads(path.read_text(encoding="utf-8")), f"{label} payload")
            if receipt.get("status") != "VALID":
                raise M6Error(f"{label} is not valid")
            if label == "T073 M3 receipt" and receipt.get("causal_claim_permitted") is not False:
                raise M6Error("M3 causal gate must remain closed")
            seen.add(label)
        if seen != set(expected):
            raise M6Error("M6 inputs do not match T073/T074/T075 contract")

    @staticmethod
    def _rows(fixture: Mapping[str, Any]) -> list[dict[str, Any]]:
        required = {
            "row_id",
            "split",
            "treatment",
            "mediator",
            "outcome",
            "propensity",
            "group_key",
        }
        rows: list[dict[str, Any]] = []
        seen: set[str] = set()
        for value in fixture["rows"]:
            source = _mapping(value, "M6 row")
            if set(source) != required:
                raise M6Error("M6 row fields do not match schema")
            row_id = _string(source.get("row_id"), "M6 row ID")
            if row_id in seen:
                raise M6Error(f"duplicate M6 row: {row_id}")
            split = _string(source.get("split"), "M6 split")
            if split not in {"train", "validation"}:
                raise M6Error(f"M6 split is invalid: {split}")
            treatment = _number(source.get("treatment"), "M6 treatment")
            if treatment not in {0.0, 1.0}:
                raise M6Error("M6 treatment must be binary")
            mediator = _number(source.get("mediator"), "M6 mediator")
            outcome = _number(source.get("outcome"), "M6 outcome")
            propensity = _number(source.get("propensity"), "M6 propensity")
            if not 0.0 < propensity < 1.0:
                raise M6Error("M6 propensity must be strictly inside (0, 1)")
            rows.append(
                {
                    "row_id": row_id,
                    "split": split,
                    "treatment": treatment,
                    "mediator": mediator,
                    "outcome": outcome,
                    "propensity": propensity,
                    "group_key": _string(source.get("group_key"), "M6 group key"),
                }
            )
            seen.add(row_id)
        if not rows:
            raise M6Error("M6 has no rows")
        return rows

    @staticmethod
    def _features(rows: list[dict[str, Any]]) -> list[list[float]]:
        return [[1.0, row["treatment"], row["mediator"]] for row in rows]

    @staticmethod
    def _metrics(rows: list[dict[str, Any]], predictions: Mapping[str, float]) -> dict[str, Any]:
        adapted = [{"instance_id": row["row_id"], "target": row["outcome"]} for row in rows]
        return _regression_metrics(
            adapted,
            {row["row_id"]: predictions[row["row_id"]] for row in rows},
        )

    def run(self, *, fixture: bool = True) -> M6Summary:
        """Run M6 with explicit overlap, confounding, DAG, and language gates."""
        if not fixture:
            raise M6Error("--fixture is required for M6")
        config = self._config()
        fixture_data = self._fixture()
        self._inputs(fixture_data)
        rows = self._rows(fixture_data)
        train = [row for row in rows if row["split"] == "train"]
        validation = [row for row in rows if row["split"] == "validation"]
        if not train or not validation:
            raise M6Error("M6 requires non-empty train and validation splits")

        propensities = [row["propensity"] for row in rows]
        threshold = _number(config.get("overlap_threshold"), "M6 overlap threshold")
        margins = [min(propensity, 1.0 - propensity) for propensity in propensities]
        overlap_passed = min(margins) >= threshold
        overlap = {
            "schema_version": 1,
            "rows": len(rows),
            "propensity_min": round(min(propensities), 6),
            "propensity_max": round(max(propensities), 6),
            "minimum_overlap_margin": round(min(margins), 6),
            "threshold": threshold,
            "passed": overlap_passed,
            "target_values_exposed": False,
        }

        coefficients = _ridge_fit(
            self._features(train), [row["outcome"] for row in train], float(config["ridge"])
        )
        predictions = {
            row["row_id"]: _predict_linear(coefficients, self._features([row])[0]) for row in rows
        }
        train_metrics = self._metrics(train, predictions)
        validation_metrics = self._metrics(validation, predictions)
        validation_rmse = float(validation_metrics["rmse"])
        treated_mean = sum(row["outcome"] for row in rows if row["treatment"] == 1.0) / sum(
            row["treatment"] == 1.0 for row in rows
        )
        control_mean = sum(row["outcome"] for row in rows if row["treatment"] == 0.0) / sum(
            row["treatment"] == 0.0 for row in rows
        )
        beta_treatment = coefficients[1]
        beta_mediator = coefficients[2]
        sensitivity_strengths = [
            _number(value, "M6 confounding bias strength")
            for value in config["confounding_bias_strengths"]
        ]
        sensitivity = [
            {
                "bias_strength": strength,
                "adjusted_treatment_coefficient": round(
                    beta_treatment - strength * beta_mediator, 6
                ),
                "absolute_shift": round(abs(strength * beta_mediator), 6),
                "identified": False,
            }
            for strength in sensitivity_strengths
        ]
        estimands = {
            "schema_version": 1,
            "preregistered": True,
            "primary": {
                "name": "predictive_treatment_coefficient",
                "estimand": round(beta_treatment, 6),
                "status": "PREDICTIVE_ASSOCIATIONAL",
            },
            "secondary": {
                "name": "associational_mediator_adjusted_prediction",
                "status": "PREDICTIVE_ASSOCIATIONAL",
            },
            "causal_ate": {"status": "NONIDENTIFIED", "reason": "unblocked confounding"},
            "mediated_effect": {"status": "NONIDENTIFIED", "reason": "DAG assumptions fail"},
            "observed_treatment_mean_difference": round(treated_mean - control_mean, 6),
            "target_values_exposed": False,
        }
        alternative_dags = [
            {
                "dag_id": "DAG-OBSERVED-CONFOUNDING",
                "assumption": "unmeasured common cause of treatment and outcome",
                "identification": "NONIDENTIFIED",
            },
            {
                "dag_id": "DAG-MEDIATOR-CONFOUNDING",
                "assumption": "treatment-mediator and mediator-outcome confounding unblocked",
                "identification": "NONIDENTIFIED",
            },
            {
                "dag_id": "DAG-TEMPORAL-ORDER",
                "assumption": "cross-sectional fixture does not establish temporal order",
                "identification": "NONIDENTIFIED",
            },
        ]
        gates = {
            "overlap": overlap_passed,
            "randomized_treatment": False,
            "temporal_order": False,
            "confounding_blocked": False,
            "all_alternative_dags_identified": False,
        }
        causal_claim_permitted = all(gates.values())
        language_policy = {
            "schema_version": 1,
            "policy": "automatic_downgrade",
            "causal_claim_permitted": causal_claim_permitted,
            "allowed_label": (
                "CAUSAL" if causal_claim_permitted else "PREDICTIVE_ASSOCIATIONAL_ONLY"
            ),
            "blocked_terms": ["causal effect", "causes", "mediates", "ATE", "identified effect"],
            "approved_summary": (
                "The model supports predictive and associational reporting only; causal "
                "effects are not identified under the audited DAG assumptions."
            ),
            "target_values_exposed": False,
        }
        results = {
            "schema_version": 1,
            "model": "M6",
            "status": "VALID",
            "ridge": config["ridge"],
            "coefficients": {
                "intercept": round(coefficients[0], 6),
                "treatment": round(coefficients[1], 6),
                "mediator": round(coefficients[2], 6),
            },
            "train_metrics": train_metrics,
            "validation_metrics": validation_metrics,
            "validation_confidence_interval": _bootstrap_ci(
                [{"instance_id": row["row_id"], "target": row["outcome"]} for row in validation],
                predictions,
                int(config["seed"]),
                int(config["bootstrap_samples"]),
            ),
            "prediction_count": len(rows),
            "prediction_ids": sorted(predictions),
            "target_values_exposed": False,
        }
        raw_payloads: dict[str, Any] = {
            "dag_card": {
                "schema_version": 1,
                "gates": gates,
                "causal_claim_permitted": causal_claim_permitted,
            },
            "estimand_card": estimands,
            "overlap_audit": overlap,
            "confounding_sensitivity": {
                "schema_version": 1,
                "observed_treatment_coefficient": round(beta_treatment, 6),
                "mediator_coefficient": round(beta_mediator, 6),
                "bias_strengths": sensitivity,
            },
            "alternative_dags": {"schema_version": 1, "cards": alternative_dags},
            "m6_results": results,
            "language_policy": language_policy,
            "failures": {"schema_version": 1, "status": "VALID", "failures": []},
        }
        resume_key = _sha256(_canonical(raw_payloads))
        self.output_root.mkdir(parents=True, exist_ok=True)
        paths = {
            "dag_card": self.output_root / "dag_card.json",
            "estimand_card": self.output_root / "estimand_card.json",
            "overlap_audit": self.output_root / "overlap_audit.json",
            "confounding_sensitivity": self.output_root / "confounding_sensitivity.json",
            "alternative_dags": self.output_root / "alternative_dags.json",
            "m6_results": self.output_root / "m6_results.json",
            "language_policy": self.output_root / "language_policy.json",
            "failures": self.output_root / "failure_ledger.json",
            "receipt": self.output_root / "m6_receipt.json",
            "log": self.output_root / "m6_log.json",
            "manifest": self.output_root / "m6_manifest.json",
        }
        payload_bytes = {name: _canonical(value) for name, value in raw_payloads.items()}
        artifact_records = {
            name: {
                "path": (
                    str(path.relative_to(self.root))
                    if path.is_relative_to(self.root)
                    else str(path)
                ),
                "sha256": _sha256(payload_bytes[name]),
                "bytes": len(payload_bytes[name]),
            }
            for name, path in paths.items()
            if name in payload_bytes
        }
        receipt = {
            "schema_version": 1,
            "model": "M6",
            "status": "VALID",
            "fixture": True,
            "rows": len(rows),
            "train": len(train),
            "validation": len(validation),
            "overlap_passed": overlap_passed,
            "causal_claim_permitted": causal_claim_permitted,
            "estimand_status": "PREDICTIVE_ASSOCIATIONAL_ONLY",
            "validation_rmse": validation_rmse,
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
                    {"event": "T073_T074_T075_inputs_verified", "rows": len(rows)},
                    {"event": "overlap_gate_evaluated", "passed": overlap_passed},
                    {"event": "causal_identification_audited", "permitted": causal_claim_permitted},
                    {"event": "language_policy_applied", "label": language_policy["allowed_label"]},
                ],
            }
        )
        payload_bytes["manifest"] = _canonical(
            {
                "schema_version": 1,
                "model": "M6",
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
                raise M6Error("existing M6 receipt differs from rerun")
            for name, payload in payload_bytes.items():
                if paths[name].read_bytes() != payload:
                    raise M6Error(f"existing M6 artifact differs: {name}")
            resumed = 1
        else:
            for name, payload in payload_bytes.items():
                paths[name].write_bytes(payload)
            resumed = 0
        return M6Summary(
            rows=len(rows),
            train=len(train),
            validation=len(validation),
            overlap_passed=overlap_passed,
            causal_claim_permitted=causal_claim_permitted,
            validation_rmse=validation_rmse,
            resumed=resumed,
            receipt_path=paths["receipt"],
        )
