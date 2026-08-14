import csv
import json
from pathlib import Path

from biointerfaceos.r4_t214_source_heterogeneity import R4T214SourceHeterogeneityWorkflow


ROOT = Path(__file__).resolve().parents[2]


def test_t214_receipt_verifies_and_keeps_external_gates_closed() -> None:
    summary = R4T214SourceHeterogeneityWorkflow(ROOT).verify(strict=True)
    assert summary.effect_row_count == 8
    assert summary.primary_study_count == 5
    assert summary.positive_effect_count == 2
    assert summary.negative_effect_count == 1
    receipt = json.loads(summary.receipt_path.read_text(encoding="utf-8"))
    assert receipt["pooling_prohibited"] is True
    assert receipt["scientific_submission_ready"] is False


def test_t214_preserves_route_and_missingness_boundaries() -> None:
    output = ROOT / R4T214SourceHeterogeneityWorkflow.OUTPUT_RELATIVE
    rows = list(csv.DictReader((output / "study_level_effects.csv").open(encoding="utf-8", newline="")))
    assert {row["route"] for row in rows} == {
        "T195_common_target_laboratory_holdout",
        "T197_source_availability_sensitivity",
        "T203_paper_cohort_ood",
        "T209_manchester_paper_cohort_ood",
    }
    thresholds = list(csv.DictReader((output / "missingness_threshold_sensitivity.csv").open(encoding="utf-8", newline="")))
    assert {int(row["threshold"]) for row in thresholds} == {5, 7, 10, 12, 15, 20, 25, 30}
    assert all(row["claim_status"] == "MISSINGNESS_SENSITIVITY_DESCRIPTIVE_ONLY" for row in thresholds)
