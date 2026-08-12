"""Regression tests for the R2 external-evaluator readiness gate."""

from __future__ import annotations

from pathlib import Path

import pytest

from biointerfaceos.independent_evaluation_workflow import (
    IndependentEvaluationError,
    IndependentEvaluationWorkflow,
)

ROOT = Path(__file__).resolve().parents[2]


def test_readiness_audit_records_t123_block_without_claiming_evaluation(tmp_path: Path) -> None:
    workflow = IndependentEvaluationWorkflow(ROOT, output_root=tmp_path / "independent-evaluation")

    summary = workflow.run(strict=True)
    verified = workflow.verify()

    assert summary.status == "BLOCKED_T123_COMPATIBLE_TARGET_REQUIRED"
    assert summary.compatible_target_count == 0
    assert summary.evaluator_receipt_verified is False
    assert summary.blocking_reason_count >= 1
    assert verified == summary


def test_readiness_audit_requires_strict_mode(tmp_path: Path) -> None:
    workflow = IndependentEvaluationWorkflow(ROOT, output_root=tmp_path / "independent-evaluation")

    with pytest.raises(IndependentEvaluationError, match="--strict"):
        workflow.run()


def test_readiness_audit_rejects_tampered_receipt(tmp_path: Path) -> None:
    output_root = tmp_path / "independent-evaluation"
    workflow = IndependentEvaluationWorkflow(ROOT, output_root=output_root)
    workflow.run(strict=True)
    report = output_root / "readiness_report.json"
    report.chmod(0o600)
    report.write_text('{"scientific_submission_ready":true}\n', encoding="utf-8")

    with pytest.raises(IndependentEvaluationError, match="receipt is invalid"):
        workflow.verify()
