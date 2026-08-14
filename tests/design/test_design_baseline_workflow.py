import json
from pathlib import Path

from biointerfaceos.design_baseline_workflow import DesignBaselineWorkflow


def test_design_baseline_enforces_constraints_penalties_and_controls(tmp_path: Path) -> None:
    root = Path(__file__).parents[2]
    workflow = DesignBaselineWorkflow(root, output_root=tmp_path / "baseline")

    first = workflow.run(fixture=True)
    second = workflow.run(fixture=True)

    assert first.candidates == 9
    assert first.valid_candidates == 7
    assert first.invalid_candidates == 2
    assert first.supported_candidates == 6
    assert first.methods == 3
    assert first.constraint_pass_rate == 1.0
    assert first.controls_recovered == 2
    assert first.controls_total == 2
    assert first.pareto_members >= 2
    assert first.abstentions == 1
    assert first.selected_method in {"enumeration", "nsga_ii", "bo_style"}
    assert first.resumed == 0
    assert second.resumed == 1

    receipt = json.loads(first.receipt_path.read_text(encoding="utf-8"))
    assert receipt["lockbox_clean"] is True
    assert receipt["target_values_exposed"] is False


def test_design_baseline_preserves_invalid_and_ood_audits(tmp_path: Path) -> None:
    root = Path(__file__).parents[2]
    workflow = DesignBaselineWorkflow(root, output_root=tmp_path / "baseline")
    workflow.run(fixture=True)

    candidates = json.loads((tmp_path / "baseline" / "candidate_ledger.json").read_text(encoding="utf-8"))
    penalties = json.loads((tmp_path / "baseline" / "penalty_audit.json").read_text(encoding="utf-8"))
    controls = json.loads((tmp_path / "baseline" / "control_recovery.json").read_text(encoding="utf-8"))
    abstentions = json.loads((tmp_path / "baseline" / "abstention_ledger.json").read_text(encoding="utf-8"))
    assert {item["reason"] for item in candidates["invalid"]} == {
        "simplex_violation",
        "charge_not_neutral",
    }
    assert penalties["uncertainty_penalty_active"] is True
    assert penalties["ad_penalty_active"] is True
    assert controls["recovery_rate"] == 1.0
    assert abstentions["ood_candidates_excluded"] is True
    assert abstentions["count"] == 1
