"""Audit the license-resolved PMC13106918 technical source.

The article reports one pooled human-plasma material from eight donors with
five digestion protocols and four technical replicates per protocol.  This
module creates a byte-traceable, no-imputation source-cell ledger for a
separately scoped R4 technical candidate.  It deliberately does not merge the
source into the frozen R3 training population or promote it to biological
validation, independent evaluation, or scientific readiness.
"""

from __future__ import annotations

import csv
import json
import math
import zipfile
from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from biointerfaceos.r3_uniprot_mapping import _canonical, _checksum, _mapping, _sha256, _string


class R4PMC13106918SourceAuditError(RuntimeError):
    """Raised when the public PMC13106918 source cannot be reproduced safely."""


@dataclass(frozen=True)
class R4PMC13106918SourceAuditSummary:
    """Compact accounting for the separately scoped technical source."""

    source_asset_count: int
    protein_row_count: int
    measurement_batch_count: int
    rank_qualified_measurement_batch_count: int
    shared_canonical_protein_count: int
    source_cell_count: int
    positive_source_cell_count: int
    biological_unit_count: int
    laboratory_anchor_count: int
    receipt_path: Path


class R4PMC13106918SourceAuditWorkflow:
    """Create and verify a strict source-cell map for PMC13106918."""

    AUDIT_ID = "bioif-r4-pmc13106918-technical-source-audit-v1.0.0"
    REGISTRY_RELATIVE = "docs/data/R4_T176_PMC13106918_TECHNICAL_SOURCE_REGISTRY.json"
    OUTPUT_RELATIVE = "reports/review_round_4/pmc13106918_source_audit/v1.0.0"
    DERIVED_RELATIVE = "derived/R4_PMC13106918_technical_source_cell_map.csv"
    STATUS = "R4_LICENSE_RESOLVED_TECHNICAL_SOURCE_AUDITED_EXPLORATORY"
    SOURCE_CELL_FIELDS = (
        "source_id",
        "laboratory_anchor",
        "source_asset_id",
        "source_worksheet",
        "source_row",
        "source_coordinate",
        "source_identifier",
        "canonical_accession",
        "measurement_batch_id",
        "biological_unit_id",
        "condition_label",
        "analysis_candidate_eligible",
        "author_quantity_type",
        "author_numeric_value",
        "author_value_state",
        "rank_target_eligible",
    )
    REQUIRED_TOP_LEVEL = {
        "schema_version",
        "audit_id",
        "evaluated_at",
        "evidence_class",
        "allowed_claim_level",
        "article",
        "dataset",
        "source_scope",
        "source_assets",
        "r3_reference_asset",
        "table_contract",
        "quantification_contract",
        "admission_minimums",
        "claim_boundary",
    }

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
    def _write(path: Path, value: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(_canonical(value))

    @staticmethod
    def _json(path: Path, label: str) -> dict[str, Any]:
        try:
            return _mapping(json.loads(path.read_text(encoding="utf-8")), label)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise R4PMC13106918SourceAuditError(f"cannot parse {label}") from exc

    @staticmethod
    def _number(value: Any) -> float | None:
        if value is None or (isinstance(value, str) and not value.strip()):
            return None
        if isinstance(value, bool):
            raise R4PMC13106918SourceAuditError("LFQ intensity must be numeric or blank")
        try:
            numeric = float(str(value).strip())
        except (TypeError, ValueError) as exc:
            raise R4PMC13106918SourceAuditError("LFQ intensity must be numeric or blank") from exc
        if not math.isfinite(numeric):
            raise R4PMC13106918SourceAuditError("LFQ intensity must be finite")
        return numeric

    def _under(self, root: Path, relative_path: str, label: str) -> Path:
        if "\\" in relative_path:
            raise R4PMC13106918SourceAuditError(f"{label} must use POSIX path separators")
        pure = PurePosixPath(relative_path)
        if pure.is_absolute() or not pure.parts or ".." in pure.parts:
            raise R4PMC13106918SourceAuditError(f"{label} escapes its root")
        path = (root / Path(*pure.parts)).resolve(strict=False)
        if not path.is_relative_to(root) or not path.is_file():
            raise R4PMC13106918SourceAuditError(f"{label} is missing or outside its root")
        return path

    def _registry(self) -> tuple[dict[str, Any], dict[str, Path], Path]:
        registry = self._json(self.registry_path, "PMC13106918 registry")
        if set(registry) != self.REQUIRED_TOP_LEVEL or registry.get("schema_version") != 1:
            raise R4PMC13106918SourceAuditError("registry fields are invalid")
        if registry.get("audit_id") != self.AUDIT_ID:
            raise R4PMC13106918SourceAuditError("registry audit ID is invalid")
        if registry.get("evidence_class") != "DEVELOPMENT_OBSERVATION" or registry.get(
            "allowed_claim_level"
        ) != "EXPLORATORY":
            raise R4PMC13106918SourceAuditError("registry evidence boundary is invalid")
        _string(registry.get("evaluated_at"), "evaluated_at")
        _string(registry.get("claim_boundary"), "claim_boundary")
        if _mapping(registry.get("article"), "article") != {
            "pmcid": "PMC13106918",
            "doi": "10.1002/pmic.70118",
            "title": "Mass Spectrometry Proteomics of the Nanoparticle Corona Is Highly Dependent on Sample Preparation Protocol",
            "publication_year": 2026,
            "license": "CC-BY-4.0",
            "full_text_locator": "https://pmc.ncbi.nlm.nih.gov/articles/PMC13106918/",
            "data_locator": "https://zenodo.org/records/16813857",
        }:
            raise R4PMC13106918SourceAuditError("article declaration is invalid")
        dataset = _mapping(registry.get("dataset"), "dataset")
        if dataset != {
            "zenodo_record_doi": "10.5281/zenodo.16813857",
            "api_locator": "https://zenodo.org/api/records/16813857",
            "access_right": "open",
            "license": "CC-BY-4.0",
            "license_verified_at": "2026-08-13",
            "license_verification_method": "Zenodo public record API metadata",
        }:
            raise R4PMC13106918SourceAuditError("dataset declaration is invalid")
        scope = _mapping(registry.get("source_scope"), "source scope")
        if set(scope) != {
            "source_id",
            "laboratory_anchor",
            "source_lineage",
            "biofluid",
            "nanoparticle",
            "analysis_role",
            "biological_independence",
            "prohibited_interpretations",
        } or (
            scope.get("source_id") != "PMC13106918_RCSI_DCU_SILICA_CORONA"
            or scope.get("laboratory_anchor")
            != "Royal College of Surgeons in Ireland and Dublin City University"
            or scope.get("source_lineage") != "NEW_TO_CURRENT_R3_ANCHORS"
            or scope.get("biofluid") != "pooled human plasma from eight healthy donors"
            or scope.get("nanoparticle") != "silica nanoparticles"
            or scope.get("analysis_role") != "SEPARATE_R4_TECHNICAL_CORONA_CANDIDATE"
            or scope.get("biological_independence")
            != "one pooled material with four technical replicates per digestion protocol"
            or not isinstance(scope.get("prohibited_interpretations"), list)
            or len(scope["prohibited_interpretations"]) != 5
        ):
            raise R4PMC13106918SourceAuditError("source scope is invalid")

        assets = registry.get("source_assets")
        if not isinstance(assets, list) or len(assets) != 4:
            raise R4PMC13106918SourceAuditError("source assets are invalid")
        paths: dict[str, Path] = {}
        asset_declarations: dict[str, dict[str, Any]] = {}
        for item in assets:
            item = _mapping(item, "source asset")
            allowed = {
                "asset_id",
                "relative_path",
                "sha256",
                "expected_bytes",
                "source_url",
                "source_md5",
            }
            required = {"asset_id", "relative_path", "sha256", "expected_bytes"}
            if set(item) - allowed or not required.issubset(item):
                raise R4PMC13106918SourceAuditError("source asset fields are invalid")
            asset_id = _string(item.get("asset_id"), "source asset ID")
            path = self._under(self.assets_root, _string(item.get("relative_path"), asset_id), asset_id)
            expected_bytes = item.get("expected_bytes")
            if (
                asset_id in paths
                or isinstance(expected_bytes, bool)
                or not isinstance(expected_bytes, int)
                or path.stat().st_size != expected_bytes
                or _sha256(path) != _checksum(item.get("sha256"), asset_id)
            ):
                raise R4PMC13106918SourceAuditError("source asset checksum differs")
            paths[asset_id] = path
            asset_declarations[asset_id] = item
        if set(paths) != {"maxquant_zip", "protein_groups", "summary", "parameters"}:
            raise R4PMC13106918SourceAuditError("source assets are incomplete")

        with zipfile.ZipFile(paths["maxquant_zip"]) as archive:
            required = {
                "protein_groups": "MaxQuant_txt/proteinGroups.txt",
                "summary": "MaxQuant_txt/summary.txt",
                "parameters": "MaxQuant_txt/parameters.txt",
            }
            for asset_id, name in required.items():
                if name not in archive.namelist() or archive.read(name) != paths[asset_id].read_bytes():
                    raise R4PMC13106918SourceAuditError("official extraction differs from source package")

        reference = _mapping(registry.get("r3_reference_asset"), "R3 reference asset")
        if set(reference) != {"relative_path", "sha256"}:
            raise R4PMC13106918SourceAuditError("R3 reference asset fields are invalid")
        feature_path = self._under(
            self.root, _string(reference.get("relative_path"), "R3 reference asset"), "R3 reference asset"
        )
        if _sha256(feature_path) != _checksum(reference.get("sha256"), "R3 reference asset"):
            raise R4PMC13106918SourceAuditError("R3 reference asset checksum differs")

        if _mapping(registry.get("table_contract"), "table contract") != {
            "relative_table_path": "extracted/MaxQuant_txt/proteinGroups.txt",
            "delimiter": "tab",
            "header_row": 1,
            "expected_protein_group_rows": 751,
            "expected_column_count": 196,
            "protein_group_id_column": "Majority protein IDs",
            "lfq_column_prefix": "LFQ intensity ",
            "expected_measurement_batch_count": 20,
            "condition_labels": ["iST", "Pmax", "RapiG", "STD", "Strap"],
            "technical_replicates_per_condition": 4,
        }:
            raise R4PMC13106918SourceAuditError("table contract is invalid")
        if _mapping(registry.get("quantification_contract"), "quantification contract") != {
            "source_accession_policy": "split Majority protein IDs on semicolons, remove CON__ tokens, retain only exactly one accession present in the frozen R3 feature table",
            "author_quantity_type": "LFQ_INTENSITY",
            "rank_eligibility": "strictly positive finite LFQ intensity, Reverse and Potential contaminant flags absent, one uniquely mapped R3 target",
            "numeric_zero_policy": "retain as NUMERIC_ZERO and exclude from rank; never impute",
            "missing_policy": "retain blank/NA as SOURCE_NA or SOURCE_BLANK and exclude from rank; never impute",
            "raw_scale_cross_study_use": "PROHIBITED",
        }:
            raise R4PMC13106918SourceAuditError("quantification contract is invalid")
        if _mapping(registry.get("admission_minimums"), "admission minimums") != {
            "minimum_positive_proteins_per_measurement_batch": 10,
            "minimum_rank_qualified_measurement_batch_count": 12,
            "expected_conservative_rank_qualified_measurement_batch_count": 16,
            "expected_unique_target_count": 53,
            "biological_unit_count": 1,
            "laboratory_anchor_count": 1,
        }:
            raise R4PMC13106918SourceAuditError("admission minimums are invalid")
        return registry, paths, feature_path

    @staticmethod
    def _feature_accessions(path: Path) -> set[str]:
        with path.open(newline="", encoding="utf-8") as stream:
            fields = csv.DictReader(stream)
            if fields.fieldnames != [
                "canonical_accession",
                "sequence_length",
                "estimated_molecular_mass_da",
                "hydrophobic_fraction",
                "aromatic_fraction",
                "acidic_fraction",
                "basic_fraction",
                "cysteine_fraction",
                "proline_fraction",
                "mean_kyte_doolittle",
                "aa_fraction_A",
                "aa_fraction_C",
                "aa_fraction_D",
                "aa_fraction_E",
                "aa_fraction_F",
                "aa_fraction_G",
                "aa_fraction_H",
                "aa_fraction_I",
                "aa_fraction_K",
                "aa_fraction_L",
                "aa_fraction_M",
                "aa_fraction_N",
                "aa_fraction_P",
                "aa_fraction_Q",
                "aa_fraction_R",
                "aa_fraction_S",
                "aa_fraction_T",
                "aa_fraction_V",
                "aa_fraction_W",
                "aa_fraction_Y",
            ]:
                raise R4PMC13106918SourceAuditError("frozen R3 feature table header differs")
            accessions = {row["canonical_accession"] for row in fields}
        if len(accessions) != 99:
            raise R4PMC13106918SourceAuditError("frozen R3 feature population differs")
        return accessions

    @staticmethod
    def _source_accession(value: Any, features: set[str]) -> str | None:
        tokens = {
            token.strip()
            for token in str(value or "").split(";")
            if token.strip() and not token.strip().startswith("CON__")
        }
        mapped = tokens & features
        return next(iter(mapped)) if len(mapped) == 1 else None

    @staticmethod
    def _state(raw: Any) -> tuple[str, str, bool]:
        if raw is None or not str(raw).strip():
            return "SOURCE_BLANK", "", False
        if str(raw).strip().upper() == "NA":
            return "SOURCE_NA", "", False
        try:
            numeric = float(str(raw).strip())
        except ValueError as exc:
            raise R4PMC13106918SourceAuditError("LFQ intensity must be numeric or blank") from exc
        if not math.isfinite(numeric):
            raise R4PMC13106918SourceAuditError("LFQ intensity must be finite")
        rendered = format(numeric, ".17g")
        if numeric == 0.0:
            return "NUMERIC_ZERO", rendered, False
        if numeric < 0.0:
            return "NEGATIVE_FINITE", rendered, False
        return "POSITIVE_FINITE", rendered, True

    def _cells(
        self, source_path: Path, feature_path: Path
    ) -> tuple[list[dict[str, str]], dict[str, Any]]:
        features = self._feature_accessions(feature_path)
        with source_path.open(newline="", encoding="utf-8") as stream:
            reader = csv.DictReader(stream, delimiter="\t")
            if reader.fieldnames is None:
                raise R4PMC13106918SourceAuditError("proteinGroups header is missing")
            if len(reader.fieldnames) != 196:
                raise R4PMC13106918SourceAuditError("proteinGroups column count differs")
            lfq_columns = [field for field in reader.fieldnames if field.startswith("LFQ intensity ")]
            expected = [
                f"LFQ intensity {condition}_{replicate}"
                for condition in ("iST", "Pmax", "RapiG", "STD", "Strap")
                for replicate in range(1, 5)
            ]
            if lfq_columns != expected:
                raise R4PMC13106918SourceAuditError("LFQ measurement columns differ")
            rows = list(reader)
        if len(rows) != 751:
            raise R4PMC13106918SourceAuditError("proteinGroups row count differs")

        cells: list[dict[str, str]] = []
        seen_targets: set[str] = set()
        source_row_count = 0
        for source_row, row in enumerate(rows, start=2):
            source_row_count += 1
            accession = self._source_accession(row.get("Majority protein IDs"), features)
            if accession is None or row.get("Reverse", "").strip() == "+" or row.get(
                "Potential contaminant", ""
            ).strip() == "+":
                continue
            if accession in seen_targets:
                raise R4PMC13106918SourceAuditError("a target maps to multiple qualifying protein groups")
            seen_targets.add(accession)
            for column_index, column in enumerate(lfq_columns, start=1):
                condition, replicate = column.removeprefix("LFQ intensity ").rsplit("_", 1)
                state, rendered, rank_eligible = self._state(row.get(column))
                cells.append(
                    {
                        "source_id": "PMC13106918_RCSI_DCU_SILICA_CORONA",
                        "laboratory_anchor": "Royal College of Surgeons in Ireland and Dublin City University",
                        "source_asset_id": "protein_groups",
                        "source_worksheet": "proteinGroups.txt",
                        "source_row": str(source_row),
                        "source_coordinate": f"{column}{source_row}",
                        "source_identifier": row.get("Majority protein IDs", ""),
                        "canonical_accession": accession,
                        "measurement_batch_id": f"R4_PMC13106918_{condition}_{replicate}",
                        "biological_unit_id": "POOLED_HUMAN_PLASMA_8_DONORS",
                        "condition_label": condition,
                        "analysis_candidate_eligible": "true",
                        "author_quantity_type": "LFQ_INTENSITY",
                        "author_numeric_value": rendered,
                        "author_value_state": state,
                        "rank_target_eligible": "true" if rank_eligible else "false",
                    }
                )
        if len(seen_targets) != 53 or len(cells) != 1060:
            raise R4PMC13106918SourceAuditError("strict source target accounting differs")
        by_batch: dict[str, list[dict[str, str]]] = defaultdict(list)
        for cell in cells:
            by_batch[cell["measurement_batch_id"]].append(cell)
        positive_by_batch = {
            batch: sum(cell["rank_target_eligible"] == "true" for cell in values)
            for batch, values in by_batch.items()
        }
        qualified = sum(count >= 10 for count in positive_by_batch.values())
        if len(by_batch) != 20 or qualified != 16:
            raise R4PMC13106918SourceAuditError("rank-qualified batch accounting differs")
        return cells, {
            "protein_row_count": source_row_count,
            "measurement_batch_count": len(by_batch),
            "rank_qualified_measurement_batch_count": qualified,
            "shared_canonical_protein_count": len(seen_targets),
            "source_cell_count": len(cells),
            "positive_source_cell_count": sum(
                cell["rank_target_eligible"] == "true" for cell in cells
            ),
            "positive_by_batch": dict(sorted(positive_by_batch.items())),
        }

    def run(self, *, strict: bool = False) -> R4PMC13106918SourceAuditSummary:
        if not strict:
            raise R4PMC13106918SourceAuditError("PMC13106918 source audit requires --strict")
        if self.output_root.exists():
            raise R4PMC13106918SourceAuditError("PMC13106918 source audit already executed")
        registry, paths, feature_path = self._registry()
        cells, totals = self._cells(paths["protein_groups"], feature_path)
        derived = self.assets_root / self.DERIVED_RELATIVE
        if derived.exists():
            raise R4PMC13106918SourceAuditError("derived source cell map already exists")
        derived.parent.mkdir(parents=True, exist_ok=True)
        with derived.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=self.SOURCE_CELL_FIELDS)
            writer.writeheader()
            writer.writerows(cells)
        self.output_root.mkdir(parents=True, exist_ok=False)
        report = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "status": self.STATUS,
            "evidence_class": "DEVELOPMENT_OBSERVATION",
            "allowed_claim_level": "EXPLORATORY",
            "model_fitted": False,
            "independent_validation": False,
            "external_scientific_reproduction": False,
            "scientific_submission_ready": False,
            "source_assets": {
                item["asset_id"]: {
                    "relative_path": item["relative_path"],
                    "sha256": _sha256(paths[item["asset_id"]]),
                }
                for item in registry["source_assets"]
            },
            "r3_reference_asset": {
                "relative_path": registry["r3_reference_asset"]["relative_path"],
                "sha256": _sha256(feature_path),
            },
            "source_cell_map": {"relative_path": self.DERIVED_RELATIVE, "sha256": _sha256(derived)},
            **totals,
            "biological_unit_count": 1,
            "laboratory_anchor_count": 1,
            "claim_boundary": registry["claim_boundary"],
        }
        report_path = self.output_root / "pmc13106918_source_audit_report.json"
        self._write(report_path, report)
        receipt = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "status": self.STATUS,
            "report": {"relative_path": report_path.name, "sha256": _sha256(report_path)},
            "source_cell_map": report["source_cell_map"],
            "model_fitted": False,
            "independent_validation": False,
            "external_scientific_reproduction": False,
            "scientific_submission_ready": False,
        }
        receipt_path = self.output_root / "pmc13106918_source_audit_receipt.json"
        self._write(receipt_path, receipt)
        return R4PMC13106918SourceAuditSummary(
            len(paths),
            totals["protein_row_count"],
            totals["measurement_batch_count"],
            totals["rank_qualified_measurement_batch_count"],
            totals["shared_canonical_protein_count"],
            totals["source_cell_count"],
            totals["positive_source_cell_count"],
            1,
            1,
            receipt_path,
        )

    def verify(self) -> R4PMC13106918SourceAuditSummary:
        registry, paths, feature_path = self._registry()
        report_path = self.output_root / "pmc13106918_source_audit_report.json"
        receipt_path = self.output_root / "pmc13106918_source_audit_receipt.json"
        report = self._json(report_path, "PMC13106918 audit report")
        receipt = self._json(receipt_path, "PMC13106918 audit receipt")
        if (
            report.get("status") != self.STATUS
            or receipt.get("status") != self.STATUS
            or receipt.get("report", {}).get("sha256") != _sha256(report_path)
        ):
            raise R4PMC13106918SourceAuditError("audit receipt differs")
        cell_map = self._under(
            self.assets_root,
            _string(report.get("source_cell_map", {}).get("relative_path"), "source cell map path"),
            "source cell map",
        )
        if report["source_cell_map"].get("sha256") != _sha256(cell_map):
            raise R4PMC13106918SourceAuditError("source cell map checksum differs")
        with cell_map.open(newline="", encoding="utf-8") as stream:
            rows = list(csv.DictReader(stream))
        if (set(rows[0]) if rows else set()) != set(self.SOURCE_CELL_FIELDS):
            raise R4PMC13106918SourceAuditError("source cell map fields differ")
        _, totals = self._cells(paths["protein_groups"], feature_path)
        for key, value in totals.items():
            if report.get(key) != value:
                raise R4PMC13106918SourceAuditError(f"audit accounting differs for {key}")
        if len(rows) != report["source_cell_count"] or sum(
            row["rank_target_eligible"] == "true" for row in rows
        ) != report["positive_source_cell_count"]:
            raise R4PMC13106918SourceAuditError("source cell accounting differs")
        if report.get("r3_reference_asset", {}).get("sha256") != _sha256(feature_path):
            raise R4PMC13106918SourceAuditError("R3 reference checksum differs")
        return R4PMC13106918SourceAuditSummary(
            len(paths),
            totals["protein_row_count"],
            totals["measurement_batch_count"],
            totals["rank_qualified_measurement_batch_count"],
            totals["shared_canonical_protein_count"],
            totals["source_cell_count"],
            totals["positive_source_cell_count"],
            int(report["biological_unit_count"]),
            int(report["laboratory_anchor_count"]),
            receipt_path,
        )
