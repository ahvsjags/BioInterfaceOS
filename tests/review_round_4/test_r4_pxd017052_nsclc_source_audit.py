from pathlib import Path

import pytest

from biointerfaceos.r4_pxd017052_nsclc_source_audit import (
    R4PXD017052NSCLCSourceAuditWorkflow,
)


def test_pxd017052_nsclc_source_receipt_is_reproducible() -> None:
    root = Path(__file__).resolve().parents[2]
    if not (root / "data/raw/r4_candidate_pxd017052_nsclc/41467_2020_17033_MOESM7_ESM.xlsx").is_file():
        pytest.skip("analysis-only NSCLC assets are not part of a clean public checkout")
    workflow = R4PXD017052NSCLCSourceAuditWorkflow(
        root, root / "data/raw/r4_candidate_pxd017052_nsclc"
    )
    summary = workflow.verify()
    assert summary.biological_unit_count == 141
    assert summary.measurement_batch_count == 705
    assert summary.rank_qualified_measurement_batch_count == 666
    assert summary.shared_canonical_protein_count == 34
    assert summary.source_cell_count == 23970
    assert summary.positive_source_cell_count == 17330
