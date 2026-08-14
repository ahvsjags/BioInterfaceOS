"""Audit the CC0 PXD064962 proteinGroups table for low-coverage sensitivity work.

PXD064962 is a useful public, row-level proteomics source, but it does not
meet the frozen primary R4 coverage rule in most batches.  This module keeps
the source auditable without silently lowering the primary endpoint: it emits
one traceable row for every frozen-target/source-column pairing, preserves
zeros and blanks, and reports both raw target cells and batch-level target
observations.  It does not fit a model.
"""

from __future__ import annotations

import csv
import json
import math
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from biointerfaceos.r3_uniprot_mapping import _canonical, _checksum, _mapping, _sha256, _string


class R4PXD064962SourceAuditError(RuntimeError):
    """Raised when the PXD064962 source contract is not reproducible."""


@dataclass(frozen=True)
class R4PXD064962SourceAuditSummary:
    """Accounting summary for the low-coverage CC0 source candidate."""

    source_cell_count: int
    positive_source_cell_count: int
    target_source_cell_count: int
    target_positive_source_cell_count: int
    target_positive_batch_observation_count: int
    unique_target_source_coordinate_count: int
    ambiguous_target_source_coordinate_count: int
    ambiguous_target_accession_pair_excess: int
    positive_shared_canonical_protein_count: int
    biological_unit_count: int
    measurement_batch_count: int
    rank_qualified_measurement_batch_count: int
    shared_canonical_protein_count: int
    technical_replicate_count: int
    receipt_path: Path


