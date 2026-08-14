"""Regression tests for the CC0 PXD060795 small-n source audit."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from biointerfaceos.r4_dalian_plasma_corona_sensitivity import (
    R4DalianPlasmaCoronaSensitivityWorkflow,
)
from biointerfaceos.r4_dalian_plasma_corona_source_audit import (
    R4DalianPlasmaCoronaSourceAuditError,
    R4DalianPlasmaCoronaSourceAuditWorkflow,
)

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "data/raw/r4_candidate_pxd060795"


def _assets(tmp_path: Path) -> Path:
    destination = tmp_path / "pxd060795"
    destination.mkdir()
    shutil.copy2(SOURCE / "Search_result.xlsx", destination / "Search_result.xlsx")
    return destination


def test_r4_dalian_audit_creates_and_verifies_source_cells(tmp_path: Path) -> None:
    assets = _assets(tmp_path)
    workflow = R4DalianPlasmaCoronaSourceAuditWorkflow(ROOT, assets, output_root=tmp_path / "audit")

    summary = workflow.run(strict=True)

    assert summary.source_asset_count == 1
    assert summary.protein_row_count == 547
    assert summary.all_measurement_batch_count == 9
    assert summary.corona_measurement_batch_count == 6
    assert summary.rank_qualified_measurement_batch_count == 6
    assert summary.shared_canonical_protein_count == 27
    assert summary.source_cell_count == 243
    assert summary.candidate_positive_source_cell_count == 109
    assert workflow.verify() == summary


def test_r4_dalian_audit_rejects_tampered_workbook(tmp_path: Path) -> None:
    assets = _assets(tmp_path)
    source = assets / "Search_result.xlsx"
    source.write_bytes(source.read_bytes() + b"tampered")
    workflow = R4DalianPlasmaCoronaSourceAuditWorkflow(ROOT, assets, output_root=tmp_path / "audit")

    with pytest.raises(R4DalianPlasmaCoronaSourceAuditError, match="checksum differs"):
        workflow.run(strict=True)


def test_r4_dalian_small_n_sensitivity_executes_with_explicit_claim_boundary(
    tmp_path: Path,
) -> None:
    del tmp_path
    output_root = ROOT / "reports/review_round_4/_test_r4_dalian_sensitivity"
    shutil.rmtree(output_root, ignore_errors=True)
    try:
        result = R4DalianPlasmaCoronaSensitivityWorkflow(ROOT, output_root=output_root).run(strict=True)

        assert result["external_observation_count"] == 109
        assert result["external_measurement_batch_count"] == 6
        assert result["model_metrics"]["SEQUENCE_RIDGE_FULL"]["mean_spearman"] == pytest.approx(0.2323323348478147)
        report = (output_root / "dalian_sensitivity_report.json").read_text(encoding="utf-8")
        assert '"independent_validation":false' in report
        assert '"scientific_submission_ready":false' in report
    finally:
        shutil.rmtree(output_root, ignore_errors=True)
