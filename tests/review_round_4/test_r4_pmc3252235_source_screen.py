"""Regression tests for the negative PMC3252235 full-text source screen."""

from pathlib import Path

import pytest

from biointerfaceos.r4_pmc3252235_source_screen import R4PMC3252235SourceScreenWorkflow

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "data/raw/r4_candidate_pmc3252235_NIHMS344183"


def test_pmc3252235_screen_runs_and_verifies(tmp_path: Path) -> None:
    if not (ASSETS / "NIHMS344183-supplement-Supp_Tables_pow.xls").is_file():
        pytest.skip("analysis-only PMC3252235 assets are not part of a clean public checkout")
    workflow = R4PMC3252235SourceScreenWorkflow(ROOT, ASSETS, output_root=tmp_path / "screen")
    summary = workflow.run(strict=True)
    assert summary.source_bytes == 6702592
    assert summary.direct_overlap_accessions == 2
    assert summary.measurement_columns == 24
    assert summary.rank_qualified_columns == 0
    verified = workflow.verify()
    assert verified == summary
