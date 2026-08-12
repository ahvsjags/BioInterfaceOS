"""Tests for the corrective, non-admission PXD030327 source-map audit."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import pytest
from openpyxl import Workbook

from biointerfaceos.cc0_pxd030327_unit_map import (
    CC0PXD030327UnitMapError,
    CC0PXD030327UnitMapWorkflow,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fixture_root(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "repository"
    asset_dir = root / "staged"
    asset_dir.mkdir(parents=True)
    design_path = asset_dir / "design.xlsx"
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Run info"
    worksheet.append(
        ["Run", "NP", "P/NP ratio", "Replicate", "Remove from analysis", "Notes", "Incubation time"]
    )
    worksheet.append(["run1", "NP-A", 1, 1, False, None, 1])
    worksheet.append(["run2", "NP-B", 2, 2, False, None, 1])
    worksheet.append(["run3", "NP-A", 1, 1, True, None, 1])
    workbook.save(design_path)
    seven_path = asset_dir / "seven.tsv"
    ten_path = asset_dir / "ten.tsv"
    metadata = [
        "Protein.Group",
        "Protein.Ids",
        "Protein.Names",
        "Genes",
        "First.Protein.Description",
    ]
    for path, run in ((seven_path, "run1"), (ten_path, "run2")):
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle, delimiter="\t")
            writer.writerow([*metadata, f"D:\\\\raw\\\\{run}.d"])
            writer.writerow(["P1", "P1", "protein", "GENE", "description", "1.0"])
    assets = []
    for asset_id, path in (
        ("sample_table", design_path),
        ("seven_np_matrix", seven_path),
        ("ten_plate_matrix", ten_path),
    ):
        assets.append(
            {
                "asset_id": asset_id,
                "local_relative_path": str(path.relative_to(root)).replace("\\", "/"),
                "download_url": f"https://ftp.pride.ebi.ac.uk/example/{path.name}",
                "expected_bytes": path.stat().st_size,
                "sha256": _sha256(path),
            }
        )
    manifest = {
        "schema_version": 1,
        "audit_id": CC0PXD030327UnitMapWorkflow.AUDIT_ID,
        "evaluated_at": "2026-08-13T00:00:00+00:00",
        "evidence_class": "DEVELOPMENT_OBSERVATION",
        "allowed_claim_level": "EXPLORATORY",
        "source": {
            "accession": "PXD030327",
            "laboratory": "Seer Inc.",
            "license_id": "CC0-1.0",
            "project_api_url": "https://www.ebi.ac.uk/pride/ws/archive/v2/projects/PXD030327",
            "landing_url": "https://www.ebi.ac.uk/pride/archive/projects/PXD030327",
            "publication_date": "2022-09-02",
        },
        "assets": assets,
        "analysis_unit_contract": {
            "worksheet": "Run info",
            "required_columns": [
                "Run",
                "NP",
                "P/NP ratio",
                "Replicate",
                "Remove from analysis",
                "Notes",
                "Incubation time",
            ],
            "matrix_metadata_columns": metadata,
            "source_row_count": 3,
            "unexcluded_unit_count": 2,
            "excluded_row_count": 1,
            "source_np_labels": ["NP-A", "NP-B"],
            "source_ratio_values": [1, 2],
            "source_replicate_values": [1, 2],
            "matrix_run_column_counts": {"seven_np_matrix": 1, "ten_plate_matrix": 1},
            "unexcluded_matrix_match_counts": {"seven_np_matrix": 1, "ten_plate_matrix": 1},
            "unmapped_matrix_column_counts": {"seven_np_matrix": 0, "ten_plate_matrix": 0},
            "unique_matrix_run_count": 2,
            "unexcluded_units_missing_from_matrices": 0,
        },
        "target_admission": {
            "numeric_material_covariate_status": "MISSING_SOURCE_MATCHED_MATERIAL_OR_SIZE_COVARIATE",
            "source_ratio_interpretation": "SOURCE_DEFINED_NUMERIC_EXPOSURE_NOT_MATERIAL_OR_SIZE_COVARIATE",
            "categorical_np_label_status": "PROHIBITED_AS_PREDICTIVE_IDENTITY_FEATURE",
            "cross_laboratory_endpoint_status": "SINGLE_LAB_ONLY_NO_COMMON_ENDPOINT",
            "admission": "NOT_ADMITTED",
            "model_use": "PROHIBITED",
        },
    }
    manifest_path = root / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return root, manifest_path


def test_audit_verifies_source_units_without_admitting_a_target(tmp_path: Path) -> None:
    root, manifest_path = _fixture_root(tmp_path)
    workflow = CC0PXD030327UnitMapWorkflow(
        root, manifest_path=manifest_path, output_root=root / "output"
    )

    summary = workflow.run(strict=True)

    assert summary.status == "VERIFIED_SINGLE_LAB_UNIT_MAP_NOT_ADMITTED"
    assert summary.unexcluded_unit_count == 2
    assert summary.matrix_run_count == 2
    assert summary.unmapped_matrix_column_count == 0
    assert workflow.verify() == summary


def test_audit_requires_strict_mode(tmp_path: Path) -> None:
    root, manifest_path = _fixture_root(tmp_path)
    workflow = CC0PXD030327UnitMapWorkflow(
        root, manifest_path=manifest_path, output_root=root / "output"
    )

    with pytest.raises(CC0PXD030327UnitMapError, match="requires --strict"):
        workflow.run()


def test_audit_rejects_weakened_non_admission_boundary(tmp_path: Path) -> None:
    root, manifest_path = _fixture_root(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["target_admission"]["admission"] = "ADMITTED"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    workflow = CC0PXD030327UnitMapWorkflow(
        root, manifest_path=manifest_path, output_root=root / "output"
    )

    with pytest.raises(CC0PXD030327UnitMapError, match="boundary is weakened"):
        workflow.run(strict=True)


def test_audit_rejects_matrix_column_without_source_unit(tmp_path: Path) -> None:
    root, manifest_path = _fixture_root(tmp_path)
    matrix_path = root / "staged" / "seven.tsv"
    matrix_path.write_text(
        matrix_path.read_text(encoding="utf-8").replace("run1.d", "run9.d"),
        encoding="utf-8",
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["assets"][1]["expected_bytes"] = matrix_path.stat().st_size
    manifest["assets"][1]["sha256"] = _sha256(matrix_path)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    workflow = CC0PXD030327UnitMapWorkflow(
        root, manifest_path=manifest_path, output_root=root / "output"
    )

    with pytest.raises(CC0PXD030327UnitMapError, match="mapping is stale"):
        workflow.run(strict=True)
