import json
from pathlib import Path

import pytest

from biointerfaceos.split_audit import SplitAuditError, SplitAuditWorkflow


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_split_audit_detects_attacks_and_blocks_lockbox(tmp_path: Path) -> None:
    summary = SplitAuditWorkflow(_root(), output_root=tmp_path / "audit").run(strict=True)

    assert summary.attacks == 10
    assert summary.detected == 9
    assert summary.blocked == 1
    assert summary.critical_findings == 0
    assert summary.clean_scan is True
    assert summary.resumed == 0

    approval = json.loads((tmp_path / "audit" / "approval_receipt.json").read_text())
    assert approval["status"] == "APPROVED"
    assert approval["lockbox_forbidden_read_blocked"] is True
    findings = json.loads((tmp_path / "audit" / "attack_findings.json").read_text())
    assert all(row["passed"] for row in findings["attacks"])


def test_split_audit_resume_is_deterministic(tmp_path: Path) -> None:
    workflow = SplitAuditWorkflow(_root(), output_root=tmp_path / "audit")
    first = workflow.run(strict=True)
    receipt_before = first.receipt_path.read_bytes()
    second = workflow.run(strict=True)

    assert second.resumed == 1
    assert second.receipt_path.read_bytes() == receipt_before


def test_split_audit_requires_fixture(tmp_path: Path) -> None:
    with pytest.raises(SplitAuditError, match="--fixture is required"):
        SplitAuditWorkflow(_root(), output_root=tmp_path / "audit").run(fixture=False)
