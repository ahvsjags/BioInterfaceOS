import csv
import json
from pathlib import Path

from biointerfaceos.r4_t214_source_heterogeneity import R4T214SourceHeterogeneityWorkflow


ROOT = Path(__file__).resolve().parents[2]


def test_t214_receipt_verifies_and_keeps_external_gates_closed() -> None:
    summary = R4T214SourceHeterogeneityWorkflow(ROOT).verify(strict=True)
    assert summary.effect_row_count == 8
    assert summary.primary_effect_unit_count == 5
    assert summary.positive_effect_count == 2
    assert summary.negative_effect_count == 1
    receipt = json.loads(summary.receipt_path.read_text(encoding="utf-8"))
    assert receipt["pooling_prohibited"] is True
    assert receipt["scientific_submission_ready"] is False


def test_t214_preserves_route_and_missingness_boundaries() -> None:
    output = ROOT / R4T214SourceHeterogeneityWorkflow.OUTPUT_RELATIVE
    rows = list(csv.DictReader((output / "effect_unit_descriptive_audit.csv").open(encoding="utf-8", newline="")))
    assert {row["route"] for row in rows} == {
        "T195_common_target_laboratory_holdout",
        "T197_source_availability_sensitivity",
        "T203_paper_cohort_ood",
        "T209_manchester_paper_cohort_ood",
    }
    thresholds = list(csv.DictReader((output / "missingness_threshold_sensitivity.csv").open(encoding="utf-8", newline="")))
    assert {int(row["threshold"]) for row in thresholds} == {5, 7, 10, 12, 15, 20, 25, 30}
    assert all(row["claim_status"] == "MISSINGNESS_SENSITIVITY_DESCRIPTIVE_ONLY" for row in thresholds)


def test_t214_does_not_infer_biological_n_from_measurement_batches() -> None:
    output = ROOT / R4T214SourceHeterogeneityWorkflow.OUTPUT_RELATIVE
    rows = list(csv.DictReader((output / "effect_unit_descriptive_audit.csv").open(encoding="utf-8", newline="")))
    t203 = next(row for row in rows if row["route"] == "T203_paper_cohort_ood")
    assert t203["biological_unit_count"] == ""
    assert t203["reported_paper_unit_count"] == "45"
    assert t203["unit_count_semantics"] == "paper_reported_measurement_batch_count_not_biological_n"
    assert t203["display_effect"] == "+0.024"


def test_t214_marks_degenerate_intervals_as_computational() -> None:
    output = ROOT / R4T214SourceHeterogeneityWorkflow.OUTPUT_RELATIVE
    rows = list(csv.DictReader((output / "effect_unit_descriptive_audit.csv").open(encoding="utf-8", newline="")))
    degenerate = [row for row in rows if row["interval_semantics"] == "DEGENERATE_COMPUTATIONAL_INTERVAL_NOT_BIOLOGICAL_ZERO"]
    assert {row["source_id"] for row in degenerate} == {
        "University College Dublin / Conway Institute",
        "University of Edinburgh-led controlled human exposure study",
        "EDINBURGH_DS7545_HUMAN_PLASMA_NANOOMICS",
    }
