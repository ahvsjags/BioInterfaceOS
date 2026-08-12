import json
from pathlib import Path

from biointerfaceos.modeling_agent_workflow import ModelingAgentWorkflow


def test_modeling_agent_executes_valid_plan_and_rejects_hacks() -> None:
    root = Path(__file__).parents[2]
    summary = ModelingAgentWorkflow(root).run(fixture=True)

    assert summary.plans == 4
    assert summary.executable_plans == 1
    assert summary.rejected == 3
    assert summary.metric_hacking_rejected == 1
    assert summary.split_modification_rejected == 1
    assert summary.heldout_tuning_rejected == 1
    assert summary.tests_generated == 5
    assert summary.preregistration_complete is True
    assert summary.sandbox_passed is True
    assert summary.splits_unchanged is True
    assert summary.selected_pipeline == "modeling_agent"

    plans = json.loads(
        (root / "reports/agents/modeling/modeling_plans.json").read_text(encoding="utf-8")
    )
    executed = [row for row in plans["plans"] if row["status"] == "EXECUTE"]
    assert len(executed) == 1
    assert executed[0]["claim_accepted"] is False


def test_modeling_agent_preserves_split_and_records_rejections() -> None:
    root = Path(__file__).parents[2]
    ModelingAgentWorkflow(root).run(fixture=True)

    split_audit = json.loads(
        (root / "reports/agents/modeling/split_integrity_audit.json").read_text(encoding="utf-8")
    )
    assert split_audit["unchanged"] is True
    assert split_audit["before_sha256"] == split_audit["after_sha256"]
    rejections = json.loads(
        (root / "reports/agents/modeling/modeling_rejections.json").read_text(encoding="utf-8")
    )
    assert {row["rejection_reason"] for row in rejections["rejections"]} == {
        "METRIC_HACKING",
        "SPLIT_MODIFICATION",
        "HELDOUT_TUNING",
    }


def test_modeling_agent_resume_is_byte_stable() -> None:
    root = Path(__file__).parents[2]
    first = ModelingAgentWorkflow(root).run(fixture=True)
    first_bytes = first.receipt_path.read_bytes()
    resumed = ModelingAgentWorkflow(root).run(fixture=True)

    assert resumed.resumed == 1
    assert resumed.receipt_path.read_bytes() == first_bytes
