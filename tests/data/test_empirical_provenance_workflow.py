"""Tests for the real-source, row-level empirical provenance gate."""

from __future__ import annotations

from pathlib import Path

import pytest

from biointerfaceos.empirical_provenance_workflow import (
    EmpiricalProvenanceError,
    EmpiricalProvenanceWorkflow,
)

ROOT = Path(__file__).resolve().parents[2]


def test_real_open_observations_are_traced_to_raw_cells(tmp_path: Path) -> None:
    output_root = tmp_path / "empirical_provenance"
    workflow = EmpiricalProvenanceWorkflow(ROOT, output_root=output_root)

    summary = workflow.run(strict=True)
    audit = workflow.verify()

    assert summary.source_count == 1
    assert summary.laboratory_count == 1
    assert summary.raw_asset_count == 4
    assert summary.observation_count == 14
    assert audit["status"] == "PASS_EMPIRICAL_PROVENANCE"
    assert audit["row_provenance"][0]["raw_locator"] == "Shrinking_rates!B2"
    assert audit["row_provenance"][0]["independent_unit_id"] == "GUV 1"
    assert audit["empirical_source"] is True
    assert audit["statistical_conclusions"] is False
    assert audit["independent_validation"] is False
    assert audit["scientific_submission_ready"] is False


def test_empirical_provenance_requires_strict_mode(tmp_path: Path) -> None:
    workflow = EmpiricalProvenanceWorkflow(ROOT, output_root=tmp_path / "empirical_provenance")

    with pytest.raises(EmpiricalProvenanceError, match="requires --strict"):
        workflow.run()
