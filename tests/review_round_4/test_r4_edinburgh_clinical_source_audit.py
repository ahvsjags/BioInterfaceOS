"""Regression tests for the separately scoped CC-BY Edinburgh source audit."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from biointerfaceos.r4_edinburgh_clinical_source_audit import (
    R4EdinburghClinicalSourceAuditError,
    R4EdinburghClinicalSourceAuditWorkflow,
)


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "data/raw/r4_candidate_edinburgh_ds7545"


def _assets(tmp_path: Path) -> Path:
    destination = tmp_path / "edinburgh"
    destination.mkdir()
    for name in ("blood_proteomics_data.xlsx", "README.txt"):
        shutil.copy2(SOURCE / name, destination / name)
    return destination


def test_r4_edinburgh_source_audit_creates_and_verifies_a_cell_map(tmp_path: Path) -> None:
    assets = _assets(tmp_path)
    workflow = R4EdinburghClinicalSourceAuditWorkflow(
        ROOT, assets, output_root=tmp_path / "audit"
    )

    summary = workflow.run(strict=True)

    assert summary.source_asset_count == 2
    assert summary.protein_row_count == 1478
    assert summary.measurement_batch_count == 49
    assert summary.shared_canonical_protein_count == 23
    assert summary.source_cell_count == 983
    assert summary.positive_source_cell_count == 932
    assert workflow.verify() == summary


def test_r4_edinburgh_source_audit_rejects_tampered_source_bytes(tmp_path: Path) -> None:
    assets = _assets(tmp_path)
    source = assets / "blood_proteomics_data.xlsx"
    source.write_bytes(source.read_bytes() + b"tampered")
    workflow = R4EdinburghClinicalSourceAuditWorkflow(
        ROOT, assets, output_root=tmp_path / "audit"
    )

    with pytest.raises(R4EdinburghClinicalSourceAuditError, match="checksum differs"):
        workflow.run(strict=True)
