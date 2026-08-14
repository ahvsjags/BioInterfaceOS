import csv
import json
from pathlib import Path

from biointerfaceos.r4_t217_statistical_amendment import (
    R4T217StatisticalAmendmentWorkflow,
)

ROOT = Path(__file__).resolve().parents[2]


def test_t217_receipt_verifies_and_keeps_external_gates_closed() -> None:
    summary = R4T217StatisticalAmendmentWorkflow(ROOT).verify(strict=True)
    assert summary.availability_row_count == 16
    assert summary.missingness_row_count == 149
    assert summary.multiplicity_row_count == 8
    receipt = json.loads(summary.receipt_path.read_text(encoding="utf-8"))
    assert receipt["primary_estimand_frozen"] is True
    assert receipt["availability_denominators_audited"] is True
    assert receipt["missingness_policy_frozen"] is True
    assert receipt["project_multiplicity_ledger_frozen"] is True
    assert receipt["independent_validation"] is False
    assert receipt["protected_lockbox_evaluator_receipt"] is False
    assert receipt["external_scientific_reproduction"] is False
    assert receipt["scientific_submission_ready"] is False


def test_t217_primary_and_secondary_availability_denominators_are_explicit() -> None:
    output = ROOT / R4T217StatisticalAmendmentWorkflow.OUTPUT_RELATIVE
    rows = list(
        csv.DictReader((output / "availability_flow.csv").open(encoding="utf-8", newline=""))
    )
    primary = [row for row in rows if row["route"] == "T195"]
    assert len(primary) == 3
    assert {(row["candidate_count"], row["retained_count"]) for row in primary} == {("9", "9")}
    t197 = [row for row in rows if row["route"] == "T197"]
    assert {(row["candidate_count"], row["retained_count"]) for row in t197} == {
        ("12", "9"),
        ("13", "9"),
    }
    t198 = [row for row in rows if row["route"] == "T198"]
    assert {int(row["denominator_type"].rsplit("_", 1)[-1]) for row in t198} == {
        5,
        7,
        10,
        12,
        15,
        20,
        25,
        30,
    }
    threshold_10 = next(row for row in t198 if row["denominator_type"].endswith("_10"))
    assert threshold_10["candidate_count"] == "705"
    assert threshold_10["retained_count"] == "666"
    assert threshold_10["retained_biological_unit_count"] == "141"
    t203 = next(row for row in rows if row["route"] == "T203")
    t209 = next(row for row in rows if row["route"] == "T209")
    assert (t203["candidate_count"], t203["retained_count"], t203["reported_paper_unit_count"]) == (
        "99",
        "97",
        "45",
    )
    assert (
        t209["candidate_count"],
        t209["retained_count"],
        t209["retained_biological_unit_count"],
    ) == ("99", "25", "60")


def test_t217_missingness_flow_preserves_author_na_without_imputation() -> None:
    output = ROOT / R4T217StatisticalAmendmentWorkflow.OUTPUT_RELATIVE
    rows = list(
        csv.DictReader((output / "missingness_flow.csv").open(encoding="utf-8", newline=""))
    )
    overall = next(row for row in rows if row["dimension"] == "overall")
    assert overall["source_row_count"] == "23970"
    assert overall["author_na_row_count"] == "6640"
    assert overall["positive_finite_row_count"] == "17330"
    assert overall["imputation"] == "NONE"
    assert overall["missingness_assumption"] == "NONE_CLAIMED"
    assert overall["retained_measurement_batch_count_at_primary_threshold"] == "666"
    assert overall["retained_biological_unit_count_at_primary_threshold"] == "141"


def test_t217_multiplicity_ledger_separates_primary_qc_and_secondary_routes() -> None:
    output = ROOT / R4T217StatisticalAmendmentWorkflow.OUTPUT_RELATIVE
    rows = list(
        csv.DictReader((output / "multiplicity_ledger.csv").open(encoding="utf-8", newline=""))
    )
    primary = [row for row in rows if row["family_id"] == "T217_PRIMARY_EFFECT_AND_INTERVAL"]
    qc = [row for row in rows if row["family_id"] == "T197_WITHIN_BATCH_NEGATIVE_CONTROL"]
    secondary = [row for row in rows if row["family_id"] == "T217_SECONDARY_DESCRIPTIVE_ROUTES"]
    assert len(primary) == 1
    assert primary[0]["p_value_status"] == "NOT_ESTIMATED"
    assert len(qc) == 3
    assert all(row["p_value_status"] == "HOLM_ADJUSTED_QC_ONLY" for row in qc)
    assert len(secondary) == 4
    assert all(row["p_value_status"] == "PROHIBITED" for row in secondary)
