"""Regression tests for the PXD064962 low-coverage CC0 source audit."""

from pathlib import Path
from shutil import copy2

from biointerfaceos.r4_pxd064962_source_audit import R4PXD064962SourceAuditWorkflow

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "data/raw/r4_candidate_pxd064962_ucd"


def test_pxd064962_audit_runs_and_verifies(tmp_path: Path) -> None:
    test_assets = tmp_path / "assets"
    test_assets.mkdir()
    copy2(ASSETS / "proteinGroups.txt", test_assets / "proteinGroups.txt")
    copy2(ASSETS / "summary.txt", test_assets / "summary.txt")
    workflow = R4PXD064962SourceAuditWorkflow(ROOT, test_assets, output_root=tmp_path / "audit")
    summary = workflow.run(strict=True)
    assert summary.source_cell_count == 24300
    assert summary.positive_source_cell_count == 11776
    assert summary.target_source_cell_count == 1260
    assert summary.target_positive_source_cell_count == 454
    assert summary.target_positive_batch_observation_count == 259
    assert summary.biological_unit_count == 30
    assert summary.measurement_batch_count == 30
    assert summary.rank_qualified_measurement_batch_count == 5
    assert summary.shared_canonical_protein_count == 21
    assert summary.technical_replicate_count == 2
    assert workflow.verify() == summary
