import json
from pathlib import Path

from biointerfaceos.ablation_workflow import AblationWorkflow


def test_ablation_matrix_uses_same_pairs_and_reports_effects(tmp_path: Path) -> None:
    root = Path(__file__).parents[2]
    workflow = AblationWorkflow(root, output_root=tmp_path / "ablations")

    first = workflow.run(all_ablations=True)
    second = workflow.run(all_ablations=True)

    assert first.comparisons == 5
    assert first.rows == 20
    assert first.same_splits is True
    assert first.same_budget is True
    assert first.mean_effect > 0
    assert first.interval_records == 5
    assert first.calibration_records == 5
    assert first.ood_records == 5
    assert first.missing_ablations == 1
    assert first.claim_blocks == 0
    assert first.resumed == 0
    assert second.resumed == 1

    receipt = json.loads(first.receipt_path.read_text(encoding="utf-8"))
    assert receipt["lockbox_clean"] is True
    assert receipt["target_values_exposed"] is False

    gate = json.loads((tmp_path / "ablations" / "claim_gate.json").read_text(encoding="utf-8"))
    assert gate["status"] == "PASS"
    assert gate["same_splits"] is True
    assert gate["same_budget"] is True


def test_ablation_missing_interface_is_explicitly_justified(tmp_path: Path) -> None:
    root = Path(__file__).parents[2]
    workflow = AblationWorkflow(root, output_root=tmp_path / "ablations")
    workflow.run(all_ablations=True)

    missing = json.loads(
        (tmp_path / "ablations" / "missingness_ledger.json").read_text(encoding="utf-8")
    )
    assert missing["records"][0]["result"] == "BLOCKED_EXPECTED"
    assert missing["records"][0]["interface_test"] == "network_disabled"
    assert missing["records"][0]["claim_blocked"] is False
