"""Representation baselines with explicit structure-coverage accounting."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from biointerfaceos.benchmark_baselines import (
    _bootstrap_ci,
    _canonical,
    _group_metrics,
    _hash_bucket,
    _mapping,
    _number,
    _predict_linear,
    _regression_metrics,
    _ridge_fit,
    _sha256,
    _string,
)


class BenchmarkRepresentationError(RuntimeError):
    """Raised when a representation baseline contract is invalid."""


@dataclass(frozen=True)
class BenchmarkRepresentationSummary:
    """Summary of one representation-baseline run."""

    baselines: int
    successful: int
    validation_instances: int
    best_rmse: float
    resumed: int
    receipt_path: Path


def _mean(values: list[float]) -> float:
    if not values:
        raise BenchmarkRepresentationError("cannot average an empty list")
    return sum(values) / len(values)


class BenchmarkRepresentationWorkflow:
    """Run descriptor, fingerprint, text, and polymer-embedding baselines."""

    def __init__(
        self,
        root: Path,
        *,
        fixture_path: Path | None = None,
        output_root: Path | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.fixture_path = fixture_path or (self.root / "tests/fixtures/benchmark/representation_fixture.json")
        self.instances_path = self.root / "reports/benchmark/instances/public_instances.json"
        self.baseline_fixture_path = self.root / "tests/fixtures/benchmark/baseline_fixture.json"
        self.output_root = output_root or self.root / "reports/benchmark/representations"

    def _load_fixture(self) -> dict[str, Any]:
        try:
            data = _mapping(
                json.loads(self.fixture_path.read_text(encoding="utf-8")),
                "representation fixture",
            )
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise BenchmarkRepresentationError(f"cannot load representation fixture: {exc}") from exc
        if data.get("schema_version") != 1 or data.get("mode") != "benchmark_baselines_representation":
            raise BenchmarkRepresentationError("representation fixture schema or mode is invalid")
        if data.get("target_values_are_fixture_only") is not True:
            raise BenchmarkRepresentationError("representation targets must be fixture-only")
        if not isinstance(data.get("inputs"), list) or not isinstance(data.get("representations"), list):
            raise BenchmarkRepresentationError("representation inputs/rows are invalid")
        config = _mapping(data.get("config"), "representation config")
        if config.get("group") != "representation" or config.get("seed") != 23:
            raise BenchmarkRepresentationError("representation config is not frozen")
        if config.get("bootstrap_samples") != 128:
            raise BenchmarkRepresentationError("representation bootstrap count is not frozen")
        return data

    def _verify_inputs(self, fixture: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
        required = {
            "T067 public instances": self.instances_path,
            "T069 baseline fixture": self.baseline_fixture_path,
        }
        seen: set[str] = set()
        loaded: dict[str, Any] = {}
        for value in fixture["inputs"]:
            row = _mapping(value, "representation input")
            label = _string(row.get("label"), "representation input label")
            if label not in required:
                raise BenchmarkRepresentationError(f"unexpected representation input: {label}")
            path = (self.root / _string(row.get("path"), "representation input path")).resolve(strict=True)
            if path != required[label].resolve(strict=True):
                raise BenchmarkRepresentationError(f"representation input path mismatch: {label}")
            if _sha256(path.read_bytes()) != _string(row.get("sha256"), "representation input checksum"):
                raise BenchmarkRepresentationError(f"representation input checksum differs: {label}")
            try:
                loaded[label] = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                raise BenchmarkRepresentationError(f"cannot load representation input: {label}") from exc
            seen.add(label)
        if seen != set(required):
            raise BenchmarkRepresentationError("representation inputs do not match T067/T069 contract")
        public = _mapping(loaded["T067 public instances"], "public instances")
        baseline_fixture = _mapping(loaded["T069 baseline fixture"], "baseline fixture")
        if public.get("status") != "VALID" or public.get("target_values_exposed") is not False:
            raise BenchmarkRepresentationError("public instances are not target-isolated")
        if baseline_fixture.get("target_values_are_fixture_only") is not True:
            raise BenchmarkRepresentationError("baseline fixture targets are not fixture-only")
        return public, baseline_fixture

    @staticmethod
    def _targets(baseline_fixture: Mapping[str, Any], public: Mapping[str, Any]) -> dict[str, float]:
        public_ids = {
            _string(_mapping(row, "public instance").get("instance_id"), "public instance ID")
            for row in public["instances"]
        }
        targets: dict[str, float] = {}
        for value in baseline_fixture["targets"]:
            row = _mapping(value, "baseline target")
            instance_id = _string(row.get("instance_id"), "baseline target instance ID")
            if instance_id not in public_ids or instance_id in targets:
                raise BenchmarkRepresentationError(f"baseline target identity is invalid: {instance_id}")
            targets[instance_id] = _number(row.get("target"), "baseline target")
        if set(targets) != public_ids:
            raise BenchmarkRepresentationError("representation targets do not cover public instances")
        return targets

    @staticmethod
    def _representation_rows(
        fixture: Mapping[str, Any], public: Mapping[str, Any], targets: Mapping[str, float]
    ) -> list[dict[str, Any]]:
        public_by_id = {
            _string(_mapping(row, "public instance").get("instance_id"), "public instance ID"): _mapping(
                row, "public instance"
            )
            for row in public["instances"]
        }
        required = {
            "instance_id",
            "material_text",
            "structure_smiles",
            "descriptor",
            "fingerprint",
            "polymer_embedding",
        }
        seen: set[str] = set()
        rows: list[dict[str, Any]] = []
        for value in fixture["representations"]:
            representation = _mapping(value, "representation row")
            if set(representation) != required:
                raise BenchmarkRepresentationError("representation row fields do not match schema")
            instance_id = _string(representation.get("instance_id"), "representation instance ID")
            if instance_id not in public_by_id or instance_id in seen:
                raise BenchmarkRepresentationError(f"representation identity is invalid: {instance_id}")
            text = representation.get("material_text")
            if not isinstance(text, str) or not text.strip():
                raise BenchmarkRepresentationError(f"material text is missing: {instance_id}")
            descriptor = representation.get("descriptor")
            if descriptor is not None and (
                not isinstance(descriptor, list)
                or len(descriptor) != 3
                or any(not isinstance(number, int | float) for number in descriptor)
            ):
                raise BenchmarkRepresentationError(f"descriptor shape is invalid: {instance_id}")
            fingerprint = representation.get("fingerprint")
            if fingerprint is not None and (
                not isinstance(fingerprint, str) or len(fingerprint) != 8 or any(bit not in "01" for bit in fingerprint)
            ):
                raise BenchmarkRepresentationError(f"fingerprint shape is invalid: {instance_id}")
            embedding = representation.get("polymer_embedding")
            if embedding is not None and (
                not isinstance(embedding, list)
                or len(embedding) != 3
                or any(not isinstance(number, int | float) for number in embedding)
            ):
                raise BenchmarkRepresentationError(f"polymer embedding shape is invalid: {instance_id}")
            public_row = public_by_id[instance_id]
            rows.append(
                {
                    "instance_id": instance_id,
                    "family": _string(public_row.get("family"), "public family"),
                    "split": _string(public_row.get("split"), "public split"),
                    "group_key": _string(public_row.get("group_key"), "public group key"),
                    "missingness": _number(public_row.get("missingness"), "instance missingness"),
                    "target": targets[instance_id],
                    "material_text": text.strip(),
                    "structure_smiles": representation.get("structure_smiles"),
                    "descriptor": descriptor,
                    "fingerprint": fingerprint,
                    "polymer_embedding": embedding,
                }
            )
            seen.add(instance_id)
        if seen != set(public_by_id):
            raise BenchmarkRepresentationError("representation rows do not cover public instances")
        return rows

    @staticmethod
    def _vector(row: Mapping[str, Any], name: str) -> tuple[list[float], bool]:
        if name == "text":
            text = _string(row["material_text"], "material text")
            tokens = text.lower().split()
            return [
                _mean([_hash_bucket(token) for token in tokens]),
                min(len(text) / 32.0, 1.0),
                min(len(tokens) / 8.0, 1.0),
            ], True
        value = row[name]
        if value is None:
            return [0.0, 0.0, 0.0], False
        if name == "fingerprint":
            return [float(bit) for bit in str(value)[:3]], True
        if name in {"descriptor", "polymer_embedding"}:
            return [float(number) for number in value], True
        raise BenchmarkRepresentationError(f"unknown representation: {name}")

    def run(self, *, group: str = "representation") -> BenchmarkRepresentationSummary:
        """Run representation baselines over the complete frozen split."""
        if group != "representation":
            raise BenchmarkRepresentationError("--group representation is required")
        fixture = self._load_fixture()
        public, baseline_fixture = self._verify_inputs(fixture)
        targets = self._targets(baseline_fixture, public)
        rows = self._representation_rows(fixture, public, targets)
        train = [row for row in rows if row["split"] == "train"]
        validation = [row for row in rows if row["split"] == "validation"]
        seed = int(_mapping(fixture["config"], "representation config")["seed"])
        bootstrap_samples = int(_mapping(fixture["config"], "representation config")["bootstrap_samples"])
        names = ("descriptor", "fingerprint", "text", "polymer_embedding")
        predictions_by_name: dict[str, dict[str, float]] = {}
        coverage: dict[str, Any] = {}
        for name in names:
            vectors = {row["instance_id"]: self._vector(row, name) for row in rows}
            train_features = [
                [1.0, *vectors[row["instance_id"]][0], float(not vectors[row["instance_id"]][1])] for row in train
            ]
            coefficients = _ridge_fit(train_features, [row["target"] for row in train], ridge=0.1)
            predictions_by_name[name] = {
                row["instance_id"]: _predict_linear(
                    coefficients,
                    [
                        1.0,
                        *vectors[row["instance_id"]][0],
                        float(not vectors[row["instance_id"]][1]),
                    ],
                )
                for row in rows
            }
            available = [row for row in rows if vectors[row["instance_id"]][1]]
            validation_available = [row for row in validation if vectors[row["instance_id"]][1]]
            coverage[name] = {
                "overall_available": len(available),
                "train_available": sum(vectors[row["instance_id"]][1] for row in train),
                "validation_available": len(validation_available),
                "validation_coverage": round(len(validation_available) / len(validation), 6),
                "full_split_primary": True,
                "missingness_indicator_used": True,
                "available_subset_reported": bool(validation_available),
                "available_subset_metrics": _regression_metrics(validation_available, predictions_by_name[name])
                if validation_available
                else None,
            }
        results: list[dict[str, Any]] = []
        for offset, name in enumerate(names):
            predictions = predictions_by_name[name]
            validation_metrics = _regression_metrics(validation, predictions)
            results.append(
                {
                    "baseline": name,
                    "status": "SUCCESS",
                    "seed": seed,
                    "config": {
                        "group": group,
                        "bootstrap_samples": bootstrap_samples,
                        "ridge": 0.1,
                        "feature_names": [
                            "feature_0",
                            "feature_1",
                            "feature_2",
                            "missing_indicator",
                        ],
                    },
                    "train_metrics": _regression_metrics(train, predictions),
                    "validation_metrics": validation_metrics,
                    "primary_ood_metric": "rmse",
                    "primary_ood_value": validation_metrics["rmse"],
                    "primary_ood_confidence_interval": _bootstrap_ci(
                        validation, predictions, seed + offset, bootstrap_samples
                    ),
                    "family_metrics": _group_metrics(validation, predictions, "family"),
                    "split_metrics": _group_metrics(validation, predictions, "split"),
                    "group_metrics": _group_metrics(validation, predictions, "group_key"),
                    "coverage": coverage[name],
                }
            )
        raw_payloads: dict[str, Any] = {
            "results": {
                "schema_version": 1,
                "benchmark_version": public["benchmark_version"],
                "group": group,
                "status": "VALID",
                "target_values_exposed": False,
                "baselines": results,
            },
            "coverage": {
                "schema_version": 1,
                "status": "VALID",
                "structure_missing_fraction": round(
                    sum(row["structure_smiles"] is None for row in rows) / len(rows), 6
                ),
                "baselines": coverage,
                "complete_case_not_primary": True,
            },
            "failures": {"schema_version": 1, "status": "VALID", "failures": []},
        }
        resume_key = _sha256(_canonical(raw_payloads))
        self.output_root.mkdir(parents=True, exist_ok=True)
        paths = {
            "results": self.output_root / "representation_results.json",
            "coverage": self.output_root / "coverage_audit.json",
            "failures": self.output_root / "failure_ledger.json",
            "receipt": self.output_root / "representation_receipt.json",
            "log": self.output_root / "representation_log.json",
            "manifest": self.output_root / "representation_manifest.json",
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
        best_rmse = min(float(result["primary_ood_value"]) for result in results)
        receipt = {
            "schema_version": 1,
            "status": "VALID",
            "fixture": True,
            "group": group,
            "baselines": len(results),
            "successful": len(results),
            "validation_instances": len(validation),
            "best_rmse": best_rmse,
            "structure_missing_fraction": raw_payloads["coverage"]["structure_missing_fraction"],
            "complete_case_not_primary": True,
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
                    {"event": "T067_T069_inputs_verified", "instances": len(rows)},
                    {
                        "event": "representation_coverage_audited",
                        "structure_missing_fraction": raw_payloads["coverage"]["structure_missing_fraction"],
                    },
                    {"event": "representation_baselines_completed", "baselines": len(results)},
                    {"event": "complete_case_bias_guard_passed", "full_split_primary": True},
                ],
            }
        )
        payload_bytes["manifest"] = _canonical(
            {
                "schema_version": 1,
                "status": "VALID",
                "resume_supported": True,
                "resume_key": resume_key,
                "group": group,
                "baselines": len(results),
                "successful": len(results),
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
                raise BenchmarkRepresentationError("existing representation receipt differs from rerun")
            for name, payload in payload_bytes.items():
                if paths[name].read_bytes() != payload:
                    raise BenchmarkRepresentationError(f"existing representation artifact differs: {name}")
            resumed = 1
        else:
            for name, payload in payload_bytes.items():
                paths[name].write_bytes(payload)
            resumed = 0
        return BenchmarkRepresentationSummary(
            baselines=len(results),
            successful=len(results),
            validation_instances=len(validation),
            best_rmse=best_rmse,
            resumed=resumed,
            receipt_path=paths["receipt"],
        )
