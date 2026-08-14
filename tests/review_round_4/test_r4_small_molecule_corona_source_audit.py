"""Regression tests for the separately frozen PMC11544298 source audit."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from biointerfaceos.r4_small_molecule_corona_source_audit import (
    R4SmallMoleculeCoronaSourceAuditError,
    R4SmallMoleculeCoronaSourceAuditWorkflow,
)

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "data/raw/r4_candidate_pmc11544298"


def _assets(tmp_path: Path) -> Path:
    destination = tmp_path / "pmc11544298"
    destination.mkdir()
    shutil.copy2(SOURCE / "PMC11544298_supplementary.zip", destination / "PMC11544298_supplementary.zip")
    for name in (
        "41467_2024_53966_MOESM3_ESM.xlsx",
        "41467_2024_53966_MOESM5_ESM.xlsx",
        "41467_2024_53966_MOESM7_ESM.xlsx",
    ):
        target = destination / "official_extracted"
        target.mkdir(exist_ok=True)
        shutil.copy2(SOURCE / "official_extracted" / name, target / name)
    return destination


def test_r4_small_molecule_audit_creates_and_verifies_source_cells(tmp_path: Path) -> None:
    assets = _assets(tmp_path)
    workflow = R4SmallMoleculeCoronaSourceAuditWorkflow(ROOT, assets, output_root=tmp_path / "audit")

    summary = workflow.run(strict=True)

    assert summary.source_asset_count == 4
    assert summary.protein_row_count == 2168
    assert summary.all_measurement_batch_count == 142
    assert summary.corona_measurement_batch_count == 136
    assert summary.rank_qualified_measurement_batch_count == 134
    assert summary.shared_canonical_protein_count == 97
    assert summary.source_cell_count == 8064
    assert summary.candidate_positive_source_cell_count == 7075
    assert workflow.verify() == summary


def test_r4_small_molecule_audit_rejects_tampered_extraction(tmp_path: Path) -> None:
    assets = _assets(tmp_path)
    source = assets / "official_extracted" / "41467_2024_53966_MOESM3_ESM.xlsx"
    source.write_bytes(source.read_bytes() + b"tampered")
    workflow = R4SmallMoleculeCoronaSourceAuditWorkflow(ROOT, assets, output_root=tmp_path / "audit")

    with pytest.raises(R4SmallMoleculeCoronaSourceAuditError, match="checksum differs"):
        workflow.run(strict=True)
