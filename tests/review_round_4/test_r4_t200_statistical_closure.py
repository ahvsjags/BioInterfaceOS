import csv
import json
from pathlib import Path

from biointerfaceos.r4_t200_statistical_closure import R4T200StatisticalClosureWorkflow

ROOT = Path(__file__).resolve().parents[2]


def test_t200_receipt_verifies_statistical_contract() -> None:
    summary = R4T200StatisticalClosureWorkflow(ROOT).verify(strict=True)
    assert summary.t197_fold_interval_count == 27
    assert summary.t198_stratum_count > 100
    assert summary.t198_threshold_stratum_count == summary.t198_stratum_count * 8
    report = json.loads(summary.receipt_path.with_name("t200_statistical_closure_report.json").read_text())
    assert report["scientific_submission_ready"] is False


def test_t200_t197_intervals_are_batch_clustered_and_t198_is_stratified() -> None:
    root = ROOT / R4T200StatisticalClosureWorkflow.OUTPUT_RELATIVE
    intervals = list(
        csv.DictReader((root / "t197_fold_metric_cluster_intervals.csv").open(encoding="utf-8", newline=""))
    )
    assert {row["cluster"] for row in intervals} == {"measurement_batch"}
    assert {int(row["cluster_count"]) for row in intervals if row["interval_status"] == "DEFINED"} >= {6, 30, 49}
    strata = list(csv.DictReader((root / "t198_missingness_stratified.csv").open(encoding="utf-8", newline="")))
    assert {row["dimension"] for row in strata} == {
        "biological_unit_id",
        "clinical_group",
        "particle",
    }
    assert any(float(row["author_na_row_count"]) > 0 for row in strata)
