"""Regression tests for the license-resolved PMC13106918 source audit."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from biointerfaceos.r4_pmc13106918_source_audit import (
    R4PMC13106918SourceAuditError,
    R4PMC13106918SourceAuditWorkflow,
)


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "data/raw/r4_candidate_pmc13106918"
REGISTRY = ROOT / "docs/data/R4_T176_PMC13106918_TECHNICAL_SOURCE_REGISTRY.json"


class _TestWorkflow(R4PMC13106918SourceAuditWorkflow):
    DERIVED_RELATIVE = "derived/test_R4_PMC13106918_technical_source_cell_map.csv"


def test_pmc13106918_source_audit_creates_and_verifies_cell_map(tmp_path: Path) -> None:
    workflow = _TestWorkflow(
        ROOT, SOURCE, output_root=tmp_path / "audit"
    )
    workflow.DERIVED_RELATIVE = f"derived/test_R4_PMC13106918_{tmp_path.name}.csv"
    derived_path = SOURCE / workflow.DERIVED_RELATIVE
    if derived_path.exists():
        derived_path.unlink()
    try:
        summary = workflow.run(strict=True)

        assert summary.source_asset_count == 4
        assert summary.protein_row_count == 751
        assert summary.measurement_batch_count == 20
        assert summary.rank_qualified_measurement_batch_count == 16
        assert summary.shared_canonical_protein_count == 53
        assert summary.source_cell_count == 1060
        assert summary.positive_source_cell_count == 451
        assert summary.biological_unit_count == 1
        assert summary.laboratory_anchor_count == 1
        assert workflow.verify() == summary
    finally:
        if derived_path.exists():
            derived_path.unlink()


def test_pmc13106918_source_audit_rejects_registry_checksum_mismatch(tmp_path: Path) -> None:
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    registry["source_assets"][1]["expected_bytes"] += 1
    registry_path = tmp_path / "registry.json"
    registry_path.write_text(json.dumps(registry), encoding="utf-8")
    workflow = _TestWorkflow(
        ROOT, SOURCE, registry_path=registry_path, output_root=tmp_path / "audit"
    )

    with pytest.raises(R4PMC13106918SourceAuditError, match="checksum differs"):
        workflow.run(strict=True)
