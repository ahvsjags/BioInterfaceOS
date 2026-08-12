import json
from pathlib import Path

from biointerfaceos.candidate_audit_workflow import CandidateAuditWorkflow


def test_candidate_audit_deduplicates_and_gates_supported_cards(tmp_path: Path) -> None:
    root = Path(__file__).parents[2]
    workflow = CandidateAuditWorkflow(root, output_root=tmp_path / "candidates")

    first = workflow.run(fixture=True)
    second = workflow.run(fixture=True)

    assert first.candidates == 7
    assert first.unique_candidates == 6
    assert first.duplicate_candidates == 1
    assert first.supported_candidates == 3
    assert first.rejected_candidates == 4
    assert first.temporal_matches == 2
    assert first.unresolved_matches == 1
    assert first.abstentions == 3
    assert first.selected_wording == "exploratory_supported"
    assert first.resumed == 0
    assert second.resumed == 1

    receipt = json.loads(first.receipt_path.read_text(encoding="utf-8"))
    assert receipt["lockbox_clean"] is True
    assert receipt["target_values_exposed"] is False

    cards = json.loads(
        (tmp_path / "candidates" / "candidate_cards.json").read_text(encoding="utf-8")
    )
    assert len(cards["cards"]) == 3
    assert all(card["allowed_wording"] == "exploratory_supported" for card in cards["cards"])


def test_candidate_audit_temporal_matches_never_change_selection(tmp_path: Path) -> None:
    root = Path(__file__).parents[2]
    workflow = CandidateAuditWorkflow(root, output_root=tmp_path / "candidates")
    workflow.run(fixture=True)

    retrospective = json.loads(
        (tmp_path / "candidates" / "retrospective_validation.json").read_text(encoding="utf-8")
    )
    abstentions = json.loads(
        (tmp_path / "candidates" / "abstention_ledger.json").read_text(encoding="utf-8")
    )
    assert retrospective["policy"] == "descriptive_only"
    assert retrospective["used_for_selection"] is False
    assert all(item["used_for_selection"] is False for item in retrospective["matches"])
    assert {item["reasons"][0] for item in abstentions["entries"]} == {
        "high_applicability_domain_distance",
        "perturbation_instability",
        "unsafe_candidate",
    }
