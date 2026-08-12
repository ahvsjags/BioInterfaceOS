import json
from pathlib import Path
from typing import Any, cast

import pytest

from biointerfaceos.claim_audit_workflow import ClaimAuditError, ClaimAuditWorkflow


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def _json(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def test_claim_audit_produces_complete_report_and_revised_manuscripts(tmp_path: Path) -> None:
    workflow = ClaimAuditWorkflow(_root(), output_root=tmp_path / "audit")
    report = workflow.run(strict=True)
    assert report["claim_count"] == 24
    assert report["submission_blockers"] == 0
    assert report["unresolved_evidence"] == 0
    assert workflow.verify()["status"] == "VALID_FINAL_CLAIM_AUDIT"
    assert len(list((tmp_path / "audit" / "revised_manuscripts").glob("*.md"))) == 3


def test_claim_audit_rejects_positive_causal_wording() -> None:
    findings = ClaimAuditWorkflow._language_findings(
        "The intervention causes a universal reversal."
    )
    assert findings


def test_claim_audit_allows_explicit_boundary_wording() -> None:
    findings = ClaimAuditWorkflow._language_findings(
        "The package blocks causal and universal-law wording."
    )
    assert findings == []


def test_claim_audit_rejects_missing_evidence() -> None:
    workflow = ClaimAuditWorkflow(_root())
    resolved = workflow._resolve_evidence("paper_a", "missing_receipt.json")
    assert resolved["resolved"] is False


def test_claim_audit_rejects_tampered_receipt(tmp_path: Path) -> None:
    workflow = ClaimAuditWorkflow(_root(), output_root=tmp_path / "audit")
    workflow.run(strict=True)
    receipt_path = tmp_path / "audit" / "audit_receipt.json"
    receipt = _json(receipt_path)
    receipt_path.chmod(0o644)
    receipt["critical_findings"] = 1
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    with pytest.raises(ClaimAuditError, match="critical findings"):
        workflow.verify()


def test_claim_audit_is_one_shot(tmp_path: Path) -> None:
    workflow = ClaimAuditWorkflow(_root(), output_root=tmp_path / "audit")
    workflow.run(strict=True)
    with pytest.raises(ClaimAuditError, match="already executed"):
        workflow.run(strict=True)
