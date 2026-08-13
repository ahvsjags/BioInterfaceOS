"""Regression checks for the executed T188 secondary sensitivity analysis."""

import json
from pathlib import Path

from biointerfaceos.r4_pxd064962_low_coverage_sensitivity import (
    R4PXD064962LowCoverageSensitivityWorkflow,
)

ROOT = Path(__file__).resolve().parents[2]


def test_pxd064962_sensitivity_receipt_verifies_and_preserves_boundary() -> None:
    workflow = R4PXD064962LowCoverageSensitivityWorkflow(ROOT)
    summary = workflow.verify()
    assert summary.development_observation_count == 2724
    assert summary.external_observation_count == 259
    assert summary.all_eligible_batch_count == 30
    assert summary.low_coverage_batch_count == 25
    assert summary.high_coverage_batch_count == 5
    assert summary.biological_unit_count == 30
    assert summary.shared_positive_target_count == 15
    assert summary.model_count == 3

    report_path = (
        ROOT
        / "reports/review_round_4/pxd064962_low_coverage_sensitivity/v1.0.0"
        / "r4_pxd064962_low_coverage_sensitivity_report.json"
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["model_fitted"] is True
    assert report["primary_ood_minimum_met"] is False
    assert report["scientific_submission_ready"] is False
    full = next(
        row
        for row in report["model_results"]
        if row["stratum_id"] == "GE5_ALL" and row["model_id"] == "SEQUENCE_RIDGE_FULL"
    )
    composition = next(
        row
        for row in report["model_results"]
        if row["stratum_id"] == "GE5_ALL" and row["model_id"] == "SEQUENCE_RIDGE_COMPOSITION_ONLY"
    )
    assert full["subject_equal_mean_spearman"] > composition["subject_equal_mean_spearman"]
    assert report["negative_control_summary"]["selection_reexecuted_per_resample"] is True
    qc = report["technical_replicate_qc_summary"]
    assert qc["batch_count"] == 30
    assert qc["target_pairs_with_any_positive"] == 259
    assert qc["target_pairs_two_positive_replicates"] == 195
    assert qc["target_pairs_one_positive_replicate"] == 64
    assert qc["positive_zero_discordance_count"] == 64
    assert qc["positive_blank_discordance_count"] == 0
