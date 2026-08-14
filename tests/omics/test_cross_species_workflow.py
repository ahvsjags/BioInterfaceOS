import json
from pathlib import Path

from biointerfaceos.cross_species_workflow import CrossSpeciesWorkflow


def test_cross_species_workflow_compares_methods_and_abstains(tmp_path: Path) -> None:
    root = Path(__file__).parents[2]
    workflow = CrossSpeciesWorkflow(root, output_root=tmp_path / "cross_species")

    first = workflow.run(fixture=True)
    second = workflow.run(fixture=True)

    assert first.rows == 10
    assert first.strata == 2
    assert first.methods == 4
    assert first.development_materials == 3
    assert first.heldout_materials == 2
    assert first.scored_heldout == 2
    assert first.abstentions == 2
    assert first.overlap_passed is True
    assert first.pairing_passed is True
    assert first.selected_method in {"direct", "functional", "optimal_transport", "conditional"}
    assert first.resumed == 0
    assert second.resumed == 1

    receipt = json.loads(first.receipt_path.read_text(encoding="utf-8"))
    assert receipt["lockbox_clean"] is True
    assert receipt["target_values_exposed"] is False


def test_cross_species_outputs_preserve_pairing_and_leave_material_gate(tmp_path: Path) -> None:
    root = Path(__file__).parents[2]
    workflow = CrossSpeciesWorkflow(root, output_root=tmp_path / "cross_species")
    workflow.run(fixture=True)

    pairing = json.loads((tmp_path / "cross_species" / "pairing_audit.json").read_text(encoding="utf-8"))
    leave_material = json.loads((tmp_path / "cross_species" / "leave_material_report.json").read_text(encoding="utf-8"))
    abstentions = json.loads((tmp_path / "cross_species" / "abstention_ledger.json").read_text(encoding="utf-8"))
    assert pairing["pseudo_pairs_created"] is False
    assert pairing["unmatched_exclusions_preserved"] is True
    assert len(leave_material["materials"]) == 2
    assert leave_material["materials"][0]["tuned_on_heldout"] is False
    assert abstentions["unsupported_cases_abstained"] is True
    assert abstentions["count"] == 2
