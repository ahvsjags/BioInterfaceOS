"""Freeze development data and model artifacts into an immutable release."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class DevelopmentReleaseFreezeError(RuntimeError):
    """Raised when a development data/model release cannot be frozen safely."""


@dataclass(frozen=True)
class DevelopmentReleaseFreezeSummary:
    """Summary of one immutable development data/model release."""

    release_id: str
    semantic_version: str
    input_count: int
    data_layers: int
    model_layers: int
    thresholds: int
    license_layers_separated: bool
    negative_controls_clean: bool
    resumed: int
    receipt_path: Path


def _canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise DevelopmentReleaseFreezeError(f"{label} must be an object")
    return dict(value)


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DevelopmentReleaseFreezeError(f"{label} must be a non-empty string")
    return value.strip()


class DevelopmentReleaseFreezeWorkflow:
    """Verify pinned data/model inputs and emit a new version without overwrite."""

    REQUIRED_INPUTS = {
        "T047 silver manifest",
        "T048 gold-auto manifest",
        "T057 PRIDE QC report",
        "T062 modality-link receipt",
        "T078 uncertainty receipt",
        "T079 multimodal receipt",
        "T102 negative-controls receipt",
        "uncertainty config",
        "multimodal config",
        "uncertainty results",
        "multimodal results",
    }

    def __init__(
        self,
        root: Path,
        *,
        fixture_path: Path | None = None,
        output_root: Path | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.fixture_path = fixture_path or self.root / "tests/fixtures/release/freeze_dev_fixture.json"
        self.output_root = output_root or (self.root / "release/dev_data_model/bioif-data-model-dev-v1.0.0")

    def _fixture(self) -> dict[str, Any]:
        try:
            fixture = _mapping(
                json.loads(self.fixture_path.read_text(encoding="utf-8")),
                "development release fixture",
            )
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise DevelopmentReleaseFreezeError(f"cannot load freeze fixture: {exc}") from exc
        if fixture.get("schema_version") != 1 or fixture.get("mode") != ("development_data_model_freeze"):
            raise DevelopmentReleaseFreezeError("development release fixture schema or mode is invalid")
        prereg = _mapping(fixture.get("preregistration"), "development preregistration")
        if prereg.get("release_id") != "bioif-data-model-dev-v1.0.0":
            raise DevelopmentReleaseFreezeError("development data/model release id is not frozen")
        if prereg.get("semantic_version") != "1.0.0":
            raise DevelopmentReleaseFreezeError("development data/model version is not frozen")
        if prereg.get("target_values_exposed") is not False:
            raise DevelopmentReleaseFreezeError("development release exposes target values")
        if not isinstance(fixture.get("inputs"), list):
            raise DevelopmentReleaseFreezeError("development release inputs must be a list")
        if {row.get("label") for row in fixture["inputs"]} != self.REQUIRED_INPUTS:
            raise DevelopmentReleaseFreezeError("development release input set is incomplete")
        layers = _mapping(prereg.get("license_layers"), "license layers")
        if layers != {
            "data_and_model_artifacts": "analysis_only",
            "configs_and_cards": "redistributable_config",
            "locked_targets": "not_included_locked_targets",
        }:
            raise DevelopmentReleaseFreezeError("license layers are ambiguous or unsafe")
        return fixture

    def _path(self, value: Any, label: str) -> Path:
        path = (self.root / _string(value, label)).resolve(strict=True)
        if not path.is_relative_to(self.root):
            raise DevelopmentReleaseFreezeError(f"{label} escaped repository")
        return path

    def _load_json(self, path: Path, label: str) -> dict[str, Any]:
        try:
            return _mapping(json.loads(path.read_text(encoding="utf-8")), label)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise DevelopmentReleaseFreezeError(f"cannot load {label}: {exc}") from exc

    def _verify_inputs(self, fixture: Mapping[str, Any]) -> dict[str, dict[str, Any] | str]:
        loaded: dict[str, dict[str, Any] | str] = {}
        for value in fixture["inputs"]:
            row = _mapping(value, "development release input")
            label = _string(row.get("label"), "input label")
            path = self._path(row.get("path"), f"{label} path")
            raw = path.read_bytes()
            if _sha256(raw) != _string(row.get("sha256"), f"{label} checksum"):
                raise DevelopmentReleaseFreezeError(f"input checksum differs: {label}")
            kind = _string(row.get("kind"), f"{label} kind")
            if kind == "json":
                loaded[label] = self._load_json(path, label)
            elif kind == "text":
                text = raw.decode("utf-8")
                if not text.strip():
                    raise DevelopmentReleaseFreezeError(f"input is empty: {label}")
                loaded[label] = text
            else:
                raise DevelopmentReleaseFreezeError(f"unsupported input kind: {label}")
        silver = loaded["T047 silver manifest"]
        gold = loaded["T048 gold-auto manifest"]
        qc = loaded["T057 PRIDE QC report"]
        links = loaded["T062 modality-link receipt"]
        uncertainty = loaded["T078 uncertainty receipt"]
        multimodal = loaded["T079 multimodal receipt"]
        negative = loaded["T102 negative-controls receipt"]
        if not isinstance(silver, dict) or not isinstance(gold, dict):
            raise DevelopmentReleaseFreezeError("data manifests are invalid")
        if not silver.get("tables") or not gold.get("rows"):
            raise DevelopmentReleaseFreezeError("data manifests have no frozen records")
        if not isinstance(qc, str) or "concordance" not in qc.lower():
            raise DevelopmentReleaseFreezeError("T057 QC evidence is missing concordance")
        if not isinstance(links, dict) or links.get("status") != "COMPLETED":
            raise DevelopmentReleaseFreezeError("T062 modality links are not completed")
        if links.get("pseudo_pairs_created") is not False:
            raise DevelopmentReleaseFreezeError("T062 pseudo-pairing gate failed")
        if not isinstance(uncertainty, dict) or uncertainty.get("status") != "VALID":
            raise DevelopmentReleaseFreezeError("T078 uncertainty receipt is invalid")
        if uncertainty.get("selected_model") != "conservative_conformal":
            raise DevelopmentReleaseFreezeError("T078 conservative uncertainty model is not selected")
        if not isinstance(multimodal, dict) or multimodal.get("status") != "VALID":
            raise DevelopmentReleaseFreezeError("T079 multimodal receipt is invalid")
        if multimodal.get("leakage_passed") is not True or multimodal.get("missingness_masked") is not True:
            raise DevelopmentReleaseFreezeError("T079 multimodal safety gates failed")
        if not isinstance(negative, dict) or negative.get("strict_pass") is not True:
            raise DevelopmentReleaseFreezeError("T102 negative-control gate failed")
        if negative.get("critical_leaks") != 0:
            raise DevelopmentReleaseFreezeError("T102 has critical leakage")
        return loaded

    def run(self, *, fixture: bool = True) -> DevelopmentReleaseFreezeSummary:
        """Freeze data, model results, configs, thresholds, and dependencies."""
        if not fixture:
            raise DevelopmentReleaseFreezeError("--fixture is required for development freeze")
        fixture_data = self._fixture()
        loaded = self._verify_inputs(fixture_data)
        prereg = _mapping(fixture_data["preregistration"], "development preregistration")
        silver = _mapping(loaded["T047 silver manifest"], "T047 silver manifest")
        gold = _mapping(loaded["T048 gold-auto manifest"], "T048 gold-auto manifest")
        uncertainty = _mapping(loaded["T078 uncertainty receipt"], "T078 uncertainty receipt")
        multimodal = _mapping(loaded["T079 multimodal receipt"], "T079 multimodal receipt")
        input_records = []
        for value in fixture_data["inputs"]:
            row = _mapping(value, "development input")
            path = self._path(row["path"], f"{row['label']} path")
            input_records.append(
                {
                    "label": row["label"],
                    "path": row["path"],
                    "sha256": row["sha256"],
                    "bytes": path.stat().st_size,
                    "kind": row["kind"],
                }
            )
        thresholds = _mapping(prereg["thresholds"], "frozen thresholds")
        dependencies = _mapping(prereg["dependencies"], "frozen dependencies")
        release_manifest = {
            "schema_version": 1,
            "status": "FROZEN_DEV",
            "release_id": prereg["release_id"],
            "semantic_version": prereg["semantic_version"],
            "immutable": True,
            "target_values_exposed": False,
            "inputs": input_records,
            "data_layers": {
                "silver_tables": len(silver["tables"]),
                "gold_auto_rows": len(gold["rows"]),
            },
            "model_layers": {
                "uncertainty": uncertainty["selected_model"],
                "multimodal": multimodal["selected_model"],
            },
            "thresholds": thresholds,
            "dependencies": dependencies,
            "license_layers": prereg["license_layers"],
            "robustness": {
                "negative_controls": "ATTACKS_CLEAN",
                "critical_leaks": 0,
                "pseudo_pairs_created": False,
                "model_leakage_passed": True,
            },
        }
        card = (
            f"# Development data/model release {prereg['semantic_version']}\n\n"
            f"Release ID: `{prereg['release_id']}`  \nStatus: `FROZEN_DEV`  \n"
            "Target values exposed: `false`  \nLicense layers separated: `true`\n\n"
            "## Frozen contents\n\n"
            f"- Silver tables: {len(silver['tables'])}\n"
            f"- Gold-auto admitted rows: {len(gold['rows'])}\n"
            f"- Uncertainty model: `{uncertainty['selected_model']}`\n"
            f"- Multimodal model: `{multimodal['selected_model']}`\n"
            f"- Frozen thresholds: {len(thresholds)}\n"
            f"- Frozen dependency entries: {len(dependencies)}\n\n"
            "## Safety and licensing\n\n"
            "T102 strict negative controls are clean with zero critical leakage. "
            "T062 pseudo-pairing is disabled and T079 leakage/missingness gates pass.\n"
            "Data and model artifacts remain analysis-only; configs and cards are "
            "redistributable metadata. Locked targets are not included.\n"
        )
        freeze_manifest = {
            "schema_version": 1,
            "status": "FROZEN_DEV",
            "release_id": prereg["release_id"],
            "semantic_version": prereg["semantic_version"],
            "release_manifest": "release_manifest.json",
            "data_model_card": "data_model_card.md",
            "immutable": True,
            "target_values_exposed": False,
            "license_layers": prereg["license_layers"],
            "input_count": len(input_records),
        }
        manifest_bytes = _canonical(release_manifest)
        card_bytes = card.encode("utf-8")
        freeze_bytes = _canonical(freeze_manifest)
        resume_key = _sha256(manifest_bytes + card_bytes + freeze_bytes)
        receipt = {
            "schema_version": 1,
            "status": "VALID",
            "release_id": prereg["release_id"],
            "semantic_version": prereg["semantic_version"],
            "immutable": True,
            "target_values_exposed": False,
            "license_layers_separated": True,
            "negative_controls_clean": True,
            "resume_key": resume_key,
            "artifacts": {
                "release_manifest": {
                    "path": "release_manifest.json",
                    "sha256": _sha256(manifest_bytes),
                    "bytes": len(manifest_bytes),
                },
                "data_model_card": {
                    "path": "data_model_card.md",
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
            "release_manifest.json": manifest_bytes,
            "data_model_card.md": card_bytes,
            "freeze_manifest.json": freeze_bytes,
            "freeze_receipt.json": receipt_bytes,
        }
        resumed = 0
        for name, payload in payloads.items():
            path = self.output_root / name
            if path.exists():
                if path.read_bytes() != payload:
                    raise DevelopmentReleaseFreezeError(f"immutable artifact differs: {name}")
                resumed = 1
            else:
                path.write_bytes(payload)
        return DevelopmentReleaseFreezeSummary(
            release_id=prereg["release_id"],
            semantic_version=prereg["semantic_version"],
            input_count=len(input_records),
            data_layers=2,
            model_layers=2,
            thresholds=len(thresholds),
            license_layers_separated=True,
            negative_controls_clean=True,
            resumed=resumed,
            receipt_path=self.output_root / "freeze_receipt.json",
        )
