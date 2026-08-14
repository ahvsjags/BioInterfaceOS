import json
from pathlib import Path

from biointerfaceos.ood_workflow import OODWorkflow


def test_ood_suite_covers_all_group_dimensions_and_narrows_claim(tmp_path: Path) -> None:
    root = Path(__file__).parents[2]
    workflow = OODWorkflow(root, output_root=tmp_path / "ood")

    first = workflow.run(all_groups=True)
    second = workflow.run(all_groups=True)

    assert first.dimensions == 6
    assert first.groups == 12
    assert first.low_n_groups == 6
    assert first.leave_largest == 1
    assert first.sensitivity_records == 3
    assert first.primary_records == 12
    assert first.calibration_records == 12
    assert first.selective_risk_records == 12
    assert first.claim_status == "NARROWED_BY_OOD"
    assert first.resumed == 0
    assert second.resumed == 1

    receipt = json.loads(first.receipt_path.read_text(encoding="utf-8"))
    assert receipt["lockbox_clean"] is True
    assert receipt["target_values_exposed"] is False


def test_ood_sensitivity_includes_largest_study_and_evidence_grade(tmp_path: Path) -> None:
    root = Path(__file__).parents[2]
    workflow = OODWorkflow(root, output_root=tmp_path / "ood")
    workflow.run(all_groups=True)

    sensitivity = json.loads((tmp_path / "ood" / "sensitivity_report.json").read_text(encoding="utf-8"))
    low_n = json.loads((tmp_path / "ood" / "low_n_ledger.json").read_text(encoding="utf-8"))
    assert {row["scenario"] for row in sensitivity["rows"]} == {
        "leave_largest_study",
        "drop_low_n",
        "evidence_grade_only",
    }
    assert sensitivity["leave_largest_study"] == "STUDY-A"
    assert low_n["count"] == 6
    assert all(row["abstain"] is True for row in low_n["rows"])
