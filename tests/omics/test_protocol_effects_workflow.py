import json
from pathlib import Path

from biointerfaceos.protocol_effects_workflow import ProtocolEffectsWorkflow


def test_protocol_effects_workflow_reports_reversal_and_boundary_language(tmp_path: Path) -> None:
    root = Path(__file__).parents[2]
    workflow = ProtocolEffectsWorkflow(root, output_root=tmp_path / "protocol_effects")

    first = workflow.run(fixture=True)
    second = workflow.run(fixture=True)

    assert first.rows == 6
    assert first.variables == 4
    assert first.studies == 6
    assert first.reversal_tests == 6
    assert first.reversals_detected >= 2
    assert first.counterexamples >= 2
    assert first.universal_reversal_permitted is False
    assert first.language_status == "PROTOCOL_DEPENDENT_BOUNDARY"
    assert first.resumed == 0
    assert second.resumed == 1

    receipt = json.loads(first.receipt_path.read_text(encoding="utf-8"))
    assert receipt["lockbox_clean"] is True
    assert receipt["target_values_exposed"] is False


def test_protocol_effects_outputs_keep_predefined_subgroups_and_counterexamples(
    tmp_path: Path,
) -> None:
    root = Path(__file__).parents[2]
    workflow = ProtocolEffectsWorkflow(root, output_root=tmp_path / "protocol_effects")
    workflow.run(fixture=True)

    ontology = json.loads(
        (tmp_path / "protocol_effects" / "protocol_ontology.json").read_text(encoding="utf-8")
    )
    reversal = json.loads(
        (tmp_path / "protocol_effects" / "reversal_tests.json").read_text(encoding="utf-8")
    )
    exclusions = json.loads(
        (tmp_path / "protocol_effects" / "exclusion_ledger.json").read_text(encoding="utf-8")
    )
    language = json.loads(
        (tmp_path / "protocol_effects" / "language_gate.json").read_text(encoding="utf-8")
    )
    assert ontology["no_posthoc_subgroups"] is True
    assert len(ontology["variables"]) == 4
    assert reversal["counterexamples"]
    assert exclusions["posthoc_subgroup_exclusions"] == 0
    assert language["status"] == "PROTOCOL_DEPENDENT_BOUNDARY"
    assert language["protocol_dependence_reported"] is True
