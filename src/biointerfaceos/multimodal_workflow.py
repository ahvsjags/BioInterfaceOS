"""Fixture-backed missing-modality-safe multimodal representation workflow."""

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
    _predict_linear,
    _regression_metrics,
    _ridge_fit,
    _sha256,
    _string,
)


class MultimodalError(RuntimeError):
    """Raised when the multimodal representation contract is invalid."""


@dataclass(frozen=True)
class MultimodalSummary:
    """Summary of one deterministic multimodal comparison."""

    rows: int
    train: int
    validation: int
    modalities: int
    selected_model: str
    fusion_ood_gain: float
    selected_ood_rmse: float
    leakage_passed: bool
    missingness_masked: bool
    resumed: int
    receipt_path: Path


def _number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise MultimodalError(f"{label} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise MultimodalError(f"{label} must be finite")
    return result


def _metrics(rows: list[dict[str, Any]], predictions: Mapping[str, float]) -> dict[str, Any]:
    adapted = [{"instance_id": row["row_id"], "target": row["target"]} for row in rows]
    return _regression_metrics(
        adapted,
        {row["row_id"]: predictions[row["row_id"]] for row in rows},
    )


class MultimodalWorkflow:
    """Compare modality-specific and masked fusion representations."""

    def __init__(
        self,
        root: Path,
        *,
        config_path: Path | None = None,
        fixture_path: Path | None = None,
        output_root: Path | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.config_path = config_path or self.root / "configs/models/multimodal.yaml"
        self.fixture_path = fixture_path or (
            self.root / "tests/fixtures/models/multimodal_fixture.json"
        )
        self.output_root = output_root or self.root / "reports/models/multimodal"

    def _config(self) -> dict[str, Any]:
        try:
            config = _mapping(
                yaml.safe_load(self.config_path.read_text(encoding="utf-8")),
                "multimodal config",
            )
        except (OSError, UnicodeError, yaml.YAMLError) as exc:
            raise MultimodalError(f"cannot load multimodal config: {exc}") from exc
        if config.get("schema_version") != 1 or config.get("model") != "MULTIMODAL":
            raise MultimodalError("multimodal config schema or model is invalid")
        if config.get("seed") != 71 or config.get("bootstrap_samples") != 128:
            raise MultimodalError("multimodal seed/bootstrap configuration is not frozen")
        if config.get("fallback_model") != "material_protocol_masked":
            raise MultimodalError("multimodal fallback model is invalid")
        return config

    def _fixture(self) -> dict[str, Any]:
        try:
            data = _mapping(
                json.loads(self.fixture_path.read_text(encoding="utf-8")),
                "multimodal fixture",
            )
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise MultimodalError(f"cannot load multimodal fixture: {exc}") from exc
        if data.get("schema_version") != 1 or data.get("mode") != "multimodal_fixture":
            raise MultimodalError("multimodal fixture schema or mode is invalid")
        if not isinstance(data.get("inputs"), list) or not isinstance(data.get("rows"), list):
            raise MultimodalError("multimodal inputs/rows are invalid")
        if not isinstance(data.get("modality_definitions"), list):
            raise MultimodalError("multimodal definitions are invalid")
        return data

    def _inputs(self, fixture: Mapping[str, Any]) -> None:
        expected = {
            "T070 representation receipt": (
                self.root / "reports/benchmark/representations/representation_receipt.json",
                "d8d55f78dcb945b0244efef6c4db57ce366fb14da2dad929de66f08a673c99c3",
            ),
            "T074 M4 receipt": (
                self.root / "reports/models/m4/m4_receipt.json",
                "a86fb1c74acdc0c5804bb7b4f4cf16e2e1be14689ae75b0864790ae750d54455",
            ),
            "T078 uncertainty receipt": (
                self.root / "reports/models/uncertainty/uncertainty_receipt.json",
                "f36a003c4c2afb5dc7713af841e6736274ee9582a58f9eef306bc7f537676a71",
            ),
        }
        seen: set[str] = set()
        for value in fixture["inputs"]:
            row = _mapping(value, "multimodal input")
            label = _string(row.get("label"), "multimodal input label")
            if label not in expected:
                raise MultimodalError(f"unexpected multimodal input: {label}")
            path, checksum = expected[label]
            declared_path = (self.root / _string(row.get("path"), "multimodal input path")).resolve(
                strict=True
            )
            if declared_path != path.resolve(strict=True):
                raise MultimodalError(f"multimodal input path mismatch: {label}")
            if _sha256(path.read_bytes()) != checksum or row.get("sha256") != checksum:
                raise MultimodalError(f"multimodal input checksum differs: {label}")
            receipt = _mapping(json.loads(path.read_text(encoding="utf-8")), f"{label} payload")
            if receipt.get("status") != "VALID":
                raise MultimodalError(f"{label} is not valid")
            seen.add(label)
        if seen != set(expected):
            raise MultimodalError("multimodal inputs do not match T070/T074/T078")

    @staticmethod
    def _rows(fixture: Mapping[str, Any]) -> list[dict[str, Any]]:
        required = {
            "row_id",
            "split",
            "source_id",
            "ood",
            "target",
            "material_feature",
            "protocol_feature",
            "structure_feature",
            "figure_feature",
            "text_feature",
        }
        rows: list[dict[str, Any]] = []
        seen: set[str] = set()
        fields = [
            "material_feature",
            "protocol_feature",
            "structure_feature",
            "figure_feature",
            "text_feature",
        ]
        for value in fixture["rows"]:
            source = _mapping(value, "multimodal row")
            if set(source) != required:
                raise MultimodalError("multimodal row fields do not match schema")
            row_id = _string(source.get("row_id"), "multimodal row ID")
            if row_id in seen:
                raise MultimodalError(f"duplicate multimodal row: {row_id}")
            split = _string(source.get("split"), "multimodal split")
            if split not in {"train", "validation"}:
                raise MultimodalError(f"multimodal split is invalid: {split}")
            ood = source.get("ood")
            if not isinstance(ood, bool):
                raise MultimodalError("multimodal OOD flag must be boolean")
            row: dict[str, Any] = {
                "row_id": row_id,
                "split": split,
                "source_id": _string(source.get("source_id"), "multimodal source ID"),
                "ood": ood,
                "target": _number(source.get("target"), "multimodal target"),
            }
            for field in fields:
                raw = source.get(field)
                if raw is None:
                    row[field] = None
                else:
                    row[field] = _number(raw, f"multimodal {field}")
            rows.append(row)
            seen.add(row_id)
        if not rows:
            raise MultimodalError("multimodal fixture has no rows")
        return rows

    @staticmethod
    def _audit_definitions(
        fixture: Mapping[str, Any], rows: list[dict[str, Any]], config: Mapping[str, Any]
    ) -> tuple[list[dict[str, Any]], bool, bool]:
        required = {"name", "field", "source", "outcome_derived"}
        forbidden = set(config["forbidden_feature_fields"])
        definitions: list[dict[str, Any]] = []
        fields: set[str] = set()
        outcome_text_leakage = False
        for value in fixture["modality_definitions"]:
            definition = _mapping(value, "multimodal definition")
            if set(definition) != required:
                raise MultimodalError("multimodal definition fields do not match schema")
            name = _string(definition.get("name"), "multimodal definition name")
            field = _string(definition.get("field"), "multimodal definition field")
            source = _string(definition.get("source"), "multimodal definition source")
            outcome_derived = definition.get("outcome_derived")
            if not isinstance(outcome_derived, bool):
                raise MultimodalError("multimodal outcome-derived flag must be boolean")
            if field in fields or field not in rows[0]:
                raise MultimodalError(f"multimodal field is duplicated or missing: {field}")
            if field in forbidden or outcome_derived:
                raise MultimodalError(f"forbidden or outcome-derived modality: {field}")
            if name == "text" and (
                outcome_derived or "outcome" in source.lower() or "result" in source.lower()
            ):
                outcome_text_leakage = True
            fields.add(field)
            definitions.append(
                {
                    "name": name,
                    "field": field,
                    "source": source,
                    "outcome_derived": outcome_derived,
                    "missing_train": sum(
                        row[field] is None for row in rows if row["split"] == "train"
                    ),
                    "missing_validation": sum(
                        row[field] is None for row in rows if row["split"] == "validation"
                    ),
                }
            )
        expected = set(config["modality_fields"])
        if fields != expected or len(definitions) < 5:
            raise MultimodalError("multimodal definitions do not match config")
        source_identity_leakage = bool(config["source_identity_field"] in fields)
        return definitions, not source_identity_leakage, not outcome_text_leakage

    @staticmethod
    def _features(rows: list[dict[str, Any]], fields: list[str]) -> list[list[float]]:
        features: list[list[float]] = []
        for row in rows:
            values: list[float] = [1.0]
            for field in fields:
                value = row[field]
                values.extend([0.0 if value is None else value, 1.0 if value is None else 0.0])
            features.append(values)
        return features

    def _fit_model(
        self,
        train: list[dict[str, Any]],
        rows: list[dict[str, Any]],
        fields: list[str],
        ridge: float,
    ) -> dict[str, Any]:
        coefficients = _ridge_fit(
            self._features(train, fields), [row["target"] for row in train], ridge
        )
        predictions = {
            row["row_id"]: _predict_linear(coefficients, self._features([row], fields)[0])
            for row in rows
        }
        return {
            "feature_fields": fields,
            "predictions": predictions,
            "train_metrics": _metrics(train, predictions),
        }

    def run(self, *, fixture: bool = True) -> MultimodalSummary:
        """Run masked modality comparisons and OOD fusion acceptance gate."""
        if not fixture:
            raise MultimodalError("--fixture is required for multimodal")
        config = self._config()
        fixture_data = self._fixture()
        self._inputs(fixture_data)
        rows = self._rows(fixture_data)
        train = [row for row in rows if row["split"] == "train"]
        validation = [row for row in rows if row["split"] == "validation"]
        ood = [row for row in validation if row["ood"]]
        if not train or not validation or not ood:
            raise MultimodalError("multimodal requires train, validation, and OOD rows")
        definitions, source_identity_passed, text_leakage_passed = self._audit_definitions(
            fixture_data, rows, config
        )
        modality_fields = [str(field) for field in config["modality_fields"]]
        ridge = float(config["ridge"])
        model_fields = {
            f"single_{field.removesuffix('_feature')}": [field] for field in modality_fields
        }
        model_fields["material_protocol_masked"] = [
            "material_feature",
            "protocol_feature",
        ]
        model_fields["fusion"] = modality_fields
        model_records: dict[str, dict[str, Any]] = {}
        model_predictions: dict[str, dict[str, float]] = {}
        for name, fields in model_fields.items():
            fit = self._fit_model(train, rows, fields, ridge)
            predictions = fit["predictions"]
            model_predictions[name] = predictions
            model_records[name] = {
                "model": name,
                "feature_fields": fields,
                "train_metrics": fit["train_metrics"],
                "validation_metrics": _metrics(validation, predictions),
                "ood_metrics": _metrics(ood, predictions),
                "missingness_masked": True,
                "target_values_exposed": False,
            }
        single_names = [name for name in model_records if name.startswith("single_")]
        best_single_name = min(
            single_names, key=lambda name: model_records[name]["ood_metrics"]["rmse"]
        )
        fusion_ood_rmse = float(model_records["fusion"]["ood_metrics"]["rmse"])
        best_single_ood_rmse = float(model_records[best_single_name]["ood_metrics"]["rmse"])
        fusion_ood_gain = best_single_ood_rmse - fusion_ood_rmse
        leakage_passed = source_identity_passed and text_leakage_passed
        fusion_gain_persists = leakage_passed and fusion_ood_gain >= float(
            config["minimum_ood_gain"]
        )
        selected_model = "fusion" if fusion_gain_persists else str(config["fallback_model"])
        missingness = {
            "schema_version": 1,
            "modalities": definitions,
            "mask_columns_emitted": True,
            "all_missingness_masked": True,
            "missing_rows": {
                field: sum(row[field] is None for row in rows) for field in modality_fields
            },
            "target_values_exposed": False,
        }
        leakage = {
            "schema_version": 1,
            "source_identity_field": config["source_identity_field"],
            "source_identity_leakage_passed": source_identity_passed,
            "outcome_text_leakage_passed": text_leakage_passed,
            "forbidden_feature_fields": config["forbidden_feature_fields"],
            "model_feature_fields": sorted(
                {field for fields in model_fields.values() for field in fields}
            ),
            "target_values_exposed": False,
        }
        comparison = {
            "schema_version": 1,
            "models": model_records,
            "best_single_modality": best_single_name,
            "fusion_in_domain_gain": round(
                float(model_records[best_single_name]["validation_metrics"]["rmse"])
                - float(model_records["fusion"]["validation_metrics"]["rmse"]),
                6,
            ),
            "fusion_ood_gain": round(fusion_ood_gain, 6),
            "minimum_ood_gain": config["minimum_ood_gain"],
            "fusion_gain_persists_ood": fusion_gain_persists,
            "selected_model": selected_model,
            "target_values_exposed": False,
        }
        ood_evaluation = {
            "schema_version": 1,
            "ood_rows": len(ood),
            "best_single_ood_rmse": best_single_ood_rmse,
            "fusion_ood_rmse": fusion_ood_rmse,
            "fusion_ood_gain": round(fusion_ood_gain, 6),
            "gain_persists": fusion_gain_persists,
            "fallback_reason": None
            if fusion_gain_persists
            else "fusion OOD gain did not clear the preregistered threshold or leakage gate",
            "target_values_exposed": False,
        }
        results = {
            "schema_version": 1,
            "model": "MULTIMODAL",
            "status": "VALID",
            "selected_model": selected_model,
            "selected_ood_rmse": model_records[selected_model]["ood_metrics"]["rmse"],
            "leakage_passed": leakage_passed,
            "missingness_masked": True,
            "target_values_exposed": False,
        }
        raw_payloads: dict[str, Any] = {
            "missingness": missingness,
            "leakage": leakage,
            "comparison": comparison,
            "ood_evaluation": ood_evaluation,
            "multimodal_results": results,
            "failures": {"schema_version": 1, "status": "VALID", "failures": []},
        }
        resume_key = _sha256(_canonical(raw_payloads))
        self.output_root.mkdir(parents=True, exist_ok=True)
        paths = {
            "missingness": self.output_root / "missingness_audit.json",
            "leakage": self.output_root / "leakage_audit.json",
            "comparison": self.output_root / "model_comparison.json",
            "ood_evaluation": self.output_root / "ood_evaluation.json",
            "multimodal_results": self.output_root / "multimodal_results.json",
            "failures": self.output_root / "failure_ledger.json",
            "receipt": self.output_root / "multimodal_receipt.json",
            "log": self.output_root / "multimodal_log.json",
            "manifest": self.output_root / "multimodal_manifest.json",
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
            "model": "MULTIMODAL",
            "status": "VALID",
            "fixture": True,
            "rows": len(rows),
            "train": len(train),
            "validation": len(validation),
            "modalities": len(definitions),
            "selected_model": selected_model,
            "fusion_ood_gain": round(fusion_ood_gain, 6),
            "leakage_passed": leakage_passed,
            "missingness_masked": True,
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
                    {"event": "T070_T074_T078_inputs_verified", "rows": len(rows)},
                    {"event": "missing_modality_masks_emitted", "modalities": len(definitions)},
                    {"event": "source_and_text_leakage_audited", "passed": leakage_passed},
                    {"event": "fusion_ood_gate_evaluated", "selected_model": selected_model},
                ],
            }
        )
        payload_bytes["manifest"] = _canonical(
            {
                "schema_version": 1,
                "model": "MULTIMODAL",
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
                raise MultimodalError("existing multimodal receipt differs from rerun")
            for name, payload in payload_bytes.items():
                if paths[name].read_bytes() != payload:
                    raise MultimodalError(f"existing multimodal artifact differs: {name}")
            resumed = 1
        else:
            for name, payload in payload_bytes.items():
                paths[name].write_bytes(payload)
            resumed = 0
        return MultimodalSummary(
            rows=len(rows),
            train=len(train),
            validation=len(validation),
            modalities=len(definitions),
            selected_model=selected_model,
            fusion_ood_gain=round(fusion_ood_gain, 6),
            selected_ood_rmse=float(model_records[selected_model]["ood_metrics"]["rmse"]),
            leakage_passed=leakage_passed,
            missingness_masked=True,
            resumed=resumed,
            receipt_path=paths["receipt"],
        )
