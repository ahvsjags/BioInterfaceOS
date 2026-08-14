import json
from pathlib import Path
from typing import Any, cast

import pytest

from biointerfaceos.lockbox_audit_workflow import LockboxAuditError, LockboxAuditWorkflow


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def _json(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def test_audit_rejects_legacy_fixture_results_for_new_scientific_audit(tmp_path: Path) -> None:
    workflow = LockboxAuditWorkflow(_root(), output_root=tmp_path / "audit")
    with pytest.raises(LockboxAuditError, match="legacy fixture evaluation"):
        workflow.run(strict=True)


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
    with pytest.raises(LockboxAuditError, match="legacy fixture evaluation"):
        workflow.run(strict=True)


def test_audit_rejects_protected_value_contamination() -> None:
    result_path = _root() / "reports/lockbox/evaluation/bioif-lockbox-eval-v1.0.0/evaluation_results.json"
    log_path = _root() / "reports/lockbox/evaluation/bioif-lockbox-eval-v1.0.0/operation_log.json"
    receipt_path = _root() / "reports/lockbox/evaluation/bioif-lockbox-eval-v1.0.0/first_run_receipt.json"
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
    with pytest.raises(LockboxAuditError, match="legacy fixture evaluation"):
        workflow.run(strict=True)
