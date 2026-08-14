"""Fixture-backed cross-domain invariant-learning comparison for M7."""

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
    _solve,
    _string,
)


class M7Error(RuntimeError):
    """Raised when the M7 invariance or leakage contract is invalid."""


@dataclass(frozen=True)
class M7Summary:
    """Summary of one deterministic M7 comparison."""

    rows: int
    train: int
    validation: int
    domain_definitions: int
    selected_model: str
    hierarchical_erm_rmse: float
    ood_rmse: float
    leakage_passed: bool
    resumed: int
    receipt_path: Path


def _number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise M7Error(f"{label} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise M7Error(f"{label} must be finite")
    return result


def _features(rows: list[dict[str, Any]]) -> list[list[float]]:
    return [[1.0, row["x1"], row["x2"]] for row in rows]


def _weighted_ridge(rows: list[dict[str, Any]], weights: list[float], ridge: float) -> list[float]:
    features = _features(rows)
    matrix = [[0.0 for _ in range(3)] for _ in range(3)]
    vector = [0.0 for _ in range(3)]
    for row, feature, weight in zip(rows, features, weights, strict=True):
        for left in range(3):
            vector[left] += weight * feature[left] * row["target"]
            for right in range(3):
                matrix[left][right] += weight * feature[left] * feature[right]
    for index in range(1, 3):
        matrix[index][index] += ridge
    return _solve(matrix, vector)


def _metrics(rows: list[dict[str, Any]], predictions: Mapping[str, float]) -> dict[str, Any]:
    adapted = [{"instance_id": row["row_id"], "target": row["target"]} for row in rows]
    return _regression_metrics(
        adapted,
        {row["row_id"]: predictions[row["row_id"]] for row in rows},
    )


def _group_rmse(rows: list[dict[str, Any]], predictions: Mapping[str, float], field: str) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault(row[field], []).append(row)
    return [
        {"domain": key, "rmse": _metrics(group, predictions)["rmse"], "rows": len(group)}
        for key, group in sorted(groups.items())
    ]


class M7Workflow:
    """Compare invariant alternatives under a shared budget and OOD gate."""

    def __init__(
        self,
        root: Path,
        *,
        config_path: Path | None = None,
        fixture_path: Path | None = None,
        output_root: Path | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.config_path = config_path or self.root / "configs/models/m7.yaml"
        self.fixture_path = fixture_path or self.root / "tests/fixtures/models/m7_fixture.json"
        self.output_root = output_root or self.root / "reports/models/m7"

    def _config(self) -> dict[str, Any]:
        try:
            config = _mapping(yaml.safe_load(self.config_path.read_text(encoding="utf-8")), "M7 config")
        except (OSError, UnicodeError, yaml.YAMLError) as exc:
            raise M7Error(f"cannot load M7 config: {exc}") from exc
        if config.get("schema_version") != 1 or config.get("model") != "M7":
            raise M7Error("M7 config schema or model is invalid")
        if config.get("seed") != 59 or config.get("bootstrap_samples") != 128:
            raise M7Error("M7 seed/bootstrap configuration is not frozen")
        if config.get("fallback_model") != "hierarchical_erm":
            raise M7Error("M7 fallback model is invalid")
        return config

    def _fixture(self) -> dict[str, Any]:
        try:
            data = _mapping(json.loads(self.fixture_path.read_text(encoding="utf-8")), "M7 fixture")
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise M7Error(f"cannot load M7 fixture: {exc}") from exc
        if data.get("schema_version") != 1 or data.get("mode") != "m7_invariance_fixture":
            raise M7Error("M7 fixture schema or mode is invalid")
        if not isinstance(data.get("inputs"), list) or not isinstance(data.get("rows"), list):
            raise M7Error("M7 inputs/rows are invalid")
        if not isinstance(data.get("domain_definitions"), list):
            raise M7Error("M7 domain definitions are invalid")
        return data

    def _inputs(self, fixture: Mapping[str, Any]) -> None:
        expected = {
            "T071 M1 receipt": (
                self.root / "reports/models/m1/m1_receipt.json",
                "6f11129540792ffe84e185b84f4b11d8d2d39466f906d226e28d0648789aca5f",
            ),
            "T074 M4 receipt": (
                self.root / "reports/models/m4/m4_receipt.json",
                "a86fb1c74acdc0c5804bb7b4f4cf16e2e1be14689ae75b0864790ae750d54455",
            ),
            "T076 M6 receipt": (
                self.root / "reports/models/m6/m6_receipt.json",
                "8ab469c76f87aa530743773d8582199a04f1eb4e91be62c6f0910f68622c759a",
            ),
        }
        seen: set[str] = set()
        for value in fixture["inputs"]:
            row = _mapping(value, "M7 input")
            label = _string(row.get("label"), "M7 input label")
            if label not in expected:
                raise M7Error(f"unexpected M7 input: {label}")
            path, checksum = expected[label]
            declared_path = (self.root / _string(row.get("path"), "M7 input path")).resolve(strict=True)
            if declared_path != path.resolve(strict=True):
                raise M7Error(f"M7 input path mismatch: {label}")
            if _sha256(path.read_bytes()) != checksum or row.get("sha256") != checksum:
                raise M7Error(f"M7 input checksum differs: {label}")
            receipt = _mapping(json.loads(path.read_text(encoding="utf-8")), f"{label} payload")
            if receipt.get("status") != "VALID":
                raise M7Error(f"{label} is not valid")
            if label == "T076 M6 receipt" and receipt.get("causal_claim_permitted") is not False:
                raise M7Error("M6 causal gate must remain closed")
            seen.add(label)
        if seen != set(expected):
            raise M7Error("M7 inputs do not match T071/T074/T076 contract")

    @staticmethod
    def _domains(
        fixture: Mapping[str, Any], rows: list[dict[str, Any]], config: Mapping[str, Any]
    ) -> tuple[list[dict[str, Any]], bool]:
        required = {"name", "field", "source", "target_derived"}
        definitions: list[dict[str, Any]] = []
        fields: set[str] = set()
        leakage_reasons: list[str] = []
        for value in fixture["domain_definitions"]:
            definition = _mapping(value, "M7 domain definition")
            if set(definition) != required:
                raise M7Error("M7 domain definition fields do not match schema")
            name = _string(definition.get("name"), "M7 domain name")
            field = _string(definition.get("field"), "M7 domain field")
            source = _string(definition.get("source"), "M7 domain source")
            target_derived = definition.get("target_derived")
            if not isinstance(target_derived, bool):
                raise M7Error("M7 target-derived flag must be boolean")
            if field in fields or field not in rows[0]:
                raise M7Error(f"M7 domain field is duplicated or missing: {field}")
            if target_derived or field in {"target", "outcome", "label"}:
                leakage_reasons.append(f"target-derived domain field: {field}")
            if source in {"target", "outcome", "validation_target"}:
                leakage_reasons.append(f"target-derived domain source: {source}")
            fields.add(field)
            definitions.append(
                {
                    "name": name,
                    "field": field,
                    "source": source,
                    "target_derived": target_derived,
                    "unique_train_domains": len({row[field] for row in rows if row["split"] == "train"}),
                    "unique_validation_domains": len({row[field] for row in rows if row["split"] == "validation"}),
                }
            )
        expected_fields = {
            _string(config.get("primary_domain_field"), "M7 primary domain field"),
            _string(config.get("secondary_domain_field"), "M7 secondary domain field"),
        }
        if fields != expected_fields:
            raise M7Error("M7 domain fields do not match config")
        if len(definitions) < 2:
            raise M7Error("M7 requires at least two domain definitions")
        return definitions, not leakage_reasons

    @staticmethod
    def _rows(fixture: Mapping[str, Any]) -> list[dict[str, Any]]:
        required = {
            "row_id",
            "split",
            "x1",
            "x2",
            "target",
            "study_domain",
            "protocol_domain",
            "group_key",
        }
        rows: list[dict[str, Any]] = []
        seen: set[str] = set()
        for value in fixture["rows"]:
            source = _mapping(value, "M7 row")
            if set(source) != required:
                raise M7Error("M7 row fields do not match schema")
            row_id = _string(source.get("row_id"), "M7 row ID")
            if row_id in seen:
                raise M7Error(f"duplicate M7 row: {row_id}")
            split = _string(source.get("split"), "M7 split")
            if split not in {"train", "validation"}:
                raise M7Error(f"M7 split is invalid: {split}")
            rows.append(
                {
                    "row_id": row_id,
                    "split": split,
                    "x1": _number(source.get("x1"), "M7 x1"),
                    "x2": _number(source.get("x2"), "M7 x2"),
                    "target": _number(source.get("target"), "M7 target"),
                    "study_domain": _string(source.get("study_domain"), "M7 study domain"),
                    "protocol_domain": _string(source.get("protocol_domain"), "M7 protocol domain"),
                    "group_key": _string(source.get("group_key"), "M7 group key"),
                }
            )
            seen.add(row_id)
        if not rows:
            raise M7Error("M7 has no rows")
        return rows

    def run(self, *, fixture: bool = True) -> M7Summary:
        """Run fixed-budget cross-domain comparisons with an OOD acceptance gate."""
        if not fixture:
            raise M7Error("--fixture is required for M7")
        config = self._config()
        fixture_data = self._fixture()
        self._inputs(fixture_data)
        rows = self._rows(fixture_data)
        train = [row for row in rows if row["split"] == "train"]
        validation = [row for row in rows if row["split"] == "validation"]
        if not train or not validation:
            raise M7Error("M7 requires non-empty train and validation splits")
        domains, leakage_passed = self._domains(fixture_data, rows, config)
        primary = _string(config["primary_domain_field"], "M7 primary field")
        secondary = _string(config["secondary_domain_field"], "M7 secondary field")
        train_primary = {row[primary] for row in train}
        validation_primary = {row[primary] for row in validation}
        unseen_ood_domains = sorted(validation_primary - train_primary)

        ridge = float(config["ridge"])
        budget = int(config["tuning_budget"])
        fit_specs: dict[str, tuple[list[float], dict[str, float]]] = {}
        erm_coefficients = _ridge_fit(_features(train), [row["target"] for row in train], ridge)
        fit_specs["erm"] = (erm_coefficients, {})
        group_errors: dict[str, list[float]] = {}
        erm_predictions = {row["row_id"]: _predict_linear(erm_coefficients, _features([row])[0]) for row in train}
        for row in train:
            group_errors.setdefault(row[primary], []).append((erm_predictions[row["row_id"]] - row["target"]) ** 2)
        mean_group_error = sum(sum(values) / len(values) for values in group_errors.values()) / len(group_errors)
        weights = [
            1.0 + 0.5 * ((sum(group_errors[row[primary]]) / len(group_errors[row[primary]])) / mean_group_error)
            for row in train
        ]
        fit_specs["groupdro"] = (_weighted_ridge(train, weights, ridge), {})
        irm_coefficients = _ridge_fit([[1.0, row["x1"], 0.0] for row in train], [row["target"] for row in train], ridge)
        fit_specs["irm_like"] = (irm_coefficients, {})
        hierarchical_effects: dict[str, float] = {}
        for domain in sorted(train_primary):
            members = [row for row in train if row[primary] == domain]
            residuals = [row["target"] - _predict_linear(erm_coefficients, _features([row])[0]) for row in members]
            shrinkage = len(members) / (len(members) + float(config["random_effect_prior"]))
            hierarchical_effects[domain] = sum(residuals) / len(residuals) * shrinkage
        fit_specs["hierarchical_erm"] = (erm_coefficients, hierarchical_effects)

        model_records: dict[str, dict[str, Any]] = {}
        predictions_by_model: dict[str, dict[str, float]] = {}
        for model_name, (coefficients, effects) in fit_specs.items():
            predictions: dict[str, float] = {}
            for row in rows:
                base_features = _features([row])[0]
                if model_name == "irm_like":
                    base_features = [1.0, row["x1"], 0.0]
                prediction = _predict_linear(coefficients, base_features)
                prediction += effects.get(row[primary], 0.0)
                predictions[row["row_id"]] = prediction
            predictions_by_model[model_name] = predictions
            model_records[model_name] = {
                "model": model_name,
                "tuning_budget": budget,
                "train_metrics": _metrics(train, predictions),
                "validation_metrics": _metrics(validation, predictions),
                "primary_domain_metrics": _group_rmse(validation, predictions, primary),
                "secondary_domain_metrics": _group_rmse(validation, predictions, secondary),
                "complexity_rank": {
                    "erm": 1,
                    "groupdro": 2,
                    "irm_like": 3,
                    "hierarchical_erm": 2,
                }[model_name],
                "target_values_exposed": False,
            }
        baseline_rmse = float(model_records["hierarchical_erm"]["validation_metrics"]["rmse"])
        alternatives = {
            name: float(model_records[name]["validation_metrics"]["rmse"]) for name in ("erm", "groupdro", "irm_like")
        }
        best_alternative = min(alternatives, key=lambda name: alternatives[name])
        best_alternative_rmse = alternatives[best_alternative]
        ood_improvement = baseline_rmse - best_alternative_rmse
        complexity_accepted = leakage_passed and ood_improvement >= float(config["minimum_ood_improvement"])
        selected_model = best_alternative if complexity_accepted else str(config["fallback_model"])
        ood = {
            "schema_version": 1,
            "held_out_domains": unseen_ood_domains,
            "held_out_domain_count": len(unseen_ood_domains),
            "hierarchical_erm_rmse": baseline_rmse,
            "best_alternative": best_alternative,
            "best_alternative_rmse": best_alternative_rmse,
            "improvement_over_hierarchical_erm": round(ood_improvement, 6),
            "minimum_required_improvement": config["minimum_ood_improvement"],
            "improved": complexity_accepted,
            "target_values_exposed": False,
        }
        domain_audit = {
            "schema_version": 1,
            "definitions": domains,
            "primary_field": primary,
            "secondary_field": secondary,
            "label_leakage_passed": leakage_passed,
            "validation_domains_unseen_in_train": bool(unseen_ood_domains),
            "forbidden_sources": ["target", "outcome", "validation_target"],
            "target_values_exposed": False,
        }
        comparison = {
            "schema_version": 1,
            "model": "M7",
            "status": "VALID",
            "models": model_records,
            "identical_tuning_budget": (len({record["tuning_budget"] for record in model_records.values()}) == 1),
            "selected_model": selected_model,
            "complexity_accepted": complexity_accepted,
            "fallback_used": selected_model == "hierarchical_erm",
            "target_values_exposed": False,
        }
        results = {
            "schema_version": 1,
            "selected_model": selected_model,
            "selected_validation_rmse": model_records[selected_model]["validation_metrics"]["rmse"],
            "selected_validation_confidence_interval": _bootstrap_ci(
                [{"instance_id": row["row_id"], "target": row["target"]} for row in validation],
                predictions_by_model[selected_model],
                int(config["seed"]),
                int(config["bootstrap_samples"]),
            ),
            "target_values_exposed": False,
        }
        raw_payloads: dict[str, Any] = {
            "domain_audit": domain_audit,
            "comparison": comparison,
            "ood_evaluation": ood,
            "m7_results": results,
            "failures": {"schema_version": 1, "status": "VALID", "failures": []},
        }
        resume_key = _sha256(_canonical(raw_payloads))
        self.output_root.mkdir(parents=True, exist_ok=True)
        paths = {
            "domain_audit": self.output_root / "domain_audit.json",
            "comparison": self.output_root / "model_comparison.json",
            "ood_evaluation": self.output_root / "ood_evaluation.json",
            "m7_results": self.output_root / "m7_results.json",
            "failures": self.output_root / "failure_ledger.json",
            "receipt": self.output_root / "m7_receipt.json",
            "log": self.output_root / "m7_log.json",
            "manifest": self.output_root / "m7_manifest.json",
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
            "model": "M7",
            "status": "VALID",
            "fixture": True,
            "rows": len(rows),
            "train": len(train),
            "validation": len(validation),
            "domain_definitions": len(domains),
            "selected_model": selected_model,
            "hierarchical_erm_rmse": baseline_rmse,
            "ood_rmse": float(model_records[selected_model]["validation_metrics"]["rmse"]),
            "label_leakage_passed": leakage_passed,
            "complexity_accepted": complexity_accepted,
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
                    {"event": "T071_T074_T076_inputs_verified", "rows": len(rows)},
                    {"event": "domain_label_leakage_audited", "passed": leakage_passed},
                    {
                        "event": "identical_budget_comparison_completed",
                        "models": len(model_records),
                    },
                    {"event": "ood_complexity_gate_evaluated", "accepted": complexity_accepted},
                ],
            }
        )
        payload_bytes["manifest"] = _canonical(
            {
                "schema_version": 1,
                "model": "M7",
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
                raise M7Error("existing M7 receipt differs from rerun")
            for name, payload in payload_bytes.items():
                if paths[name].read_bytes() != payload:
                    raise M7Error(f"existing M7 artifact differs: {name}")
            resumed = 1
        else:
            for name, payload in payload_bytes.items():
                paths[name].write_bytes(payload)
            resumed = 0
        selected_rmse = float(model_records[selected_model]["validation_metrics"]["rmse"])
        return M7Summary(
            rows=len(rows),
            train=len(train),
            validation=len(validation),
            domain_definitions=len(domains),
            selected_model=selected_model,
            hierarchical_erm_rmse=baseline_rmse,
            ood_rmse=selected_rmse,
            leakage_passed=leakage_passed,
            resumed=resumed,
            receipt_path=paths["receipt"],
        )
