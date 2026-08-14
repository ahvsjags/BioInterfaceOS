"""Regression tests for the T255 cluster-aware uncertainty extension."""

import json
from pathlib import Path

from biointerfaceos.r4_t255_cluster_uncertainty import R4T255ClusterUncertaintyWorkflow

ROOT = Path(__file__).resolve().parents[2]


def test_t255_receipt_verifies_without_donor_level_claim() -> None:
    workflow = R4T255ClusterUncertaintyWorkflow(ROOT)
    summary = workflow.verify(strict=True)
    assert (summary.outer_fold_count, summary.model_count, summary.metric_row_count) == (4, 3, 36)
    receipt = json.loads(summary.receipt_path.read_text())
    assert receipt["donor_level_effective_n_claimed"] is False
    assert receipt["bootstrap_resamples"] == 2000


def test_t255_constant_spearman_is_undefined_and_ridge_intervals_are_defined() -> None:
    report_path = ROOT / R4T255ClusterUncertaintyWorkflow.OUTPUT_RELATIVE / R4T255ClusterUncertaintyWorkflow.REPORT_NAME
    report = json.loads(report_path.read_text())
    rows = report["metric_rows"]
    constant = [row for row in rows if row["model_id"] == "CONSTANT_TRAINING_MEAN" and row["metric"] == "spearman"]
    ridge = [row for row in rows if row["model_id"] == "SEQUENCE_RIDGE_FULL" and row["metric"] == "spearman"]
    assert len(constant) == 4 and all(row["estimate"] is None for row in constant)
    assert len(ridge) == 4 and all(row["lower_95"] <= row["estimate"] <= row["upper_95"] for row in ridge)
