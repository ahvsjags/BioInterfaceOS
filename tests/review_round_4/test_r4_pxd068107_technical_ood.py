"""Regression test for the frozen PXD068107 technical OOD execution."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from biointerfaceos.r4_pxd068107_technical_ood import R4PXD068107TechnicalOODWorkflow

ROOT = Path(__file__).resolve().parents[2]


def test_pxd068107_technical_ood_runs_and_verifies(tmp_path: Path) -> None:
    if not (ROOT / "data/raw/r4_candidate_pxd068107/2b_heatmap.xlsx").is_file():
        pytest.skip("analysis-only PXD068107 assets are not part of a clean public checkout")
    output_root = ROOT / "reports/review_round_4" / f"_test_pxd068107_technical_ood_{tmp_path.name}"
    workflow = R4PXD068107TechnicalOODWorkflow(
        ROOT,
        ROOT / "data/raw",
        ROOT / "data/raw/r3_uniprot_sequence_features",
        ROOT / "data/raw/r4_candidate_pxd068107",
        output_root=output_root,
    )
    try:
        summary = workflow.run(strict=True)
        assert summary.development_observation_count == 2724
        assert summary.external_observation_count == 1976
        assert summary.shared_canonical_protein_count == 98
        assert summary.external_measurement_batch_count == 21
        assert summary.model_count == 3
        assert workflow.verify() == summary
    finally:
        if output_root.exists():
            shutil.rmtree(output_root)
