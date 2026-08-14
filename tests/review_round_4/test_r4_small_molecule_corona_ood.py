"""Regression tests for the frozen public R4 OOD workflow."""

from __future__ import annotations

import shutil
from pathlib import Path

from biointerfaceos.r4_small_molecule_corona_ood import R4SmallMoleculeCoronaOODWorkflow

ROOT = Path(__file__).resolve().parents[2]


def test_r4_public_ood_replays_and_verifies(tmp_path: Path) -> None:
    del tmp_path
    output_root = ROOT / "reports/review_round_4/_test_r4_small_molecule_corona_ood"
    shutil.rmtree(output_root, ignore_errors=True)
    workflow = R4SmallMoleculeCoronaOODWorkflow(
        ROOT,
        ROOT / "data/raw",
        ROOT / "data/raw/r3_uniprot_sequence_features",
        ROOT / "data/raw/r4_candidate_pmc11544298",
        output_root=output_root,
    )
    try:
        summary = workflow.run(strict=True)

        assert summary.development_observation_count == 2724
        assert summary.external_observation_count == 7075
        assert summary.shared_canonical_protein_count == 94
        assert summary.external_measurement_batch_count == 134
        assert summary.model_count == 3
        assert workflow.verify() == summary
    finally:
        shutil.rmtree(output_root, ignore_errors=True)
