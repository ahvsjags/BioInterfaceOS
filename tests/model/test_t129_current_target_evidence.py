"""Tests for the consolidated, fail-closed T129 current evidence gate."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from biointerfaceos.t129_current_target_evidence import (
    T129CurrentTargetEvidenceError,
    T129CurrentTargetEvidenceWorkflow,
)

ROOT = Path(__file__).resolve().parents[2]


def test_audit_binds_all_current_t129_tranches_without_target_promotion(tmp_path: Path) -> None:
    workflow = T129CurrentTargetEvidenceWorkflow(ROOT, output_root=tmp_path / "current")

    summary = workflow.run(strict=True)
    receipt = json.loads(summary.receipt_path.read_text(encoding="utf-8"))

    assert summary.candidate_source_count == 8
    assert summary.candidate_laboratory_count == 5
    assert summary.verified_source_asset_count == 31
    assert receipt["status"] == "BLOCKED_NO_CROSS_LAB_COMMON_NUMERIC_MATERIAL_TARGET"
    assert receipt["target_status"] == "NOT_FROZEN"
    assert workflow.verify() == summary


def test_audit_requires_strict_mode(tmp_path: Path) -> None:
    workflow = T129CurrentTargetEvidenceWorkflow(ROOT, output_root=tmp_path / "current")

    with pytest.raises(T129CurrentTargetEvidenceError, match="requires --strict"):
        workflow.run()


def test_audit_rejects_tampered_output_receipt(tmp_path: Path) -> None:
    workflow = T129CurrentTargetEvidenceWorkflow(ROOT, output_root=tmp_path / "current")
    summary = workflow.run(strict=True)
    summary.receipt_path.chmod(0o600)
    receipt = json.loads(summary.receipt_path.read_text(encoding="utf-8"))
    receipt["model_use"] = "ALLOWED"
    summary.receipt_path.write_text(json.dumps(receipt), encoding="utf-8")

    with pytest.raises(
        T129CurrentTargetEvidenceError,
        match="current T129 target evidence receipt",
    ):
        workflow.verify()
