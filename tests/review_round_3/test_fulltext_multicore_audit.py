"""Regression tests for the narrow CC-BY full-text multi-core audit."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from openpyxl import Workbook

from biointerfaceos.fulltext_multicore_audit import (
    FulltextMulticoreAuditError,
    FulltextMulticoreAuditWorkflow,
)

ROOT = Path(__file__).resolve().parents[2]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fixture(tmp_path: Path) -> tuple[Path, Path]:
    assets_root = tmp_path / "assets"
    extracted = assets_root / "extracted"
    extracted.mkdir(parents=True)
    archive = assets_root / "PMC9633814_supplementary.zip"
    archive.write_bytes(b"fixture supplementary archive")
    workbook_path = extracted / "41467_2022_34438_MOESM4_ESM.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Final Prot"
    for _ in range(4):
        sheet.append([None])
    sheet.append(list(FulltextMulticoreAuditWorkflow.EXPECTED_COLUMNS))
    for facility in range(1, 13):
        sheet.append(
            [
                f"P{facility}",
                50.0,
                5,
                3,
                2,
                f"GENE{facility}",
                1.0,
                1.1,
                1.2,
                8.0,
                facility,
            ]
        )
    workbook.save(workbook_path)
    workbook.close()
    registry = json.loads(
        (ROOT / "docs/data/R3_T144_FULLTEXT_MULTICORE_SOURCE_REGISTRY.json").read_text(
            encoding="utf-8"
        )
    )
    registry["source_assets"] = [
        {
            "asset_id": "supplementary_package_zip",
            "relative_path": "PMC9633814_supplementary.zip",
            "sha256": _sha256(archive),
            "expected_bytes": archive.stat().st_size,
        },
        {
            "asset_id": "supplementary_data_1_xlsx",
            "relative_path": "extracted/41467_2022_34438_MOESM4_ESM.xlsx",
            "sha256": _sha256(workbook_path),
            "expected_bytes": workbook_path.stat().st_size,
        },
    ]
    registry["semiquantitative_table"]["expected_data_rows"] = 12
    registry["semiquantitative_table"]["expected_facility_row_counts"] = {
        str(facility): 1 for facility in range(1, 13)
    }
    registry["semiquantitative_table"]["expected_replicate_source_cell_count"] = 36
    registry["semiquantitative_table"]["expected_numeric_replicate_value_count"] = 36
    registry["semiquantitative_table"]["expected_non_numeric_replicate_markers"] = {}
    registry_path = tmp_path / "registry.json"
    registry_path.write_text(json.dumps(registry), encoding="utf-8")
    return assets_root, registry_path


def test_fulltext_multicore_audit_writes_source_to_cell_map(tmp_path: Path) -> None:
    assets_root, registry_path = _fixture(tmp_path)
    workflow = FulltextMulticoreAuditWorkflow(
        ROOT,
        assets_root,
        registry_path=registry_path,
        output_root=tmp_path / "report",
    )

    summary = workflow.run(strict=True)

    assert summary.source_asset_count == 2
    assert summary.semiquantitative_core_count == 12
    assert summary.analysis_unit_count == 12
    assert summary.replicate_source_cell_count == 36
    assert summary.numeric_replicate_value_count == 36
    assert summary.status == "ADMITTED_TECHNICAL_CROSS_CORE_BENCHMARK_ONLY"
    source_map = assets_root / workflow.DERIVED_RELATIVE
    rows = source_map.read_text(encoding="utf-8").splitlines()
    assert len(rows) == 13
    assert "Final Prot!A6:K6" in rows[1]
    assert workflow.verify() == summary


def test_fulltext_multicore_audit_requires_strict_mode(tmp_path: Path) -> None:
    assets_root, registry_path = _fixture(tmp_path)
    workflow = FulltextMulticoreAuditWorkflow(
        ROOT, assets_root, registry_path=registry_path, output_root=tmp_path / "report"
    )

    with pytest.raises(FulltextMulticoreAuditError, match="requires --strict"):
        workflow.run()


def test_fulltext_multicore_audit_rejects_tampered_source_bytes(tmp_path: Path) -> None:
    assets_root, registry_path = _fixture(tmp_path)
    workbook_path = assets_root / "extracted/41467_2022_34438_MOESM4_ESM.xlsx"
    workbook_path.write_bytes(workbook_path.read_bytes() + b"tampered")
    workflow = FulltextMulticoreAuditWorkflow(
        ROOT, assets_root, registry_path=registry_path, output_root=tmp_path / "report"
    )

    with pytest.raises(FulltextMulticoreAuditError, match="(size|checksum) mismatch"):
        workflow.run(strict=True)


def test_fulltext_multicore_audit_rejects_biological_promotion(tmp_path: Path) -> None:
    assets_root, registry_path = _fixture(tmp_path)
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    registry["benchmark_scope"]["measurement_scope"] = "BIOLOGICAL_COHORT_GENERALIZATION"
    registry_path.write_text(json.dumps(registry), encoding="utf-8")
    workflow = FulltextMulticoreAuditWorkflow(
        ROOT, assets_root, registry_path=registry_path, output_root=tmp_path / "report"
    )

    with pytest.raises(FulltextMulticoreAuditError, match="scope"):
        workflow.run(strict=True)
