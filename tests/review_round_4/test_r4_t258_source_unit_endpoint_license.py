"""Regression tests for the T258 source-unit and endpoint audit."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from biointerfaceos.r4_t258_source_unit_endpoint_license import (
    R4T258SourceUnitEndpointLicenseError,
    R4T258SourceUnitEndpointLicenseWorkflow,
)

ROOT = Path(__file__).resolve().parents[2]


def test_t258_run_and_verify(tmp_path: Path) -> None:
    workflow = R4T258SourceUnitEndpointLicenseWorkflow(ROOT, output_root=tmp_path / "t258")
    summary = workflow.run(strict=True)
    assert (summary.source_count, summary.source_cell_count, summary.rank_eligible_cell_count) == (4, 15971, 10852)
    assert summary.encoded_biological_unit_count == 30
    report = json.loads((tmp_path / "t258" / "r4_t258_source_unit_endpoint_license_report.json").read_text())
    assert report["endpoint_compatibility"]["pair_count"] == 6
    assert report["scientific_submission_ready"] is False
    assert workflow.verify().rank_eligible_cell_count == 10852


def test_t258_verify_rejects_tampered_matrix(tmp_path: Path) -> None:
    workflow = R4T258SourceUnitEndpointLicenseWorkflow(ROOT, output_root=tmp_path / "t258")
    workflow.run(strict=True)
    matrix_path = tmp_path / "t258" / "r4_t258_endpoint_compatibility_matrix.csv"
    matrix_path.write_text(matrix_path.read_text(encoding="utf-8").replace("false", "true", 1), encoding="utf-8")
    with pytest.raises(R4T258SourceUnitEndpointLicenseError, match="artifact hash"):
        workflow.verify()
