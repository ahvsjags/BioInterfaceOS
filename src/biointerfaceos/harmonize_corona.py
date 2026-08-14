"""Deterministic project-preserving protein-corona harmonization."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast


class HarmonizationError(RuntimeError):
    """Raised when a corona harmonization fixture violates a guard."""


@dataclass(frozen=True)
class HarmonizationSummary:
    """Summary of one project-preserving harmonization run."""

    projects: int
    samples: int
    proteins: int
    modules: int
    missing_cells: int
    mapping_rows: int
    resumed: int
    receipt_path: Path


def _canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_path(path: Path) -> str:
    return _sha256(path.read_bytes())


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise HarmonizationError(f"{label} must be an object")
    return dict(value)


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise HarmonizationError(f"{label} must be a non-empty string")
    return value.strip()


def _float(value: Any, label: str) -> float:
    if value is None or isinstance(value, bool) or not isinstance(value, float | int):
        raise HarmonizationError(f"{label} must be numeric")
    return float(value)


class HarmonizationWorkflow:
    """Harmonize project matrices without cross-project batch correction."""

    def __init__(
        self,
        root: Path,
        *,
        fixture_path: Path | None = None,
        output_root: Path | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.fixture_path = fixture_path or (self.root / "tests/fixtures/omics/harmonize_corona_fixture.json")
        self.output_root = output_root or self.root / "reports/omics/harmonization"

    def _load_fixture(self) -> dict[str, Any]:
        try:
            data = json.loads(self.fixture_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise HarmonizationError(f"cannot load harmonization fixture: {exc}") from exc
        fixture = _mapping(data, "harmonization fixture")
        if fixture.get("schema_version") != 1:
            raise HarmonizationError("harmonization fixture schema_version must be 1")
        for key in ("inputs", "policy", "projects", "mappings", "modules"):
            if key not in fixture:
                raise HarmonizationError(f"harmonization fixture missing {key}")
        for key in ("projects", "mappings", "modules"):
            if not isinstance(fixture[key], list) or not fixture[key]:
                raise HarmonizationError(f"harmonization fixture {key} must be non-empty")
        return fixture

    def _verify_inputs(self, data: Mapping[str, Any]) -> set[str]:
        inputs = _mapping(data["inputs"], "inputs")
        quant_receipt_relative = _string(
            inputs.get("quantification_receipt_path"), "inputs.quantification_receipt_path"
        )
        quant_receipt = (self.root / quant_receipt_relative).resolve(strict=True)
        normalized_relative = _string(inputs.get("normalized_matrix_path"), "inputs.normalized_matrix_path")
        normalized = (self.root / normalized_relative).resolve(strict=True)
        for path in (quant_receipt, normalized):
            try:
                path.relative_to(self.root)
            except ValueError as exc:
                raise HarmonizationError("harmonization inputs must remain inside repository") from exc
        if _sha256_path(quant_receipt) != _string(
            inputs.get("quantification_receipt_sha256"), "inputs.quantification_receipt_sha256"
        ):
            raise HarmonizationError("T055 quantification receipt checksum differs from fixture")
        if _sha256_path(normalized) != _string(
            inputs.get("normalized_matrix_sha256"), "inputs.normalized_matrix_sha256"
        ):
            raise HarmonizationError("T055 normalized matrix checksum differs from fixture")
        receipt = _mapping(json.loads(quant_receipt.read_text(encoding="utf-8")), "quantification receipt")
        if receipt.get("status") != "COMPLETED":
            raise HarmonizationError("T055 quantification receipt is not completed")
        matrix = _mapping(json.loads(normalized.read_text(encoding="utf-8")), "normalized matrix")
        rows = matrix.get("rows")
        if not isinstance(rows, list) or not rows:
            raise HarmonizationError("T055 normalized matrix has no rows")
        proteins: set[str] = set()
        for value in rows:
            row = _mapping(value, "normalized protein row")
            if row.get("is_contaminant") is True:
                continue
            proteins.add(_string(row.get("protein_accession"), "normalized protein accession"))
        if not proteins:
            raise HarmonizationError("T055 normalized matrix has no quantifiable proteins")
        return proteins

    def _policy(self, data: Mapping[str, Any]) -> dict[str, Any]:
        policy = _mapping(data["policy"], "policy")
        transform = _string(policy.get("compositional_transform"), "policy.compositional_transform")
        correction = _string(policy.get("batch_correction"), "policy.batch_correction").lower()
        leakage = policy.get("outcome_labels_used_for_transform")
        if transform != "closure_clr":
            raise HarmonizationError("only closure_clr is supported")
        if correction != "none" or "combat" in correction:
            raise HarmonizationError("ComBat or other cross-project batch correction is forbidden")
        if leakage is not False:
            raise HarmonizationError("outcome labels cannot enter the harmonization transform")
        return {
            "compositional_transform": transform,
            "batch_correction": correction,
            "outcome_labels_used_for_transform": False,
        }

    def _mappings(
        self, data: Mapping[str, Any], proteins: set[str]
    ) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
        rows: list[dict[str, Any]] = []
        by_source: dict[str, dict[str, Any]] = {}
        for value in cast(list[Any], data["mappings"]):
            row = _mapping(value, "mapping")
            source = _string(row.get("source_protein"), "mapping.source_protein")
            canonical = _string(row.get("canonical_protein"), "mapping.canonical_protein")
            species = _string(row.get("species"), "mapping.species")
            status = _string(row.get("mapping_status"), "mapping.mapping_status")
            module = _string(row.get("module"), "mapping.module")
            if source in by_source or source not in proteins or status != "EXACT":
                raise HarmonizationError("protein mapping is duplicated, stale, or non-exact")
            record = {
                "source_protein": source,
                "canonical_protein": canonical,
                "species": species,
                "mapping_status": status,
                "module": module,
            }
            rows.append(record)
            by_source[source] = record
        if set(by_source) != proteins:
            raise HarmonizationError("every T055 quantifiable protein requires an exact mapping")
        return sorted(rows, key=lambda row: row["source_protein"]), by_source

    @staticmethod
    def _closure_clr(
        values: Mapping[str, Any],
    ) -> tuple[dict[str, float | None], dict[str, float | None], int]:
        observed = {key: _float(value, f"sample value {key}") for key, value in values.items() if value is not None}
        if not observed or any(value <= 0 for value in observed.values()):
            raise HarmonizationError("each sample needs at least one positive observed protein")
        total = sum(observed.values())
        composition = {key: value / total for key, value in observed.items()}
        geometric_mean = math.exp(sum(math.log(value) for value in composition.values()) / len(composition))
        clr = {key: math.log(value / geometric_mean) for key, value in composition.items()}
        all_keys = set(values)
        return (
            {key: round(composition[key], 8) if key in composition else None for key in all_keys},
            {key: round(clr[key], 8) if key in clr else None for key in all_keys},
            len(all_keys - set(observed)),
        )

    def _project_rows(
        self,
        data: Mapping[str, Any],
        mappings: Mapping[str, Mapping[str, Any]],
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int, set[str]]:
        rows: list[dict[str, Any]] = []
        module_rows: list[dict[str, Any]] = []
        missing_cells = 0
        batches: set[str] = set()
        sample_keys: set[tuple[str, str]] = set()
        module_names = sorted({str(row["module"]) for row in mappings.values()})
        for project_value in cast(list[Any], data["projects"]):
            project = _mapping(project_value, "project")
            accession = _string(project.get("project_accession"), "project_accession")
            scale = _string(project.get("source_scale"), "project.source_scale")
            batch = _string(project.get("batch_id"), "project.batch_id")
            batches.add(batch)
            samples = project.get("samples")
            if not isinstance(samples, list) or not samples:
                raise HarmonizationError("project must have samples")
            for sample_value in samples:
                sample = _mapping(sample_value, "project sample")
                sample_id = _string(sample.get("sample_id"), "sample.sample_id")
                condition = _string(sample.get("condition"), "sample.condition")
                key = (accession, sample_id)
                if key in sample_keys:
                    raise HarmonizationError("project sample is duplicated")
                sample_keys.add(key)
                values = _mapping(sample.get("values"), "sample.values")
                if set(values) != set(mappings):
                    raise HarmonizationError("project sample proteins do not match mapping table")
                composition, clr, missing = self._closure_clr(values)
                missing_cells += missing
                row = {
                    "project_accession": accession,
                    "sample_id": sample_id,
                    "condition": condition,
                    "batch_id": batch,
                    "source_scale": scale,
                    "raw_values": {key: values[key] for key in sorted(values)},
                    "composition_values": {key: composition[key] for key in sorted(composition)},
                    "clr_values": {key: clr[key] for key in sorted(clr)},
                    "missing_proteins": sorted(key for key, value in composition.items() if value is None),
                }
                rows.append(row)
                module_values: dict[str, list[float]] = {module: [] for module in module_names}
                module_missing: dict[str, bool] = {module: False for module in module_names}
                for protein, mapping in mappings.items():
                    module = str(mapping["module"])
                    value = composition.get(protein)
                    if value is None:
                        module_missing[module] = True
                    else:
                        module_values[module].append(float(value))
                module_rows.append(
                    {
                        "project_accession": accession,
                        "sample_id": sample_id,
                        "condition": condition,
                        "batch_id": batch,
                        "source_scale": scale,
                        "module_values": {
                            module: round(sum(module_values[module]), 8) if module_values[module] else None
                            for module in module_names
                        },
                        "module_missing": module_missing,
                    }
                )
        if not rows:
            raise HarmonizationError("no project rows were harmonized")
        return (
            sorted(rows, key=lambda row: (row["project_accession"], row["sample_id"])),
            sorted(module_rows, key=lambda row: (row["project_accession"], row["sample_id"])),
            missing_cells,
            batches,
        )

    def run(self, *, fixture: bool = False) -> HarmonizationSummary:
        """Run project-preserving closure/CLR harmonization."""
        if not fixture:
            raise HarmonizationError("--fixture is required for the bounded harmonization workflow")
        data = self._load_fixture()
        proteins = self._verify_inputs(data)
        policy = self._policy(data)
        mapping_rows, mappings = self._mappings(data, proteins)
        project_rows, module_rows, missing_cells, batches = self._project_rows(data, mappings)
        modules = sorted({mapping["module"] for mapping in mapping_rows})
        qc = {
            "schema_version": 1,
            "projects": len({row["project_accession"] for row in project_rows}),
            "samples": len(project_rows),
            "proteins": len(proteins),
            "modules": len(modules),
            "missing_cells": missing_cells,
            "mapping_rows": len(mapping_rows),
            "mapping_statuses": sorted({row["mapping_status"] for row in mapping_rows}),
            "project_scales": sorted({row["source_scale"] for row in project_rows}),
            "batches": sorted(batches),
            "project_scale_preserved": all(
                len({row["source_scale"] for row in project_rows if row["project_accession"] == project}) == 1
                for project in {row["project_accession"] for row in project_rows}
            ),
            "composition_sums_valid": all(
                abs(sum(value for value in row["composition_values"].values() if value is not None) - 1.0) < 1e-7
                for row in project_rows
            ),
            "no_combat": policy["batch_correction"] == "none",
            "no_outcome_leakage": policy["outcome_labels_used_for_transform"] is False,
        }
        if not qc["project_scale_preserved"] or not qc["composition_sums_valid"]:
            raise HarmonizationError("project scale or composition guard failed")
        resume_material = {
            "policy": policy,
            "mappings": mapping_rows,
            "rows": project_rows,
            "modules": module_rows,
        }
        resume_key = _sha256(_canonical(resume_material))
        self.output_root.mkdir(parents=True, exist_ok=True)
        paths = {
            "matrix": self.output_root / "project_matrix.json",
            "mapping": self.output_root / "mapping_audit.json",
            "modules": self.output_root / "module_matrix.json",
            "batch": self.output_root / "batch_metadata.json",
            "missingness": self.output_root / "missingness_report.json",
            "qc": self.output_root / "harmonization_qc.json",
            "receipt": self.output_root / "harmonization_receipt.json",
            "log": self.output_root / "harmonization_log.json",
            "manifest": self.output_root / "harmonization_manifest.json",
        }
        raw_payloads = {
            "matrix": {"schema_version": 1, "transform": "closure_clr", "rows": project_rows},
            "mapping": {"schema_version": 1, "rows": mapping_rows},
            "modules": {
                "schema_version": 1,
                "transform": "closure_module_sum",
                "rows": module_rows,
            },
            "batch": {
                "schema_version": 1,
                "project_batches": sorted(
                    {(row["project_accession"], row["batch_id"], row["source_scale"]) for row in project_rows}
                ),
                "batch_correction": "none",
            },
            "missingness": {
                "schema_version": 1,
                "missing_cells": missing_cells,
                "no_imputation": True,
                "rows_with_missingness": [
                    {
                        "project_accession": row["project_accession"],
                        "sample_id": row["sample_id"],
                        "missing_proteins": row["missing_proteins"],
                    }
                    for row in project_rows
                    if row["missing_proteins"]
                ],
            },
            "qc": qc,
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
            "status": "COMPLETED",
            "inputs": data["inputs"],
            "policy": policy,
            "project_count": qc["projects"],
            "sample_count": qc["samples"],
            "protein_count": qc["proteins"],
            "module_count": qc["modules"],
            "missing_cells": missing_cells,
            "project_scale_preserved": qc["project_scale_preserved"],
            "no_combat": qc["no_combat"],
            "no_outcome_leakage": qc["no_outcome_leakage"],
            "resume_key": resume_key,
            "artifacts": artifact_records,
        }
        payload_bytes["receipt"] = _canonical(receipt)
        log = {
            "schema_version": 1,
            "resume_key": resume_key,
            "events": [
                {"event": "T055_input_verified", "proteins": len(proteins)},
                {"event": "mappings_verified", "rows": len(mapping_rows)},
                {"event": "project_scales_preserved", "projects": qc["projects"]},
                {"event": "batch_correction_blocked", "method": "none"},
                {"event": "composition_qc_passed", "missing_cells": missing_cells},
            ],
        }
        payload_bytes["log"] = _canonical(log)
        manifest = {
            "schema_version": 1,
            "status": "COMPLETED",
            "resume_supported": True,
            "resume_key": resume_key,
            "projects": qc["projects"],
            "samples": qc["samples"],
            "proteins": qc["proteins"],
            "modules": qc["modules"],
            "missing_cells": missing_cells,
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
        payload_bytes["manifest"] = _canonical(manifest)
        existing_receipt = paths["receipt"].read_bytes() if paths["receipt"].exists() else None
        if existing_receipt is not None:
            if existing_receipt != payload_bytes["receipt"]:
                raise HarmonizationError("existing harmonization receipt differs from rerun")
            for name, payload in payload_bytes.items():
                if paths[name].read_bytes() != payload:
                    raise HarmonizationError(f"existing harmonization artifact differs: {name}")
            resumed = 1
        else:
            for name, payload in payload_bytes.items():
                paths[name].write_bytes(payload)
            resumed = 0
        return HarmonizationSummary(
            projects=int(qc["projects"]),
            samples=int(qc["samples"]),
            proteins=int(qc["proteins"]),
            modules=int(qc["modules"]),
            missing_cells=missing_cells,
            mapping_rows=len(mapping_rows),
            resumed=resumed,
            receipt_path=paths["receipt"],
        )
