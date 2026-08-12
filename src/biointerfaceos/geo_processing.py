"""Fixture-backed GEO processed-matrix ingestion and within-study QC."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast


class GeoProcessingError(RuntimeError):
    """Raised when processed GEO data fails provenance, metadata, or QC checks."""


@dataclass(frozen=True)
class GeoProcessingSummary:
    """Summary of one study-preserving GEO processing run."""

    studies_attempted: int
    studies_passed: int
    excluded_studies: int
    genes: int
    samples: int
    contrasts: int
    missing_cells: int
    resumed: int
    receipt_path: Path


def _canonical(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    ).encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_path(path: Path) -> str:
    return _sha256(path.read_bytes())


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise GeoProcessingError(f"{label} must be an object")
    return dict(value)


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise GeoProcessingError(f"{label} must be a non-empty string")
    return value.strip()


def _float(value: Any, label: str) -> float:
    if value is None or isinstance(value, bool) or not isinstance(value, float | int):
        raise GeoProcessingError(f"{label} must be numeric")
    return float(value)


class GeoProcessingWorkflow:
    """Process eligible GEO fixtures while retaining study boundaries."""

    def __init__(
        self,
        root: Path,
        *,
        fixture_path: Path | None = None,
        output_root: Path | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.fixture_path = fixture_path or (
            self.root / "tests/fixtures/omics/geo_processing_fixture.json"
        )
        self.output_root = output_root or self.root / "reports/omics/geo_processing"

    def _load_fixture(self) -> dict[str, Any]:
        try:
            fixture = json.loads(self.fixture_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise GeoProcessingError(f"cannot load GEO processing fixture: {exc}") from exc
        data = _mapping(fixture, "GEO processing fixture")
        if data.get("schema_version") != 1 or data.get("mode") != "processed":
            raise GeoProcessingError("GEO processing fixture schema or mode is invalid")
        for key in ("inputs", "normalization", "gene_mappings", "studies"):
            if key not in data:
                raise GeoProcessingError(f"GEO processing fixture missing {key}")
        if not isinstance(data["studies"], list) or not data["studies"]:
            raise GeoProcessingError("GEO processing fixture has no studies")
        return data

    def _read_hashed_json(
        self, path_key: str, hash_key: str, data: Mapping[str, Any], label: str
    ) -> dict[str, Any]:
        relative = _string(data.get(path_key), path_key)
        path = (self.root / relative).resolve(strict=True)
        try:
            path.relative_to(self.root)
        except ValueError as exc:
            raise GeoProcessingError(f"{label} must remain inside repository") from exc
        if _sha256_path(path) != _string(data.get(hash_key), hash_key):
            raise GeoProcessingError(f"{label} checksum differs from fixture")
        try:
            return _mapping(json.loads(path.read_text(encoding="utf-8")), label)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise GeoProcessingError(f"cannot load {label}: {exc}") from exc

    def _verify_inputs(self, data: Mapping[str, Any]) -> dict[str, Any]:
        inputs = _mapping(data["inputs"], "inputs")
        registry = self._read_hashed_json(
            "candidate_registry_path", "candidate_registry_sha256", inputs, "candidate registry"
        )
        cards = self._read_hashed_json(
            "eligibility_cards_path", "eligibility_cards_sha256", inputs, "eligibility cards"
        )
        eligible_registry = {
            _string(row.get("accession"), "registry accession"): row
            for row in cast(list[Any], registry.get("candidates", []))
            if isinstance(row, Mapping) and row.get("decision") == "ELIGIBLE"
        }
        eligible_cards = {
            _string(row.get("accession"), "eligibility accession"): row
            for row in cast(list[Any], cards.get("cards", []))
            if isinstance(row, Mapping) and row.get("decision") == "ELIGIBLE"
        }
        if not eligible_registry or set(eligible_registry) != set(eligible_cards):
            raise GeoProcessingError("T058 eligible registry/cards are inconsistent")
        return {
            "registry": eligible_registry,
            "cards": eligible_cards,
            "upstream": {
                "candidate_registry_sha256": inputs["candidate_registry_sha256"],
                "eligibility_cards_sha256": inputs["eligibility_cards_sha256"],
            },
        }

    @staticmethod
    def _gene_map(data: Mapping[str, Any]) -> dict[tuple[str, str], str]:
        version = _string(data.get("version"), "gene mapping version")
        if version != "fixture-gene-map-v1":
            raise GeoProcessingError("unsupported gene mapping version")
        mappings: dict[tuple[str, str], str] = {}
        for value in cast(list[Any], data.get("mappings")):
            row = _mapping(value, "gene mapping")
            namespace = _string(row.get("namespace"), "gene namespace")
            raw = _string(row.get("raw_gene_id"), "raw gene ID")
            normalized = _string(row.get("normalized_gene_id"), "normalized gene ID")
            key = (namespace, raw)
            if key in mappings:
                raise GeoProcessingError("gene mapping is duplicated")
            mappings[key] = normalized
        if not mappings:
            raise GeoProcessingError("gene mapping is empty")
        return mappings

    def _process_study(
        self,
        study_value: Any,
        eligible_registry: Mapping[str, Mapping[str, Any]],
        gene_map: Mapping[tuple[str, str], str],
        gene_mapping_version: str,
        normalization: Mapping[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]], int]:
        study = _mapping(study_value, "study")
        accession = _string(study.get("accession"), "study accession")
        registry = eligible_registry.get(accession)
        if registry is None:
            raise GeoProcessingError(f"study is not T058 eligible: {accession}")
        source_sha = _string(study.get("source_file_sha256"), "source file checksum")
        public_files = registry.get("public_files")
        matching = [
            file
            for file in cast(list[Any], public_files)
            if isinstance(file, Mapping)
            and file.get("sha256") == source_sha
            and file.get("access") == "PUBLIC"
        ]
        if not matching:
            raise GeoProcessingError(
                f"study source checksum is not an eligible public file: {accession}"
            )
        namespace = _string(study.get("gene_id_namespace"), "gene ID namespace")
        samples = study.get("samples")
        if not isinstance(samples, list) or not samples:
            raise GeoProcessingError(f"study has no samples: {accession}")
        sample_rows: list[dict[str, Any]] = []
        sample_ids: set[str] = set()
        conditions: dict[str, set[int]] = {}
        for value in samples:
            sample = _mapping(value, "study sample")
            sample_id = _string(sample.get("sample_id"), "sample ID")
            condition = _string(sample.get("condition"), "sample condition")
            replicate = int(_float(sample.get("biological_replicate"), "biological replicate"))
            if sample_id in sample_ids or replicate < 1:
                raise GeoProcessingError(f"sample metadata is invalid: {accession}")
            sample_ids.add(sample_id)
            conditions.setdefault(condition, set()).add(replicate)
            sample_rows.append(
                {
                    "study_accession": accession,
                    "sample_id": sample_id,
                    "condition": condition,
                    "biological_replicate": replicate,
                    "material": _string(sample.get("material"), "sample material"),
                    "biological_system": _string(sample.get("biological_system"), "sample system"),
                    "dose": _string(sample.get("dose"), "sample dose"),
                    "time": _string(sample.get("time"), "sample time"),
                }
            )
        min_replicates = int(_float(normalization.get("min_replicates"), "min_replicates"))
        if any(len(replicates) < min_replicates for replicates in conditions.values()):
            raise GeoProcessingError(f"within-study replicate QC failed: {accession}")
        matrix = study.get("matrix")
        if not isinstance(matrix, list) or not matrix:
            raise GeoProcessingError(f"study matrix is empty: {accession}")
        raw_by_gene: dict[str, dict[str, float]] = {}
        normalized_by_gene: dict[str, dict[str, float]] = {}
        library_sizes = {sample_id: 0.0 for sample_id in sample_ids}
        for value in matrix:
            row = _mapping(value, "matrix row")
            raw_gene_id = _string(row.get("raw_gene_id"), "raw gene ID")
            normalized_gene_id = gene_map.get((namespace, raw_gene_id))
            if normalized_gene_id is None:
                raise GeoProcessingError(f"gene ID is unmapped: {namespace}:{raw_gene_id}")
            values = _mapping(row.get("values"), "matrix values")
            if set(values) != sample_ids:
                raise GeoProcessingError(f"matrix sample IDs disagree with metadata: {accession}")
            raw_values: dict[str, float] = {}
            for sample_id, raw_value in values.items():
                count = _float(raw_value, f"matrix count {raw_gene_id}:{sample_id}")
                if count < 0:
                    raise GeoProcessingError("matrix counts cannot be negative")
                raw_values[str(sample_id)] = count
                library_sizes[str(sample_id)] += count
            if normalized_gene_id in raw_by_gene:
                raise GeoProcessingError(
                    f"normalized gene ID collides within study: {normalized_gene_id}"
                )
            raw_by_gene[normalized_gene_id] = raw_values
        if any(total <= 0 for total in library_sizes.values()):
            raise GeoProcessingError(f"study has zero library size: {accession}")
        scale = _float(normalization.get("counts_per_million"), "counts_per_million")
        pseudocount = _float(normalization.get("pseudocount"), "pseudocount")
        if scale <= 0 or pseudocount <= 0:
            raise GeoProcessingError("normalization constants must be positive")
        for gene, values in raw_by_gene.items():
            normalized_by_gene[gene] = {
                sample_id: math.log2(1.0 + scale * value / library_sizes[sample_id] + pseudocount)
                for sample_id, value in values.items()
            }
        contrasts: list[dict[str, Any]] = []
        for value in cast(list[Any], study.get("expected_contrasts")):
            contrast = _mapping(value, "expected contrast")
            gene = _string(contrast.get("normalized_gene_id"), "contrast gene")
            direction = _string(contrast.get("expected_direction"), "contrast direction")
            numerator = _string(contrast.get("numerator_condition"), "contrast numerator")
            denominator = _string(contrast.get("denominator_condition"), "contrast denominator")
            numerator_ids = [
                row["sample_id"] for row in sample_rows if row["condition"] == numerator
            ]
            denominator_ids = [
                row["sample_id"] for row in sample_rows if row["condition"] == denominator
            ]
            if gene not in normalized_by_gene or not numerator_ids or not denominator_ids:
                raise GeoProcessingError(f"contrast inputs are invalid: {accession}:{gene}")
            numerator_mean = sum(
                normalized_by_gene[gene][sample_id] for sample_id in numerator_ids
            ) / len(numerator_ids)
            denominator_mean = sum(
                normalized_by_gene[gene][sample_id] for sample_id in denominator_ids
            ) / len(denominator_ids)
            delta = round(numerator_mean - denominator_mean, 8)
            minimum = _float(contrast.get("min_abs_delta"), "contrast min_abs_delta")
            passed = abs(delta) >= minimum and (
                (direction == "UP" and delta > 0) or (direction == "DOWN" and delta < 0)
            )
            contrasts.append(
                {
                    "study_accession": accession,
                    "normalized_gene_id": gene,
                    "numerator_condition": numerator,
                    "denominator_condition": denominator,
                    "numerator_mean": round(numerator_mean, 8),
                    "denominator_mean": round(denominator_mean, 8),
                    "delta_log2_cpm": delta,
                    "expected_direction": direction,
                    "min_abs_delta": minimum,
                    "passed": passed,
                }
            )
        if not contrasts or not all(row["passed"] for row in contrasts):
            raise GeoProcessingError(f"within-study contrast QC failed: {accession}")
        qc = {
            "study_accession": accession,
            "gene_count": len(raw_by_gene),
            "sample_count": len(sample_rows),
            "library_sizes": {key: round(value, 8) for key, value in sorted(library_sizes.items())},
            "replicate_counts": {
                condition: len(replicates) for condition, replicates in sorted(conditions.items())
            },
            "contrast_count": len(contrasts),
            "contrast_passed": True,
            "within_study_only": True,
            "cross_study_batch_merge": False,
        }
        study_object = {
            "study_accession": accession,
            "source_file_sha256": source_sha,
            "gene_id_namespace": namespace,
            "gene_mapping_version": gene_mapping_version,
            "normalization_method": "log2_cpm",
            "sample_metadata": sample_rows,
            "raw_matrix": [
                {"normalized_gene_id": gene, "values": values}
                for gene, values in sorted(raw_by_gene.items())
            ],
            "normalized_matrix": [
                {"normalized_gene_id": gene, "values": values}
                for gene, values in sorted(normalized_by_gene.items())
            ],
        }
        return study_object, qc, contrasts, 0

    def run(self, *, mode: str = "processed") -> GeoProcessingSummary:
        """Ingest eligible processed matrices and resume identical outputs."""
        if mode != "processed":
            raise GeoProcessingError("only processed mode is supported")
        data = self._load_fixture()
        inputs = self._verify_inputs(data)
        gene_mapping_data = _mapping(data["gene_mappings"], "gene_mappings")
        gene_mapping_version = _string(gene_mapping_data.get("version"), "gene mapping version")
        gene_map = self._gene_map(gene_mapping_data)
        normalization = _mapping(data["normalization"], "normalization")
        study_objects: list[dict[str, Any]] = []
        qcs: list[dict[str, Any]] = []
        contrasts: list[dict[str, Any]] = []
        excluded: list[dict[str, Any]] = []
        for study in cast(list[Any], data["studies"]):
            try:
                study_object, qc, study_contrasts, _ = self._process_study(
                    study,
                    inputs["registry"],
                    gene_map,
                    gene_mapping_version,
                    normalization,
                )
            except GeoProcessingError as exc:
                accession = _string(_mapping(study, "study").get("accession"), "study accession")
                excluded.append({"study_accession": accession, "reason": str(exc)})
            else:
                study_objects.append(study_object)
                qcs.append(qc)
                contrasts.extend(study_contrasts)
        if not study_objects:
            raise GeoProcessingError("no eligible study passed processing")
        resume_material = {
            "study_objects": study_objects,
            "qcs": qcs,
            "contrasts": contrasts,
            "excluded": excluded,
        }
        resume_key = _sha256(_canonical(resume_material))
        self.output_root.mkdir(parents=True, exist_ok=True)
        paths = {
            "studies": self.output_root / "study_objects.json",
            "samples": self.output_root / "sample_metadata.json",
            "normalized": self.output_root / "normalized_matrices.json",
            "contrasts": self.output_root / "contrast_summaries.json",
            "qc": self.output_root / "within_study_qc.json",
            "excluded": self.output_root / "exclusion_ledger.json",
            "receipt": self.output_root / "processing_receipt.json",
            "log": self.output_root / "processing_log.json",
            "manifest": self.output_root / "processing_manifest.json",
        }
        raw_payloads = {
            "studies": {"schema_version": 1, "studies": study_objects},
            "samples": {
                "schema_version": 1,
                "samples": [
                    sample for study in study_objects for sample in study["sample_metadata"]
                ],
            },
            "normalized": {
                "schema_version": 1,
                "study_objects": [
                    {
                        "study_accession": study["study_accession"],
                        "normalization_method": study["normalization_method"],
                        "matrix": study["normalized_matrix"],
                    }
                    for study in study_objects
                ],
                "cross_study_batch_merge": False,
            },
            "contrasts": {"schema_version": 1, "contrasts": contrasts},
            "qc": {
                "schema_version": 1,
                "studies": qcs,
                "within_study_only": True,
                "cross_study_batch_merge": False,
            },
            "excluded": {"schema_version": 1, "append_only": True, "entries": excluded},
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
            "status": "COMPLETED",
            "mode": mode,
            "inputs": data["inputs"],
            "gene_mapping_version": gene_mapping_version,
            "normalization_method": "log2_cpm",
            "studies_attempted": len(data["studies"]),
            "studies_passed": len(study_objects),
            "excluded_studies": len(excluded),
            "contrasts": len(contrasts),
            "cross_study_batch_merge": False,
            "raw_downloaded": False,
            "locked_payload_accessed": False,
            "real_network_accessed": False,
            "resume_key": resume_key,
            "artifacts": artifact_records,
        }
        payload_bytes["receipt"] = _canonical(receipt)
        log = {
            "schema_version": 1,
            "resume_key": resume_key,
            "events": [
                {"event": "T058_eligibility_verified", "studies": len(data["studies"])},
                {
                    "event": "gene_ids_normalized",
                    "mapping_version": receipt["gene_mapping_version"],
                },
                {"event": "within_study_qc_passed", "studies": len(study_objects)},
                {"event": "cross_study_merge_blocked", "enabled": False},
            ],
        }
        payload_bytes["log"] = _canonical(log)
        manifest = {
            "schema_version": 1,
            "status": "COMPLETED",
            "resume_supported": True,
            "resume_key": resume_key,
            "studies_attempted": len(data["studies"]),
            "studies_passed": len(study_objects),
            "excluded_studies": len(excluded),
            "genes": len(
                {
                    gene
                    for study in study_objects
                    for gene in (row["normalized_gene_id"] for row in study["raw_matrix"])
                }
            ),
            "samples": sum(len(study["sample_metadata"]) for study in study_objects),
            "contrasts": len(contrasts),
            "cross_study_batch_merge": False,
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
                raise GeoProcessingError("existing GEO processing receipt differs from rerun")
            for name, payload in payload_bytes.items():
                if paths[name].read_bytes() != payload:
                    raise GeoProcessingError(f"existing GEO processing artifact differs: {name}")
            resumed = 1
        else:
            for name, payload in payload_bytes.items():
                paths[name].write_bytes(payload)
            resumed = 0
        missing_cells = sum(
            1
            for study in study_objects
            for row in study["raw_matrix"]
            for value in row["values"].values()
            if value is None
        )
        return GeoProcessingSummary(
            studies_attempted=len(data["studies"]),
            studies_passed=len(study_objects),
            excluded_studies=len(excluded),
            genes=len(
                {
                    gene
                    for study in study_objects
                    for gene in (row["normalized_gene_id"] for row in study["raw_matrix"])
                }
            ),
            samples=sum(len(study["sample_metadata"]) for study in study_objects),
            contrasts=len(contrasts),
            missing_cells=missing_cells,
            resumed=resumed,
            receipt_path=paths["receipt"],
        )
