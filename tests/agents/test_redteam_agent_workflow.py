import json
from pathlib import Path

from biointerfaceos.redteam_agent_workflow import RedTeamWorkflow


def test_redteam_executes_mandatory_attacks_and_passes_release_gate() -> None:
    root = Path(__file__).parents[2]
    summary = RedTeamWorkflow(root).run(all_attacks=True)

    assert summary.attacks == 5
    assert summary.executed == 5
    assert summary.detected == 2
    assert summary.blocked == 2
    assert summary.critical_findings == 0
    assert summary.remediations == 5
    assert summary.adverse_results_preserved is True
    assert summary.release_blocked is False
    assert summary.selected_pipeline == "redteam_agent"

    findings = json.loads((root / "reports/agents/redteam/redteam_findings.json").read_text(encoding="utf-8"))
    assert all(row["passed"] is True for row in findings["findings"])
    assert all(row["adverse_result_preserved"] is True for row in findings["findings"])


def test_redteam_preserves_negative_control_and_lockbox_block() -> None:
    root = Path(__file__).parents[2]
    RedTeamWorkflow(root).run(all_attacks=True)

    findings = json.loads((root / "reports/agents/redteam/redteam_findings.json").read_text(encoding="utf-8"))[
        "findings"
    ]
    by_id = {row["attack_id"]: row for row in findings}
    assert by_id["RED-NEG-001"]["observed_status"] == "CLEAN"
    assert by_id["RED-LOCKBOX-001"]["observed_status"] == "BLOCKED"
    adverse = json.loads((root / "reports/agents/redteam/adverse_results.json").read_text(encoding="utf-8"))
    assert adverse["preserved"] is True
    assert len(adverse["results"]) == 5


def test_redteam_resume_is_byte_stable() -> None:
    root = Path(__file__).parents[2]
    first = RedTeamWorkflow(root).run(all_attacks=True)
    first_bytes = first.receipt_path.read_bytes()
    resumed = RedTeamWorkflow(root).run(all_attacks=True)

    assert resumed.resumed == 1
    assert resumed.receipt_path.read_bytes() == first_bytes
