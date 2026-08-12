import json
from pathlib import Path
from typing import Any, cast

import pytest

from biointerfaceos.lockbox_audit_workflow import LockboxAuditError, LockboxAuditWorkflow


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def _json(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def test_audit_maps_all_predictions_and_preserves_boundaries(tmp_path: Path) -> None:
    workflow = LockboxAuditWorkflow(_root(), output_root=tmp_path / "audit")
    summary = workflow.run(strict=True)
    assert summary.prediction_count == 5
    assert summary.replicated == 2
    assert summary.refuted == 1
    assert summary.inconclusive == 2
    assert summary.abstentions == 2
    assert summary.claim_count == 8
    verified = workflow.verify()
    assert verified.receipt_path.read_bytes() == summary.receipt_path.read_bytes()
    transitions = _json(tmp_path / "audit" / "claim_transitions.json")["transitions"]
    prediction_rows = [row for row in transitions if row["prediction_id"]]
    assert {row["postlock_status"] for row in prediction_rows} == {
        "REPLICATED",
        "REFUTED",
        "INCONCLUSIVE",
    }
    assert all(
        not row["threshold_changed"] and not row["prediction_rewritten"] for row in transitions
    )


def test_audit_rejects_duplicate_prediction_ids() -> None:
    table = _json(_root() / "release/manuscripts/paper_c_prelock/prediction_table.json")
    table["predictions"][-1]["prediction_id"] = "P1"
    with pytest.raises(LockboxAuditError, match="unique or complete"):
        LockboxAuditWorkflow._validate_prediction_table(table)


def test_audit_rejects_threshold_or_prediction_mutation() -> None:
    table = _json(_root() / "release/manuscripts/paper_c_prelock/prediction_table.json")
    table["predictions"][0]["status"] = "PREDICTED_AFTER_LOCKBOX"
    with pytest.raises(LockboxAuditError, match="changed after pre-lock"):
        LockboxAuditWorkflow._validate_prediction_table(table)


def test_audit_rejects_tampered_audit_receipt(tmp_path: Path) -> None:
    workflow = LockboxAuditWorkflow(_root(), output_root=tmp_path / "audit")
    workflow.run(strict=True)
    receipt_path = tmp_path / "audit" / "audit_receipt.json"
    receipt_path.chmod(0o644)
    receipt = _json(receipt_path)
    receipt["refuted"] = 0
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    with pytest.raises(LockboxAuditError, match="summary differs"):
        workflow.verify()


def test_audit_rejects_protected_value_contamination() -> None:
    result_path = (
        _root() / "reports/lockbox/evaluation/bioif-lockbox-eval-v1.0.0/evaluation_results.json"
    )
    log_path = _root() / "reports/lockbox/evaluation/bioif-lockbox-eval-v1.0.0/operation_log.json"
    receipt_path = (
        _root() / "reports/lockbox/evaluation/bioif-lockbox-eval-v1.0.0/first_run_receipt.json"
    )
    results = _json(result_path)
    results["rows"][0]["raw_value"] = 0.0
    with pytest.raises(LockboxAuditError):
        LockboxAuditWorkflow._verify_evaluation(
            {
                "evaluation results": results,
                "operation log": _json(log_path),
                "first-run receipt": _json(receipt_path),
            }
        )


def test_audit_is_one_shot(tmp_path: Path) -> None:
    workflow = LockboxAuditWorkflow(_root(), output_root=tmp_path / "audit")
    workflow.run(strict=True)
    with pytest.raises(LockboxAuditError, match="already executed"):
        workflow.run(strict=True)
