"""Regression tests for the non-promoting R2 external gate-path audit."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from biointerfaceos.r2_external_gate_path_workflow import (
    R2ExternalGatePathError,
    R2ExternalGatePathWorkflow,
)

ROOT = Path(__file__).resolve().parents[2]


def test_external_gate_path_is_ordered_and_non_promoting(tmp_path: Path) -> None:
    workflow = R2ExternalGatePathWorkflow(ROOT, output_root=tmp_path / "gate-path")

    summary = workflow.run(strict=True)

    assert summary.status == "PASS_R2_EXTERNAL_GATE_PATH_AUDIT"
    assert summary.stage_count == 6
    assert summary.command_count == 6
    assert summary.reference_count == 13
    report = json.loads(
        (tmp_path / "gate-path" / "external_gate_path_report.json").read_text(encoding="utf-8")
    )
    assert report["gate_status"] == "READY_FOR_EXTERNAL_HANDOFF_WITH_EXTERNAL_GATES_OPEN"
    assert report["scientific_submission_ready"] is False
    assert workflow.verify() == summary


def test_external_gate_path_requires_strict_mode(tmp_path: Path) -> None:
    workflow = R2ExternalGatePathWorkflow(ROOT, output_root=tmp_path / "gate-path")

    with pytest.raises(R2ExternalGatePathError, match="requires --strict"):
        workflow.run()


def test_external_gate_path_rejects_promoting_receipt(tmp_path: Path) -> None:
    output_root = tmp_path / "gate-path"
    workflow = R2ExternalGatePathWorkflow(ROOT, output_root=output_root)
    workflow.run(strict=True)
    report_path = output_root / "external_gate_path_report.json"
    report_path.chmod(0o600)
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["scientific_submission_ready"] = True
    report_path.write_text(json.dumps(report), encoding="utf-8")

    with pytest.raises(R2ExternalGatePathError, match="fail-closed|receipt is invalid"):
        workflow.verify()
