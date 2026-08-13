"""Regression tests for the source-availability-aware T197 receipt."""

import csv
import json
from pathlib import Path

from biointerfaceos.r4_t197_source_availability_execution import (
    R4T197SourceAvailabilityWorkflow,
)


ROOT = Path(__file__).resolve().parents[2]


def test_t197_receipt_verifies_and_reexecutes_selection_in_null() -> None:
    workflow = R4T197SourceAvailabilityWorkflow(ROOT)
    summary = workflow.verify(strict=True)
    assert summary.outer_fold_count == 3
    assert summary.target_count_minimum == 12
    report = json.loads(summary.receipt_path.with_name("t197_source_availability_execution_report.json").read_text())
    ledger_path = summary.receipt_path.with_name("source_availability_target_ledger.csv")
    ledger_rows = list(csv.DictReader(ledger_path.open(encoding="utf-8", newline="")))
    assert {row["target_membership_basis"] for row in ledger_rows} == {"DEVELOPMENT_SOURCES_ONLY"}
    assert all(
        item["held_out_source_id"] not in item["development_source_ids"]
        for item in report["fold_targets"]
    )
    assert all(
        item["development_only_target_count"] >= summary.target_count_minimum
        for item in report["fold_targets"]
    )


def test_t197_fold_target_sets_are_not_the_all_source_intersection() -> None:
    report_path = (
        ROOT
        / R4T197SourceAvailabilityWorkflow.OUTPUT_RELATIVE
        / "outer_fold_target_sets.json"
    )
    rows = json.loads(report_path.read_text())
    assert {row["development_only_target_count"] for row in rows} == {12, 13}
    assert {row["test_available_target_count"] for row in rows} == {9}
