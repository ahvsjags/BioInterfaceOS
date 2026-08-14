import json
from pathlib import Path

from biointerfaceos.counterfactual_workflow import CounterfactualWorkflow


def test_counterfactual_workflow_restricts_scope_and_abstains(tmp_path: Path) -> None:
    root = Path(__file__).parents[2]
    workflow = CounterfactualWorkflow(root, output_root=tmp_path / "counterfactuals")

    first = workflow.run(fixture=True)
    second = workflow.run(fixture=True)

    assert first.rows == 5
    assert first.interventions == 2
    assert first.supported == 2
    assert first.rejected == 3
    assert first.model_families == 2
    assert first.scored == 2
    assert first.abstentions == 3
    assert first.rank_pairs == 1
    assert first.rank_stability == 1.0
    assert first.contradictions == 3
    assert first.unresolved == 1
    assert first.resumed == 0
    assert second.resumed == 1

    receipt = json.loads(first.receipt_path.read_text(encoding="utf-8"))
    assert receipt["lockbox_clean"] is True
    assert receipt["target_values_exposed"] is False


def test_counterfactual_outputs_preserve_contradictions_and_abstentions(tmp_path: Path) -> None:
    root = Path(__file__).parents[2]
    workflow = CounterfactualWorkflow(root, output_root=tmp_path / "counterfactuals")
    workflow.run(fixture=True)

    audit = json.loads((tmp_path / "counterfactuals" / "intervention_audit.json").read_text(encoding="utf-8"))
    contradictions = json.loads((tmp_path / "counterfactuals" / "contradiction_graph.json").read_text(encoding="utf-8"))
    language = json.loads((tmp_path / "counterfactuals" / "language_gate.json").read_text(encoding="utf-8"))
    assert audit["supported_only_predictions"] is True
    assert len(audit["rejected"]) == 3
    assert contradictions["all_edges_preserved"] is True
    assert contradictions["category_counts"]["unresolved"] == 1
    assert language["abstention_required"] is True
    assert language["universal_ranking_permitted"] is False
