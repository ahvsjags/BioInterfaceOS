"""Regression tests for the reviewer-facing R2 current-evidence status audit."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from biointerfaceos.r2_remediation_workflow import R2RemediationError, R2RemediationWorkflow

ROOT = Path(__file__).resolve().parents[2]


def test_r2_remediation_audit_preserves_open_empirical_gates(tmp_path: Path) -> None:
    workflow = R2RemediationWorkflow(ROOT, output_root=tmp_path / "remediation")

    summary = workflow.run(strict=True)

    assert summary.status == "PARTIALLY_REMEDIATED_R2_EVIDENCE_GAPS_REMAIN"
    assert summary.finding_count == 9
    assert summary.open_finding_count == 4
    assert summary.protocol_fallback_count == 3
    assert summary.bounded_pass_count == 2
    assert workflow.verify() == summary


def test_r2_remediation_requires_strict_mode(tmp_path: Path) -> None:
    workflow = R2RemediationWorkflow(ROOT, output_root=tmp_path / "remediation")

    with pytest.raises(R2RemediationError, match="requires --strict"):
        workflow.run()


def test_r2_remediation_rejects_stale_semantic_state(tmp_path: Path) -> None:
    root = tmp_path / "repository"
    required_paths = [
        "docs/review_round_2/R2_CURRENT_EVIDENCE_STATUS.md",
        *[relative for relative, _ in R2RemediationWorkflow.RECEIPTS.values()],
    ]
    for relative in required_paths:
        source = ROOT / relative
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    semantics_path = root / R2RemediationWorkflow.RECEIPTS["semantics"][0]
    semantics_path.chmod(0o600)
    payload = json.loads(semantics_path.read_text(encoding="utf-8"))
    payload["blocking_findings"] = 0
    semantics_path.write_text(json.dumps(payload), encoding="utf-8")

    workflow = R2RemediationWorkflow(root, output_root=root / "remediation")

    with pytest.raises(R2RemediationError, match="R2-04"):
        workflow.run(strict=True)


def test_r2_remediation_rejects_tampered_receipt(tmp_path: Path) -> None:
    output_root = tmp_path / "remediation"
    workflow = R2RemediationWorkflow(ROOT, output_root=output_root)
    workflow.run(strict=True)
    receipt_path = output_root / "remediation_status_receipt.json"
    receipt_path.chmod(0o600)
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["scientific_submission_ready"] = True
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")

    with pytest.raises(R2RemediationError, match="receipt is invalid"):
        workflow.verify()
