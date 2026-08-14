"""Tests for the R2 external reproduction and editorial re-review readiness gate."""

from __future__ import annotations

import json
import shutil
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


def test_r2_acceptance_rejects_tampered_current_t129_receipt(tmp_path: Path) -> None:
    root = tmp_path / "repository"
    shutil.copytree(ROOT / "docs", root / "docs")
    shutil.copytree(ROOT / "reports/review_round_2", root / "reports/review_round_2")
    shutil.copy2(ROOT / "TASKS.tsv", root / "TASKS.tsv")
    receipt_path = root / (
        "reports/review_round_2/t129_current_target_evidence/v1.3.0/current_target_evidence_receipt.json"
    )
    receipt_path.chmod(0o600)
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["candidate_laboratory_count"] = 3
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    workflow = R2AcceptanceWorkflow(root, output_root=root / "r2-acceptance")

    with pytest.raises(R2AcceptanceError, match="T129 current target-evidence receipt"):
        workflow.run(strict=True)


def test_r2_acceptance_rejects_tampered_receipt(tmp_path: Path) -> None:
    output_root = tmp_path / "r2-acceptance"
    workflow = R2AcceptanceWorkflow(ROOT, output_root=output_root)
    workflow.run(strict=True)
    report_path = output_root / "acceptance_readiness_report.json"
    report_path.chmod(0o600)
    report_path.write_text('{"scientific_submission_ready":true}\n', encoding="utf-8")

    with pytest.raises(R2AcceptanceError, match="receipt is invalid"):
        workflow.verify()
