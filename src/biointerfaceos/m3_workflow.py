"""Fixture-backed static corona mediator M3 decomposition."""

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


class M3Error(RuntimeError):
    """Raised when the M3 paired-unit or identification contract is invalid."""


@dataclass(frozen=True)
class M3Summary:
    """Summary of one M3 fit."""

    pairs: int
    train: int
    validation: int
    identification_status: str
    direct_rmse: float
    mediated_rmse: float
    resumed: int
    receipt_path: Path


class M3Workflow:
    """Fit direct/mediated associational decompositions with negative control."""

    def __init__(
        self,
        root: Path,
        *,
        config_path: Path | None = None,
        fixture_path: Path | None = None,
        output_root: Path | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.config_path = config_path or self.root / "configs/models/m3.yaml"
        self.fixture_path = fixture_path or self.root / "tests/fixtures/models/m3_fixture.json"
        self.public_path = self.root / "reports/benchmark/instances/public_instances.json"
        self.module_path = self.root / "reports/omics/harmonization/module_matrix.json"
        self.link_path = self.root / "reports/omics/modality_links/link_graph.json"
        self.baseline_fixture_path = self.root / "tests/fixtures/benchmark/baseline_fixture.json"
        self.output_root = output_root or self.root / "reports/models/m3"

    def _config(self) -> dict[str, Any]:
        try:
            config = _mapping(yaml.safe_load(self.config_path.read_text(encoding="utf-8")), "M3 config")
        except (OSError, UnicodeError, yaml.YAMLError) as exc:
            raise M3Error(f"cannot load M3 config: {exc}") from exc
        if config.get("schema_version") != 1 or config.get("model") != "M3":
            raise M3Error("M3 config schema or model is invalid")
        if config.get("seed") != 37 or config.get("bootstrap_samples") != 128:
            raise M3Error("M3 seed/bootstrap configuration is not frozen")
        if config.get("identification_status") != "ASSOCIATIONAL_ONLY":
            raise M3Error("M3 identification status must be associational-only")
        return config

    def _fixture(self) -> dict[str, Any]:
        try:
            data = _mapping(json.loads(self.fixture_path.read_text(encoding="utf-8")), "M3 fixture")
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise M3Error(f"cannot load M3 fixture: {exc}") from exc
        if data.get("schema_version") != 1 or data.get("mode") != "m3_static_corona_fixture":
            raise M3Error("M3 fixture schema or mode is invalid")
        if not isinstance(data.get("inputs"), list) or not isinstance(data.get("pairs"), list):
            raise M3Error("M3 inputs/pairs are invalid")
        return data

    def _inputs(self, fixture: Mapping[str, Any]) -> dict[str, Any]:
        required = {
            "T067 public instances": self.public_path,
            "T056 corona module matrix": self.module_path,
            "T062 modality links": self.link_path,
            "T069 baseline fixture": self.baseline_fixture_path,
        }
        loaded: dict[str, Any] = {}
        seen: set[str] = set()
        for value in fixture["inputs"]:
            row = _mapping(value, "M3 input")
            label = _string(row.get("label"), "M3 input label")
            if label not in required:
                raise M3Error(f"unexpected M3 input: {label}")
            path = (self.root / _string(row.get("path"), "M3 input path")).resolve(strict=True)
            if path != required[label].resolve(strict=True):
                raise M3Error(f"M3 input path mismatch: {label}")
            if _sha256(path.read_bytes()) != _string(row.get("sha256"), "M3 input checksum"):
                raise M3Error(f"M3 input checksum differs: {label}")
            loaded[label] = json.loads(path.read_text(encoding="utf-8"))
            seen.add(label)
        if seen != set(required):
            raise M3Error("M3 inputs do not match T056/T062/T067/T069 contract")
        public = _mapping(loaded["T067 public instances"], "public instances")
        if public.get("status") != "VALID" or public.get("target_values_exposed") is not False:
            raise M3Error("M3 public instances are not target-isolated")
        return loaded

    @staticmethod
    def _targets(baseline: Mapping[str, Any]) -> dict[str, float]:
        targets: dict[str, float] = {}
        for value in baseline["targets"]:
            row = _mapping(value, "M3 target")
            instance_id = _string(row.get("instance_id"), "M3 target instance ID")
            if instance_id in targets:
                raise M3Error(f"duplicate M3 target: {instance_id}")
            targets[instance_id] = _number(row.get("target"), "M3 target")
        return targets

    @staticmethod
    def _pairs(
        fixture: Mapping[str, Any], public: Mapping[str, Any], targets: Mapping[str, float]
    ) -> list[dict[str, Any]]:
        public_rows = {
            _string(_mapping(row, "public row").get("instance_id"), "public ID"): _mapping(row, "public row")
            for row in public["instances"]
        }
        required = {
            "pair_id",
            "instance_id",
            "split",
            "material_feature",
            "mediator_feature",
            "response_feature",
            "mediator_uncertainty",
        }
        pairs: list[dict[str, Any]] = []
        seen_ids: set[str] = set()
        seen_pairs: set[str] = set()
        pair_splits: dict[str, str] = {}
        for value in fixture["pairs"]:
            row = _mapping(value, "M3 pair")
            if set(row) != required:
                raise M3Error("M3 pair fields do not match schema")
            pair_id = _string(row.get("pair_id"), "M3 pair ID")
            instance_id = _string(row.get("instance_id"), "M3 instance ID")
            split = _string(row.get("split"), "M3 split")
            if pair_id in seen_pairs or instance_id in seen_ids:
                raise M3Error(f"M3 pair identity is duplicated: {pair_id}")
            if instance_id not in public_rows:
                raise M3Error(f"M3 pair is not in T067 public instances: {instance_id}")
            if split not in {"train", "validation"}:
                raise M3Error(f"M3 split is invalid: {split}")
            if split != _string(public_rows[instance_id].get("split"), "public split"):
                raise M3Error(f"M3 split differs from T067: {instance_id}")
            if pair_id in pair_splits and pair_splits[pair_id] != split:
                raise M3Error(f"M3 pair crosses split: {pair_id}")
            pair_splits[pair_id] = split
            uncertainty = _number(row.get("mediator_uncertainty"), "M3 mediator uncertainty")
            if uncertainty < 0.0 or uncertainty > 1.0:
                raise M3Error(f"M3 mediator uncertainty outside [0, 1]: {pair_id}")
            pairs.append(
                {
                    "pair_id": pair_id,
                    "instance_id": instance_id,
                    "split": split,
                    "material_feature": _hash_bucket(_string(row.get("material_feature"), "M3 material feature")),
                    "mediator_feature": _number(row.get("mediator_feature"), "M3 mediator feature"),
                    "response_feature": _hash_bucket(_string(row.get("response_feature"), "M3 response feature")),
                    "mediator_uncertainty": uncertainty,
                    "target": targets[instance_id],
                }
            )
            seen_ids.add(instance_id)
            seen_pairs.add(pair_id)
        if seen_ids != set(public_rows):
            raise M3Error("M3 pairs do not cover public instances")
        return pairs

    @staticmethod
    def _fit(
        train: list[dict[str, Any]],
        rows: list[dict[str, Any]],
        features: list[str],
        ridge: float,
    ) -> tuple[list[float], dict[str, float]]:
        coefficients = _ridge_fit(
            [[1.0, *[row[feature] for feature in features]] for row in train],
            [row["target"] for row in train],
            ridge=ridge,
        )
        predictions = {
            row["instance_id"]: _predict_linear(coefficients, [1.0, *[row[feature] for feature in features]])
            for row in rows
        }
        return coefficients, predictions

    def run(self, *, fixture: bool = True) -> M3Summary:
        """Fit direct, mediated, and random-mediator controls."""
        if not fixture:
            raise M3Error("--fixture is required for M3")
        config = self._config()
        fixture_data = self._fixture()
        inputs = self._inputs(fixture_data)
        targets = self._targets(inputs["T069 baseline fixture"])
        pairs = self._pairs(fixture_data, inputs["T067 public instances"], targets)
        train = [row for row in pairs if row["split"] == "train"]
        validation = [row for row in pairs if row["split"] == "validation"]
        direct_features = ["material_feature", "response_feature"]
        mediated_features = ["material_feature", "mediator_feature", "response_feature"]
        direct_coefficients, direct_predictions = self._fit(train, pairs, direct_features, float(config["ridge"]))
        mediated_coefficients, mediated_predictions = self._fit(train, pairs, mediated_features, float(config["ridge"]))
        random_rows = [dict(row) for row in train]
        values = [row["mediator_feature"] for row in random_rows]
        for row, value in zip(random_rows, values[1:] + values[:1], strict=True):
            row["mediator_feature"] = value
        random_coefficients, _ = self._fit(random_rows, random_rows, mediated_features, float(config["ridge"]))
        random_predictions = {
            row["instance_id"]: _predict_linear(
                random_coefficients, [1.0, *[row[feature] for feature in mediated_features]]
            )
            for row in pairs
        }
        direct_metrics = _regression_metrics(validation, direct_predictions)
        mediated_metrics = _regression_metrics(validation, mediated_predictions)
        random_metrics = _regression_metrics(validation, random_predictions)
        residual_sd = math.sqrt(
            _mean([(row["target"] - mediated_predictions[row["instance_id"]]) ** 2 for row in train])
        )
        uncertainty = {
            "mediator_uncertainty_mean": round(_mean([row["mediator_uncertainty"] for row in validation]), 6),
            "model_residual_sd": round(residual_sd, 6),
            "combined_prediction_sd": round(
                math.sqrt(residual_sd**2 + _mean([row["mediator_uncertainty"] ** 2 for row in validation])),
                6,
            ),
            "propagation": "quadrature",
        }
        pairing = {
            "schema_version": 1,
            "pairs": len(pairs),
            "unique_pair_ids": len({row["pair_id"] for row in pairs}),
            "duplicate_pair_ids": 0,
            "cross_split_pairs": 0,
            "complete_material_mediator_response": True,
            "split_safe": True,
            "identity_features_used": False,
        }
        identification = {
            "schema_version": 1,
            "status": config["identification_status"],
            "causal_claim_permitted": False,
            "randomized_intervention": False,
            "temporal_order_verified": False,
            "unmeasured_confounding_blocked": False,
            "downgrade_reason": (
                "Paired associational data lack randomized intervention, temporal order, and confounding control."
            ),
        }
        comparison = {
            "direct": {"metrics": direct_metrics, "features": direct_features},
            "mediated": {"metrics": mediated_metrics, "features": mediated_features},
            "random_mediator": {"metrics": random_metrics, "features": mediated_features},
            "mediated_minus_direct_rmse": round(mediated_metrics["rmse"] - direct_metrics["rmse"], 6),
            "random_control_minus_mediated_rmse": round(random_metrics["rmse"] - mediated_metrics["rmse"], 6),
            "direct_group_metrics": _group_metrics(validation, direct_predictions, "split"),
            "mediated_group_metrics": _group_metrics(validation, mediated_predictions, "split"),
        }
        coefficients = {
            "direct": {
                name: round(value, 6)
                for name, value in zip(["intercept", *direct_features], direct_coefficients, strict=True)
            },
            "mediated": {
                name: round(value, 6)
                for name, value in zip(["intercept", *mediated_features], mediated_coefficients, strict=True)
            },
            "random_mediator": {
                name: round(value, 6)
                for name, value in zip(["intercept", *mediated_features], random_coefficients, strict=True)
            },
        }
        raw_payloads: dict[str, Any] = {
            "comparison": {
                "schema_version": 1,
                "model": "M3",
                "status": "VALID",
                "target_values_exposed": False,
                "identification_status": config["identification_status"],
                **comparison,
            },
            "pairing": pairing,
            "identification": identification,
            "uncertainty": uncertainty,
            "coefficients": coefficients,
            "failures": {"schema_version": 1, "status": "VALID", "failures": []},
        }
        resume_key = _sha256(_canonical(raw_payloads))
        self.output_root.mkdir(parents=True, exist_ok=True)
        paths = {
            "comparison": self.output_root / "m3_comparison.json",
            "pairing": self.output_root / "pairing_audit.json",
            "identification": self.output_root / "identification_audit.json",
            "uncertainty": self.output_root / "uncertainty_propagation.json",
            "coefficients": self.output_root / "m3_coefficients.json",
            "failures": self.output_root / "failure_ledger.json",
            "receipt": self.output_root / "m3_receipt.json",
            "log": self.output_root / "m3_log.json",
            "manifest": self.output_root / "m3_manifest.json",
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
            "model": "M3",
            "status": "VALID",
            "fixture": True,
            "pairs": len(pairs),
            "train": len(train),
            "validation": len(validation),
            "identification_status": config["identification_status"],
            "causal_claim_permitted": False,
            "direct_rmse": direct_metrics["rmse"],
            "mediated_rmse": mediated_metrics["rmse"],
            "random_mediator_rmse": random_metrics["rmse"],
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
                    {"event": "T056_T062_T067_T069_inputs_verified", "pairs": len(pairs)},
                    {"event": "paired_unit_audit_passed", "cross_split_pairs": 0},
                    {"event": "direct_mediated_random_control_completed", "models": 3},
                    {"event": "uncertainty_propagated", "method": "quadrature"},
                    {
                        "event": "causal_identification_downgraded",
                        "status": config["identification_status"],
                    },
                ],
            }
        )
        payload_bytes["manifest"] = _canonical(
            {
                "schema_version": 1,
                "model": "M3",
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
                raise M3Error("existing M3 receipt differs from rerun")
            for name, payload in payload_bytes.items():
                if paths[name].read_bytes() != payload:
                    raise M3Error(f"existing M3 artifact differs: {name}")
            resumed = 1
        else:
            for name, payload in payload_bytes.items():
                paths[name].write_bytes(payload)
            resumed = 0
        return M3Summary(
            pairs=len(pairs),
            train=len(train),
            validation=len(validation),
            identification_status=str(config["identification_status"]),
            direct_rmse=float(direct_metrics["rmse"]),
            mediated_rmse=float(mediated_metrics["rmse"]),
            resumed=resumed,
            receipt_path=paths["receipt"],
        )
