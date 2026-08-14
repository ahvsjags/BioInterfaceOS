"""Regression tests for the CC0 PXD068107 source audit."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from biointerfaceos.r4_pxd068107_source_audit import (
    R4PXD068107SourceAuditError,
    R4PXD068107SourceAuditWorkflow,
)

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "data/raw/r4_candidate_pxd068107"


class _TestWorkflow(R4PXD068107SourceAuditWorkflow):
    DERIVED_RELATIVE = "derived/test_R4_PXD068107_technical_source_cell_map.csv"


def test_pxd068107_source_audit_creates_and_verifies_cell_map(tmp_path: Path) -> None:
    if not (SOURCE / "2b_heatmap.xlsx").is_file():
        pytest.skip("analysis-only PXD068107 assets are not part of a clean public checkout")
    workflow = _TestWorkflow(ROOT, SOURCE, output_root=tmp_path / "audit")
    derived_path = SOURCE / workflow.DERIVED_RELATIVE
    if derived_path.exists():
        derived_path.unlink()
    try:
        summary = workflow.run(strict=True)
        assert summary.source_asset_count == 6
        assert summary.protein_row_count == 21
        assert summary.measurement_batch_count == 21
        assert summary.rank_qualified_measurement_batch_count == 21
        assert summary.shared_canonical_protein_count == 98
        assert summary.source_cell_count == 2058
        assert summary.positive_source_cell_count == 1976
        assert summary.biological_unit_count == 1
        assert summary.laboratory_anchor_count == 1
        assert workflow.verify() == summary
    finally:
        if derived_path.exists():
            derived_path.unlink()


def test_pxd068107_source_audit_rejects_registry_checksum_mismatch(tmp_path: Path) -> None:
    if not (SOURCE / "2b_heatmap.xlsx").is_file():
        pytest.skip("analysis-only PXD068107 assets are not part of a clean public checkout")
    registry_path = tmp_path / "registry.json"
    registry = json.loads((ROOT / "docs/data/R4_T264_PXD068107_SOURCE_REGISTRY.json").read_text(encoding="utf-8"))
    registry["source_assets"][0]["expected_bytes"] += 1
    registry_path.write_text(json.dumps(registry), encoding="utf-8")
    workflow = _TestWorkflow(ROOT, SOURCE, registry_path=registry_path, output_root=tmp_path / "audit")
    with pytest.raises(R4PXD068107SourceAuditError, match="byte count differs"):
        workflow.run(strict=True)
