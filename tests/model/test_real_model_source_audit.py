"""Tests for the strict T123 source-candidate qualification audit."""

from __future__ import annotations

from pathlib import Path

import pytest

from biointerfaceos.real_model_source_audit import (
    RealModelSourceAudit,
    RealModelSourceAuditError,
)

ROOT = Path(__file__).resolve().parents[2]


def test_source_candidates_are_recorded_but_not_promoted(tmp_path: Path) -> None:
    workflow = RealModelSourceAudit(ROOT, output_root=tmp_path / "source-candidates")

    summary = workflow.run(strict=True)
    receipt = workflow.verify()

    assert summary.source_count == 3
    assert summary.distinct_measurement_definitions == 3
    assert summary.admissible_target_count == 0
    assert receipt["status"] == "BLOCKED_SOURCE_CANDIDATES_NOT_ADMISSIBLE_AS_COMMON_TARGET"
    assert receipt["model_fitted"] is False
    assert receipt["external_ood_evaluated"] is False


def test_source_candidate_audit_requires_strict_mode(tmp_path: Path) -> None:
    workflow = RealModelSourceAudit(ROOT, output_root=tmp_path / "source-candidates")

    with pytest.raises(RealModelSourceAuditError, match="requires --strict"):
        workflow.run()


def test_source_candidate_audit_rejects_tampered_receipt(tmp_path: Path) -> None:
    workflow = RealModelSourceAudit(ROOT, output_root=tmp_path / "source-candidates")
    workflow.run(strict=True)
    decision = tmp_path / "source-candidates" / "source_candidate_decision.json"
    decision.chmod(0o600)
    decision.write_text('{"admissible_target_count":1}\n', encoding="utf-8")

    with pytest.raises(RealModelSourceAuditError, match="receipt is invalid"):
        workflow.verify()
