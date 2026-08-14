"""Regression tests for the four-source development-only target route."""

import json
from pathlib import Path

from biointerfaceos.r4_t238_four_source_availability_execution import (
    R4T238FourSourceAvailabilityWorkflow,
)

ROOT = Path(__file__).resolve().parents[2]


def test_t238_receipt_verifies_and_reexecutes_selection_in_null() -> None:
    workflow = R4T238FourSourceAvailabilityWorkflow(ROOT)
    summary = workflow.verify(strict=True)
    assert summary.outer_fold_count == 4
    assert summary.target_count_minimum == 9
    report = json.loads(summary.receipt_path.with_name(workflow.REPORT_NAME).read_text())
    assert len(report["fold_targets"]) == 4
    assert all(item["held_out_source_id"] not in item["development_source_ids"] for item in report["fold_targets"])
    assert all(item["test_available_target_count"] == 7 for item in report["fold_targets"])


def test_t238_fold_target_sets_are_not_the_all_source_intersection() -> None:
    report_path = ROOT / R4T238FourSourceAvailabilityWorkflow.OUTPUT_RELATIVE / "outer_fold_target_sets.json"
    rows = json.loads(report_path.read_text())
    assert {row["development_only_target_count"] for row in rows} == {9, 10}
    assert {row["test_available_target_count"] for row in rows} == {7}
