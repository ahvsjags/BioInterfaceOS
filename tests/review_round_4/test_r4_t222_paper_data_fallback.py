from __future__ import annotations

import json
from pathlib import Path

from biointerfaceos.r4_paper_data_fallback import R4PaperDataFallbackWorkflow

ROOT = Path(__file__).resolve().parents[2]


def test_t222_paper_data_fallback_receipt_verifies() -> None:
    summary = R4PaperDataFallbackWorkflow(ROOT).verify(strict=True)

    assert summary.route_count == 4
    assert summary.source_registry_count == 4
    assert summary.source_map_count == 8
    assert summary.report_count == 4
    assert summary.external_gate_count == 24

    receipt = json.loads(summary.receipt_path.read_text(encoding="utf-8"))
    assert receipt["published_paper_data_audited"] is True
    assert receipt["independent_validation"] is False
    assert receipt["external_scientific_reproduction"] is False
    assert receipt["external_user_adoption"] is False
    assert receipt["doi_archived"] is False
    assert receipt["scientific_submission_ready"] is False


def test_t222_routes_preserve_paper_data_claim_boundaries() -> None:
    report_path = (
        ROOT
        / R4PaperDataFallbackWorkflow.OUTPUT_RELATIVE
        / "r4_t222_paper_data_fallback_report.json"
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))

    assert {route["evidence_class"] for route in report["routes"]} == {
        "REDISTRIBUTABLE_DEVELOPMENT",
        "AUTHOR_RUN_EXTERNAL_OOD",
        "AUTHOR_RUN_PAPER_OOD",
        "EXTERNAL_REPRODUCTION_CANDIDATE",
    }
    assert all(
        all(value is False for value in route["external_gate_effect"].values())
        for route in report["routes"]
    )
