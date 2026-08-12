import json
from pathlib import Path

from biointerfaceos.symbolic_laws_workflow import SymbolicLawsWorkflow


def test_symbolic_laws_workflow_enforces_units_and_stability(tmp_path: Path) -> None:
    root = Path(__file__).parents[2]
    workflow = SymbolicLawsWorkflow(root, output_root=tmp_path / "symbolic_laws")

    first = workflow.run(fixture=True)
    second = workflow.run(fixture=True)

    assert first.candidates == 4
    assert first.unit_valid == 3
    assert first.rejected == 1
    assert first.nested_folds == 4
    assert first.controls == 2
    assert first.bootstrap_stability == 1.0
    assert first.ood_passed is True
    assert first.selected_expression.startswith("0.62*surface_norm")
    assert first.fallback is False
    assert first.resumed == 0
    assert second.resumed == 1

    receipt = json.loads(first.receipt_path.read_text(encoding="utf-8"))
    assert receipt["target_values_exposed"] is False
    assert receipt["lockbox_clean"] is True


def test_symbolic_laws_outputs_keep_controls_and_study_disjoint_cv(tmp_path: Path) -> None:
    root = Path(__file__).parents[2]
    workflow = SymbolicLawsWorkflow(root, output_root=tmp_path / "symbolic_laws")
    workflow.run(fixture=True)

    unit_audit = json.loads(
        (tmp_path / "symbolic_laws" / "unit_audit.json").read_text(encoding="utf-8")
    )
    nested = json.loads(
        (tmp_path / "symbolic_laws" / "nested_study_cv.json").read_text(encoding="utf-8")
    )
    controls = json.loads(
        (tmp_path / "symbolic_laws" / "flexible_controls.json").read_text(encoding="utf-8")
    )
    assert unit_audit["rejected_candidates"][0]["reason"] == "dimensional_inconsistency"
    assert nested["nested"] is True
    assert nested["study_disjoint"] is True
    assert len(nested["folds"]) == 4
    assert controls["selection_role"] == "control_only"
