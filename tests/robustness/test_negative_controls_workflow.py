import json
from pathlib import Path

from biointerfaceos.negative_controls_workflow import NegativeControlsWorkflow


def test_negative_controls_detect_leaks_and_pass_strict_gate(tmp_path: Path) -> None:
    root = Path(__file__).parents[2]
    workflow = NegativeControlsWorkflow(root, output_root=tmp_path / "negative")

    first = workflow.run(strict=True)
    second = workflow.run(strict=True)

    assert first.attacks == 9
    assert first.expected_failures == 5
    assert first.detected == 6
    assert first.critical_leaks == 0
    assert first.duplicate_hits == 2
    assert first.strict_pass is True
    assert first.claim_status == "ATTACKS_CLEAN"
    assert first.resumed == 0
    assert second.resumed == 1

    receipt = json.loads(first.receipt_path.read_text(encoding="utf-8"))
    assert receipt["lockbox_clean"] is True
    assert receipt["target_values_exposed"] is False


def test_negative_controls_preserve_rollback_policy_and_duplicate_audit(tmp_path: Path) -> None:
    root = Path(__file__).parents[2]
    workflow = NegativeControlsWorkflow(root, output_root=tmp_path / "negative")
    workflow.run(strict=True)

    rollback = json.loads((tmp_path / "negative" / "rollback_claim_gate.json").read_text(encoding="utf-8"))
    duplicates = json.loads((tmp_path / "negative" / "duplicate_audit.json").read_text(encoding="utf-8"))
    assert rollback["release_action"] == "CLEAN_RELEASE_RETAINED"
    assert rollback["critical_leaks"] == 0
    assert duplicates["duplicate_hits"] == 2
