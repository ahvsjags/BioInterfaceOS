"""Tests for the strict, blocked T123 public source-discovery audit."""

from __future__ import annotations

from pathlib import Path

import pytest

from biointerfaceos.real_model_source_discovery_workflow import (
    RealModelSourceDiscoveryError,
    RealModelSourceDiscoveryWorkflow,
)

ROOT = Path(__file__).resolve().parents[2]


def test_source_discovery_preserves_rejections_and_lockbox_boundary(tmp_path: Path) -> None:
    workflow = RealModelSourceDiscoveryWorkflow(ROOT, output_root=tmp_path / "source-discovery")

    summary = workflow.run(strict=True)
    receipt = workflow.verify()

    assert summary.candidate_count == 3
    assert summary.rejected_candidate_count == 2
    assert summary.reserved_lockbox_candidate_count == 1
    assert receipt["status"] == "BLOCKED_NO_ADMISSIBLE_T123_TARGET_FOUND"
    assert receipt["admitted_candidate_count"] == 0
    assert receipt["model_fitted"] is False


def test_source_discovery_requires_strict_mode(tmp_path: Path) -> None:
    workflow = RealModelSourceDiscoveryWorkflow(ROOT, output_root=tmp_path / "source-discovery")

    with pytest.raises(RealModelSourceDiscoveryError, match="requires --strict"):
        workflow.run()


def test_source_discovery_rejects_tampered_receipt(tmp_path: Path) -> None:
    workflow = RealModelSourceDiscoveryWorkflow(ROOT, output_root=tmp_path / "source-discovery")
    workflow.run(strict=True)
    decision = tmp_path / "source-discovery" / "source_discovery_decision.json"
    decision.chmod(0o600)
    decision.write_text('{"admitted_candidate_count":1}\n', encoding="utf-8")

    with pytest.raises(RealModelSourceDiscoveryError, match="receipt is invalid"):
        workflow.verify()