class R4PXD064962SourceAuditWorkflow:
    """Create and verify the PXD064962 source-cell audit receipt."""

    AUDIT_ID = "bioif-r4-pxd064962-ucd-source-audit-v1.0.0"
    REGISTRY_RELATIVE = "docs/data/R4_T188_PXD064962_UCD_SOURCE_REGISTRY.json"
    OUTPUT_RELATIVE = "reports/review_round_4/pxd064962_ucd_source_audit/v1.0.0"
    DERIVED_RELATIVE = "derived/R4_PXD064962_UCD_source_cell_map.csv"
    STATUS = "ADMITTED_R4_LOW_COVERAGE_CC0_SENSITIVITY_CANDIDATE"
    SAMPLE_PATTERN = re.compile(r"^(PT|T)_(D[13])_([^_]+)_([12])_(.+)$")
    SOURCE_CELL_FIELDS = (
        "source_id",
        "laboratory_anchor",
        "source_asset_id",
        "source_row",
        "source_column",
        "source_coordinate",
        "source_sample",
        "canonical_accession",
        "source_identifier",
        "measurement_batch_id",
        "biological_unit_id",
        "cohort_label",
        "timepoint",
        "technical_replicate_id",
        "author_numeric_value",
        "author_value_state",
        "rank_target_eligible",
    )

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
            return _mapping(json.loads(path.read_text(encoding="utf-8")), label)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise R4PXD064962SourceAuditError(f"cannot parse {label}") from exc

    @staticmethod
    def _write(path: Path, value: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(_canonical(value))

    @staticmethod
    def _under(root: Path, relative_path: str, label: str) -> Path:
        if "\\" in relative_path:
            raise R4PXD064962SourceAuditError(f"{label} must use POSIX separators")
        pure = PurePosixPath(relative_path)
        if pure.is_absolute() or not pure.parts or ".." in pure.parts:
            raise R4PXD064962SourceAuditError(f"{label} escapes its root")
        path = (root / Path(*pure.parts)).resolve(strict=False)
        if not path.is_relative_to(root) or not path.is_file():
            raise R4PXD064962SourceAuditError(f"{label} is missing or outside its root")
        return path

    def _registry(self) -> tuple[dict[str, Any], Path, Path, Path, Path]:
        registry = self._json(self.registry_path, "R4 T188 source registry")
        expected = {
            "schema_version",
            "audit_id",
            "evaluated_at",
            "evidence_class",
            "allowed_claim_level",
            "dataset",
            "source_scope",
            "source_assets",
            "r3_reference_asset",
            "table_contract",
            "quantification_contract",
            "admission_minimums",
            "claim_boundary",
        }
        if (
            set(registry) != expected
            or registry.get("schema_version") != 1
            or registry.get("audit_id") != self.AUDIT_ID
        ):
            raise R4PXD064962SourceAuditError("T188 registry fields are invalid")
        if registry.get("evidence_class") != "EXPLORATORY_SENSITIVITY":
            raise R4PXD064962SourceAuditError("T188 evidence class is invalid")
        if registry.get("allowed_claim_level") != "EXPLORATORY":
            raise R4PXD064962SourceAuditError("T188 claim level is invalid")
        dataset = _mapping(registry["dataset"], "T188 dataset")
        if dataset.get("accession") != "PXD064962" or dataset.get("license") != "CC0":
            raise R4PXD064962SourceAuditError("T188 dataset license or accession is invalid")
        scope = _mapping(registry["source_scope"], "T188 source scope")
        if scope.get("source_id") != "PXD064962_UCD_EVENT":
            raise R4PXD064962SourceAuditError("T188 source scope is invalid")
        assets = registry["source_assets"]
        if not isinstance(assets, list) or len(assets) != 3:
            raise R4PXD064962SourceAuditError("T188 source assets are invalid")
        by_id: dict[str, Path] = {}
        for item_value in assets:
            item = _mapping(item_value, "T188 source asset")
            asset_id = _string(item.get("asset_id"), "T188 asset ID")
            if asset_id in by_id:
                raise R4PXD064962SourceAuditError("T188 source asset IDs are duplicated")
            asset = self._under(
                self.assets_root,
                _string(item.get("relative_path"), "T188 source asset path"),
                "T188 source asset",
            )
            if asset.stat().st_size != int(item.get("expected_bytes", -1)):
                raise R4PXD064962SourceAuditError(f"{asset_id} byte count differs")
            if _sha256(asset) != _checksum(item.get("sha256"), f"{asset_id} checksum"):
                raise R4PXD064962SourceAuditError(f"{asset_id} checksum differs")
            by_id[asset_id] = asset
        if set(by_id) != {"protein_groups", "summary", "pride_project_metadata"}:
            raise R4PXD064962SourceAuditError("T188 source asset IDs are incomplete")
        reference = _mapping(registry["r3_reference_asset"], "T188 R3 reference asset")
        reference_path = self._under(
            self.root,
            _string(reference.get("relative_path"), "T188 R3 reference path"),
            "T188 R3 reference asset",
        )
        if _sha256(reference_path) != _checksum(reference.get("sha256"), "T188 R3 reference checksum"):
            raise R4PXD064962SourceAuditError("T188 R3 reference checksum differs")
        return (
            registry,
            by_id["protein_groups"],
            by_id["summary"],
            by_id["pride_project_metadata"],
            reference_path,
        )

    @staticmethod
    def _features(path: Path) -> set[str]:
        try:
            with path.open(newline="", encoding="utf-8-sig") as stream:
                features = {row["canonical_accession"] for row in csv.DictReader(stream)}
        except (OSError, KeyError, csv.Error) as exc:
            raise R4PXD064962SourceAuditError("cannot read R3 target table") from exc
        if len(features) != 99:
            raise R4PXD064962SourceAuditError("R3 target table size differs")
        return features

    @staticmethod
    def _number(value: str) -> float | None:
        value = value.strip()
        if not value:
            return None
        try:
            number = float(value)
        except ValueError as exc:
            raise R4PXD064962SourceAuditError("LFQ value is not numeric") from exc
        if not math.isfinite(number) or number < 0:
            raise R4PXD064962SourceAuditError("LFQ value is not finite and non-negative")
        return number

    @classmethod
    def _sample_contract(cls, sample: str) -> dict[str, str]:
        match = cls.SAMPLE_PATTERN.fullmatch(sample)
        if match is None:
            raise R4PXD064962SourceAuditError(f"sample label does not match frozen contract: {sample}")
        cohort, timepoint, patient, replicate, injection = match.groups()
        batch = f"{cohort}_{timepoint}_{patient}"
        return {
            "biological_unit_id": batch,
            "measurement_batch_id": batch,
            "cohort_label": "PRETERM" if cohort == "PT" else "TERM",
            "timepoint": timepoint,
            "technical_replicate_id": replicate,
            "injection_label": injection,
        }

    def _cells(
        self, asset: Path, feature_path: Path, registry: dict[str, Any]
    ) -> tuple[list[dict[str, str]], dict[str, Any]]:
        csv.field_size_limit(10**9)
        features = self._features(feature_path)
        target_rows: list[tuple[int, str, set[str]]] = []
        source_cell_count = 0
        positive_source_cell_count = 0
        target_positive_source_cell_count = 0
        samples: list[tuple[str, str, dict[str, str]]] = []
        with asset.open(newline="", encoding="utf-8-sig") as stream:
            reader = csv.DictReader(stream, delimiter="\t")
            if reader.fieldnames is None:
                raise R4PXD064962SourceAuditError("proteinGroups header is missing")
            measurement_columns = [field for field in reader.fieldnames if field.startswith("LFQ intensity ")]
            contract = _mapping(registry["table_contract"], "T188 table contract")
            admission = _mapping(registry["admission_minimums"], "T188 admission minimums")
            minimum_positive_targets = int(admission["minimum_positive_shared_proteins_per_measurement_batch"])
            if len(measurement_columns) != contract["expected_lfq_columns"]:
                raise R4PXD064962SourceAuditError("LFQ column count differs")
            for column in measurement_columns:
                sample = column.removeprefix("LFQ intensity ")
                samples.append((column, sample, self._sample_contract(sample)))
            rows = list(reader)
        if len(rows) != contract["expected_protein_group_rows"]:
            raise R4PXD064962SourceAuditError("protein-group row count differs")
        for row_number, row in enumerate(rows, start=2):
            identifiers = {value.strip() for value in row.get("Protein IDs", "").split(";") if value.strip()}
            target_accessions = identifiers & features
            for column, sample, _sample_info in samples:
                value = self._number(row.get(column, ""))
                source_cell_count += 1
                if value is not None and value > 0:
                    positive_source_cell_count += 1
                if not target_accessions:
                    continue
                if value is not None and value > 0:
                    target_positive_source_cell_count += len(target_accessions)
                target_rows.append((row_number, sample, target_accessions))
        rows_out: list[dict[str, str]] = []
        batch_targets: dict[str, set[str]] = defaultdict(set)
        target_source_cell_count = 0
        for row_number, sample, target_accessions in target_rows:
            column = next(column for column, sample_name, _ in samples if sample_name == sample)
            sample_info = next(info for _, sample_name, info in samples if sample_name == sample)
            raw_value = rows[row_number - 2].get(column, "")
            value = self._number(raw_value)
            state = "SOURCE_BLANK" if value is None else ("EXPLICIT_ZERO" if value == 0 else "POSITIVE")
            eligible = value is not None and value > 0
            for accession in sorted(target_accessions):
                target_source_cell_count += 1
                if eligible:
                    batch_targets[sample_info["measurement_batch_id"]].add(accession)
                rows_out.append(
                    {
                        "source_id": registry["source_scope"]["source_id"],
                        "laboratory_anchor": registry["source_scope"]["laboratory_anchor"],
                        "source_asset_id": "protein_groups",
                        "source_row": str(row_number),
                        "source_column": column,
                        "source_coordinate": f"{column}:{row_number}",
                        "source_sample": sample,
                        "canonical_accession": accession,
                        "source_identifier": rows[row_number - 2].get("Protein IDs", ""),
                        "measurement_batch_id": sample_info["measurement_batch_id"],
                        "biological_unit_id": sample_info["biological_unit_id"],
                        "cohort_label": sample_info["cohort_label"],
                        "timepoint": sample_info["timepoint"],
                        "technical_replicate_id": sample_info["technical_replicate_id"],
                        "author_numeric_value": "" if value is None else repr(value),
                        "author_value_state": state,
                        "rank_target_eligible": "true" if eligible else "false",
                    }
                )
        unique_batch_info = {info["measurement_batch_id"]: info for _, _, info in samples}
        counts = sorted(len(batch_targets.get(batch, set())) for batch in unique_batch_info)
        if counts != contract["expected_batch_target_counts"]:
            raise R4PXD064962SourceAuditError("batch target qualification counts differ")
        if source_cell_count != contract["expected_source_cell_count"]:
            raise R4PXD064962SourceAuditError("source-cell count differs")
        if positive_source_cell_count != contract["expected_positive_source_cell_count"]:
            raise R4PXD064962SourceAuditError("positive source-cell count differs")
        if target_source_cell_count != contract["expected_target_source_cell_count"]:
            raise R4PXD064962SourceAuditError("target source-cell count differs")
        if target_positive_source_cell_count != contract["expected_target_positive_source_cell_count"]:
            raise R4PXD064962SourceAuditError("target positive source-cell count differs")
        if len(batch_targets) != contract["expected_measurement_batches"]:
            raise R4PXD064962SourceAuditError("measurement-batch count differs")
        positive_batch_observations = sum(len(values) for values in batch_targets.values())
        if positive_batch_observations != contract["expected_target_positive_batch_observations"]:
            raise R4PXD064962SourceAuditError("batch-level target observation count differs")
        if len({row["canonical_accession"] for row in rows_out}) != contract["expected_shared_target_count"]:
            raise R4PXD064962SourceAuditError("shared target count differs")
        source_coordinates = {row["source_coordinate"] for row in rows_out}
        target_accessions_by_coordinate: dict[str, set[str]] = defaultdict(set)
        for row in rows_out:
            target_accessions_by_coordinate[row["source_coordinate"]].add(row["canonical_accession"])
        ambiguous_coordinates = {
            coordinate for coordinate, accessions in target_accessions_by_coordinate.items() if len(accessions) > 1
        }
        ambiguous_pair_excess = sum(
            len(accessions) - 1 for accessions in target_accessions_by_coordinate.values() if len(accessions) > 1
        )
        positive_shared_targets = {
            row["canonical_accession"] for row in rows_out if row["rank_target_eligible"] == "true"
        }
        if (
            len(source_coordinates) != contract["expected_unique_target_source_coordinates"]
            or len(ambiguous_coordinates) != contract["expected_ambiguous_target_source_coordinates"]
            or ambiguous_pair_excess != contract["expected_ambiguous_target_accession_pair_excess"]
            or len(positive_shared_targets) != contract["expected_positive_shared_target_count"]
        ):
            raise R4PXD064962SourceAuditError("target mapping ambiguity accounting differs")
        summary = {
            "source_cell_count": source_cell_count,
            "positive_source_cell_count": positive_source_cell_count,
            "target_source_cell_count": target_source_cell_count,
            "target_positive_source_cell_count": target_positive_source_cell_count,
            "target_positive_batch_observation_count": positive_batch_observations,
            "unique_target_source_coordinate_count": len(source_coordinates),
            "ambiguous_target_source_coordinate_count": len(ambiguous_coordinates),
            "ambiguous_target_accession_pair_excess": ambiguous_pair_excess,
            "positive_shared_canonical_protein_count": len(positive_shared_targets),
            "biological_unit_count": len({info["biological_unit_id"] for _, _, info in samples}),
            "measurement_batch_count": len(unique_batch_info),
            "rank_qualified_measurement_batch_count": sum(
                len(values) >= minimum_positive_targets for values in batch_targets.values()
            ),
            "shared_canonical_protein_count": len({row["canonical_accession"] for row in rows_out}),
            "technical_replicate_count": len({info["technical_replicate_id"] for _, _, info in samples}),
            "batch_target_counts": counts,
        }
        return rows_out, summary

    def run(self, *, strict: bool = False) -> R4PXD064962SourceAuditSummary:
        if not strict:
            raise R4PXD064962SourceAuditError("R4 T188 source audit requires --strict")
        if self.output_root.exists():
            raise R4PXD064962SourceAuditError("R4 T188 source audit already executed")
        (
            registry,
            asset,
            summary_asset,
            pride_metadata_asset,
            feature_path,
        ) = self._registry()
        rows, accounting = self._cells(asset, feature_path, registry)
        derived = self.assets_root / self.DERIVED_RELATIVE
        if derived.exists():
            raise R4PXD064962SourceAuditError("T188 source-cell map already exists")
        derived.parent.mkdir(parents=True, exist_ok=True)
        with derived.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=self.SOURCE_CELL_FIELDS, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        self.output_root.mkdir(parents=True, exist_ok=False)
        report = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "status": self.STATUS,
            "registry": {
                "relative_path": self.registry_path.relative_to(self.root).as_posix(),
                "sha256": _sha256(self.registry_path),
            },
            "evidence_class": registry["evidence_class"],
            "allowed_claim_level": registry["allowed_claim_level"],
            "model_fitted": False,
            "independent_validation": False,
            "external_scientific_reproduction": False,
            "scientific_submission_ready": False,
            "source_asset": {
                "relative_path": "proteinGroups.txt",
                "sha256": _sha256(asset),
                "summary_relative_path": "summary.txt",
                "summary_sha256": _sha256(summary_asset),
                "pride_metadata_relative_path": "pride_project_metadata.json",
                "pride_metadata_sha256": _sha256(pride_metadata_asset),
            },
            "r3_reference_asset": {
                "relative_path": registry["r3_reference_asset"]["relative_path"],
                "sha256": _sha256(feature_path),
            },
            "source_cell_map": {
                "relative_path": self.DERIVED_RELATIVE,
                "sha256": _sha256(derived),
            },
            **accounting,
            "primary_ood_minimum_met": False,
            "secondary_low_coverage_sensitivity_candidate": True,
            "claim_boundary": registry["claim_boundary"],
        }
        report_path = self.output_root / "pxd064962_ucd_source_audit_report.json"
        self._write(report_path, report)
        receipt = {
            "schema_version": 1,
            "audit_id": self.AUDIT_ID,
            "status": self.STATUS,
            "registry": report["registry"],
            "report": {"relative_path": report_path.name, "sha256": _sha256(report_path)},
            "source_cell_map": report["source_cell_map"],
            "primary_ood_minimum_met": False,
            "secondary_low_coverage_sensitivity_candidate": True,
            "model_fitted": False,
            "independent_validation": False,
            "external_scientific_reproduction": False,
            "scientific_submission_ready": False,
        }
        receipt_path = self.output_root / "pxd064962_ucd_source_audit_receipt.json"
        self._write(receipt_path, receipt)
        return R4PXD064962SourceAuditSummary(
            source_cell_count=accounting["source_cell_count"],
            positive_source_cell_count=accounting["positive_source_cell_count"],
            target_source_cell_count=accounting["target_source_cell_count"],
            target_positive_source_cell_count=accounting["target_positive_source_cell_count"],
            target_positive_batch_observation_count=accounting["target_positive_batch_observation_count"],
            unique_target_source_coordinate_count=accounting["unique_target_source_coordinate_count"],
            ambiguous_target_source_coordinate_count=accounting["ambiguous_target_source_coordinate_count"],
            ambiguous_target_accession_pair_excess=accounting["ambiguous_target_accession_pair_excess"],
            positive_shared_canonical_protein_count=accounting["positive_shared_canonical_protein_count"],
            biological_unit_count=accounting["biological_unit_count"],
            measurement_batch_count=accounting["measurement_batch_count"],
            rank_qualified_measurement_batch_count=accounting["rank_qualified_measurement_batch_count"],
            shared_canonical_protein_count=accounting["shared_canonical_protein_count"],
            technical_replicate_count=accounting["technical_replicate_count"],
            receipt_path=receipt_path,
        )

    def verify(self) -> R4PXD064962SourceAuditSummary:
        (
            registry,
            asset,
            summary_asset,
            pride_metadata_asset,
            feature_path,
        ) = self._registry()
        rows, accounting = self._cells(asset, feature_path, registry)
        report_path = self.output_root / "pxd064962_ucd_source_audit_report.json"
        receipt_path = self.output_root / "pxd064962_ucd_source_audit_receipt.json"
        report = self._json(report_path, "T188 source audit report")
        receipt = self._json(receipt_path, "T188 source audit receipt")
        derived = self._under(self.assets_root, self.DERIVED_RELATIVE, "T188 source-cell map")
        with derived.open(newline="", encoding="utf-8") as stream:
            observed_rows = list(csv.DictReader(stream))
        if observed_rows != rows:
            raise R4PXD064962SourceAuditError("T188 source-cell map differs")
        if (
            report.get("audit_id") != self.AUDIT_ID
            or report.get("status") != self.STATUS
            or report.get("registry", {}).get("relative_path") != self.registry_path.relative_to(self.root).as_posix()
            or report.get("registry", {}).get("sha256") != _sha256(self.registry_path)
            or report.get("source_cell_map", {}).get("sha256") != _sha256(derived)
            or report.get("source_asset", {}).get("sha256") != _sha256(asset)
            or report.get("source_asset", {}).get("summary_sha256") != _sha256(summary_asset)
            or report.get("source_asset", {}).get("pride_metadata_sha256") != _sha256(pride_metadata_asset)
            or receipt.get("audit_id") != self.AUDIT_ID
            or receipt.get("status") != self.STATUS
            or receipt.get("registry") != report.get("registry")
            or receipt.get("report", {}).get("sha256") != _sha256(report_path)
            or receipt.get("model_fitted") is not False
            or receipt.get("independent_validation") is not False
            or receipt.get("external_scientific_reproduction") is not False
            or receipt.get("scientific_submission_ready") is not False
        ):
            raise R4PXD064962SourceAuditError("T188 receipt is invalid")
        return R4PXD064962SourceAuditSummary(
            source_cell_count=accounting["source_cell_count"],
            positive_source_cell_count=accounting["positive_source_cell_count"],
            target_source_cell_count=accounting["target_source_cell_count"],
            target_positive_source_cell_count=accounting["target_positive_source_cell_count"],
            target_positive_batch_observation_count=accounting["target_positive_batch_observation_count"],
            unique_target_source_coordinate_count=accounting["unique_target_source_coordinate_count"],
            ambiguous_target_source_coordinate_count=accounting["ambiguous_target_source_coordinate_count"],
            ambiguous_target_accession_pair_excess=accounting["ambiguous_target_accession_pair_excess"],
            positive_shared_canonical_protein_count=accounting["positive_shared_canonical_protein_count"],
            biological_unit_count=accounting["biological_unit_count"],
            measurement_batch_count=accounting["measurement_batch_count"],
            rank_qualified_measurement_batch_count=accounting["rank_qualified_measurement_batch_count"],
            shared_canonical_protein_count=accounting["shared_canonical_protein_count"],
            technical_replicate_count=accounting["technical_replicate_count"],
            receipt_path=receipt_path,
        )


def _main() -> int:
    """Run a small standalone audit from the repository root."""
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--assets-root", type=Path, required=True)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    workflow = R4PXD064962SourceAuditWorkflow(args.root, args.assets_root)
    summary = workflow.verify() if args.verify else workflow.run(strict=args.strict)
    print(summary)
    return 0


if __name__ == "__main__":
    sys.exit(_main())
