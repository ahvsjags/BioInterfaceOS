"""Tests for the R2 external reproduction and editorial re-review readiness gate."""

from __future__ import annotations

from pathlib import Path

import pytest

from biointerfaceos.r2_acceptance_workflow import R2AcceptanceError, R2AcceptanceWorkflow

ROOT = Path(__file__).resolve().parents[2]


def test_r2_acceptance_records_external_evidence_blocker(tmp_path: Path) -> None:
    workflow = R2AcceptanceWorkflow(ROOT, output_root=tmp_path / "r2-acceptance")

    summary = workflow.run(strict=True)

    assert summary.status == "BLOCKED_R2_EXTERNAL_EVIDENCE_REQUIRED"
    assert summary.prerequisite_blocker_count >= 1
    assert summary.external_reproduction_verified is False
    assert summary.editorial_rereview_verified is False
    assert workflow.verify() == summary


def test_r2_acceptance_requires_strict_mode(tmp_path: Path) -> None:
    workflow = R2AcceptanceWorkflow(ROOT, output_root=tmp_path / "r2-acceptance")

    with pytest.raises(R2AcceptanceError, match="requires --strict"):
        workflow.run()


def test_r2_acceptance_rejects_tampered_receipt(tmp_path: Path) -> None:
    output_root = tmp_path / "r2-acceptance"
    workflow = R2AcceptanceWorkflow(ROOT, output_root=output_root)
    workflow.run(strict=True)
    report_path = output_root / "acceptance_readiness_report.json"
    report_path.chmod(0o600)
    report_path.write_text('{"scientific_submission_ready":true}\n', encoding="utf-8")

    with pytest.raises(R2AcceptanceError, match="receipt is invalid"):
        workflow.verify()
