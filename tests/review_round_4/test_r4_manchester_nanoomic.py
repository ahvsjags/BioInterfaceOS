"""Regression tests for the Manchester analysis-only OOD boundary."""

import json
from pathlib import Path

import pytest

from biointerfaceos.r4_manchester_nanoomic_ood import R4ManchesterNanoOmicWorkflow

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "data/raw/r4_candidate_pmc13212878/author_repo"


def test_manchester_protocol_freezes_analysis_only_accounting() -> None:
    protocol_path = ROOT / R4ManchesterNanoOmicWorkflow.PROTOCOL_RELATIVE
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    expected = protocol["external_evaluation"]
    assert expected["expected_external_observation_count"] == 4169
    assert expected["expected_measurement_batch_count"] == 289
    assert expected["expected_biological_unit_count"] == 61
    assert expected["expected_shared_canonical_protein_count"] == 25
    assert protocol["scientific_submission_ready"] is False
    assert "independent evaluator receipt" in protocol["claim_boundary"]
    assert "no-author reproduction" in protocol["claim_boundary"]


def test_manchester_receipts_verify_when_analysis_artifacts_are_present() -> None:
    audit_report = ROOT / R4ManchesterNanoOmicWorkflow.AUDIT_OUTPUT_RELATIVE / (
        "r4_manchester_nanoomic_source_report.json"
    )
    ood_report = ROOT / R4ManchesterNanoOmicWorkflow.OOD_OUTPUT_RELATIVE / (
        "r4_manchester_nanoomic_ood_report.json"
    )
    if not audit_report.is_file() or not ood_report.is_file():
        pytest.skip("analysis-only source receipts are not part of a clean checkout")

    workflow = R4ManchesterNanoOmicWorkflow(ROOT, ASSETS)
    audit = workflow.verify_audit()
    ood = workflow.verify_ood()
    assert audit.source_cell_count == 193971
    assert audit.positive_source_cell_count == 177636
    assert audit.biological_unit_count == 61
    assert audit.measurement_batch_count == 289
    assert audit.shared_canonical_protein_count == 25
    assert ood.external_observation_count == 4169
    assert ood.external_measurement_batch_count == 289
    assert ood.biological_unit_count == 61
    assert ood.model_count == 3
