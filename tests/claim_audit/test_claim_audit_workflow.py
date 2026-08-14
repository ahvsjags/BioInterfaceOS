import json
from pathlib import Path
from typing import Any, cast

import pytest

from biointerfaceos.claim_audit_workflow import ClaimAuditError, ClaimAuditWorkflow


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def _json(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def test_claim_audit_rejects_legacy_fixture_lockbox_receipt(tmp_path: Path) -> None:
    workflow = ClaimAuditWorkflow(_root(), output_root=tmp_path / "audit")
    with pytest.raises(ClaimAuditError, match="legacy fixture lockbox receipt"):
        workflow.run(strict=True)


def test_claim_audit_rejects_positive_causal_wording() -> None:
    findings = ClaimAuditWorkflow._language_findings("The intervention causes a universal reversal.")
    assert findings


def test_claim_audit_allows_explicit_boundary_wording() -> None:
    findings = ClaimAuditWorkflow._language_findings("The package blocks causal and universal-law wording.")
    assert findings == []


def test_claim_audit_rejects_missing_evidence() -> None:
    workflow = ClaimAuditWorkflow(_root())
    resolved = workflow._resolve_evidence("paper_a", "missing_receipt.json")
    assert resolved["resolved"] is False


def test_claim_audit_rejects_tampered_receipt(tmp_path: Path) -> None:
    workflow = ClaimAuditWorkflow(_root(), output_root=tmp_path / "audit")
    with pytest.raises(ClaimAuditError, match="legacy fixture lockbox receipt"):
        workflow.run(strict=True)


def test_claim_audit_is_one_shot(tmp_path: Path) -> None:
    workflow = ClaimAuditWorkflow(_root(), output_root=tmp_path / "audit")
    with pytest.raises(ClaimAuditError, match="legacy fixture lockbox receipt"):
        workflow.run(strict=True)
