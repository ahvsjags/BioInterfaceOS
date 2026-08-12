"""Tests for the strict R2 real-model compatibility gate."""

from __future__ import annotations

from pathlib import Path

import pytest

from biointerfaceos.real_model_compatibility_workflow import (
    RealModelCompatibilityError,
    RealModelCompatibilityWorkflow,
)

ROOT = Path(__file__).resolve().parents[2]


def test_real_model_compatibility_records_blocked_state(tmp_path: Path) -> None:
    workflow = RealModelCompatibilityWorkflow(ROOT, output_root=tmp_path / "compatibility")

    summary = workflow.run(strict=True)
    receipt = workflow.verify()

    assert summary.source_count == 3
    assert summary.endpoint_count == 3
    assert summary.compatible_target_count == 0
    assert receipt["status"] == "BLOCKED_NO_COMPATIBLE_CROSS_STUDY_TARGET"
    assert receipt["model_fitted"] is False
    assert receipt["external_ood_evaluated"] is False


def test_real_model_compatibility_requires_strict_mode(tmp_path: Path) -> None:
    workflow = RealModelCompatibilityWorkflow(ROOT, output_root=tmp_path / "compatibility")

    with pytest.raises(RealModelCompatibilityError, match="requires --strict"):
        workflow.run()


def test_real_model_compatibility_rejects_tampered_receipt(tmp_path: Path) -> None:
    workflow = RealModelCompatibilityWorkflow(ROOT, output_root=tmp_path / "compatibility")
    workflow.run(strict=True)
    decision = tmp_path / "compatibility" / "compatibility_decision.json"
    decision.chmod(0o600)
    decision.write_text('{"status":"READY_FOR_FROZEN_REAL_MODEL_EVALUATION"}\n', encoding="utf-8")

    with pytest.raises(RealModelCompatibilityError, match="receipt is invalid"):
        workflow.verify()
