"""Build leakage-safe BioInterfaceBench development task instances."""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class BenchmarkBuildError(RuntimeError):
    """Raised when benchmark instance construction violates a contract."""


@dataclass(frozen=True)
class BenchmarkBuildSummary:
    """Summary of one deterministic benchmark build."""

    instances: int
    families: int
    primary_families: int
    pilot_families: int
    train: int
    validation: int
    missingness_mean: float
    resumed: int
    receipt_path: Path


_HASH_RE = re.compile(r"^[0-9a-f]{64}$")


def _canonical(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    ).encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise BenchmarkBuildError(f"{label} must be an object")
    return dict(value)


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise BenchmarkBuildError(f"{label} must be a non-empty string")
    return value.strip()


class BenchmarkInstanceWorkflow:
    """Validate a sanitized fixture and emit public/hidden benchmark artifacts."""

    def __init__(
        self,
        root: Path,
        *,
        fixture_path: Path | None = None,
        output_root: Path | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.fixture_path = fixture_path or (
            self.root / "tests/fixtures/benchmark/benchmark_fixture.json"
        )
        self.output_root = output_root or self.root / "reports/benchmark/instances"

    def _load_fixture(self) -> dict[str, Any]:
        try:
            fixture = json.loads(self.fixture_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise BenchmarkBuildError(f"cannot load benchmark fixture: {exc}") from exc
        data = _mapping(fixture, "benchmark fixture")
        if data.get("schema_version") != 1 or data.get("mode") != "benchmark_build_dev":
            raise BenchmarkBuildError("benchmark fixture schema or mode is invalid")
        if not isinstance(data.get("inputs"), list):
            raise BenchmarkBuildError("benchmark inputs must be a list")
        rules = _mapping(data.get("rules"), "benchmark rules")
        if not isinstance(rules.get("task_families"), list):
            raise BenchmarkBuildError("benchmark task families must be a list")
        if not isinstance(rules.get("minimum_instances_per_family"), int):
            raise BenchmarkBuildError("benchmark minimum size must be an integer")
        if rules["minimum_instances_per_family"] < 1:
            raise BenchmarkBuildError("benchmark minimum size must be positive")
        if not isinstance(rules.get("public_forbidden_fields"), list):
            raise BenchmarkBuildError("benchmark forbidden fields must be a list")
        if not isinstance(data.get("instances"), list):
            raise BenchmarkBuildError("benchmark instances must be a list")
        return data

    def _verify_inputs(self, fixture: Mapping[str, Any]) -> dict[str, Any]:
        required = {
            "T048 Gold-auto manifest",
            "T056 corona module matrix",
            "T062 modality links",
            "T065 split manifest",
        }
        loaded: dict[str, Any] = {}
        for value in fixture["inputs"]:
            row = _mapping(value, "benchmark input")
            label = _string(row.get("label"), "input label")
            relative = _string(row.get("path"), "input path")
            path = (self.root / relative).resolve(strict=True)
            try:
                path.relative_to(self.root)
            except ValueError as exc:
                raise BenchmarkBuildError("benchmark input escaped repository") from exc
            expected = _string(row.get("sha256"), "input checksum")
            observed = _sha256(path.read_bytes())
            if observed != expected:
                raise BenchmarkBuildError(f"benchmark input checksum differs: {label}")
            try:
                loaded[label] = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                raise BenchmarkBuildError(f"cannot load benchmark input: {label}") from exc
        if set(loaded) != required:
            raise BenchmarkBuildError("benchmark inputs do not match T048/T056/T062/T065 contract")
        split_manifest = _mapping(loaded["T065 split manifest"], "split manifest")
        if split_manifest.get("status") != "FROZEN_DEV":
            raise BenchmarkBuildError("T065 split manifest is not frozen")
        if not isinstance(split_manifest.get("rows"), list) or not split_manifest["rows"]:
            raise BenchmarkBuildError("T065 split manifest has no rows")
        return loaded

    @staticmethod
    def _find_forbidden(value: Any, forbidden: set[str], path: str = "public_input") -> list[str]:
        found: list[str] = []
        if isinstance(value, Mapping):
            for key, child in value.items():
                key_text = str(key)
                child_path = f"{path}.{key_text}"
                if key_text in forbidden:
                    found.append(child_path)
                found.extend(
                    BenchmarkInstanceWorkflow._find_forbidden(child, forbidden, child_path)
                )
        elif isinstance(value, list):
            for index, child in enumerate(value):
                found.extend(
                    BenchmarkInstanceWorkflow._find_forbidden(child, forbidden, f"{path}[{index}]")
                )
        return found

    def _validate_instances(
        self, fixture: Mapping[str, Any], inputs: Mapping[str, Any]
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
        rules = _mapping(fixture["rules"], "benchmark rules")
        families = [_string(value, "task family") for value in rules["task_families"]]
        if len(families) != len(set(families)):
            raise BenchmarkBuildError("benchmark task families contain duplicates")
        forbidden = {
            _string(value, "forbidden public field") for value in rules["public_forbidden_fields"]
        }
        minimum = int(rules["minimum_instances_per_family"])
        split_manifest = _mapping(inputs["T065 split manifest"], "split manifest")
        split_rows = [_mapping(row, "split row") for row in split_manifest["rows"]]
        allowed_groups = {
            _string(row.get("paper_family_group_key"), "split paper-family group key")
            for row in split_rows
        }
        group_splits = {
            _string(row.get("paper_family_group_key"), "split paper-family group key"): _string(
                row.get("split"), "split label"
            )
            for row in split_rows
        }
        required_fields = {
            "instance_id",
            "family",
            "split",
            "group_key",
            "public_input",
            "hidden_target_ref",
            "hidden_target_sha256",
            "missingness",
        }
        seen_ids: set[str] = set()
        seen_refs: set[str] = set()
        seen_hashes: set[str] = set()
        counts = {family: 0 for family in families}
        records: list[dict[str, Any]] = []
        hidden: list[dict[str, Any]] = []
        for value in fixture["instances"]:
            instance = _mapping(value, "benchmark instance")
            if set(instance) != required_fields:
                raise BenchmarkBuildError("benchmark instance fields do not match schema")
            instance_id = _string(instance.get("instance_id"), "instance ID")
            family = _string(instance.get("family"), "instance family")
            split = _string(instance.get("split"), "instance split")
            group_key = _string(instance.get("group_key"), "instance group key")
            if family not in counts:
                raise BenchmarkBuildError(f"unknown task family: {family}")
            if split not in {"train", "validation"}:
                raise BenchmarkBuildError(f"invalid benchmark split: {split}")
            if group_key not in allowed_groups:
                raise BenchmarkBuildError(
                    f"group key is absent from T065 split manifest: {group_key}"
                )
            if group_splits[group_key] != split:
                raise BenchmarkBuildError(f"group key split mismatch: {group_key}")
            public_input = _mapping(instance.get("public_input"), "public input")
            forbidden_paths = self._find_forbidden(public_input, forbidden)
            if forbidden_paths:
                raise BenchmarkBuildError(
                    "public input contains forbidden target fields: " + ", ".join(forbidden_paths)
                )
            hidden_ref = _string(instance.get("hidden_target_ref"), "hidden target reference")
            hidden_hash = _string(instance.get("hidden_target_sha256"), "hidden target hash")
            if not _HASH_RE.fullmatch(hidden_hash):
                raise BenchmarkBuildError(
                    f"hidden target hash is not lowercase sha256: {instance_id}"
                )
            missingness = instance.get("missingness")
            if isinstance(missingness, bool) or not isinstance(missingness, int | float):
                raise BenchmarkBuildError(f"missingness is not numeric: {instance_id}")
            if not math.isfinite(float(missingness)) or not 0.0 <= float(missingness) <= 1.0:
                raise BenchmarkBuildError(f"missingness is outside [0, 1]: {instance_id}")
            if instance_id in seen_ids or hidden_ref in seen_refs or hidden_hash in seen_hashes:
                raise BenchmarkBuildError(f"benchmark identity is duplicated: {instance_id}")
            seen_ids.add(instance_id)
            seen_refs.add(hidden_ref)
            seen_hashes.add(hidden_hash)
            counts[family] += 1
            records.append(
                {
                    "instance_id": instance_id,
                    "family": family,
                    "split": split,
                    "group_key": group_key,
                    "public_input": public_input,
                    "missingness": float(missingness),
                }
            )
            hidden.append(
                {
                    "instance_id": instance_id,
                    "family": family,
                    "split": split,
                    "hidden_target_ref": hidden_ref,
                    "hidden_target_sha256": hidden_hash,
                }
            )
        if not records:
            raise BenchmarkBuildError("benchmark contains no instances")
        underpowered = [family for family in families if counts[family] < minimum]
        coverage = {
            "schema_version": 1,
            "status": "VALID",
            "minimum_instances_per_family": minimum,
            "families": [
                {
                    "family": family,
                    "instances": counts[family],
                    "train": sum(
                        row["family"] == family and row["split"] == "train" for row in records
                    ),
                    "validation": sum(
                        row["family"] == family and row["split"] == "validation" for row in records
                    ),
                    "tier": "PILOT_UNDERPOWERED" if family in underpowered else "PRIMARY",
                    "reason": "below_minimum_instance_count" if family in underpowered else None,
                    "missingness_mean": round(
                        sum(row["missingness"] for row in records if row["family"] == family)
                        / counts[family],
                        6,
                    )
                    if counts[family]
                    else None,
                }
                for family in families
            ],
            "underpowered_families": underpowered,
            "primary_families": [family for family in families if family not in underpowered],
            "missingness_mean": round(sum(row["missingness"] for row in records) / len(records), 6),
            "target_values_exposed": False,
            "public_forbidden_fields": [],
            "group_keys_attached": all(bool(row["group_key"]) for row in records),
        }
        return records, hidden, coverage

    def run(self, *, dev: bool = True, fixture: bool = True) -> BenchmarkBuildSummary:
        """Build benchmark instances from the offline development fixture."""
        if not dev:
            raise BenchmarkBuildError("--dev is required for benchmark build")
        if not fixture:
            raise BenchmarkBuildError("--fixture is required for benchmark build")
        data = self._load_fixture()
        inputs = self._verify_inputs(data)
        records, hidden, coverage = self._validate_instances(data, inputs)
        primary = coverage["primary_families"]
        pilot = coverage["underpowered_families"]
        public_payload = {
            "schema_version": 1,
            "benchmark_version": "biointerfacebench-dev-v1",
            "status": "VALID",
            "target_values_exposed": False,
            "instances": [
                {**row, "tier": "PRIMARY" if row["family"] in primary else "PILOT_UNDERPOWERED"}
                for row in records
            ],
        }
        hidden_payload = {
            "schema_version": 1,
            "benchmark_version": "biointerfacebench-dev-v1",
            "status": "LOCKED_REGISTRY_METADATA_ONLY",
            "target_values_exposed": False,
            "targets": hidden,
        }
        raw_payloads: dict[str, Any] = {
            "public": public_payload,
            "hidden": hidden_payload,
            "coverage": coverage,
        }
        resume_key = _sha256(_canonical(raw_payloads))
        self.output_root.mkdir(parents=True, exist_ok=True)
        paths = {
            "public": self.output_root / "public_instances.json",
            "hidden": self.output_root / "hidden_target_registry.json",
            "coverage": self.output_root / "coverage_audit.json",
            "receipt": self.output_root / "processing_receipt.json",
            "log": self.output_root / "processing_log.json",
            "manifest": self.output_root / "processing_manifest.json",
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
            "status": "VALID",
            "fixture": True,
            "dev": True,
            "instances": len(records),
            "families": len(coverage["families"]),
            "primary_families": len(primary),
            "pilot_families": len(pilot),
            "train": sum(row["split"] == "train" for row in records),
            "validation": sum(row["split"] == "validation" for row in records),
            "missingness_mean": coverage["missingness_mean"],
            "target_values_exposed": False,
            "public_forbidden_fields": [],
            "input_hashes": {
                _string(_mapping(item, "benchmark input").get("label"), "input label"): _string(
                    _mapping(item, "benchmark input").get("sha256"), "input checksum"
                )
                for item in data["inputs"]
            },
            "resume_key": resume_key,
            "artifacts": artifact_records,
        }
        payload_bytes["receipt"] = _canonical(receipt)
        log = {
            "schema_version": 1,
            "resume_key": resume_key,
            "events": [
                {"event": "T048_T056_T062_T065_inputs_verified", "inputs": len(data["inputs"])},
                {"event": "public_hidden_target_separation_verified", "exposed": False},
                {
                    "event": "task_family_coverage_audited",
                    "primary": len(primary),
                    "pilot": len(pilot),
                },
                {"event": "group_keys_and_missingness_validated", "instances": len(records)},
            ],
        }
        payload_bytes["log"] = _canonical(log)
        manifest = {
            "schema_version": 1,
            "status": "VALID",
            "resume_supported": True,
            "resume_key": resume_key,
            "instances": len(records),
            "primary_families": primary,
            "pilot_families": pilot,
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
        payload_bytes["manifest"] = _canonical(manifest)
        existing_receipt = paths["receipt"].read_bytes() if paths["receipt"].exists() else None
        if existing_receipt is not None:
            if existing_receipt != payload_bytes["receipt"]:
                raise BenchmarkBuildError("existing benchmark receipt differs from rerun")
            for name, payload in payload_bytes.items():
                if paths[name].read_bytes() != payload:
                    raise BenchmarkBuildError(f"existing benchmark artifact differs: {name}")
            resumed = 1
        else:
            for name, payload in payload_bytes.items():
                paths[name].write_bytes(payload)
            resumed = 0
        return BenchmarkBuildSummary(
            instances=len(records),
            families=len(coverage["families"]),
            primary_families=len(primary),
            pilot_families=len(pilot),
            train=sum(row["split"] == "train" for row in records),
            validation=sum(row["split"] == "validation" for row in records),
            missingness_mean=float(coverage["missingness_mean"]),
            resumed=resumed,
            receipt_path=paths["receipt"],
        )
