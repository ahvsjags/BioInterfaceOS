"""Freeze a versioned, leakage-safe BioInterfaceBench development release."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class BenchmarkFreezeError(RuntimeError):
    """Raised when a benchmark development freeze cannot be made safely."""


@dataclass(frozen=True)
class BenchmarkFreezeSummary:
    """Summary of one immutable benchmark development freeze."""

    release_id: str
    semantic_version: str
    instances: int
    train: int
    validation: int
    graders: int
    baselines: int
    representations: int
    public_hidden_separated: bool
    negative_controls_clean: bool
    resumed: int
    receipt_path: Path


def _canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise BenchmarkFreezeError(f"{label} must be an object")
    return dict(value)


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise BenchmarkFreezeError(f"{label} must be a non-empty string")
    return value.strip()


class BenchmarkFreezeWorkflow:
    """Verify all benchmark layers and atomically emit a versioned release."""

    REQUIRED_INPUTS = (
        "T067 benchmark instances receipt",
        "T068 benchmark graders receipt",
        "T069 statistical baselines receipt",
        "T070 representation baselines receipt",
        "T065 frozen development split manifest",
        "T102 negative-controls receipt",
    )

    def __init__(
        self,
        root: Path,
        *,
        fixture_path: Path | None = None,
        output_root: Path | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.fixture_path = fixture_path or self.root / "tests/fixtures/benchmark/freeze_dev_fixture.json"
        self.output_root = output_root or (self.root / "reports/benchmark/releases/biointerfacebench-dev-v1.0.0")

    def _load_fixture(self) -> dict[str, Any]:
        try:
            data = json.loads(self.fixture_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise BenchmarkFreezeError(f"cannot load freeze fixture: {exc}") from exc
        fixture = _mapping(data, "freeze fixture")
        if fixture.get("schema_version") != 1 or fixture.get("mode") != "benchmark_freeze_dev":
            raise BenchmarkFreezeError("freeze fixture schema or mode is invalid")
        prereg = _mapping(fixture.get("preregistration"), "freeze preregistration")
        if prereg.get("schema_version") != 1:
            raise BenchmarkFreezeError("freeze preregistration schema is invalid")
        if prereg.get("release_id") != "biointerfacebench-dev-v1.0.0":
            raise BenchmarkFreezeError("development release id is not frozen")
        if prereg.get("semantic_version") != "1.0.0":
            raise BenchmarkFreezeError("semantic version is not frozen")
        if prereg.get("target_values_exposed") is not False:
            raise BenchmarkFreezeError("freeze target exposure flag must be false")
        if prereg.get("public_hidden_separation") is not True:
            raise BenchmarkFreezeError("public/hidden separation is not required")
        if not fixture.get("inputs"):
            raise BenchmarkFreezeError("freeze inputs are missing")
        if not isinstance(fixture.get("inputs"), list):
            raise BenchmarkFreezeError("freeze inputs must be a list")
        if set(fixture["layers"]) != {"public_instances", "hidden_registry_metadata"}:
            raise BenchmarkFreezeError("freeze layers are incomplete")
        return fixture

    def _path(self, relative: Any, label: str) -> Path:
        candidate = (self.root / _string(relative, label)).resolve(strict=True)
        if not candidate.is_relative_to(self.root):
            raise BenchmarkFreezeError(f"{label} escaped repository")
        return candidate

    def _load_json(self, path: Path, label: str) -> dict[str, Any]:
        try:
            return _mapping(json.loads(path.read_text(encoding="utf-8")), label)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise BenchmarkFreezeError(f"cannot load {label}: {exc}") from exc

    def _verify_inputs(self, fixture: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
        rows = [_mapping(value, "freeze input") for value in fixture["inputs"]]
        if {row.get("label") for row in rows} != set(self.REQUIRED_INPUTS):
            raise BenchmarkFreezeError("freeze input set does not match preregistration")
        loaded: dict[str, dict[str, Any]] = {}
        for row in rows:
            label = _string(row.get("label"), "freeze input label")
            path = self._path(row.get("path"), f"{label} path")
            raw = path.read_bytes()
            if _sha256(raw) != _string(row.get("sha256"), f"{label} checksum"):
                raise BenchmarkFreezeError(f"freeze input checksum differs: {label}")
            payload = self._load_json(path, label)
            expected_status = _mapping(fixture["preregistration"]["required_statuses"], "statuses")[label]
            if payload.get("status") != expected_status:
                raise BenchmarkFreezeError(f"{label} status is not {expected_status}")
            if label != "T065 frozen development split manifest" and payload.get("target_values_exposed") is not False:
                raise BenchmarkFreezeError(f"{label} exposes target values")
            loaded[label] = payload
        negative = loaded["T102 negative-controls receipt"]
        if negative.get("strict_pass") is not True or negative.get("critical_leaks") != 0:
            raise BenchmarkFreezeError("T102 negative-control gate is not clean")
        split = loaded["T065 frozen development split manifest"]
        if not isinstance(split.get("rows"), list) or not split["rows"]:
            raise BenchmarkFreezeError("frozen development split has no rows")
        return loaded

    def _verify_layers(self, fixture: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
        layers: dict[str, dict[str, Any]] = {}
        for name, value in fixture["layers"].items():
            row = _mapping(value, f"{name} layer")
            path = self._path(row.get("path"), f"{name} layer path")
            raw = path.read_bytes()
            if _sha256(raw) != _string(row.get("sha256"), f"{name} layer checksum"):
                raise BenchmarkFreezeError(f"{name} layer checksum differs")
            layers[name] = self._load_json(path, f"{name} layer")
        public = layers["public_instances"]
        hidden = layers["hidden_registry_metadata"]
        if public.get("target_values_exposed") is not False or hidden.get("target_values_exposed") is not False:
            raise BenchmarkFreezeError("benchmark layer target exposure flag is invalid")
        public_rows = public.get("instances")
        hidden_rows = hidden.get("targets")
        if not isinstance(public_rows, list) or not isinstance(hidden_rows, list):
            raise BenchmarkFreezeError("benchmark layer records are missing")
        if len(public_rows) != len(hidden_rows):
            raise BenchmarkFreezeError("public and hidden layer counts differ")
        public_ids = {row.get("instance_id") for row in public_rows if isinstance(row, dict)}
        hidden_ids = {row.get("instance_id") for row in hidden_rows if isinstance(row, dict)}
        if public_ids != hidden_ids or None in public_ids:
            raise BenchmarkFreezeError("public and hidden instance ids differ")
        for row in public_rows:
            if not isinstance(row, dict):
                raise BenchmarkFreezeError("public instance row is invalid")
            for key in row:
                if key in {"target", "hidden_target_ref", "hidden_target_sha256"}:
                    raise BenchmarkFreezeError("hidden target field leaked into public layer")
        return layers

    def run(self, *, fixture: bool = True) -> BenchmarkFreezeSummary:
        """Freeze the development benchmark, refusing mutable or unsafe inputs."""
        if not fixture:
            raise BenchmarkFreezeError("--fixture is required for benchmark freeze")
        fixture_data = self._load_fixture()
        inputs = self._verify_inputs(fixture_data)
        layers = self._verify_layers(fixture_data)
        prereg = _mapping(fixture_data["preregistration"], "freeze preregistration")
        instances_receipt = inputs["T067 benchmark instances receipt"]
        graders_receipt = inputs["T068 benchmark graders receipt"]
        baselines_receipt = inputs["T069 statistical baselines receipt"]
        representations_receipt = inputs["T070 representation baselines receipt"]
        public = layers["public_instances"]
        split_counts = {
            "train": sum(row.get("split") == "train" for row in public["instances"]),
            "validation": sum(row.get("split") == "validation" for row in public["instances"]),
        }
        input_records = []
        for row in fixture_data["inputs"]:
            input_records.append(
                {
                    "label": row["label"],
                    "path": row["path"],
                    "sha256": row["sha256"],
                    "status": inputs[row["label"]]["status"],
                }
            )
        layer_records = {}
        for name, row in fixture_data["layers"].items():
            path = self._path(row["path"], f"{name} layer path")
            layer_records[name] = {
                "path": row["path"],
                "sha256": row["sha256"],
                "bytes": path.stat().st_size,
                "records": len(layers[name].get("instances", layers[name].get("targets", []))),
            }
        release_manifest = {
            "schema_version": 1,
            "status": "FROZEN_DEV",
            "release_id": prereg["release_id"],
            "semantic_version": prereg["semantic_version"],
            "immutable": True,
            "target_values_exposed": False,
            "public_hidden_separation": True,
            "inputs": input_records,
            "layers": layer_records,
            "benchmark": {
                "instances": instances_receipt["instances"],
                "families": instances_receipt["families"],
                "train": split_counts["train"],
                "validation": split_counts["validation"],
                "graders": graders_receipt["cases"],
                "baselines": baselines_receipt["baselines"],
                "representations": representations_receipt["baselines"],
            },
            "negative_controls": {
                "status": inputs["T102 negative-controls receipt"]["status"],
                "strict_pass": True,
                "critical_leaks": 0,
            },
        }
        card = (
            f"# BioInterfaceBench development release {prereg['semantic_version']}\n\n"
            f"Release ID: `{prereg['release_id']}`  \n"
            "Status: `FROZEN_DEV`  \n"
            "Target values exposed: `false`  \n"
            "Public/hidden separation: `true`\n\n"
            "## Frozen benchmark\n\n"
            f"- Instances: {instances_receipt['instances']} across "
            f"{instances_receipt['families']} families\n"
            f"- Development split: {split_counts['train']} train / "
            f"{split_counts['validation']} validation\n"
            f"- Grader cases: {graders_receipt['cases']}\n"
            f"- Statistical baselines: {baselines_receipt['baselines']}\n"
            f"- Representation baselines: {representations_receipt['baselines']}\n"
            "- Hidden layer: metadata-only registry; target values remain inaccessible\n\n"
            "## Robustness gate\n\n"
            "T102 negative controls passed strict mode with zero critical leakage.\n"
            "All recorded inputs are checksum-pinned; a corrected benchmark requires a new "
            "semantic version.\n"
        )
        freeze_manifest = {
            "schema_version": 1,
            "status": "FROZEN_DEV",
            "release_id": prereg["release_id"],
            "semantic_version": prereg["semantic_version"],
            "release_manifest": "release_manifest.json",
            "benchmark_card": "benchmark_card.md",
            "target_values_exposed": False,
            "immutable": True,
            "inputs": input_records,
            "layers": layer_records,
        }
        release_bytes = _canonical(release_manifest)
        card_bytes = card.encode("utf-8")
        freeze_bytes = _canonical(freeze_manifest)
        resume_key = _sha256(release_bytes + card_bytes + freeze_bytes)
        receipt = {
            "schema_version": 1,
            "status": "VALID",
            "release_id": prereg["release_id"],
            "semantic_version": prereg["semantic_version"],
            "target_values_exposed": False,
            "public_hidden_separation": True,
            "immutable": True,
            "resume_key": resume_key,
            "artifacts": {
                "release_manifest": {
                    "path": "release_manifest.json",
                    "sha256": _sha256(release_bytes),
                    "bytes": len(release_bytes),
                },
                "benchmark_card": {
                    "path": "benchmark_card.md",
                    "sha256": _sha256(card_bytes),
                    "bytes": len(card_bytes),
                },
                "freeze_manifest": {
                    "path": "freeze_manifest.json",
                    "sha256": _sha256(freeze_bytes),
                    "bytes": len(freeze_bytes),
                },
            },
        }
        receipt_bytes = _canonical(receipt)
        self.output_root.mkdir(parents=True, exist_ok=True)
        payloads = {
            "release_manifest.json": release_bytes,
            "benchmark_card.md": card_bytes,
            "freeze_manifest.json": freeze_bytes,
            "freeze_receipt.json": receipt_bytes,
        }
        resumed = 0
        for name, payload in payloads.items():
            path = self.output_root / name
            if path.exists():
                if path.read_bytes() != payload:
                    raise BenchmarkFreezeError(f"immutable release artifact differs: {name}")
                resumed = 1
            else:
                path.write_bytes(payload)
        return BenchmarkFreezeSummary(
            release_id=prereg["release_id"],
            semantic_version=prereg["semantic_version"],
            instances=instances_receipt["instances"],
            train=split_counts["train"],
            validation=split_counts["validation"],
            graders=graders_receipt["cases"],
            baselines=baselines_receipt["baselines"],
            representations=representations_receipt["baselines"],
            public_hidden_separated=True,
            negative_controls_clean=True,
            resumed=resumed,
            receipt_path=self.output_root / "freeze_receipt.json",
        )
