import json
from pathlib import Path

from biointerfaceos.hypothesis_agent_workflow import HypothesisAgentWorkflow


def test_hypothesis_agent_gates_candidates_and_preserves_exploratory_status() -> None:
    root = Path(__file__).parents[2]
    summary = HypothesisAgentWorkflow(root).run(fixture=True)

    assert summary.proposals == 5
    assert summary.valid_proposals == 2
    assert summary.rejected == 3
    assert summary.duplicates_rejected == 1
    assert summary.falsifiable == 4
    assert summary.formalized == 5
    assert summary.evidence_linked == 4
    assert summary.schema_valid is True
    assert summary.lockbox_clean is True
    assert summary.claims_auto_accepted is False
    assert summary.selected_pipeline == "hypothesis_agent"
    payload = json.loads(summary.receipt_path.read_text(encoding="utf-8"))
    assert payload["target_values_exposed"] is False

    proposals = json.loads((root / "reports/agents/hypothesis/hypothesis_proposals.json").read_text(encoding="utf-8"))
    assert all(row["status"] == "EXPLORATORY_PROPOSAL" for row in proposals["proposals"])
    assert all(row["claim_accepted"] is False for row in proposals["proposals"])


def test_hypothesis_agent_records_rejections_and_lockbox_scan() -> None:
    root = Path(__file__).parents[2]
    HypothesisAgentWorkflow(root).run(fixture=True)

    rejections = json.loads((root / "reports/agents/hypothesis/hypothesis_rejections.json").read_text(encoding="utf-8"))
    reasons = {row["rejection_reason"] for row in rejections["rejections"]}
    assert reasons == {
        "DUPLICATE_NORMALIZED_HYPOTHESIS",
        "NOT_FALSIFIABLE",
        "UNGROUNDED_EVIDENCE",
    }
    lockbox = json.loads((root / "reports/agents/hypothesis/lockbox_scan.json").read_text(encoding="utf-8"))
    assert lockbox["clean"] is True
    assert lockbox["findings"] == []
    assert lockbox["locked_payload_opened"] is False


def test_hypothesis_agent_resume_is_byte_stable() -> None:
    root = Path(__file__).parents[2]
    first = HypothesisAgentWorkflow(root).run(fixture=True)
    first_bytes = first.receipt_path.read_bytes()
    resumed = HypothesisAgentWorkflow(root).run(fixture=True)

    assert resumed.resumed == 1
    assert resumed.receipt_path.read_bytes() == first_bytes
