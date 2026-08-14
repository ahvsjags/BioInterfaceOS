"""Verify the analysis-only PMC10257194 paper-data source.

The article is CC-BY-NC-ND.  This audit therefore binds the locally acquired
supplementary workbook and derived source map without admitting either asset
to the redistributable release.  It records provenance and accounting only.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from biointerfaceos.r3_uniprot_mapping import _canonical, _checksum, _mapping, _sha256, _string


class R4PMC10257194PaperSourceAuditError(RuntimeError):
    """Raised when the paper-data source or its derived map is not byte-bound."""


@dataclass(frozen=True)
class R4PMC10257194PaperSourceAuditSummary:
    source_cell_count: int
    positive_source_cell_count: int
    shared_canonical_protein_count: int
    measurement_batch_count: int
    biological_unit_count: int
    receipt_path: Path


class R4PMC10257194PaperSourceAuditWorkflow:
    AUDIT_ID = "bioif-r4-pmc10257194-paper-source-audit-v1.0.0"
    REGISTRY_RELATIVE = "docs/data/R4_T203_PMC10257194_NAY_LUAD_PAPER_SOURCE_REGISTRY.json"
    OUTPUT_RELATIVE = "reports/review_round_4/pmc10257194_paper_source_audit/v1.0.0"
    MAP_RELATIVE = "data/raw/r4_candidate_pmc10257194/derived/R4_PMC10257194_NAY_LUAD_source_cell_map.csv"
    RECEIPT_NAME = "r4_pmc10257194_paper_source_audit_receipt.json"
    REPORT_NAME = "r4_pmc10257194_paper_source_audit_report.json"
    REQUIRED_REFERENCE = {"relative_path", "sha256"}

    def __init__(
        self,
        root: Path,
        assets_root: Path,
        *,
        registry_path: Path | None = None,
        output_root: Path | None = None,
    ) -> None:
        self.root = root.resolve(strict=True)
        self.assets_root = assets_root.resolve(strict=False)
        self.registry_path = registry_path or self.root / self.REGISTRY_RELATIVE
        self.output_root = output_root or self.root / self.OUTPUT_RELATIVE

    @staticmethod
    def _json(path: Path, label: str) -> dict[str, Any]:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            return _mapping(value, label)
        except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
            raise R4PMC10257194PaperSourceAuditError(f"cannot parse {label}") from exc

    def _under(self, root: Path, relative_path: str, label: str) -> Path:
        if "\\" in relative_path:
            raise R4PMC10257194PaperSourceAuditError(f"{label} must use POSIX separators")
        pure = PurePosixPath(relative_path)
        if pure.is_absolute() or not pure.parts or ".." in pure.parts:
            raise R4PMC10257194PaperSourceAuditError(f"{label} escapes its root")
        path = (root / Path(*pure.parts)).resolve(strict=False)
        if not path.is_relative_to(root) or not path.is_file():
            raise R4PMC10257194PaperSourceAuditError(f"{label} is missing or outside its root")
        return path

    def _reference(self, value: Any, label: str, *, root: Path | None = None) -> Path:
        item = _mapping(value, label)
        if set(item) != self.REQUIRED_REFERENCE:
            raise R4PMC10257194PaperSourceAuditError(f"{label} reference fields are invalid")
        base = self.root if root is None else root
        path = self._under(base, _string(item["relative_path"], label), label)
        if _sha256(path) != _checksum(item["sha256"], label):
            raise R4PMC10257194PaperSourceAuditError(f"{label} checksum differs")
        return path

    def _registry(self) -> tuple[dict[str, Any], Path, Path]:
        registry = self._json(self.registry_path, "PMC10257194 source registry")
        expected = {
            "schema_version", "audit_id", "status", "evidence_class", "allowed_claim_level",
            "article", "source_scope", "source_asset", "derived_source_map", "expected_accounting",
            "claim_boundary", "scientific_submission_ready",
        }
        if set(registry) != expected or registry.get("schema_version") != 1:
            raise R4PMC10257194PaperSourceAuditError("source registry fields are invalid")
        if (
            registry.get("audit_id") != self.AUDIT_ID
            or registry.get("status") != "ANALYSIS_ONLY_PAPER_SOURCE_REGISTERED"
            or registry.get("evidence_class") != "DEVELOPMENT_OBSERVATION"
            or registry.get("allowed_claim_level") != "EXPLORATORY"
            or registry.get("scientific_submission_ready") is not False
        ):
            raise R4PMC10257194PaperSourceAuditError("source registry identity or boundary is invalid")
        article = _mapping(registry["article"], "article")
        if article != {
            "pmcid": "PMC10257194",
            "doi": "10.1016/j.jpha.2023.04.002",
            "title": "Comprehensive and deep profiling of the plasma proteome with protein corona on zeolite NaY",
            "license": "CC-BY-NC-ND-4.0",
            "full_text_locator": "https://pmc.ncbi.nlm.nih.gov/articles/PMC10257194/",
            "supplementary_locator": "https://www.ncbi.nlm.nih.gov/pmc/articles/instance/10257194/bin/mmc6.xlsx",
        }:
            raise R4PMC10257194PaperSourceAuditError("article declaration is invalid")
        scope = _mapping(registry["source_scope"], "source scope")
        if scope != {
            "source_id": "PMC10257194_NAY_LUAD_PLASMA_CORONA",
            "laboratory_anchor": "Tianjin University / Tianjin Medical University",
            "source_lineage": "NEW_TO_CURRENT_R3_LABORATORY_ANCHORS",
            "biofluid": "human plasma",
            "biological_unit_semantics": "45 subject plasma units: 15 healthy and 30 lung adenocarcinoma; one measurement batch per subject",
            "analysis_role": "ANALYSIS_ONLY_EXTERNAL_PAPER_OOD",
        }:
            raise R4PMC10257194PaperSourceAuditError("source scope is invalid")
        asset = _mapping(registry["source_asset"], "source asset")
        asset_path = self._under(self.assets_root, _string(asset["relative_path"], "source asset"), "source asset")
        if set(asset) != {"relative_path", "sha256", "expected_bytes"} or asset_path.stat().st_size != asset["expected_bytes"] or _sha256(asset_path) != _checksum(asset["sha256"], "source asset"):
            raise R4PMC10257194PaperSourceAuditError("source asset checksum differs")
        derived = self._reference(registry["derived_source_map"], "derived source map")
        return registry, asset_path, derived

    @staticmethod
    def _read_rows(path: Path) -> list[dict[str, str]]:
        with path.open("r", encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        if not rows:
            raise R4PMC10257194PaperSourceAuditError("derived source map is empty")
        required = {
            "source_id", "laboratory_anchor", "source_worksheet", "source_row", "source_coordinate",
            "source_identifier", "measurement_batch_id", "biological_unit_id", "condition_label",
            "canonical_accession", "author_quantity_type", "author_numeric_value",
            "analysis_candidate_eligible", "rank_target_eligible",
        }
        if not required.issubset(rows[0]):
            raise R4PMC10257194PaperSourceAuditError("derived source map schema is invalid")
        return rows

    def run(self, *, strict: bool = False) -> R4PMC10257194PaperSourceAuditSummary:
        if not strict:
            raise R4PMC10257194PaperSourceAuditError("PMC10257194 source audit requires --strict")
        if self.output_root.exists():
            raise R4PMC10257194PaperSourceAuditError("PMC10257194 source audit already executed")
        registry, asset_path, map_path = self._registry()
        rows = self._read_rows(map_path)
        eligible = [row for row in rows if row["analysis_candidate_eligible"] == "true" and row["rank_target_eligible"] == "true"]
        if any(row["source_id"] != registry["source_scope"]["source_id"] for row in rows):
            raise R4PMC10257194PaperSourceAuditError("source map source ID differs")
        batches = {row["measurement_batch_id"] for row in eligible}
        units = {row["biological_unit_id"] for row in eligible}
        accessions = {row["canonical_accession"] for row in eligible}
        positive = sum(float(row["author_numeric_value"]) > 0 for row in eligible)
        expected = _mapping(registry["expected_accounting"], "expected accounting")
        actual = {
            "source_cell_count": len(rows),
            "positive_source_cell_count": positive,
            "shared_canonical_protein_count": len(accessions),
            "measurement_batch_count": len(batches),
            "biological_unit_count": len(units),
        }
        if actual != expected:
            raise R4PMC10257194PaperSourceAuditError(f"source accounting differs: {actual} != {expected}")
        report = {
            "schema_version": 1, "audit_id": self.AUDIT_ID, "status": "ANALYSIS_ONLY_PAPER_SOURCE_AUDITED",
            "source_asset": {"relative_path": asset_path.relative_to(self.root).as_posix(), "sha256": _sha256(asset_path)},
            "derived_source_map": {"relative_path": map_path.relative_to(self.root).as_posix(), "sha256": _sha256(map_path)},
            "accounting": actual,
            "license_boundary": "CC-BY-NC-ND-4.0 source and numeric derivatives remain analysis-only and are excluded from redistributable release",
            "claim_boundary": registry["claim_boundary"], "scientific_submission_ready": False,
        }
        self.output_root.mkdir(parents=True, exist_ok=False)
        report_path = self.output_root / self.REPORT_NAME
        report_path.write_bytes(_canonical(report))
        receipt = {
            "schema_version": 1, "audit_id": self.AUDIT_ID, "status": "ANALYSIS_ONLY_PAPER_SOURCE_AUDITED",
            "report_sha256": _sha256(report_path), **actual, "independent_validation": False,
            "external_scientific_reproduction": False, "scientific_submission_ready": False,
        }
        receipt_path = self.output_root / self.RECEIPT_NAME
        receipt_path.write_bytes(_canonical(receipt))
        return R4PMC10257194PaperSourceAuditSummary(receipt_path=receipt_path, **actual)

    def verify(self) -> R4PMC10257194PaperSourceAuditSummary:
        registry, _, map_path = self._registry()
        rows = self._read_rows(map_path)
        eligible = [row for row in rows if row["analysis_candidate_eligible"] == "true" and row["rank_target_eligible"] == "true"]
        actual = {
            "source_cell_count": len(rows),
            "positive_source_cell_count": sum(float(row["author_numeric_value"]) > 0 for row in eligible),
            "shared_canonical_protein_count": len({row["canonical_accession"] for row in eligible}),
            "measurement_batch_count": len({row["measurement_batch_id"] for row in eligible}),
            "biological_unit_count": len({row["biological_unit_id"] for row in eligible}),
        }
        if actual != registry["expected_accounting"]:
            raise R4PMC10257194PaperSourceAuditError("source accounting differs")
        receipt_path = self.output_root / self.RECEIPT_NAME
        report_path = self.output_root / self.REPORT_NAME
        receipt = self._json(receipt_path, "PMC10257194 source receipt")
        if receipt.get("audit_id") != self.AUDIT_ID or receipt.get("report_sha256") != _sha256(report_path) or any(receipt.get(k) != v for k, v in actual.items()) or receipt.get("scientific_submission_ready") is not False:
            raise R4PMC10257194PaperSourceAuditError("source receipt is invalid")
        return R4PMC10257194PaperSourceAuditSummary(receipt_path=receipt_path, **actual)
