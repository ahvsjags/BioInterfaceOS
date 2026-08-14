"""Regression tests for the T198 paper-cohort missingness sensitivity."""

import csv
from pathlib import Path

from biointerfaceos.r4_t198_paper_cohort_missingness import (
    R4T198PaperCohortMissingnessWorkflow,
)

ROOT = Path(__file__).resolve().parents[2]


def test_t198_receipt_verifies_primary_accounting_and_nested_null() -> None:
    summary = R4T198PaperCohortMissingnessWorkflow(ROOT).verify(strict=True)
    assert summary.threshold_count == 8
    assert summary.primary_threshold == 10
    assert summary.primary_batch_count == 666
    assert summary.primary_biological_unit_count == 141
    assert summary.primary_observation_count == 17026


def test_t198_threshold_grid_reports_retention_and_no_imputation() -> None:
    path = ROOT / R4T198PaperCohortMissingnessWorkflow.OUTPUT_RELATIVE / "threshold_summary.csv"
    rows = list(csv.DictReader(path.open(encoding="utf-8", newline="")))
    assert [int(row["minimum_mapped_positive_proteins_per_batch"]) for row in rows] == [
        5,
        7,
        10,
        12,
        15,
        20,
        25,
        30,
    ]
    primary = next(row for row in rows if row["minimum_mapped_positive_proteins_per_batch"] == "10")
    assert int(primary["measurement_batch_count"]) == 666
    assert int(primary["biological_unit_count"]) == 141
    assert int(primary["source_na_row_count"]) == 6640
    assert int(primary["source_explicit_zero_row_count"]) == 0
